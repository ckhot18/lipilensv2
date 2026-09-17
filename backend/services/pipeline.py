"""Phase 4+: full non-persisted pipeline — image in, transcription out.

Wires restoration (services.restoration) and transcription
(services.transcription, local or Colab via INFERENCE_MODE) behind one
in-process function. Phase 5/6 build on this: PipelineOutput carries every
field the archive tables and API responses need, so routes stay thin.

Failure semantics (PROJECT_GUIDE.md Sec. 23):
- restoration stage throws -> fall back to the ORIGINAL image, record a
  warning, continue (never fail the whole call for a restoration bug).
- transcription throws -> propagate (caller decides: API returns 503).

Efficiency:
- Transcription service instances are reused per INFERENCE_MODE (no
  re-instantiation per call; model weights still load exactly once via the
  service's own singleton logic).
- Opt-in transcription disk cache (`cache_dir`): keyed by
  sha256(image bytes + config dict + prompt). Safe because generation is
  greedy/deterministic — same key always means the same output. Restoration
  still re-runs (cheap, ~0.2 s) so the restored file always exists for display.
  Cache hits are logged at INFO so experiment logs can cite them.
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.services.restoration.pipeline import PRESET_CONFIGS, run_pipeline
from backend.services.transcription.inference import (
    TranscriptionService,
    get_transcription_service,
)
from backend.utils.image_io import load_image, save_image

logger = logging.getLogger(__name__)

DEFAULT_PROMPT = (
    "This image contains handwritten text in Modi script, a historical cursive "
    "script used to write the Marathi language. "
    "Transliterate the text in this image into Devanagari script. "
    "Output only the Devanagari text, with no explanation."
)


@dataclass
class PipelineOutput:
    """Result of one full pipeline run (nothing persisted).

    Field-for-field aligned with what Phase 5 stores
    (manuscripts + transcriptions + preprocessing_configs) and what Phase 6
    returns from POST /api/manuscripts — see to_dict().
    """

    config_name: str
    config_dict: dict[str, Any]
    source_image: str
    image_sha256: str
    restored_image_path: str
    transcription: str
    model_name: str
    inference_mode: str
    prompt: str
    restore_seconds: float
    transcribe_seconds: float
    restoration_warning: str | None = None
    cache_hit: bool = False

    def to_dict(self) -> dict[str, Any]:
        """JSON-safe dict for API responses and experiment logs."""
        return {
            "config_name": self.config_name,
            "config_dict": self.config_dict,
            "source_image": self.source_image,
            "image_sha256": self.image_sha256,
            "restored_image_path": self.restored_image_path,
            "transcription": self.transcription,
            "model_name": self.model_name,
            "inference_mode": self.inference_mode,
            "prompt": self.prompt,
            "restore_seconds": self.restore_seconds,
            "transcribe_seconds": self.transcribe_seconds,
            "restoration_warning": self.restoration_warning,
            "cache_hit": self.cache_hit,
        }


# ---------------------------------------------------------------------------
# Service reuse (one instance per mode per process)
# ---------------------------------------------------------------------------
_service_cache: dict[str, TranscriptionService] = {}


def _get_service() -> TranscriptionService:
    from backend import config as app_config

    mode = app_config.INFERENCE_MODE.lower().strip()
    if mode not in _service_cache:
        _service_cache[mode] = get_transcription_service()
    return _service_cache[mode]


def clear_service_cache() -> None:
    """Drop reused service instances (tests, mode switches)."""
    _service_cache.clear()


# ---------------------------------------------------------------------------
# Transcription disk cache
# ---------------------------------------------------------------------------
def _cache_key(image_bytes: bytes, config_dict: dict[str, Any],
               prompt: str, mode: str) -> str:
    from backend import config as app_config

    h = hashlib.sha256()
    h.update(image_bytes)
    h.update(json.dumps(config_dict, sort_keys=True).encode())
    h.update(prompt.encode())
    h.update(mode.encode())  # local vs colab outputs must never share cache
    # A server-side model update must invalidate the cache.
    h.update(app_config.BASE_MODEL_REVISION.encode())
    h.update(app_config.LORA_REVISION.encode())
    return h.hexdigest()[:32]


def _cache_path(cache_dir: Path, key: str) -> Path:
    return cache_dir / f"tcache_{key}.json"


def run_full_pipeline(
    image_path: str | Path,
    config_name: str = "full_restoration",
    output_dir: str | Path | None = None,
    prompt: str = DEFAULT_PROMPT,
    cache_dir: str | Path | None = None,
) -> PipelineOutput:
    """Run restoration then transcription on one image.

    The model ALWAYS receives the restored image file (never the original
    object in memory) — passing the wrong variant is the classic Phase-4 bug.
    """
    if config_name not in PRESET_CONFIGS:
        raise ValueError(
            f"Unknown config '{config_name}'. Available: {list(PRESET_CONFIGS)}"
        )
    image_path = Path(image_path)
    config = PRESET_CONFIGS[config_name]
    config_dict = config.to_dict()

    raw_bytes = image_path.read_bytes()
    image_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    source = load_image(image_path)

    # --- restoration (graceful fallback per Sec. 23) ----------------------
    t0 = time.perf_counter()
    warning = None
    try:
        result = run_pipeline(source, config)
        restored = result.final_image
    except Exception as exc:  # noqa: BLE001
        logger.exception("Restoration '%s' failed; falling back to original",
                         config_name)
        warning = f"restoration '{config_name}' failed ({exc}); used original"
        restored = source
    restore_seconds = time.perf_counter() - t0

    # --- persist restored image to disk (model consumes a FILE) -----------
    # Default scratch lives under data/outputs (NOT served by /files).
    out_dir = (Path(output_dir) if output_dir
               else Path("data/outputs/_pipeline"))
    restored_path = save_image(
        restored, out_dir / f"{image_path.stem}_{config_name}.png"
    )

    # --- transcription on the RESTORED file (cached when asked) -----------
    mode = _current_mode_label()
    cache_hit = False
    key = _cache_key(raw_bytes, config_dict, prompt, mode)
    cached_text = cached_model = None
    if cache_dir is not None:
        cpath = _cache_path(Path(cache_dir), key)
        if cpath.exists():
            try:
                payload = json.loads(cpath.read_text(encoding="utf-8"))
                cached_text, cached_model = (payload["text"],
                                             payload["model_name"])
            except (json.JSONDecodeError, KeyError, OSError):
                logger.warning("Ignoring corrupt cache file %s", cpath)

    t1 = time.perf_counter()
    if cached_text is not None:
        cache_hit = True
        text, model_name = cached_text, cached_model
        inference_mode = mode
        logger.info("Transcription cache HIT (%s) — model call skipped", key)
    else:
        service = _get_service()
        tresult = service.transcribe(restored_path, prompt)
        text, model_name = tresult.text, tresult.model_name
        inference_mode = tresult.inference_mode
        if cache_dir is not None:
            cpath = _cache_path(Path(cache_dir), key)
            cpath.parent.mkdir(parents=True, exist_ok=True)
            cpath.write_text(json.dumps(
                {"text": text, "model_name": model_name},
                ensure_ascii=False), encoding="utf-8")
    transcribe_seconds = time.perf_counter() - t1

    logger.info("Pipeline '%s' done: restore=%.2fs transcribe=%.2fs mode=%s%s",
                config_name, restore_seconds, transcribe_seconds,
                inference_mode, " (cache hit)" if cache_hit else "")
    return PipelineOutput(
        config_name=config_name,
        config_dict=config_dict,
        source_image=str(image_path),
        image_sha256=image_sha256,
        restored_image_path=str(restored_path),
        transcription=text,
        model_name=model_name,
        inference_mode=inference_mode,
        prompt=prompt,
        restore_seconds=round(restore_seconds, 2),
        transcribe_seconds=round(transcribe_seconds, 1),
        restoration_warning=warning,
        cache_hit=cache_hit,
    )


def _current_mode_label() -> str:
    from backend import config as app_config

    return app_config.INFERENCE_MODE.lower().strip()
