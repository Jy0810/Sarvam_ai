from pydantic import BaseModel, Field


class TextRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    response_language: str | None = Field(default=None, max_length=16)
    research: bool | None = None


class Source(BaseModel):
    title: str
    url: str


class AssistantResponse(BaseModel):
    transcript: str
    detected_language: str | None = None
    answer: str
    response_language: str
    audio_base64: str | None = None
    audio_mime_type: str | None = None
    sources: list[Source] = []
    researched: bool
    timings_ms: dict[str, int] = {}
