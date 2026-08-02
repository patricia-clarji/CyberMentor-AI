from app.core.config import Settings
from app.mentor.adaptation import AdaptationDecision
from app.mentor.provider import MentorPrompt, generate_with_provider
from app.mentor.retrieval import RankedChunk, ReviewedChunk


def prompt() -> MentorPrompt:
    return MentorPrompt(
        question="How should I reason about this alert?",
        chunks=[
            RankedChunk(
                chunk=ReviewedChunk(
                    publication_id="reviewed-lesson",
                    publication_version="1.0.0",
                    chunk_id="evidence",
                    title="Evidence reasoning",
                    text="An alert is a lead that requires correlation.",
                    publisher="NIST",
                    url="https://csrc.nist.gov/example",
                ),
                lexical_score=1.0,
                rank=1,
            )
        ],
        learner_context={
            "weakSkills": ["alert-triage"],
            "strongSkills": [],
            "currentContext": {"type": "lesson"},
        },
        decision=AdaptationDecision(
            mode="socratic",
            intervention="ask_question",
            rationale="Test the learner's evidence reasoning.",
            related_skills=["alert-triage"],
            recommended_action=None,
            difficulty_risk="medium",
        ),
        history=[],
    )


def settings(provider: str) -> Settings:
    return Settings(
        environment="test",
        database_url="sqlite+pysqlite:///:memory:",
        email_backend="console",
        llm_provider=provider,
        llm_api_key="test-key",
        llm_model="test-model",
    )


def test_provider_registry_switches_request_and_response_shapes_by_configuration(
    monkeypatch,
) -> None:
    from app.mentor import provider as module

    requests: list[tuple[str, dict[str, object]]] = []

    def fake_post(url, *, headers, payload, timeout):
        del headers, timeout
        requests.append((url, payload))
        if url.endswith("/responses"):
            return {
                "output_text": "OpenAI grounded response.",
                "usage": {"input_tokens": 11, "output_tokens": 7},
            }, 10
        if url.endswith("/messages"):
            return {
                "content": [{"type": "text", "text": "Anthropic grounded response."}],
                "usage": {"input_tokens": 12, "output_tokens": 8},
            }, 11
        if ":generateContent" in url:
            return {
                "candidates": [{"content": {"parts": [{"text": "Google grounded response."}]}}],
                "usageMetadata": {
                    "promptTokenCount": 13,
                    "candidatesTokenCount": 9,
                },
            }, 12
        return {
            "message": {"content": "Ollama grounded response."},
            "prompt_eval_count": 14,
            "eval_count": 10,
        }, 13

    monkeypatch.setattr(module, "_post", fake_post)
    for name in ("openai", "anthropic", "google", "ollama", "mock"):
        result = generate_with_provider(settings(name), prompt())
        assert result.provider == name
        assert result.answer
    assert requests[0][0].endswith("/responses")
    assert requests[1][0].endswith("/messages")
    assert ":generateContent" in requests[2][0]
    assert requests[3][0].endswith("/api/chat")
    assert requests[3][1]["stream"] is False
