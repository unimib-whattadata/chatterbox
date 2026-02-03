import io
import os
import torch
import numpy as np
import soundfile as sf
import asyncio
from fastapi import FastAPI, HTTPException, Header, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from contextlib import asynccontextmanager

try:
    import intel_extension_for_pytorch as ipex
except ImportError:
    pass

from chatterbox.tts_turbo import ChatterboxTurboTTS

# Global model
model = None
# Global lock for inference
lock = asyncio.Lock()

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    # Detect device
    if hasattr(torch, "xpu") and torch.xpu.is_available():
        device = "xpu"
    elif torch.cuda.is_available():
        device = "cuda"
    elif torch.backends.mps.is_available():
        device = "mps"
    else:
        device = "cpu"

    print(f"Loading ChatterboxTurboTTS on {device}...", flush=True)
    # Using from_pretrained to load the model
    model = ChatterboxTurboTTS.from_pretrained(device=device)
    print("Model loaded.", flush=True)
    yield
    # Cleanup if needed

app = FastAPI(lifespan=lifespan)

class VoiceSettings(BaseModel):
    stability: Optional[float] = 0.5
    similarity_boost: Optional[float] = 0.75
    style: Optional[float] = 0.0
    use_speaker_boost: Optional[bool] = True

class ChatterboxTTSRequest(BaseModel):
    text: str
    model_id: Optional[str] = "chatterbox_turbo"
    language_code: Optional[str] = None
    voice_settings: Optional[VoiceSettings] = None

@app.get("/")
def healthcheck():
    """
    Root healthcheck endpoint used by docker-compose.
    Returns 200 when the application is up. Includes model initialization status.
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "model_initialized": model is not None
        }
    )

@app.post("/v1/text-to-speech/{voice_id}")
async def text_to_speech_elevenlabs(
    voice_id: str,
    request: ChatterboxTTSRequest,
    xi_api_key: str = Header(None, alias="xi-api-key", description="CHATTERBOX_API_KEY")
):
    expected_key = os.environ.get("CHATTERBOX_API_KEY")

    # Check authentication if environment variable is set
    if expected_key:
        if xi_api_key != expected_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API Key",
            )
    else:
        # Warn if no key configured, but proceed (or should we fail? User example failed)
        # User example: if not expected_key: raise 500.
        # We will log and raise 500 to match behavior if strictly required,
        # but often for testing we might want it open.
        # I'll stick to user's logic: raise 500.
        print("Error: CHATTERBOX_API_KEY not set in environment.", flush=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server authentication configuration missing (CHATTERBOX_API_KEY not set).",
        )

    if model is None:
        raise HTTPException(status_code=500, detail="Model not initialized")

    # Map settings
    exaggeration = 0.5
    if request.voice_settings and request.voice_settings.style is not None:
        exaggeration = request.voice_settings.style

    # Determine voice/audio prompt
    audio_prompt_path = None
    target_voice = voice_id

    # Simple logic: if voice_id points to a file, use it.
    # If not, check request.model_id.
    if os.path.exists(target_voice):
        audio_prompt_path = target_voice
    elif request.model_id and os.path.exists(request.model_id):
        audio_prompt_path = request.model_id

    # Generate
    try:
        loop = asyncio.get_running_loop()
        async with lock:
            wav_tensor = await loop.run_in_executor(
                None,
                lambda: model.generate(
                    request.text,
                    exaggeration=exaggeration,
                    audio_prompt_path=audio_prompt_path
                )
            )
        
        # wav_tensor is [1, T]
        wav_numpy = wav_tensor.squeeze(0).cpu().numpy()

        buffer = io.BytesIO()
        sf.write(buffer, wav_numpy, model.sr, format="WAV")
        buffer.seek(0)

        return Response(content=buffer.read(), media_type="audio/wav")

    except Exception as e:
        print(f"Generation error: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))
