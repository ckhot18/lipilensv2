import logging
from pathlib import Path
from typing import Any, Callable

import torch
from PIL import Image

from backend.config import BASE_MODEL_NAME, LORA_ADAPTER_NAME
from backend.services.transcription.inference import TranscriptionResult, TranscriptionService

logger = logging.getLogger(__name__)

# Singleton instances to avoid reloading
_model = None
_processor = None
# The pixel budget the resident processor was built with. Rebuilding the
# processor is milliseconds; rebuilding the model is ~85 s, so a budget change
# must not cost the model.
_processor_pixels = None
# What the resident weights were actually built with. An evaluation sweep that
# changes dtype or LoRA merging MUST reload, otherwise the next arm silently
# inherits the previous arm's weights.
_model_dtype = None
_model_merged = None


def model_matches(dtype: str, merged: bool) -> bool:
    """True when the resident model was built with these settings."""
    return (_model is not None
            and _model_dtype == dtype
            and _model_merged == merged)


def invalidate_model() -> None:
    """Drop the resident model so the next call rebuilds it."""
    global _model, _processor, _processor_pixels, _model_dtype, _model_merged
    _model = None
    _processor = None
    _processor_pixels = None
    _model_dtype = None
    _model_merged = None


def _emit(on_progress: Callable[[dict[str, Any]], None] | None,
          **event: Any) -> None:
    if on_progress is not None:
        on_progress(event)


def _prepare_image(image: "Image.Image") -> "Image.Image":
    """Upscale the page so the visual-token budget buys more tokens/character.

    `max_pixels` only ever *downscales*: a 1268x463 page is 587k px, already
    under the 1280*28*28 budget, so raising the budget changes nothing for a
    whole page. Resampling first is what actually spends the budget on more
    tokens. LANCZOS keeps stroke edges sharper than the bicubic used for
    segmentation crops.
    """
    from backend import config as app_config

    scale = float(app_config.MODEL_UPSCALE or 1.0)
    if scale <= 1.01:
        return image
    w, h = image.size
    return image.resize((max(1, int(w * scale)), max(1, int(h * scale))),
                        Image.LANCZOS)


class LocalQwenTranscriptionService(TranscriptionService):
    # When this service is wrapped by LineSegmentedTranscriptionService the
    # wrapper emits per-line events and knows the line count; only a bare
    # service has to announce an unmeasured single step.
    reports_own_progress = True

    def __init__(self, load_on_init: bool = False):
        if load_on_init:
            self._load_model()

    def _load_model(self, on_progress=None):
        global _model, _processor, _processor_pixels, _model_dtype, _model_merged

        from backend import config as app_config

        want_dtype = "float16" if app_config.COMPUTE_DTYPE == "float16" \
            else "bfloat16"
        want_merged = bool(app_config.MERGE_LORA)
        if _model is not None and _processor is not None:
            if not model_matches(want_dtype, want_merged):
                # dtype or merging changed: the resident weights no longer
                # match the config, so they must not be reused.
                logger.info("Model settings changed (%s/%s -> %s/%s); reloading.",
                            _model_dtype, _model_merged, want_dtype, want_merged)
                invalidate_model()
            else:
                # The processor carries the pixel budget, and changing the
                # budget is a research lever (token count vs aspect-ratio
                # distortion). Rebuilding it is cheap; reloading the model is not.
                if _processor_pixels != int(app_config.MAX_MODEL_PIXELS):
                    from transformers import AutoProcessor

                    logger.info("Rebuilding processor: max_pixels %s -> %s",
                                _processor_pixels, app_config.MAX_MODEL_PIXELS)
                    _processor = AutoProcessor.from_pretrained(
                        BASE_MODEL_NAME,
                        max_pixels=int(app_config.MAX_MODEL_PIXELS))
                    _processor_pixels = int(app_config.MAX_MODEL_PIXELS)
                return

        logger.info(f"Loading local model: base={BASE_MODEL_NAME}, adapter={LORA_ADAPTER_NAME}")
        # Weight loading is the first ~95 s of a cold run and happens with no
        # output at all; the UI needs to show that something is happening.
        _emit(on_progress, stage="loading_model")

        try:
            from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
            from peft import PeftModel

            compute = torch.float16 if want_dtype == "float16" else torch.bfloat16
            # BitsAndBytes configuration for 4-bit quantization (to fit in 4GB VRAM)
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=compute,
            )

            base_model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                BASE_MODEL_NAME,
                quantization_config=bnb_config,
                device_map="auto"
            )

            _model = PeftModel.from_pretrained(base_model, LORA_ADAPTER_NAME)
            if want_merged:
                # Folds the adapter into the base weights, so inference runs a
                # single dequantised matmul per layer instead of base+LoRA.
                # NOTE: on a 4-bit base this folds the delta into already
                # NF4-quantised weights, which is not numerically sound.
                _model = _model.merge_and_unload()
                logger.info("LoRA merged into base weights.")
            _model.eval()
            _model_dtype = want_dtype
            _model_merged = want_merged

            _processor = AutoProcessor.from_pretrained(
                BASE_MODEL_NAME, max_pixels=int(app_config.MAX_MODEL_PIXELS))
            _processor_pixels = int(app_config.MAX_MODEL_PIXELS)

            logger.info("Local model loaded successfully.")
            _emit(on_progress, stage="model_ready")

            # Update health state
            from backend.api.health import set_model_loaded
            set_model_loaded(True)

        except Exception as e:
            logger.error(f"Failed to load local model: {e}")
            from backend.api.health import set_load_failed
            set_load_failed()
            raise

    def transcribe(self, image_path: str | Path, prompt: str,
                   on_progress=None) -> TranscriptionResult:
        self._load_model(on_progress)

        # Emitted here, after the load, so it is not overwritten by the
        # loading stages. One image is one indivisible unit of work, so there
        # is no denominator: the UI sweeps rather than sitting at 0% looking
        # hung, which is what it did before this existed.
        if self.reports_own_progress:
            _emit(on_progress, stage="reading", lines_total=0,
                  message="Reading the page as one block")

        global _model, _processor
        from backend import config as app_config

        logger.info(f"Transcribing image locally: {image_path}")
        image = _prepare_image(Image.open(image_path).convert("RGB"))
        
        messages = [{
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt},
            ],
        }]
        
        text_in = _processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = _processor(text=[text_in], images=[image], return_tensors="pt").to(_model.device)
        
        # Read the knobs at call time so an evaluation sweep can vary them
        # without paying the ~65 s model load again.
        gen_kwargs: dict[str, Any] = {
            "max_new_tokens": int(app_config.MAX_NEW_TOKENS),
            "do_sample": False,
        }
        penalty = float(app_config.REPETITION_PENALTY)
        if penalty > 1.0:
            gen_kwargs["repetition_penalty"] = penalty
        beams = int(getattr(app_config, "NUM_BEAMS", 1) or 1)
        if beams > 1:
            # Greedy and beam search are mutually exclusive in HF.
            gen_kwargs.pop("do_sample", None)
            gen_kwargs["num_beams"] = beams
            gen_kwargs["early_stopping"] = True

        with torch.inference_mode():
            out = _model.generate(**inputs, **gen_kwargs)

        result_text = _processor.batch_decode(
            out[:, inputs["input_ids"].shape[1]:], skip_special_tokens=True
        )[0].strip()

        return TranscriptionResult(
            text=result_text,
            model_name=f"{BASE_MODEL_NAME} + {LORA_ADAPTER_NAME}",
            inference_mode="local",
            raw_output=result_text
        )
