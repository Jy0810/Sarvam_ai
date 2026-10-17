from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    sarvam_api_key: str = ""
    openai_api_key: str = ""
    sarvam_stt_model: str = "saaras:v4"
    sarvam_tts_model: str = "bulbul:v4-flash"
    openai_model: str = "gpt-4.1-mini"
    default_language_code: str = "en-IN"
    default_speaker: str = "simran_en_customer"
    tts_pace: float = 1.0
    max_audio_seconds: int = 30
    max_upload_mb: int = 15
    request_timeout_seconds: int = 45
    cors_origins: str = "http://127.0.0.1:8000,http://localhost:8000"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def missing_keys(self) -> list[str]:
        missing = []
        if not self.sarvam_api_key or self.sarvam_api_key == "replace_me":
            missing.append("SARVAM_API_KEY")
        if not self.openai_api_key or self.openai_api_key == "replace_me":
            missing.append("OPENAI_API_KEY")
        return missing


@lru_cache

def get_settings() -> Settings:
    return Settings()
