from types import SimpleNamespace

from app.orchestrator import should_research, language_name
from app.providers.openai import OpenAIProvider


def test_research_router_auto_for_current_query():
    assert should_research("What is the latest OpenAI model?", None) is True


def test_research_router_skips_search_for_simple_question():
    assert should_research("Explain what a neural network is", None) is False


def test_research_router_respects_explicit_choice():
    assert should_research("What happened today?", False) is False
    assert should_research("Explain PCA", True) is True


def test_language_names():
    assert language_name("te-IN") == "Telugu"
    assert language_name(None) == "the same language as the user's question"


def test_tts_language_mapping():
    from app.orchestrator import Orchestrator
    from app.config import Settings
    obj = Orchestrator.__new__(Orchestrator)
    obj.settings = Settings(default_language_code="en-IN")
    assert obj._tts_language("Telugu") == "te-IN"
    assert obj._tts_language("English") == "en-IN"
    assert obj._tts_language("te-IN") == "te-IN"
    assert obj._tts_language(None) == "en-IN"


def test_openai_provider_uses_web_search_only_when_requested():
    provider = OpenAIProvider.__new__(OpenAIProvider)
    provider.model = "test-model"
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(output_text="A concise answer.", output=[])

    provider.client = SimpleNamespace(responses=SimpleNamespace(create=create))

    answer = provider.answer("Question", "English", research=True)
    assert answer.answer == "A concise answer."
    assert answer.researched is True
    assert calls[0]["tools"] == [{"type": "web_search"}]

    provider.answer("Question", "English", research=False)
    assert calls[1]["tools"] == []


def test_openai_provider_extracts_unique_web_citations():
    response = SimpleNamespace(output=[
        SimpleNamespace(content=[
            SimpleNamespace(annotations=[
                SimpleNamespace(type="url_citation", url="https://example.com", title="Example"),
                SimpleNamespace(type="url_citation", url="https://example.com", title="Duplicate"),
                SimpleNamespace(type="url_citation", url="javascript:alert(1)", title="Unsafe"),
            ])
        ])
    ])

    assert OpenAIProvider._extract_sources(response) == [
        {"title": "Example", "url": "https://example.com"}
    ]
