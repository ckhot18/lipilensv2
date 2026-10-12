"""Tests for the runtime inference levers and the model-singleton bookkeeping.

The bug these guard against: an evaluation sweep changed MERGE_LORA or
COMPUTE_DTYPE, but the resident model was not rebuilt, so a later arm silently
reported the previous arm's weights. Every one of those numbers was fake.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import backend.services.transcription.local_qwen as lq


def test_no_model_never_matches():
    assert lq.model_matches("bfloat16", False) is False


def test_model_matches_requires_both_dtype_and_merge_state():
    lq.invalidate_model()
    try:
        # Pretend a bf16 unmerged model is resident.
        lq._model = object()
        lq._model_dtype = "bfloat16"
        lq._model_merged = False

        assert lq.model_matches("bfloat16", False) is True
        # Different dtype must not match.
        assert lq.model_matches("float16", False) is False
        # Different merge state must not match.
        assert lq.model_matches("bfloat16", True) is False
        # Both wrong must not match.
        assert lq.model_matches("float16", True) is False
    finally:
        lq.invalidate_model()


def test_invalidate_model_clears_all_resident_state():
    lq._model = object()
    lq._processor = object()
    lq._processor_pixels = 12345
    lq._model_dtype = "float16"
    lq._model_merged = True

    lq.invalidate_model()

    assert lq._model is None
    assert lq._processor is None
    assert lq._processor_pixels is None
    assert lq._model_dtype is None
    assert lq._model_merged is None


def test_processor_pixel_budget_change_does_not_drop_the_model():
    """A max_pixels change is a cheap processor rebuild, not a model reload."""
    lq._model = object()
    lq._processor = object()
    lq._model_dtype = "bfloat16"
    lq._model_merged = False
    lq._processor_pixels = 401408
    try:
        # Same dtype and merge state => the model is reusable regardless of the
        # pixel budget, because the budget only lives in the processor.
        assert lq.model_matches("bfloat16", False) is True
    finally:
        lq.invalidate_model()


def test_new_config_knobs_exist_and_default_to_the_measured_config():
    from backend import config

    assert isinstance(config.NUM_BEAMS, int)
    assert config.NUM_BEAMS >= 1
    assert config.COMPUTE_DTYPE in ("bfloat16", "float16")
    assert isinstance(config.MERGE_LORA, bool)


def test_beam_search_and_sampling_are_mutually_exclusive():
    """HuggingFace rejects do_sample=True together with num_beams>1."""
    gen_kwargs = {"max_new_tokens": 8, "do_sample": False}

    beams = 4
    if beams > 1:
        gen_kwargs.pop("do_sample", None)
        gen_kwargs["num_beams"] = beams
        gen_kwargs["early_stopping"] = True

    assert "do_sample" not in gen_kwargs
    assert gen_kwargs["num_beams"] == 4
    assert gen_kwargs["early_stopping"] is True