import hashlib
import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import String, cast, delete, func, or_, select
from sqlalchemy.orm import Session as DatabaseSession

from app.core.errors import AppError
from app.models.cms import (
    CmsContent,
    CmsContentRelation,
    CmsContentVersion,
    CmsLearningObjective,
    CmsLessonSection,
    CmsMediaAsset,
    CmsMediaUsage,
    CmsPublicationEvent,
    CmsReviewAssignment,
    CmsReviewComment,
    CmsReviewDecision,
    CmsReviewRequirement,
    CmsValidationResult,
)
from app.models.identity import User
from app.schemas.cms import ContentCreateRequest, ContentUpdateRequest

EDITABLE_STATES = {"draft", "revision_requested"}
UNSAFE_FRAGMENTS = ("<script", "javascript:", "onerror=", "onload=", "<iframe")
REQUIRED_REVIEWERS = {
    "course": {"technical_reviewer", "instructional_reviewer"},
    "module": {"technical_reviewer", "instructional_reviewer"},
    "lesson": {"technical_reviewer", "instructional_reviewer"},
    "lab": {"technical_reviewer", "instructional_reviewer"},
    "mission": {"technical_reviewer", "instructional_reviewer"},
    "assessment": {"technical_reviewer", "instructional_reviewer"},
    "question": {"instructional_reviewer"},
    "learning_path": {"technical_reviewer", "instructional_reviewer"},
}


def required_reviewers(db: DatabaseSession, content_type: str) -> set[str]:
    configured = set(
        db.scalars(
            select(CmsReviewRequirement.reviewer_type).where(
                CmsReviewRequirement.content_type == content_type,
                CmsReviewRequirement.required.is_(True),
                CmsReviewRequirement.active.is_(True),
            )
        ).all()
    )
    return configured or REQUIRED_REVIEWERS.get(content_type, {"content_reviewer"})


def required_reviewers_for_version(
    db: DatabaseSession, content_type: str, version: CmsContentVersion
) -> set[str]:
    required = required_reviewers(db, content_type)
    if content_type == "lesson":
        has_images = db.scalar(
            select(CmsLessonSection.id).where(
                CmsLessonSection.version_id == version.id,
                CmsLessonSection.section_type.in_(["image", "diagram_placeholder"]),
            )
        )
        if has_images:
            required.add("accessibility_reviewer")
    return required


def request_id(request: Any) -> str | None:
    return getattr(request.state, "request_id", None)


def scope_key(organization_id: uuid.UUID | None) -> str:
    return str(organization_id) if organization_id else "platform"


def canonical_checksum(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def version_payload(
    version: CmsContentVersion,
    sections: list[CmsLessonSection],
    objectives: list[CmsLearningObjective],
    relationships: list[CmsContentRelation] | None = None,
) -> dict[str, Any]:
    return {
        "title": version.title,
        "slug": version.public_slug,
        "description": version.description,
        "visibility": version.visibility,
        "language": version.language,
        "metadata": version.metadata_json,
        "sections": [
            {
                "key": str(item.section_key),
                "type": item.section_type,
                "title": item.title,
                "body": item.body,
                "data": item.structured_data,
                "visibility": item.visibility,
                "accessibilityLabel": item.accessibility_label,
                "order": item.sort_order,
                "createdAt": item.created_at,
                "updatedAt": item.updated_at,
            }
            for item in sorted(sections, key=lambda row: row.sort_order)
        ],
        "objectives": [
            {
                "key": str(item.objective_key),
                "title": item.title,
                "description": item.description,
                "bloomLevel": item.bloom_level,
                "skills": item.linked_skill_keys,
                "assessmentCoverage": item.assessment_coverage,
                "practicalCoverage": item.practical_coverage,
                "reviewStatus": item.review_status,
            }
            for item in objectives
        ],
        "relationships": [
            {
                "id": str(item.id),
                "targetContentId": str(item.target_content_id),
                "targetVersionId": str(item.target_version_id) if item.target_version_id else None,
                "type": item.relation_type,
                "required": item.required,
                "order": item.sort_order,
                "configuration": item.configuration,
            }
            for item in sorted(relationships or [], key=lambda row: row.sort_order)
        ],
    }


def load_version_parts(
    db: DatabaseSession, version: CmsContentVersion
) -> tuple[list[CmsLessonSection], list[CmsLearningObjective]]:
    sections = list(
        db.scalars(
            select(CmsLessonSection)
            .where(CmsLessonSection.version_id == version.id)
            .order_by(CmsLessonSection.sort_order)
        ).all()
    )
    objectives = list(
        db.scalars(
            select(CmsLearningObjective).where(CmsLearningObjective.version_id == version.id)
        ).all()
    )
    return sections, objectives


def get_content(db: DatabaseSession, content_id: uuid.UUID) -> CmsContent:
    content = db.get(CmsContent, content_id)
    if content is None or content.deleted_at is not None:
        raise AppError(404, "cms_content_not_found", "Managed content was not found.")
    return content


def get_version(db: DatabaseSession, version_id: uuid.UUID) -> CmsContentVersion:
    version = db.get(CmsContentVersion, version_id)
    if version is None or version.soft_deleted_at is not None:
        raise AppError(404, "cms_version_not_found", "Content version was not found.")
    return version


def assert_scope(content: CmsContent, organization_id: uuid.UUID, platform_admin: bool) -> None:
    if not platform_admin and content.organization_id not in {None, organization_id}:
        raise AppError(404, "cms_content_not_found", "Managed content was not found.")


def assert_editable(version: CmsContentVersion) -> None:
    if version.lifecycle_status not in EDITABLE_STATES:
        raise AppError(
            409,
            "cms_version_immutable",
            "Only draft or revision-requested versions can be edited.",
        )


def _normalize_reference_url(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    parsed = urlsplit(value.strip())
    if parsed.scheme.casefold() != "https" or not parsed.hostname:
        return value.strip()
    host = parsed.hostname.casefold()
    try:
        port = parsed.port
    except ValueError:
        return value.strip()
    if port and port != 443:
        host = f"{host}:{port}"
    path = parsed.path or "/"
    return urlunsplit(("https", host, path, parsed.query, ""))


def _prepare_reference_metadata(
    db: DatabaseSession,
    content_type: str,
    metadata: dict[str, Any],
    content_scope: str,
    excluded_content_id: uuid.UUID | None = None,
) -> None:
    if content_type != "reference":
        return
    normalized = _normalize_reference_url(metadata.get("url"))
    if normalized is None:
        return
    metadata["url"] = normalized
    candidates = db.execute(
        select(CmsContentVersion.metadata_json, CmsContentVersion.content_id)
        .join(CmsContent, CmsContent.id == CmsContentVersion.content_id)
        .where(
            CmsContent.scope_key == content_scope,
            CmsContent.content_type == "reference",
            CmsContent.deleted_at.is_(None),
        )
    ).all()
    if any(
        content_id != excluded_content_id
        and _normalize_reference_url(candidate.get("url")) == normalized
        for candidate, content_id in candidates
    ):
        raise AppError(
            409,
            "cms_reference_duplicate",
            "A managed reference already uses that normalized URL.",
        )


def _replace_parts(
    db: DatabaseSession,
    content: CmsContent,
    version: CmsContentVersion,
    sections: list[Any],
    objectives: list[Any],
    relationships: list[Any],
) -> None:
    section_keys = [section.section_key for section in sections]
    objective_keys = [objective.objective_key for objective in objectives]
    section_orders = [section.sort_order for section in sections]
    if len(section_keys) != len(set(section_keys)):
        raise AppError(422, "cms_section_duplicate", "Structured block IDs must be unique.")
    if len(objective_keys) != len(set(objective_keys)):
        raise AppError(422, "cms_objective_duplicate", "Objective IDs must be unique.")
    if len(section_orders) != len(set(section_orders)):
        raise AppError(422, "cms_section_order_duplicate", "Structured block order must be unique.")
    existing_sections = {
        item.section_key: item
        for item in db.scalars(
            select(CmsLessonSection).where(CmsLessonSection.version_id == version.id)
        ).all()
    }
    existing_objectives = {
        item.objective_key: item
        for item in db.scalars(
            select(CmsLearningObjective).where(CmsLearningObjective.version_id == version.id)
        ).all()
    }
    stale_section_keys = set(existing_sections) - set(section_keys)
    stale_objective_keys = set(existing_objectives) - set(objective_keys)
    if stale_section_keys:
        db.execute(
            delete(CmsLessonSection).where(
                CmsLessonSection.version_id == version.id,
                CmsLessonSection.section_key.in_(stale_section_keys),
            )
        )
    if stale_objective_keys:
        db.execute(
            delete(CmsLearningObjective).where(
                CmsLearningObjective.version_id == version.id,
                CmsLearningObjective.objective_key.in_(stale_objective_keys),
            )
        )
    # Move retained rows out of the constrained ordering range before assigning
    # their new positions. This preserves row identity/timestamps without
    # transient unique-key collisions when two blocks swap places.
    for retained in existing_sections.values():
        if retained.section_key not in stale_section_keys:
            retained.sort_order += 1000
    db.flush()
    db.execute(delete(CmsContentRelation).where(CmsContentRelation.source_version_id == version.id))
    for section in sections:
        section_row = existing_sections.get(section.section_key)
        if section_row is None:
            section_row = CmsLessonSection(
                version_id=version.id,
                section_key=section.section_key,
            )
            db.add(section_row)
        section_row.section_type = section.section_type
        section_row.title = section.title
        section_row.body = section.body
        section_row.structured_data = section.structured_data
        section_row.visibility = section.visibility
        section_row.accessibility_label = section.accessibility_label
        section_row.sort_order = section.sort_order
    for objective in objectives:
        objective_row = existing_objectives.get(objective.objective_key)
        if objective_row is None:
            objective_row = CmsLearningObjective(
                version_id=version.id,
                objective_key=objective.objective_key,
            )
            db.add(objective_row)
        objective_row.title = objective.title
        objective_row.description = objective.description
        objective_row.bloom_level = objective.bloom_level
        objective_row.linked_skill_keys = objective.linked_skill_keys
        objective_row.assessment_coverage = objective.assessment_coverage
        objective_row.practical_coverage = objective.practical_coverage
        objective_row.review_status = objective.review_status
    seen_relations: set[tuple[uuid.UUID, str]] = set()
    for relationship in relationships:
        key = (relationship.target_content_id, relationship.relation_type)
        if key in seen_relations:
            raise AppError(422, "cms_relation_duplicate", "Duplicate content relationship.")
        seen_relations.add(key)
        target = get_content(db, relationship.target_content_id)
        if target.id == content.id:
            raise AppError(422, "cms_relation_self", "Content cannot depend on itself.")
        if target.organization_id not in {None, content.organization_id}:
            raise AppError(404, "cms_relation_target_missing", "Relationship target was not found.")
        if relationship.target_version_id:
            target_version = get_version(db, relationship.target_version_id)
            if target_version.content_id != target.id:
                raise AppError(
                    422,
                    "cms_relation_version_mismatch",
                    "Relationship version does not belong to the target content.",
                )
        db.add(
            CmsContentRelation(
                source_content_id=content.id,
                source_version_id=version.id,
                target_content_id=target.id,
                target_version_id=relationship.target_version_id,
                relation_type=relationship.relation_type,
                required=relationship.required,
                sort_order=relationship.sort_order,
                configuration=relationship.configuration,
            )
        )
    db.flush()
    rows, goals = load_version_parts(db, version)
    relation_rows = list(
        db.scalars(
            select(CmsContentRelation).where(CmsContentRelation.source_version_id == version.id)
        ).all()
    )
    version.content_checksum = canonical_checksum(
        version_payload(version, rows, goals, relation_rows)
    )


def create_content(
    db: DatabaseSession,
    payload: ContentCreateRequest,
    user_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> tuple[CmsContent, CmsContentVersion]:
    _prepare_reference_metadata(
        db,
        payload.content_type,
        payload.metadata,
        scope_key(organization_id),
    )
    existing = db.scalar(
        select(CmsContent.id).where(
            CmsContent.scope_key == scope_key(organization_id),
            CmsContent.public_slug == payload.public_slug,
            CmsContent.default_language == payload.language,
            CmsContent.deleted_at.is_(None),
        )
    )
    if existing:
        raise AppError(409, "cms_slug_conflict", "That active content slug already exists.")
    content = CmsContent(
        scope_key=scope_key(organization_id),
        organization_id=organization_id,
        content_type=payload.content_type,
        public_slug=payload.public_slug,
        title=payload.title,
        description=payload.description,
        lifecycle_status="draft",
        visibility=payload.visibility,
        owner_user_id=user_id,
        creator_user_id=user_id,
        default_language=payload.language,
        fallback_language=payload.fallback_language,
    )
    db.add(content)
    db.flush()
    version = CmsContentVersion(
        content_id=content.id,
        revision=1,
        version=payload.version,
        created_by_user_id=user_id,
        title=payload.title,
        public_slug=payload.public_slug,
        description=payload.description,
        lifecycle_status="draft",
        review_state="draft",
        visibility=payload.visibility,
        language=payload.language,
        change_summary=payload.change_summary,
        metadata_json=payload.metadata,
        content_checksum="pending",
    )
    db.add(version)
    db.flush()
    _replace_parts(
        db, content, version, payload.sections, payload.objectives, payload.relationships
    )
    return content, version


def update_content(
    db: DatabaseSession,
    content: CmsContent,
    version: CmsContentVersion,
    payload: ContentUpdateRequest,
) -> CmsContentVersion:
    assert_editable(version)
    _prepare_reference_metadata(
        db,
        content.content_type,
        payload.metadata,
        content.scope_key,
        content.id,
    )
    if version.lock_version != payload.expected_lock_version:
        raise AppError(
            409,
            "cms_edit_conflict",
            "A newer server revision exists. Reload before saving your changes.",
        )
    conflict = db.scalar(
        select(CmsContent.id).where(
            CmsContent.scope_key == content.scope_key,
            CmsContent.public_slug == payload.public_slug,
            CmsContent.default_language == content.default_language,
            CmsContent.id != content.id,
            CmsContent.deleted_at.is_(None),
        )
    )
    if conflict:
        raise AppError(409, "cms_slug_conflict", "That active content slug already exists.")
    version.title = payload.title
    version.public_slug = payload.public_slug
    version.description = payload.description
    version.visibility = payload.visibility
    version.change_summary = payload.change_summary
    version.metadata_json = payload.metadata
    version.lock_version += 1
    content.title = payload.title
    content.public_slug = payload.public_slug
    content.description = payload.description
    content.visibility = payload.visibility
    _replace_parts(
        db, content, version, payload.sections, payload.objectives, payload.relationships
    )
    return version


def validate_version(
    db: DatabaseSession, content: CmsContent, version: CmsContentVersion
) -> list[CmsValidationResult]:
    db.execute(delete(CmsValidationResult).where(CmsValidationResult.version_id == version.id))
    sections, objectives = load_version_parts(db, version)
    results: list[CmsValidationResult] = []

    def add(
        category: str,
        rule: str,
        severity: str,
        state: str,
        explanation: str,
        location: str | None = None,
        remediation: str | None = None,
    ) -> None:
        result = CmsValidationResult(
            version_id=version.id,
            category=category,
            rule_id=rule,
            severity=severity,
            state=state,
            field_location=location,
            explanation=explanation,
            remediation=remediation,
            created_at=datetime.now(UTC),
        )
        db.add(result)
        results.append(result)

    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", version.public_slug):
        add("schema", "slug.format", "error", "failure", "Slug format is invalid.", "slug")
    if not version.title.strip():
        add("schema", "title.required", "error", "failure", "Title is required.", "title")
    if content.content_type == "lesson":
        if not sections:
            add(
                "learning",
                "lesson.sections.required",
                "error",
                "failure",
                "A lesson requires at least one structured section.",
                "sections",
            )
        if not objectives:
            add(
                "learning",
                "lesson.objectives.required",
                "error",
                "failure",
                "A lesson requires structured learning objectives.",
                "objectives",
            )
        if not any(item.section_type == "references" for item in sections):
            add(
                "metadata",
                "lesson.references.required",
                "error",
                "failure",
                "A reviewed references section is required.",
                "sections",
            )
        if not version.metadata_json.get("skillKeys"):
            add(
                "learning",
                "lesson.skills.required",
                "error",
                "failure",
                "At least one skill mapping is required.",
                "metadata.skillKeys",
            )
        if not version.metadata_json.get("difficulty") or not version.metadata_json.get(
            "estimatedMinutes"
        ):
            add(
                "metadata",
                "lesson.metadata.required",
                "error",
                "failure",
                "Difficulty and estimated duration are required.",
                "metadata",
            )
    metadata = version.metadata_json

    def require_metadata(*keys: str) -> None:
        for key in keys:
            value = metadata.get(key)
            if value is None or value == "" or value == [] or value == {}:
                add(
                    "metadata",
                    f"{content.content_type}.{key}.required",
                    "error",
                    "failure",
                    f"{key.replace('_', ' ').replace('Minutes', ' minutes')} is required.",
                    f"metadata.{key}",
                )

    if content.content_type == "course":
        require_metadata(
            "summary",
            "audience",
            "difficulty",
            "estimatedMinutes",
            "outcomes",
            "skillKeys",
            "completionRule",
        )
    elif content.content_type == "module":
        require_metadata("purpose", "estimatedMinutes", "completionRule")
    elif content.content_type == "question":
        require_metadata("questionType", "prompt", "answerKey", "explanation", "skillKeys")
        allowed_question_types = {
            "single_choice",
            "multiple_choice",
            "true_false",
            "ordering",
            "matching",
            "command_interpretation",
            "log_interpretation",
            "scenario_decision",
            "short_response",
        }
        if metadata.get("questionType") not in allowed_question_types:
            add(
                "assessment",
                "question.type.invalid",
                "error",
                "failure",
                "Question type is not supported by the learner assessment contract.",
                "metadata.questionType",
            )
        if metadata.get("questionType") in {
            "single_choice",
            "multiple_choice",
            "ordering",
            "matching",
            "scenario_decision",
        } and not metadata.get("options"):
            add(
                "assessment",
                "question.options.required",
                "error",
                "failure",
                "This question type requires learner-visible options or items.",
                "metadata.options",
            )
    elif content.content_type == "assessment":
        require_metadata(
            "purpose",
            "instructions",
            "passingScore",
            "attemptLimit",
            "feedbackPolicy",
        )
        passing = metadata.get("passingScore")
        if not isinstance(passing, int | float) or not 0 <= passing <= 1:
            add(
                "assessment",
                "assessment.passing_score.invalid",
                "error",
                "failure",
                "Passing score must be between 0 and 1.",
                "metadata.passingScore",
            )
    elif content.content_type == "lab":
        require_metadata(
            "scenario",
            "difficulty",
            "estimatedMinutes",
            "allowedCommands",
            "commandResponses",
            "expectedEvidence",
            "validationRules",
            "hints",
            "completionRule",
        )
    elif content.content_type == "mission":
        require_metadata(
            "briefing",
            "fictionalOrganization",
            "learnerRole",
            "stages",
            "scoring",
            "completionRule",
        )
        stages = metadata.get("stages")
        if isinstance(stages, list):
            for index, stage in enumerate(stages):
                if not isinstance(stage, dict) or not all(
                    stage.get(key) for key in ("title", "goal", "evidence", "actions")
                ):
                    add(
                        "mission",
                        "mission.stage.invalid",
                        "error",
                        "failure",
                        "Every mission stage needs title, goal, evidence, and actions.",
                        f"metadata.stages.{index}",
                    )
    elif content.content_type == "learning_path":
        require_metadata("targetRole", "completionCriteria", "readinessCriteria")
    elif content.content_type == "skill":
        require_metadata("stableSkillId", "category", "evidenceRequirements")
    elif content.content_type == "reference":
        require_metadata("publisher", "url", "retrievalDate", "freshnessDays")
        url = metadata.get("url")
        if isinstance(url, str) and not url.startswith("https://"):
            add(
                "reference",
                "reference.url.https",
                "error",
                "failure",
                "Reference URLs must use HTTPS.",
                "metadata.url",
            )
        freshness_days = metadata.get("freshnessDays")
        verified = metadata.get("lastVerifiedDate") or metadata.get("retrievalDate")
        if isinstance(freshness_days, int | float) and freshness_days <= 0:
            add(
                "reference",
                "reference.freshness.invalid",
                "error",
                "failure",
                "Freshness interval must be greater than zero days.",
                "metadata.freshnessDays",
            )
        if isinstance(verified, str) and isinstance(freshness_days, int | float):
            try:
                verified_at = datetime.fromisoformat(verified.replace("Z", "+00:00"))
                if verified_at.tzinfo is None:
                    verified_at = verified_at.replace(tzinfo=UTC)
                if (datetime.now(UTC) - verified_at).days > freshness_days:
                    add(
                        "reference",
                        "reference.freshness.expired",
                        "warning",
                        "warning",
                        "This reference is past its verification freshness interval.",
                        "metadata.lastVerifiedDate",
                    )
            except ValueError:
                add(
                    "reference",
                    "reference.verified_date.invalid",
                    "error",
                    "failure",
                    "Reference verification date is invalid.",
                    "metadata.lastVerifiedDate",
                )
        if metadata.get("brokenLinkStatus") == "broken":
            add(
                "reference",
                "reference.link.broken",
                "error",
                "failure",
                "Broken references cannot be published.",
                "metadata.brokenLinkStatus",
            )
    for section in sections:
        combined = f"{section.title}\n{section.body}".casefold()
        if any(fragment in combined for fragment in UNSAFE_FRAGMENTS):
            add(
                "security",
                "content.active_markup",
                "error",
                "failure",
                "Unsafe active markup was detected.",
                f"sections.{section.section_key}",
            )
        if (
            section.section_type in {"image", "diagram_placeholder"}
            and not section.accessibility_label
        ):
            add(
                "accessibility",
                "media.description.required",
                "error",
                "failure",
                "Images and diagrams require accessibility text.",
                f"sections.{section.section_key}.accessibilityLabel",
            )
        if section.section_type not in {"image"} and not (
            section.title.strip() or section.body.strip()
        ):
            add(
                "content",
                "lesson.block.empty",
                "error",
                "failure",
                "Structured blocks cannot be empty.",
                f"sections.{section.section_key}",
            )
        if section.section_type == "heading" and not (
            section.title.strip() or section.body.strip()
        ):
            add(
                "content",
                "lesson.heading.required",
                "error",
                "failure",
                "Heading blocks require text.",
                f"sections.{section.section_key}",
            )
        if section.section_type == "code" and not section.structured_data.get("language"):
            add(
                "content",
                "lesson.code.language_required",
                "error",
                "failure",
                "Code blocks require a language.",
                f"sections.{section.section_key}.data.language",
            )
        if section.section_type == "table" and not isinstance(
            section.structured_data.get("rows"), list
        ):
            add(
                "content",
                "lesson.table.malformed",
                "error",
                "failure",
                "Table blocks require structured rows.",
                f"sections.{section.section_key}.data.rows",
            )
        if section.section_type == "references" and not section.body.strip():
            add(
                "reference",
                "lesson.reference.empty",
                "error",
                "failure",
                "Reference blocks require at least one reviewed reference.",
                f"sections.{section.section_key}.body",
            )
        if section.section_type == "knowledge_checkpoint" and not section.body.strip():
            add(
                "assessment",
                "lesson.checkpoint.prompt_required",
                "error",
                "failure",
                "Knowledge checkpoints require a prompt.",
                f"sections.{section.section_key}.body",
            )
    if sections and [item.sort_order for item in sections] != list(range(len(sections))):
        add(
            "content",
            "lesson.order.invalid",
            "error",
            "failure",
            "Structured block ordering must be consecutive.",
            "sections",
        )
    for objective in objectives:
        if not objective.linked_skill_keys:
            add(
                "learning",
                "objective.skill.required",
                "error",
                "failure",
                "Every objective requires at least one linked skill.",
                f"objectives.{objective.objective_key}",
            )
        if not objective.assessment_coverage and not objective.practical_coverage:
            add(
                "learning",
                "objective.coverage.missing",
                "warning",
                "warning",
                "The objective has no assessment or practical coverage.",
                f"objectives.{objective.objective_key}",
            )
    relations = list(
        db.scalars(
            select(CmsContentRelation).where(CmsContentRelation.source_version_id == version.id)
        ).all()
    )
    for relation in relations:
        target = db.get(CmsContent, relation.target_content_id)
        if target is None or target.deleted_at is not None:
            add(
                "relationship",
                "dependency.missing",
                "error",
                "failure",
                "A declared dependency is unavailable.",
                f"relationships.{relation.id}",
            )
        elif relation.required and target.lifecycle_status in {"archived", "deleted"}:
            add(
                "relationship",
                "dependency.inactive",
                "error",
                "failure",
                "A required dependency is archived or deleted.",
                f"relationships.{relation.id}",
            )
        elif relation.required and target.current_published_revision is None:
            add(
                "relationship",
                "dependency.unpublished",
                "error",
                "failure",
                "A required dependency is not published.",
                f"relationships.{relation.id}",
            )

    media_usages = list(
        db.scalars(select(CmsMediaUsage).where(CmsMediaUsage.version_id == version.id)).all()
    )
    for usage in media_usages:
        asset = db.get(CmsMediaAsset, usage.media_id)
        if asset is None or asset.deleted_at is not None or asset.status != "active":
            add(
                "media",
                "media.dependency.unavailable",
                "error",
                "failure",
                "A referenced media dependency is unavailable.",
                usage.location_key,
            )
        elif asset.media_type == "image" and not asset.accessibility_text:
            add(
                "accessibility",
                "media.dependency.alt_required",
                "error",
                "failure",
                "Referenced images require alternative text.",
                usage.location_key,
            )

    graph_relations = {"prerequisite", "parent_skill"}

    def reaches(start: uuid.UUID, target_id: uuid.UUID, visited: set[uuid.UUID]) -> bool:
        if start == target_id:
            return True
        if start in visited:
            return False
        visited.add(start)
        next_ids = db.scalars(
            select(CmsContentRelation.target_content_id).where(
                CmsContentRelation.source_content_id == start,
                CmsContentRelation.relation_type.in_(graph_relations),
            )
        ).all()
        return any(reaches(next_id, target_id, visited) for next_id in next_ids)

    for relation in relations:
        if relation.relation_type in graph_relations and reaches(
            relation.target_content_id, content.id, set()
        ):
            add(
                "relationship",
                "dependency.circular",
                "error",
                "failure",
                "This relationship would create a circular dependency.",
                f"relationships.{relation.id}",
            )
    if not results:
        add("integrity", "content.valid", "info", "pass", "All implemented checks passed.")
    db.flush()
    return results


def blocking_results(results: list[CmsValidationResult]) -> list[CmsValidationResult]:
    return [item for item in results if item.state == "failure" or item.severity == "error"]


def create_draft_from_version(
    db: DatabaseSession,
    source: CmsContentVersion,
    user_id: uuid.UUID,
    version_number: str,
    change_summary: str,
) -> CmsContentVersion:
    content = get_content(db, source.content_id)
    existing = db.scalar(
        select(CmsContentVersion.id).where(
            CmsContentVersion.content_id == content.id,
            CmsContentVersion.version == version_number,
        )
    )
    if existing:
        raise AppError(409, "cms_version_conflict", "That version number already exists.")
    next_revision = (
        int(
            db.scalar(
                select(func.max(CmsContentVersion.revision)).where(
                    CmsContentVersion.content_id == content.id
                )
            )
            or 0
        )
        + 1
    )
    draft = CmsContentVersion(
        content_id=content.id,
        revision=next_revision,
        version=version_number,
        parent_version_id=source.id,
        created_from_version_id=source.id,
        created_by_user_id=user_id,
        title=source.title,
        public_slug=source.public_slug,
        description=source.description,
        lifecycle_status="draft",
        review_state="draft",
        visibility=source.visibility,
        language=source.language,
        change_summary=change_summary,
        migration_notes=source.migration_notes,
        breaking_change=False,
        metadata_json=source.metadata_json,
        content_checksum="pending",
    )
    db.add(draft)
    db.flush()
    sections, objectives = load_version_parts(db, source)
    for section in sections:
        db.add(
            CmsLessonSection(
                version_id=draft.id,
                section_key=section.section_key,
                section_type=section.section_type,
                title=section.title,
                body=section.body,
                structured_data=section.structured_data,
                visibility=section.visibility,
                accessibility_label=section.accessibility_label,
                sort_order=section.sort_order,
            )
        )
    for objective in objectives:
        db.add(
            CmsLearningObjective(
                version_id=draft.id,
                objective_key=objective.objective_key,
                title=objective.title,
                description=objective.description,
                bloom_level=objective.bloom_level,
                linked_skill_keys=objective.linked_skill_keys,
                assessment_coverage=objective.assessment_coverage,
                practical_coverage=objective.practical_coverage,
                review_status="pending",
            )
        )
    for relation in db.scalars(
        select(CmsContentRelation).where(CmsContentRelation.source_version_id == source.id)
    ):
        db.add(
            CmsContentRelation(
                source_content_id=content.id,
                source_version_id=draft.id,
                target_content_id=relation.target_content_id,
                target_version_id=relation.target_version_id,
                relation_type=relation.relation_type,
                required=relation.required,
                sort_order=relation.sort_order,
                configuration=relation.configuration,
            )
        )
    db.flush()
    rows, goals = load_version_parts(db, draft)
    relation_rows = list(
        db.scalars(
            select(CmsContentRelation).where(CmsContentRelation.source_version_id == draft.id)
        ).all()
    )
    draft.content_checksum = canonical_checksum(version_payload(draft, rows, goals, relation_rows))
    if content.current_published_revision is None:
        content.lifecycle_status = "draft"
    return draft


def publish_version(
    db: DatabaseSession,
    content: CmsContent,
    version: CmsContentVersion,
    actor_user_id: uuid.UUID,
    reason: str,
    event_type: str = "published",
) -> None:
    results = validate_version(db, content, version)
    if blocking_results(results):
        raise AppError(409, "cms_publication_blocked", "Validation failures block publication.")
    required = required_reviewers_for_version(db, content.content_type, version)
    assignments = list(
        db.scalars(
            select(CmsReviewAssignment).where(CmsReviewAssignment.version_id == version.id)
        ).all()
    )
    approved = {item.reviewer_type for item in assignments if item.status == "approved"}
    if not required.issubset(approved):
        raise AppError(
            409, "cms_reviews_incomplete", "Required independent reviews are incomplete."
        )
    unresolved = db.scalar(
        select(func.count(CmsReviewComment.id)).where(
            CmsReviewComment.version_id == version.id,
            CmsReviewComment.severity == "blocking",
            CmsReviewComment.status == "open",
        )
    )
    if unresolved:
        raise AppError(
            409, "cms_comments_unresolved", "Blocking review comments remain unresolved."
        )
    # Resolve reusable dependencies to immutable versions at publication time.
    # Learner attempts can therefore continue to reproduce the exact content
    # even when a linked question, module, lab, or mission is published again.
    for relation in db.scalars(
        select(CmsContentRelation).where(CmsContentRelation.source_version_id == version.id)
    ):
        if relation.target_version_id is not None:
            continue
        target = db.get(CmsContent, relation.target_content_id)
        if target is None or target.current_published_revision is None:
            continue
        relation.target_version_id = db.scalar(
            select(CmsContentVersion.id).where(
                CmsContentVersion.content_id == target.id,
                CmsContentVersion.revision == target.current_published_revision,
                CmsContentVersion.lifecycle_status == "published",
            )
        )
    previous = db.scalar(
        select(CmsContentVersion).where(
            CmsContentVersion.content_id == content.id,
            CmsContentVersion.revision == content.current_published_revision,
        )
    )
    if previous is not None and previous.id != version.id:
        previous.lifecycle_status = "superseded"
    now = datetime.now(UTC)
    version.lifecycle_status = "published"
    version.review_state = "published"
    version.published_at = version.published_at or now
    version.scheduled_at = None
    content.current_published_revision = version.revision
    content.lifecycle_status = "published"
    content.visibility = "public"
    db.add(
        CmsPublicationEvent(
            content_id=content.id,
            version_id=version.id,
            event_type=event_type,
            actor_user_id=actor_user_id,
            reason=reason,
            status="succeeded",
            created_at=now,
        )
    )


def content_summary(db: DatabaseSession, content: CmsContent) -> dict[str, Any]:
    versions = list(
        db.scalars(
            select(CmsContentVersion)
            .where(CmsContentVersion.content_id == content.id)
            .order_by(CmsContentVersion.revision.desc())
        ).all()
    )
    latest = versions[0] if versions else None
    return {
        "id": str(content.id),
        "content_type": content.content_type,
        "title": content.title,
        "public_slug": content.public_slug,
        "description": content.description,
        "lifecycle_status": content.lifecycle_status,
        "visibility": content.visibility,
        "language": content.default_language,
        "current_published_revision": content.current_published_revision,
        "latest_version_id": str(latest.id) if latest else None,
        "latest_version": latest.version if latest else None,
        "latest_revision": latest.revision if latest else None,
        "review_state": latest.review_state if latest else None,
        "updated_at": content.updated_at,
    }


def version_detail(
    db: DatabaseSession, content: CmsContent, version: CmsContentVersion
) -> dict[str, Any]:
    sections, objectives = load_version_parts(db, version)
    reviews = list(
        db.scalars(
            select(CmsReviewAssignment).where(CmsReviewAssignment.version_id == version.id)
        ).all()
    )
    reviewer_type_by_user = {item.reviewer_user_id: item.reviewer_type for item in reviews}
    comments = list(
        db.scalars(
            select(CmsReviewComment)
            .where(CmsReviewComment.version_id == version.id)
            .order_by(CmsReviewComment.created_at)
        ).all()
    )
    decisions = list(
        db.scalars(
            select(CmsReviewDecision)
            .where(CmsReviewDecision.version_id == version.id)
            .order_by(CmsReviewDecision.decided_at)
        ).all()
    )
    validation = list(
        db.scalars(
            select(CmsValidationResult).where(CmsValidationResult.version_id == version.id)
        ).all()
    )
    relationships = list(
        db.scalars(
            select(CmsContentRelation)
            .where(CmsContentRelation.source_version_id == version.id)
            .order_by(CmsContentRelation.sort_order)
        ).all()
    )
    return {
        **content_summary(db, content),
        "version_id": str(version.id),
        "revision": version.revision,
        "version": version.version,
        "language": version.language,
        "lock_version": version.lock_version,
        "version_status": version.lifecycle_status,
        "review_state": version.review_state,
        "required_reviewer_types": sorted(
            required_reviewers_for_version(db, content.content_type, version)
        ),
        "change_summary": version.change_summary,
        "metadata": version.metadata_json,
        "checksum": version.content_checksum,
        "scheduled_at": version.scheduled_at,
        "schedule_timezone": version.schedule_timezone,
        "published_at": version.published_at,
        "sections": version_payload(version, sections, objectives)["sections"],
        "objectives": version_payload(version, sections, objectives)["objectives"],
        "relationships": version_payload(version, sections, objectives, relationships)[
            "relationships"
        ],
        "reviews": [
            {
                "id": str(item.id),
                "reviewer_type": item.reviewer_type,
                "reviewer_user_id": str(item.reviewer_user_id),
                "status": item.status,
                "decision": item.decision,
                "notes": item.notes,
                "checklist": item.checklist,
                "due_at": item.due_at,
            }
            for item in reviews
        ],
        "comments": [
            {
                "id": str(item.id),
                "parent_comment_id": str(item.parent_comment_id)
                if item.parent_comment_id
                else None,
                "author_user_id": str(item.author_user_id),
                "reviewer_type": reviewer_type_by_user.get(
                    item.author_user_id,
                    "content_author"
                    if item.author_user_id == version.created_by_user_id
                    else "cms_user",
                ),
                "body": item.body,
                "location_type": item.location_type,
                "location_key": item.location_key,
                "severity": item.severity,
                "suggested_change": item.suggested_change,
                "status": item.status,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
                "resolved_by_user_id": str(item.resolved_by_user_id)
                if item.resolved_by_user_id
                else None,
                "resolved_at": item.resolved_at,
            }
            for item in comments
        ],
        "review_history": [
            {
                "id": str(item.id),
                "assignment_id": str(item.assignment_id),
                "reviewer_user_id": str(item.reviewer_user_id),
                "reviewer_type": item.reviewer_type,
                "decision": item.decision,
                "notes": item.notes,
                "checklist": item.checklist,
                "decided_at": item.decided_at,
            }
            for item in decisions
        ],
        "validation": [
            {
                "category": item.category,
                "rule_id": item.rule_id,
                "severity": item.severity,
                "state": item.state,
                "field_location": item.field_location,
                "explanation": item.explanation,
                "remediation": item.remediation,
            }
            for item in validation
        ],
    }


def search_contents(
    db: DatabaseSession,
    organization_id: uuid.UUID,
    platform_admin: bool,
    query: str,
    content_type: str | None,
    status: str | None,
    page: int,
    page_size: int,
    review_state: str | None = None,
    author_user_id: uuid.UUID | None = None,
    tag: str | None = None,
    author: str | None = None,
    reviewer: str | None = None,
    skill: str | None = None,
    updated_after: datetime | None = None,
    updated_before: datetime | None = None,
    sort: str = "updated_desc",
) -> dict[str, Any]:
    filters: list[Any] = [CmsContent.deleted_at.is_(None)]
    if not platform_admin:
        filters.append(
            or_(CmsContent.organization_id == organization_id, CmsContent.organization_id.is_(None))
        )
    if query:
        pattern = f"%{query.strip()}%"
        filters.append(
            or_(
                CmsContent.title.ilike(pattern),
                CmsContent.public_slug.ilike(pattern),
                CmsContent.description.ilike(pattern),
            )
        )
    if content_type:
        filters.append(CmsContent.content_type == content_type)
    if status:
        filters.append(CmsContent.lifecycle_status == status)
    if author_user_id:
        filters.append(CmsContent.creator_user_id == author_user_id)
    if author:
        filters.append(
            CmsContent.creator_user_id.in_(
                select(User.id).where(User.email.ilike(f"%{author.strip()}%"))
            )
        )
    if reviewer:
        filters.append(
            CmsContent.id.in_(
                select(CmsContentVersion.content_id)
                .join(
                    CmsReviewAssignment,
                    CmsReviewAssignment.version_id == CmsContentVersion.id,
                )
                .where(
                    CmsReviewAssignment.reviewer_user_id.in_(
                        select(User.id).where(User.email.ilike(f"%{reviewer.strip()}%"))
                    )
                )
            )
        )
    if review_state:
        filters.append(
            CmsContent.id.in_(
                select(CmsContentVersion.content_id).where(
                    CmsContentVersion.review_state == review_state
                )
            )
        )
    if tag:
        filters.append(
            CmsContent.id.in_(
                select(CmsContentVersion.content_id).where(
                    cast(CmsContentVersion.metadata_json, String).ilike(f'%"{tag}"%')
                )
            )
        )
    if skill:
        filters.append(
            CmsContent.id.in_(
                select(CmsContentVersion.content_id).where(
                    cast(CmsContentVersion.metadata_json, String).ilike(f'%"{skill}"%')
                )
            )
        )
    if updated_after:
        filters.append(CmsContent.updated_at >= updated_after)
    if updated_before:
        filters.append(CmsContent.updated_at <= updated_before)
    total = int(db.scalar(select(func.count(CmsContent.id)).where(*filters)) or 0)
    order: Any = {
        "updated_asc": CmsContent.updated_at.asc(),
        "title_asc": CmsContent.title.asc(),
        "title_desc": CmsContent.title.desc(),
    }.get(sort, CmsContent.updated_at.desc())
    rows = list(
        db.scalars(
            select(CmsContent)
            .where(*filters)
            .order_by(order)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return {
        "items": [content_summary(db, item) for item in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
    }
