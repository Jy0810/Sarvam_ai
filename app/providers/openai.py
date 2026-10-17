"""OpenAI answer generation with optional web search."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ResearchAnswer:
    answer: str
    sources: list[dict[str, str]]
    researched: bool


class OpenAIProvider:
    def __init__(self, api_key: str, model: str):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("Missing dependency openai. Install with: pip install -r requirements.txt") from exc
        self.client = OpenAI(api_key=api_key)
        self.model = model

    @staticmethod
    def _extract_sources(response) -> list[dict[str, str]]:
        found: list[dict[str, str]] = []
        seen: set[str] = set()
        for item in getattr(response, "output", None) or []:
            for content in getattr(item, "content", None) or []:
                for annotation in getattr(content, "annotations", None) or []:
                    if getattr(annotation, "type", None) != "url_citation":
                        continue
                    url = getattr(annotation, "url", None)
                    title = getattr(annotation, "title", None) or url
                    if url and url.startswith(("https://", "http://")) and url not in seen:
                        seen.add(url)
                        found.append({"title": str(title), "url": str(url)})
        return found[:8]

    def answer(self, query: str, response_language: str, research: bool) -> ResearchAnswer:
        instruction = (
            "You are a helpful multilingual voice research assistant. Answer clearly and naturally for speech. "
            f"Respond in {response_language}. Keep the initial answer concise (roughly 3-6 sentences), "
            "explain technical terms plainly, distinguish uncertainty, and never invent sources. "
            "When web search is available, ground time-sensitive or factual claims in retrieved information. "
            "Do not read URLs aloud."
        )
        response = self.client.responses.create(
            model=self.model,
            instructions=instruction,
            input=query,
            tools=[{"type": "web_search"}] if research else [],
        )
        answer = (getattr(response, "output_text", None) or "").strip()
        if not answer:
            raise RuntimeError("OpenAI returned an empty answer. Please try again.")
        return ResearchAnswer(answer=answer, sources=self._extract_sources(response), researched=research)
