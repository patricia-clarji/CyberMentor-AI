import re
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session as DatabaseSession

from app.core.config import Settings
from app.identity.dependencies import AuthContext
from app.mentor.adaptation import (
    build_learner_context,
    detect_misconceptions,
    record_roadmap_recommendation,
    select_adaptation,
)
from app.mentor.provider import (
    PROMPT_VERSION,
    MentorPrompt,
    deterministic_fallback,
    generate_with_provider,
    provider_available,
)
from app.mentor.retrieval import RETRIEVAL_VERSION, RankedChunk, retrieve
from app.mentor.safety import POLICY_VERSION, classify, redacted_hash
from app.models.mentor import (
    AIUsageEvent,
    MentorIntervention,
    MentorMessage,
    MentorThread,
    RetrievalQuery,
    RetrievalResult,
    SafetyEvent,
)

OUTPUT_LEAKAGE = re.compile(
    r"\b(the correct answer is|answer key|hidden evidence|system prompt|grading key)\b",
    re.IGNORECASE,
)


def citation_payload(chunks: list[RankedChunk]) -> list[dict[str, str]]:
    unique: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in chunks:
        key = (item.chunk.publication_id, item.chunk.url)
        if key in seen:
            continue
        seen.add(key)
        unique.append(
            {
                "publication_id": item.chunk.publication_id,
                "publication_version": item.chunk.publication_version,
                "chunk_id": item.chunk.chunk_id,
                "title": item.chunk.title,
                "publisher": item.chunk.publisher,
                "url": item.chunk.url,
                "verification_status": "verified",
            }
        )
        if len(unique) == 3:
            break
    return unique


def _history(db: DatabaseSession, thread: MentorThread) -> list[dict[str, str]]:
    messages = db.scalars(
        select(MentorMessage)
        .where(
            MentorMessage.thread_id == thread.id,
            MentorMessage.organization_id == thread.organization_id,
            MentorMessage.user_id == thread.user_id,
        )
        .order_by(MentorMessage.created_at.desc())
        .limit(8)
    ).all()
    return [
        {"role": item.role, "content": item.body}
        for item in reversed(messages)
        if item.mode != "policy_refusal"
    ]


def _estimated_cost(
    settings: Settings,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    return (prompt_tokens / 1_000_000) * settings.llm_input_cost_per_million + (
        completion_tokens / 1_000_000
    ) * settings.llm_output_cost_per_million


def _store_safety_refusal(
    db: DatabaseSession,
    auth: AuthContext,
    thread: MentorThread,
    question: str,
    category: str,
    response: str,
) -> dict[str, Any]:
    now = datetime.now(UTC)
    db.add(
        SafetyEvent(
            organization_id=auth.organization_id,
            user_id=auth.user.id,
            category=category,
            action="refused",
            redacted_input_hash=redacted_hash(question),
            policy_version=POLICY_VERSION,
            occurred_at=now,
        )
    )
    message = MentorMessage(
        organization_id=auth.organization_id,
        user_id=auth.user.id,
        thread_id=thread.id,
        role="assistant",
        mode="policy_refusal",
        mentor_mode="safety_redirect",
        body=response,
        provider_generated=False,
        prompt_version=PROMPT_VERSION,
        retrieval_version=RETRIEVAL_VERSION,
        provider="deterministic",
        model_version="safety-policy",
        temperature=0.0,
        prompt_tokens=0,
        completion_tokens=0,
        latency_ms=0,
        reasoning_summary=f"Safety policy selected a redirect for category {category}.",
        related_skills=[],
        recommended_action={
            "type": "safe_alternative",
            "id": "authorized-defensive-practice",
            "reason": "Continue with synthetic, authorized defensive learning.",
        },
        created_at=now,
    )
    db.add(message)
    db.flush()
    db.commit()
    return {
        "thread_id": thread.id,
        "message_id": message.id,
        "answer": response,
        "mode": "policy_refusal",
        "mentor_mode": "safety_redirect",
        "intervention": "review_prerequisite",
        "provider_generated": False,
        "blocked": True,
        "citations": [],
        "reasoning_summary": message.reasoning_summary,
        "related_skills": [],
        "recommended_next_action": message.recommended_action,
        "detected_misconceptions": [],
        "limitation_notice": (
            "The blocked input is not stored; only a one-way hash and policy category are logged."
        ),
        "prompt_version": PROMPT_VERSION,
        "retrieval_version": RETRIEVAL_VERSION,
        "provider": "deterministic",
        "model": "safety-policy",
        "latency_ms": 0,
    }


def answer_question(
    db: DatabaseSession,
    auth: AuthContext,
    thread: MentorThread,
    question: str,
    settings: Settings,
) -> dict[str, Any]:
    safety = classify(question)
    if safety.blocked:
        return _store_safety_refusal(
            db,
            auth,
            thread,
            question,
            str(safety.category),
            str(safety.response),
        )
    detected = detect_misconceptions(db, auth, question)
    db.flush()
    learner_context = build_learner_context(db, auth, thread)
    decision = select_adaptation(
        question,
        learner_context,
        detected,
        context_type=thread.context_type,
    )
    ranked = retrieve(
        settings,
        question,
        context_id=thread.context_id,
    )
    history = _history(db, thread)
    now = datetime.now(UTC)
    query = RetrievalQuery(
        organization_id=auth.organization_id,
        user_id=auth.user.id,
        thread_id=thread.id,
        query_text=question,
        scope={
            "profile": "junior-soc",
            "contextType": thread.context_type,
            "contextId": thread.context_id,
            "weakSkills": learner_context["weakSkills"],
        },
        index_version=RETRIEVAL_VERSION,
        created_at=now,
    )
    db.add(query)
    db.flush()
    for item in ranked:
        db.add(
            RetrievalResult(
                retrieval_query_id=query.id,
                publication_id=item.chunk.publication_id,
                publication_version=item.chunk.publication_version,
                chunk_id=item.chunk.chunk_id,
                lexical_score=item.lexical_score,
                vector_score=None,
                hybrid_score=item.lexical_score,
                rank=item.rank,
            )
        )
    user_message = MentorMessage(
        organization_id=auth.organization_id,
        user_id=auth.user.id,
        thread_id=thread.id,
        role="user",
        mode="learner_input",
        mentor_mode=decision.mode,
        body=question,
        provider_generated=False,
        prompt_version=PROMPT_VERSION,
        retrieval_version=RETRIEVAL_VERSION,
        provider="learner",
        model_version=None,
        temperature=0.0,
        prompt_tokens=0,
        completion_tokens=0,
        latency_ms=0,
        reasoning_summary=None,
        related_skills=decision.related_skills,
        recommended_action=None,
        created_at=now,
    )
    db.add(user_message)
    db.add(
        MentorIntervention(
            organization_id=auth.organization_id,
            user_id=auth.user.id,
            thread_id=thread.id,
            trigger_type=(
                "misconception" if detected else f"difficulty_{decision.difficulty_risk}"
            ),
            selected_mode=decision.mode,
            rationale=decision.rationale,
            created_at=now,
        )
    )
    answer = deterministic_fallback(
        question,
        ranked,
        decision,
        learner_context,
    )
    provider = "deterministic"
    model = "fallback-2.0.0"
    latency_ms = 0
    prompt_tokens = 0
    completion_tokens = 0
    temperature = 0.0
    provider_generated = False
    delivery_mode = "deterministic_fallback"
    if provider_available(settings) and ranked:
        try:
            result = generate_with_provider(
                settings,
                MentorPrompt(
                    question=question,
                    chunks=ranked,
                    learner_context=learner_context,
                    decision=decision,
                    history=history,
                ),
            )
            if OUTPUT_LEAKAGE.search(result.answer):
                raise ValueError("Provider output failed answer-leakage validation.")
            answer = result.answer
            provider = result.provider
            model = result.model
            latency_ms = result.latency_ms
            prompt_tokens = result.prompt_tokens
            completion_tokens = result.completion_tokens
            temperature = result.temperature
            provider_generated = True
            delivery_mode = "live_grounded"
        except (OSError, ValueError, KeyError, IndexError, TypeError, httpx.HTTPError):
            delivery_mode = "deterministic_fallback"
    reasoning_summary = (
        f"Selected {decision.mode.replace('_', ' ')} mode because "
        f"{decision.rationale} Difficulty risk: {decision.difficulty_risk}."
    )
    assistant_message = MentorMessage(
        organization_id=auth.organization_id,
        user_id=auth.user.id,
        thread_id=thread.id,
        role="assistant",
        mode=delivery_mode,
        mentor_mode=decision.mode,
        body=answer,
        provider_generated=provider_generated,
        prompt_version=PROMPT_VERSION,
        retrieval_version=RETRIEVAL_VERSION,
        provider=provider,
        model_version=model,
        temperature=temperature,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=latency_ms,
        reasoning_summary=reasoning_summary,
        related_skills=decision.related_skills,
        recommended_action=decision.recommended_action,
        created_at=datetime.now(UTC),
    )
    db.add(assistant_message)
    db.add(
        AIUsageEvent(
            organization_id=auth.organization_id,
            user_id=auth.user.id,
            provider=provider,
            model=model,
            prompt_version=PROMPT_VERSION,
            retrieval_version=RETRIEVAL_VERSION,
            temperature=temperature,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_cost=_estimated_cost(
                settings,
                prompt_tokens,
                completion_tokens,
            ),
            latency_ms=latency_ms,
            fallback_used=not provider_generated,
            occurred_at=datetime.now(UTC),
        )
    )
    record_roadmap_recommendation(db, auth, decision)
    db.flush()
    db.commit()
    return {
        "thread_id": thread.id,
        "message_id": assistant_message.id,
        "answer": answer,
        "mode": delivery_mode,
        "mentor_mode": decision.mode,
        "intervention": decision.intervention,
        "provider_generated": provider_generated,
        "blocked": False,
        "citations": citation_payload(ranked),
        "reasoning_summary": reasoning_summary,
        "related_skills": decision.related_skills,
        "recommended_next_action": decision.recommended_action,
        "detected_misconceptions": detected,
        "limitation_notice": (
            "Sentinel uses reviewed learner-visible sources and your own learning record. "
            "It does not grade work, reveal hidden evidence, or replace instructor review."
        ),
        "prompt_version": PROMPT_VERSION,
        "retrieval_version": RETRIEVAL_VERSION,
        "provider": provider,
        "model": model,
        "latency_ms": latency_ms,
    }
