from __future__ import annotations
import re
import time
from app.config import Settings
from app.providers.sarvam import SarvamProvider
from app.providers.openai import OpenAIProvider

# Known language-code labels for explicit user choices and detected Sarvam codes.
LANGUAGE_NAMES = {
    "en-IN": "English", "te-IN": "Telugu", "hi-IN": "Hindi", "ta-IN": "Tamil",
    "kn-IN": "Kannada", "ml-IN": "Malayalam", "mr-IN": "Marathi", "bn-IN": "Bengali",
    "gu-IN": "Gujarati", "pa-IN": "Punjabi", "od-IN": "Odia",
}
LANGUAGE_CODES = {name.lower(): code for code, name in LANGUAGE_NAMES.items()}

RESEARCH_HINTS = re.compile(
    r"\b(latest|today|current|recent|news|search|research|sources|citations|on the internet|online|202[5-9])\b",
    re.IGNORECASE,
)


def should_research(query: str, requested: bool | None) -> bool:
    if requested is not None:
        return requested
    # Default to research for questions likely to require freshness/evidence.
    return bool(RESEARCH_HINTS.search(query))


def language_name(code: str | None) -> str:
    return LANGUAGE_NAMES.get(code or "", "the same language as the user's question")


class Orchestrator:
    def __init__(self, settings: Settings, sarvam: SarvamProvider, openai: OpenAIProvider):
        self.settings = settings
        self.sarvam = sarvam
        self.openai = openai

    def process_text(self, query: str, response_language: str | None, research: bool | None) -> dict:
        start = time.perf_counter()
        do_research = should_research(query, research)
        language = response_language or "English"
        answer = self.openai.answer(query=query, response_language=language, research=do_research)
        answer_done = time.perf_counter()
        audio, mime = self.sarvam.synthesize(answer.answer, self._tts_language(response_language))
        end = time.perf_counter()
        return {
            "transcript": query,
            "detected_language": None,
            "answer": answer.answer,
            "response_language": language,
            "audio_base64": __import__("base64").b64encode(audio).decode("ascii"),
            "audio_mime_type": mime,
            "sources": answer.sources,
            "researched": answer.researched,
            "timings_ms": {"answer_generation": int((answer_done-start)*1000), "tts": int((end-answer_done)*1000), "total": int((end-start)*1000)},
        }

    def process_audio(self, audio: bytes, filename: str, content_type: str, response_language: str | None, research: bool | None) -> dict:
        start = time.perf_counter()
        transcription = self.sarvam.transcribe(audio, filename, content_type)
        stt_done = time.perf_counter()
        detected = transcription.language_code
        language = response_language or language_name(detected)
        do_research = should_research(transcription.text, research)
        answer = self.openai.answer(transcription.text, language, do_research)
        answer_done = time.perf_counter()
        audio_out, mime = self.sarvam.synthesize(answer.answer, self._tts_language(response_language or detected))
        end = time.perf_counter()
        import base64
        return {
            "transcript": transcription.text,
            "detected_language": detected,
            "answer": answer.answer,
            "response_language": language,
            "audio_base64": base64.b64encode(audio_out).decode("ascii"),
            "audio_mime_type": mime,
            "sources": answer.sources,
            "researched": answer.researched,
            "timings_ms": {"stt": int((stt_done-start)*1000), "answer_generation": int((answer_done-stt_done)*1000), "tts": int((end-answer_done)*1000), "total": int((end-start)*1000)},
        }

    def _tts_language(self, requested: str | None) -> str:
        if not requested:
            return self.settings.default_language_code
        if requested in LANGUAGE_NAMES:
            return requested
        return LANGUAGE_CODES.get(requested.strip().lower(), self.settings.default_language_code)
