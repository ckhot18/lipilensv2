import logging
from pathlib import Path

import torch
from PIL import Image

from backend.config import BASE_MODEL_NAME, LORA_ADAPTER_NAME
from backend.services.transcription.inference import TranscriptionResult, TranscriptionService

logger = logging.getLogger(__name__)

# Singleton instances to avoid reloading
_model = None
_processor = None


class LocalQwenTranscriptionService(TranscriptionService):
    def __init__(self, load_on_init: bool = False):
        if load_on_init:
            self._load_model()

    def _load_model(self):
        global _model, _processor
        
        if _model is not None and _processor is not None:
            return

        logger.info(f"Loading local model: base={BASE_MODEL_NAME}, adapter={LORA_ADAPTER_NAME}")
        
        try:
            from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
            from peft import PeftModel
            
            # BitsAndBytes configuration for 4-bit quantization (to fit in 4GB VRAM)
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16,  # per official adapter recipe; RTX 2050 supports bf16
            )
            
            base_model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                BASE_MODEL_NAME,
                quantization_config=bnb_config,
                device_map="auto"
            )
            
            _model = PeftModel.from_pretrained(base_model, LORA_ADAPTER_NAME)
            _model.eval()
            
            _processor = AutoProcessor.from_pretrained(BASE_MODEL_NAME, max_pixels=512 * 28 * 28)
            
            logger.info("Local model loaded successfully.")
            
            # Update health state
            from backend.api.health import set_model_loaded
            set_model_loaded(True)
            
        except Exception as e:
            logger.error(f"Failed to load local model: {e}")
            raise

    def transcribe(self, image_path: str | Path, prompt: str) -> TranscriptionResult:
        self._load_model()
        
        global _model, _processor
        
        logger.info(f"Transcribing image locally: {image_path}")
        image = Image.open(image_path).convert("RGB")
        
        messages = [{
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt},
            ],
        }]
        
        text_in = _processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = _processor(text=[text_in], images=[image], return_tensors="pt").to(_model.device)
        
        with torch.no_grad():
            out = _model.generate(**inputs, max_new_tokens=256, do_sample=False)
            
        result_text = _processor.batch_decode(
            out[:, inputs["input_ids"].shape[1]:], skip_special_tokens=True
        )[0].strip()
        
        return TranscriptionResult(
            text=result_text,
            model_name=f"{BASE_MODEL_NAME} + {LORA_ADAPTER_NAME}",
            inference_mode="local",
            raw_output=result_text
        )
