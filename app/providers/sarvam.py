"""Sarvam provider adapter. Calls are synchronous; FastAPI runs them in a worker thread."""
from __future__ import annotations
import io
from dataclasses import dataclass


@dataclass
class Transcription:
    text: str
    language_code: str | None


class SarvamProvider:
    def __init__(self, api_key: str, stt_model: str, tts_model: str, default_speaker: str, pace: float):
        try:
            from sarvamai import SarvamAI
        except ImportError as exc:
            raise RuntimeError("Missing dependency sarvamai. Install with: pip install -r requirements.txt") from exc
        self.client = SarvamAI(api_subscription_key=api_key)
        self.stt_model = stt_model
        self.tts_model = tts_model
        self.default_speaker = default_speaker
        self.pace = pace

    def transcribe(self, audio: bytes, filename: str, content_type: str, language_code: str | None = None) -> Transcription:
        # SDK expects a file-like object. BytesIO avoids writing user audio to disk.
        audio_file = io.BytesIO(audio)
        audio_file.name = filename or "recording.webm"
        kwargs = {"file": audio_file, "model": self.stt_model, "mode": "transcribe"}
        if language_code and language_code != "auto":
            kwargs["language_code"] = language_code
        result = self.client.speech_to_text.transcribe(**kwargs)
        text = getattr(result, "transcript", "") or ""
        detected = getattr(result, "language_code", None)
        if not text.strip():
            raise ValueError("Speech recognition returned an empty transcript. Please try speaking again.")
        return Transcription(text=text.strip(), language_code=detected)

    def synthesize(self, text: str, language_code: str, speaker: str | None = None) -> tuple[bytes, str]:
        # HTTP streaming lowers time-to-first-byte at the provider boundary. This MVP buffers
        # chunks before returning JSON; true browser audio streaming is a follow-up milestone.
        chunks = self.client.text_to_speech.convert_stream(
            text=text[:3400],
            language_code=language_code,
            model=self.tts_model,
            speaker=speaker or self.default_speaker,
            output_audio_codec="mp3",
            pace=self.pace,
        )
        audio = b"".join(chunks)
        if not audio:
            raise RuntimeError("Sarvam TTS returned no audio data.")
        return audio, "audio/mpeg"
