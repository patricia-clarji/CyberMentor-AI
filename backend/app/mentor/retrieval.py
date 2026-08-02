import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import Settings

RETRIEVAL_VERSION = "soc-reviewed-hybrid-2.0.0"
TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]{2,}")
ALLOWED_ARTIFACT_TYPES = {"course", "module", "lesson"}


@dataclass(frozen=True)
class ReviewedChunk:
    publication_id: str
    publication_version: str
    chunk_id: str
    title: str
    text: str
    publisher: str
    url: str
    source_kind: str = "reviewed_content"


@dataclass(frozen=True)
class RankedChunk:
    chunk: ReviewedChunk
    lexical_score: float
    rank: int


def _content_text(publication: dict[str, Any]) -> list[tuple[str, str]]:
    artifact = publication.get("artifact") or {}
    artifact_type = publication.get("artifactType")
    if artifact_type == "lesson":
        chunks: list[tuple[str, str]] = []
        for block in artifact.get("blocks") or []:
            text = block.get("text") or block.get("body")
            if isinstance(text, str) and text.strip():
                chunks.append((str(block.get("id") or len(chunks)), text.strip()))
        return chunks
    fields = [
        artifact.get("summary"),
        *(artifact.get("learningOutcomes") or []),
        *(artifact.get("learningObjectives") or []),
    ]
    return [
        (f"overview-{index}", text.strip())
        for index, text in enumerate(fields)
        if isinstance(text, str) and text.strip()
    ]


def load_reviewed_soc_chunks(settings: Settings) -> list[ReviewedChunk]:
    root = Path(settings.content_root).resolve()
    if not root.exists():
        return []
    chunks: list[ReviewedChunk] = []
    for path in sorted(root.glob("course-4*/1.0.0.json")):
        try:
            publication = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if (
            publication.get("artifactType") not in ALLOWED_ARTIFACT_TYPES
            or publication.get("verificationStatus") != "verified"
            or publication.get("publicationStatus") != "published"
        ):
            continue
        references = publication.get("references") or []
        reference = next(
            (
                item
                for item in references
                if isinstance(item, dict)
                and isinstance(item.get("url"), str)
                and item["url"].startswith("https://")
            ),
            None,
        )
        if reference is None:
            continue
        for chunk_id, text in _content_text(publication):
            chunks.append(
                ReviewedChunk(
                    publication_id=publication["id"],
                    publication_version=publication["contentVersion"],
                    chunk_id=chunk_id,
                    title=publication["title"],
                    text=text,
                    publisher=str(reference.get("publisher") or "Authoritative source"),
                    url=reference["url"],
                )
            )
        for index, item in enumerate(references):
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("url"), str)
                or not item["url"].startswith("https://")
            ):
                continue
            title = item.get("title")
            publisher = item.get("publisher")
            if not isinstance(title, str) or not title.strip():
                continue
            chunks.append(
                ReviewedChunk(
                    publication_id=publication["id"],
                    publication_version=publication["contentVersion"],
                    chunk_id=f"official-reference-{index}",
                    title=title.strip(),
                    text=(
                        f"Official documentation reference: {title.strip()}. "
                        f"Publisher: {publisher or 'authoritative source'}."
                    ),
                    publisher=str(publisher or "Authoritative source"),
                    url=item["url"],
                    source_kind="official_reference",
                )
            )
    return chunks


def tokenize(value: str) -> set[str]:
    return set(TOKEN_PATTERN.findall(value.casefold()))


def retrieve(
    settings: Settings,
    query: str,
    limit: int = 5,
    *,
    context_id: str | None = None,
) -> list[RankedChunk]:
    query_tokens = tokenize(query)
    if not query_tokens:
        return []
    ranked = []
    for chunk in load_reviewed_soc_chunks(settings):
        title_tokens = tokenize(chunk.title)
        text_tokens = tokenize(chunk.text)
        overlap = query_tokens & text_tokens
        title_overlap = query_tokens & title_tokens
        context_boost = (
            0.35
            if context_id
            and (context_id == chunk.publication_id or context_id in chunk.publication_id)
            else 0.0
        )
        score = (
            (len(overlap) / max(1, len(query_tokens))) + (0.5 * len(title_overlap)) + context_boost
        )
        if score > 0:
            ranked.append((score, chunk))
    ranked.sort(key=lambda item: (-item[0], item[1].publication_id, item[1].chunk_id))
    return [
        RankedChunk(chunk=chunk, lexical_score=score, rank=index)
        for index, (score, chunk) in enumerate(ranked[:limit], start=1)
    ]
