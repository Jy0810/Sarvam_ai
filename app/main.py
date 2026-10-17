from __future__ import annotations
import logging
import time
from pathlib import Path
from typing import Annotated
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from app.config import get_settings
from app.orchestrator import Orchestrator
from app.providers.openai import OpenAIProvider
from app.providers.sarvam import SarvamProvider
from app.schemas import TextRequest

settings = get_settings()
logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger("voice_assistant")
app = FastAPI(title="Multilingual Voice Research Assistant", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["*"])
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

_orchestrator: Orchestrator | None = None


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        missing = settings.missing_keys()
        if missing:
            raise HTTPException(status_code=503, detail=f"Configure provider credentials in .env: {', '.join(missing)}")
        try:
            _orchestrator = Orchestrator(
                settings,
                SarvamProvider(settings.sarvam_api_key, settings.sarvam_stt_model, settings.sarvam_tts_model, settings.default_speaker, settings.tts_pace),
                OpenAIProvider(settings.openai_api_key, settings.openai_model),
            )
        except Exception as exc:
            logger.exception("Could not initialize provider clients")
            raise HTTPException(status_code=503, detail="Could not initialize provider clients. Check installed SDK versions and API configuration.") from exc
    return _orchestrator


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health():
    missing = settings.missing_keys()
    return {"status": "ok" if not missing else "needs_configuration", "missing_keys": missing, "stt_model": settings.sarvam_stt_model, "tts_model": settings.sarvam_tts_model, "openai_model": settings.openai_model}


@app.post("/api/text")
async def text_query(payload: TextRequest):
    orchestrator = get_orchestrator()
    try:
        return await run_in_threadpool(orchestrator.process_text, payload.query.strip(), payload.response_language, payload.research)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Text query failed")
        raise HTTPException(status_code=502, detail=f"Assistant request failed: {safe_error(exc)}") from exc


@app.post("/api/voice")
async def voice_query(
    audio: Annotated[UploadFile, File(...)],
    response_language: Annotated[str | None, Form()] = None,
    research: Annotated[str, Form()] = "auto",
):
    content_type = (audio.content_type or "application/octet-stream").lower()
    allowed_types = ("audio/", "video/webm", "application/octet-stream")
    if not any(content_type.startswith(t) for t in allowed_types):
        raise HTTPException(status_code=415, detail=f"Unsupported audio content type: {content_type}")
    max_bytes = settings.max_upload_mb * 1024 * 1024
    content = await audio.read(max_bytes + 1)
    if not content:
        raise HTTPException(status_code=400, detail="No audio was received.")
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"Audio exceeds the {settings.max_upload_mb} MB upload limit.")
    research_flag = None if research == "auto" else research.lower() == "true"
    orchestrator = get_orchestrator()
    try:
        return await run_in_threadpool(orchestrator.process_audio, content, audio.filename or "recording.webm", content_type, response_language, research_flag)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Voice query failed")
        raise HTTPException(status_code=502, detail=f"Voice request failed: {safe_error(exc)}") from exc


def safe_error(exc: Exception) -> str:
    # Avoid returning credentials or large provider payloads to the browser.
    message = str(exc).replace(settings.sarvam_api_key, "[redacted]").replace(settings.openai_api_key, "[redacted]")
    return message[:500] or exc.__class__.__name__
