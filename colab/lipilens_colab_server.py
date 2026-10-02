#!/usr/bin/env python
"""LipiLens Colab inference server.

Easiest path: open ``lipilens_colab_server.ipynb`` in Colab with a GPU runtime
and run the cells in order. It starts this app in a background thread (a bare
``!python lipilens_colab_server.py`` blocks the cell, so nothing after it can
run), opens a tunnel, and self-tests the round trip.

Manual equivalent, if you prefer plain cells:

    !pip install -q "transformers==5.17.0" "peft==0.21.0" "bitsandbytes==0.50.2" \\
                  "accelerate==1.15.0" pillow fastapi uvicorn pyngrok

    # import without self-starting, then serve in a thread
    import threading, uvicorn, importlib.util, sys
    spec = importlib.util.spec_from_file_location("lipilens_colab_server",
                                                 "lipilens_colab_server.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["lipilens_colab_server"] = mod
    spec.loader.exec_module(mod)
    threading.Thread(target=lambda: uvicorn.run(mod.app, host="0.0.0.0", port=8000),
                     daemon=True).start()

    from pyngrok import ngrok
    ngrok.set_auth_token("YOUR_NGROK_TOKEN")
    print(ngrok.connect(8000).public_url)   # -> COLAB_ENDPOINT_URL in your .env

Set ``INFERENCE_MODE=colab`` and ``COLAB_ENDPOINT_URL=<printed url>`` in the
local .env. Keep the notebook open; closing it takes the server down.

Contract (must stay in sync with backend/services/transcription/colab_client.py):
    POST /transcribe  {"image": "<base64 png/jpg>", "prompt": "<str>"}
    -> 200 {"transcription": "<Devanagari str>"}
    GET  /health -> {"status": "ok", "model_loaded": bool}
    GET  /gpu    -> hardware/version facts for the research log

Note: the backend sends ONE REQUEST PER TEXT LINE (line segmentation is applied
on its side, so this process never needs to know about pages).
"""

import base64
import io
import logging
import time

import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from PIL import Image
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s")
logger = logging.getLogger("lipilens-colab")

MODEL_ID = "Qwen/Qwen2.5-VL-3B-Instruct"
ADAPTER_ID = "lgtk/qwen25vl-3b-modi-synth-lora"

app = FastAPI(title="LipiLens Colab Inference Server")
_model = None
_processor = None


class TranscribeRequest(BaseModel):
    image: str  # base64-encoded image bytes
    prompt: str


def load_model_once():
    global _model, _processor
    if _model is not None:
        return
    from transformers import (
        AutoProcessor,
        BitsAndBytesConfig,
        Qwen2_5_VLForConditionalGeneration,
    )
    from peft import PeftModel

    logger.info("Loading base=%s adapter=%s", MODEL_ID, ADAPTER_ID)
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_compute_dtype=torch.bfloat16)
    base = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        MODEL_ID, quantization_config=bnb, device_map="auto")
    _model = PeftModel.from_pretrained(base, ADAPTER_ID)
    _model.eval()
    # Must match backend MAX_MODEL_PIXELS: the API already upscaled each text
    # line to fill this budget, and a lower cap here would undo that.
    _processor = AutoProcessor.from_pretrained(MODEL_ID, max_pixels=1280 * 28 * 28)
    logger.info("Model ready on %s", _model.device)


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": _model is not None}


@app.get("/gpu")
def gpu():
    """Hardware facts for the research log (no model load required)."""
    import transformers, peft
    info = {
        "cuda_available": torch.cuda.is_available(),
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "peft": peft.__version__,
        "base_model": MODEL_ID,
        "adapter": ADAPTER_ID,
    }
    if torch.cuda.is_available():
        info["device_name"] = torch.cuda.get_device_name(0)
        free, total = torch.cuda.mem_get_info(0)
        info["vram_total_mib"] = total // (1024 * 1024)
        info["vram_free_mib"] = free // (1024 * 1024)
    return info


@app.post("/transcribe")
def transcribe(req: TranscribeRequest):
    try:
        load_model_once()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Model load failed")
        raise HTTPException(status_code=503,
                            detail=f"model load failed: {exc}") from exc
    try:
        image = Image.open(io.BytesIO(base64.b64decode(req.image))).convert("RGB")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400,
                            detail=f"invalid image bytes: {exc}") from exc
    messages = [{"role": "user", "content": [
        {"type": "image", "image": image},
        {"type": "text", "text": req.prompt},
    ]}]
    text_in = _processor.apply_chat_template(messages, tokenize=False,
                                             add_generation_prompt=True)
    inputs = _processor(text=[text_in], images=[image],
                        return_tensors="pt").to(_model.device)
    t0 = time.perf_counter()
    with torch.no_grad():
        out = _model.generate(**inputs, max_new_tokens=256, do_sample=False)
    text = _processor.batch_decode(
        out[:, inputs["input_ids"].shape[1]:],
        skip_special_tokens=True)[0].strip()
    logger.info("Transcribed in %.1fs -> %d chars", time.perf_counter() - t0,
                len(text))
    return {"transcription": text}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
