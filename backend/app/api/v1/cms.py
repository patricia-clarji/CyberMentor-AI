import hashlib
import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session as DatabaseSession

from app.cms.service import (
    REQUIRED_REVIEWERS,
    assert_editable,
    assert_scope,
    blocking_results,
    content_summary,
    create_content,
    create_draft_from_version,
    get_content,
    get_version,
    load_version_parts,
    publish_version,
    request_id,
    required_reviewers_for_version,
    search_contents,
    update_content,
    validate_version,
    version_detail,
    version_payload,
)
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.db.session import engine, get_db
from app.identity.dependencies import (
    AuthContext,
    assert_permission,
    permission_keys,
    require_auth,
    require_csrf,
)
from app.identity.service import audit
from app.learning.lab_terminal import execute_terminal
from app.learning.mission_service import evaluate_mission_action
from app.models import (
    AuditEvent,
    MembershipRole,
    Notification,
    OrganizationMembership,
    Permission,
    RolePermission,
    User,
)
from app.models.cms import (
    CmsApiKeyMetadata,
    CmsBackgroundJob,
    CmsContent,
    CmsContentRelation,
    CmsContentVersion,
    CmsFeatureFlag,
    CmsMaintenanceWindow,
    CmsMediaAsset,
    CmsMediaUsage,
    CmsPlatformSetting,
    CmsPublicationEvent,
    CmsReviewAssignment,
    CmsReviewComment,
    CmsReviewDecision,
    CmsReviewRequirement,
    CmsTranslation,
    CmsValidationResult,
)
from app.models.learning import LearningActivityAttempt
from app.schemas.cms import (
    CmsLabPreviewCommandRequest,
    CmsMissionPreviewActionRequest,
    CommentEditRequest,
    CommentStatusRequest,
    ContentCreateRequest,
    ContentUpdateRequest,
    DraftFromVersionRequest,
    FeatureFlagRequest,
    FeatureFlagUpdateRequest,
    JobActionRequest,
    ManagedAssessmentSubmissionRequest,
    PublishRequest,
    ReviewCommentRequest,
    ReviewDecisionRequest,
    ReviewerAssignmentRequest,
    ReviewRequirementRequest,
    RollbackRequest,
    ScheduleRequest,
    SkillMergeRequest,
)

router = APIRouter(prefix="/cms", tags=["content-management"])
public_router = APIRouter(prefix="/managed-content", tags=["managed-content"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_MEDIA = {
    "image/png": "image",
    "image/jpeg": "image",
    "image/webp": "image",
    "image/svg+xml": "image",
    "application/pdf": "document",
    "application/json": "data",
    "text/csv": "data",
}
MEDIA_EXTENSIONS = {
    "image/png": {".png"},
    "image/jpeg": {".jpg", ".jpeg"},
    "image/webp": {".webp"},
    "image/svg+xml": {".svg"},
    "application/pdf": {".pdf"},
    "application/json": {".json"},
    "text/csv": {".csv"},
}


def _utc(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=UTC)


def _flag_enabled(flag: CmsFeatureFlag, now: datetime) -> bool:
    starts_at = _utc(flag.starts_at)
    expires_at = _utc(flag.expires_at)
    return bool(
        flag.current_state
        and (starts_at is None or starts_at <= now)
        and (expires_at is None or expires_at > now)
    )


def _flag_expired(flag: CmsFeatureFlag, now: datetime) -> bool:
    expires_at = _utc(flag.expires_at)
    return bool(expires_at and expires_at < now)


def media_signature_valid(mime_type: str, data: bytes) -> bool:
    if mime_type == "image/png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if mime_type == "image/jpeg":
        return data.startswith(b"\xff\xd8\xff")
    if mime_type == "image/webp":
        return len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    if mime_type == "application/pdf":
        return data.startswith(b"%PDF-")
    if mime_type == "image/svg+xml":
        return b"<svg" in data[:2048].lower()
    if mime_type == "application/json":
        try:
            json.loads(data)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return False
    if mime_type == "text/csv":
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            return False
    return True


def require_permission(db: DatabaseSession, auth: AuthContext, permission: str) -> None:
    assert_permission(db, auth, permission)


def user_has_permission(
    db: DatabaseSession,
    user_id: uuid.UUID,
    organization_id: uuid.UUID,
    permission: str,
) -> bool:
    user = db.get(User, user_id)
    if user and user.is_platform_admin:
        return True
    value = db.scalar(
        select(Permission.id)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(MembershipRole, MembershipRole.role_id == RolePermission.role_id)
        .join(OrganizationMembership, OrganizationMembership.id == MembershipRole.membership_id)
        .where(
            Permission.key == permission,
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.is_active.is_(True),
        )
    )
    return value is not None


def notify(
    db: DatabaseSession,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    event_type: str,
    title: str,
    message: str,
    deep_link: str,
) -> None:
    existing = db.scalar(
        select(Notification.id).where(
            Notification.organization_id == organization_id,
            Notification.user_id == user_id,
            Notification.event_type == event_type,
            Notification.deep_link == deep_link,
        )
    )
    if existing is None:
        db.add(
            Notification(
                organization_id=organization_id,
                user_id=user_id,
                event_type=event_type,
                title=title,
                message=message,
                deep_link=deep_link,
            )
        )


def owned_version(
    db: DatabaseSession,
    auth: AuthContext,
    content_id: uuid.UUID,
    version_id: uuid.UUID,
) -> tuple[CmsContent, CmsContentVersion]:
    content = get_content(db, content_id)
    assert_scope(content, auth.organization_id, auth.user.is_platform_admin)
    version = get_version(db, version_id)
    if version.content_id != content.id:
        raise AppError(404, "cms_version_not_found", "Content version was not found.")
    return content, version


@router.get("/capabilities")
def capabilities(
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    require_permission(db, auth, "content.view")
    implemented = {
        "dashboard",
        "content-library",
        "lesson-manager",
        "review-queue",
        "publishing-center",
        "version-history",
        "search",
        "media-library",
        "content-validation",
        "feature-flags",
        "audit-logs",
        "system-health",
        "background-jobs",
        "data-dictionary",
        "operational-reports",
    }
    modules = [
        "dashboard",
        "content-library",
        "course-manager",
        "module-manager",
        "lesson-manager",
        "assessment-manager",
        "question-bank",
        "lab-manager",
        "mission-manager",
        "scenario-library",
        "skill-graph-manager",
        "learning-path-manager",
        "evidence-rules",
        "sentinel-knowledge-base",
        "media-library",
        "review-queue",
        "publishing-center",
        "version-history",
        "import-export",
        "search",
        "taxonomy-manager",
        "localization-manager",
        "platform-settings",
        "feature-flags",
        "audit-logs",
        "system-health",
        "background-jobs",
        "analytics-configuration",
        "notification-templates",
        "api-keys",
        "reference-sources",
        "content-validation",
        "maintenance-mode",
        "data-dictionary",
        "operational-reports",
    ]
    return {
        "permissions": sorted(permission_keys(db, auth)),
        "modules": [
            {
                "key": item,
                "status": "implemented" if item in implemented else "coming_soon",
            }
            for item in modules
        ],
    }


@router.get("/dashboard")
def dashboard(
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    require_permission(db, auth, "content.view")
    scope_filter = (
        []
        if auth.user.is_platform_admin
        else [
            or_(
                CmsContent.organization_id == auth.organization_id,
                CmsContent.organization_id.is_(None),
            )
        ]
    )
    counts = {
        status: int(
            db.scalar(
                select(func.count(CmsContent.id)).where(
                    CmsContent.deleted_at.is_(None),
                    CmsContent.lifecycle_status == status,
                    *scope_filter,
                )
            )
            or 0
        )
        for status in [
            "draft",
            "in_review",
            "approved",
            "scheduled",
            "published",
            "deprecated",
            "archived",
        ]
    }
    pending_reviews = int(
        db.scalar(
            select(func.count(CmsReviewAssignment.id)).where(
                CmsReviewAssignment.status.in_(["assigned", "in_review"])
            )
        )
        or 0
    )
    validation_failures = int(
        db.scalar(
            select(func.count(CmsValidationResult.id)).where(CmsValidationResult.state == "failure")
        )
        or 0
    )
    failed_jobs = int(
        db.scalar(
            select(func.count(CmsBackgroundJob.id)).where(
                CmsBackgroundJob.status == "failed",
                *(
                    []
                    if auth.user.is_platform_admin
                    else [CmsBackgroundJob.organization_id == auth.organization_id]
                ),
            )
        )
        or 0
    )
    recent = list(
        db.scalars(
            select(CmsContent)
            .where(CmsContent.deleted_at.is_(None), *scope_filter)
            .order_by(CmsContent.updated_at.desc())
            .limit(6)
        ).all()
    )
    recent_audit = list(
        db.scalars(
            select(AuditEvent)
            .where(
                or_(
                    AuditEvent.organization_id == auth.organization_id,
                    AuditEvent.organization_id.is_(None),
                )
            )
            .order_by(AuditEvent.created_at.desc())
            .limit(8)
        ).all()
    )
    migration = None
    database_status = "unavailable"
    try:
        with engine.connect() as connection:
            migration = connection.exec_driver_sql(
                "SELECT version_num FROM alembic_version"
            ).scalar_one()
            database_status = "healthy"
    except Exception:
        database_status = "unavailable"
    return {
        "generated_at": datetime.now(UTC),
        "counts": counts,
        "pending_reviews": pending_reviews,
        "validation_failures": validation_failures,
        "failed_jobs": failed_jobs,
        "worker_status": "unknown",
        "queue_size": None,
        "search_index_status": "database_search_active",
        "storage_usage_bytes": int(
            db.scalar(select(func.coalesce(func.sum(CmsMediaAsset.file_size), 0))) or 0
        ),
        "media_assets": int(db.scalar(select(func.count(CmsMediaAsset.id))) or 0),
        "platform_version": "0.1.0",
        "migration_version": migration,
        "database_status": database_status,
        "api_status": "healthy",
        "recent_content": [content_summary(db, item) for item in recent],
        "recent_audit": [
            {
                "id": str(item.id),
                "action": item.action,
                "outcome": item.outcome,
                "target_type": item.target_type,
                "target_id": item.target_id,
                "created_at": item.created_at,
            }
            for item in recent_audit
        ],
    }


@router.get("/contents")
def list_contents(
    q: str = "",
    content_type: str | None = None,
    status: str | None = None,
    review_state: str | None = None,
    author_user_id: uuid.UUID | None = None,
    tag: str | None = None,
    author: str | None = None,
    reviewer: str | None = None,
    skill: str | None = None,
    updated_after: datetime | None = None,
    updated_before: datetime | None = None,
    sort: str = Query(
        default="updated_desc", pattern="^(updated_desc|updated_asc|title_asc|title_desc)$"
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    require_permission(db, auth, "content.view")
    return search_contents(
        db,
        auth.organization_id,
        auth.user.is_platform_admin,
        q,
        content_type,
        status,
        page,
        page_size,
        review_state,
        author_user_id,
        tag,
        author,
        reviewer,
        skill,
        updated_after,
        updated_before,
        sort,
    )


@router.post("/contents", status_code=201)
def create_managed_content(
    payload: ContentCreateRequest,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    require_permission(db, auth, "content.create")
    if payload.content_type == "reference":
        require_permission(db, auth, "content.references.manage")
    if payload.content_type == "skill":
        require_permission(db, auth, "content.skills.manage")
    content, version = create_content(db, payload, auth.user.id, auth.organization_id)
    audit(
        db,
        "cms.content.create",
        "success",
        auth.user.id,
        auth.organization_id,
        request_id(request),
        "cms_content",
        str(content.id),
        json.dumps({"type": content.content_type, "revision": version.revision}),
    )
    db.commit()
    return version_detail(db, content, version)


@router.get("/contents/{content_id}")
def get_managed_content(
    content_id: uuid.UUID,
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    require_permission(db, auth, "content.view")
    content = get_content(db, content_id)
    assert_scope(content, auth.organization_id, auth.user.is_platform_admin)
    versions = list(
        db.scalars(
            select(CmsContentVersion)
            .where(CmsContentVersion.content_id == content.id)
            .order_by(CmsContentVersion.revision.desc())
            .limit(100)
        ).all()
    )
    return {
        **content_summary(db, content),
        "versions": [
            {
                "id": str(item.id),
                "revision": item.revision,
                "version": item.version,
                "status": item.lifecycle_status,
                "review_state": item.review_state,
                "checksum": item.content_checksum,
                "change_summary": item.change_summary,
                "created_at": item.created_at,
                "published_at": item.published_at,
            }
            for item in versions
        ],
    }


@router.post("/contents/{content_id}/archive")
def archive_managed_content(
    content_id: uuid.UUID,
    payload: PublishRequest,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    require_permission(db, auth, "content.archive")
    content = get_content(db, content_id)
    assert_scope(content, auth.organization_id, auth.user.is_platform_admin)
    content.lifecycle_status = "archived"
    content.visibility = "private"
    versions = db.scalars(
        select(CmsContentVersion).where(
            CmsContentVersion.content_id == content.id,
            CmsContentVersion.lifecycle_status.in_(["draft", "revision_requested"]),
        )
    ).all()
    for version in versions:
        version.lifecycle_status = "archived"
    audit(
        db,
        "cms.content.archive",
        "success",
        auth.user.id,
        auth.organization_id,
        request_id(request),
        "cms_content",
        str(content.id),
        json.dumps({"reason": payload.reason}),
    )
    db.commit()
    return content_summary(db, content)


@router.post("/contents/{content_id}/merge-skill")
def merge_managed_skill(
    content_id: uuid.UUID,
    payload: SkillMergeRequest,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    require_permission(db, auth, "content.skills.manage")
    require_permission(db, auth, "content.archive")
    source = get_content(db, content_id)
    target = get_content(db, payload.target_skill_id)
    assert_scope(source, auth.organization_id, auth.user.is_platform_admin)
    assert_scope(target, auth.organization_id, auth.user.is_platform_admin)
    if source.content_type != "skill" or target.content_type != "skill":
        raise AppError(422, "cms_skill_merge_type", "Only managed skills can be merged.")
    if source.id == target.id:
        raise AppError(422, "cms_skill_merge_self", "A skill cannot be merged into itself.")
    editable_relations = list(
        db.scalars(
            select(CmsContentRelation)
            .join(CmsContentVersion, CmsContentVersion.id == CmsContentRelation.source_version_id)
            .where(
                CmsContentRelation.target_content_id == source.id,
                CmsContentVersion.lifecycle_status.in_(["draft", "revision_requested"]),
            )
        ).all()
    )
    migrated = 0
    removed_duplicates = 0
    for relation in editable_relations:
        duplicate = db.scalar(
            select(CmsContentRelation.id).where(
                CmsContentRelation.source_version_id == relation.source_version_id,
                CmsContentRelation.target_content_id == target.id,
                CmsContentRelation.relation_type == relation.relation_type,
                CmsContentRelation.id != relation.id,
            )
        )
        if duplicate:
            db.delete(relation)
            removed_duplicates += 1
        else:
            relation.target_content_id = target.id
            relation.target_version_id = None
            migrated += 1
    source.replacement_content_id = target.id
    source.lifecycle_status = "archived"
    source.visibility = "private"
    audit(
        db,
        "cms.skill.merge",
        "success",
        auth.user.id,
        auth.organization_id,
        request_id(request),
        "cms_content",
        str(source.id),
        json.dumps(
            {
                "targetSkillId": str(target.id),
                "reason": payload.reason,
                "draftRelationsMigrated": migrated,
                "duplicatesRemoved": removed_duplicates,
                "publishedHistoryPreserved": True,
            }
        ),
    )
    db.commit()
    return {
        "status": "merged",
        "source_skill_id": str(source.id),
        "target_skill_id": str(target.id),
        "draft_relations_migrated": migrated,
        "duplicates_removed": removed_duplicates,
        "published_history_preserved": True,
    }


@router.get("/contents/{content_id}/versions/{version_id}")
def get_managed_version(
    content_id: uuid.UUID,
    version_id: uuid.UUID,
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    require_permission(db, auth, "content.view")
    content, version = owned_version(db, auth, content_id, version_id)
    return version_detail(db, content, version)


def learner_preview_payload(detail: dict[str, Any]) -> dict[str, Any]:
    private_keys = {
        "answerKey",
        "acceptedAnswers",
        "explanation",
        "evaluatorGuidance",
        "partialCreditRules",
        "privateRubric",
        "scoringRules",
        "validationRules",
        "commandResponses",
        "expectedActions",
    }

    def cleanse(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: cleanse(item) for key, item in value.items() if key not in private_keys}
        if isinstance(value, list):
            return [cleanse(item) for item in value]
        return value

    return cast(
        dict[str, Any],
        cleanse(
            {
                "content_type": detail["content_type"],
                "content_id": detail["id"],
                "version_id": detail["version_id"],
                "title": detail["title"],
                "public_slug": detail["public_slug"],
                "description": detail["description"],
                "version": detail["version"],
                "version_status": detail["version_status"],
                "metadata": detail["metadata"],
                "sections": detail["sections"],
                "objectives": [
                    {key: value for key, value in objective.items() if key != "reviewStatus"}
                    for objective in detail["objectives"]
                ],
            },
        ),
    )


@router.get("/contents/{content_id}/versions/{version_id}/preview")
def preview_managed_version(
    content_id: uuid.UUID,
    version_id: uuid.UUID,
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    require_permission(db, auth, "content.view")
    content, version = owned_version(db, auth, content_id, version_id)
    return {
        "preview": True,
        "draft": version.lifecycle_status != "published",
        "content": learner_preview_payload(version_detail(db, content, version)),
    }


@router.post("/contents/{content_id}/versions/{version_id}/test-lab/command")
def test_draft_lab_command(
    content_id: uuid.UUID,
    version_id: uuid.UUID,
    payload: CmsLabPreviewCommandRequest,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    require_permission(db, auth, "content.edit_draft")
    content, version = owned_version(db, auth, content_id, version_id)
    if content.content_type != "lab":
        raise AppError(409, "cms_preview_type_invalid", "This content is not a lab.")
    assert_editable(version)
    metadata = version.metadata_json
    files = metadata.get("virtualFiles", [])
    allowed_commands = metadata.get("allowedCommands", [])
    if not isinstance(files, list) or not isinstance(allowed_commands, list):
        raise AppError(
            422, "cms_lab_configuration_invalid", "Lab terminal configuration is invalid."
        )
    result = execute_terminal(
        payload.command,
        cwd=payload.cwd,
        files=files,
        processes=metadata.get("processes", []),
        connections=metadata.get("connections", []),
        allowed_tools=set(allowed_commands),
    )
    custom = metadata.get("commandResponses", {}).get(payload.command)
    return {
        "preview": True,
        "creates_evidence": False,
        "command": result.command,
        "cwd": result.cwd,
        "exit_code": result.exit_code,
        "output": custom if isinstance(custom, str) else result.output,
    }


@router.get("/contents/{content_id}/versions/{version_id}/test-mission")
def test_draft_mission(
    content_id: uuid.UUID,
    version_id: uuid.UUID,
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    require_permission(db, auth, "content.view")
    content, version = owned_version(db, auth, content_id, version_id)
    if content.content_type != "mission":
        raise AppError(409, "cms_preview_type_invalid", "This content is not a mission.")
    if version.lifecycle_status == "published":
        raise AppError(409, "cms_preview_not_draft", "Use learner delivery for published missions.")
    safe = learner_preview_payload(version_detail(db, content, version))
    return {
        "preview": True,
        "creates_evidence": False,
        "mission": safe,
    }


@router.post("/contents/{content_id}/versions/{version_id}/test-mission/action")
def test_draft_mission_action(
    content_id: uuid.UUID,
    version_id: uuid.UUID,
    payload: CmsMissionPreviewActionRequest,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    require_permission(db, auth, "content.edit_draft")
    content, version = owned_version(db, auth, content_id, version_id)
    if content.content_type != "mission":
        raise AppError(409, "cms_preview_type_invalid", "This content is not a mission.")
    assert_editable(version)
    stages = version.metadata_json.get("stages", [])
    if not isinstance(stages, list):
        raise AppError(422, "cms_mission_configuration_invalid", "Mission stages are invalid.")
    stage_index = next(
        (
            index
            for index, item in enumerate(stages)
            if isinstance(item, dict) and str(item.get("id")) == payload.stage_id
        ),
        None,
    )
    if stage_index is None:
        raise AppError(404, "cms_mission_stage_missing", "Draft mission stage was not found.")
    stage = cast(dict[str, Any], stages[stage_index])
    evidence = [str(item) for item in stage.get("evidence", [])]
    actions = [str(item) for item in stage.get("actions", [])]
    definition = {
        "resources": [{"id": item, "content": item} for item in evidence],
        "actions": [{"id": item} for item in actions],
        "required_action": str(stage.get("requiredAction") or (actions[0] if actions else "")),
        "alternative_valid_actions": [str(item) for item in stage.get("alternativeActions", [])],
    }
    outcome, feedback, resource_content, advances = evaluate_mission_action(
        definition,
        payload.action_type,
        payload.resource_id,
        payload.decision_id,
    )
    return {
        "preview": True,
        "creates_evidence": False,
        "outcome": outcome,
        "feedback": feedback,
        "resource_content": resource_content,
        "stage_index": stage_index,
        "next_stage_index": min(stage_index + 1, len(stages) - 1) if advances else stage_index,
        "mission_ready": advances and stage_index == len(stages) - 1,
    }


@router.put("/contents/{content_id}/versions/{version_id}")
def save_managed_version(
    content_id: uuid.UUID,
    version_id: uuid.UUID,
    payload: ContentUpdateRequest,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    require_permission(db, auth, "content.edit_draft")
    content, version = owned_version(db, auth, content_id, version_id)
    if content.content_type == "reference":
        require_permission(db, auth, "content.references.manage")
    if content.content_type == "skill":
        require_permission(db, auth, "content.skills.manage")
    update_content(db, content, version, payload)
    audit(
        db,
        "cms.content.edit",
        "success",
        auth.user.id,
        auth.organization_id,
        request_id(request),
        "cms_content_version",
        str(version.id),
        json.dumps({"lockVersion": version.lock_version, "checksum": version.content_checksum}),
    )
    db.commit()
    return version_detail(db, content, version)


@router.post("/contents/{content_id}/versions/{version_id}/draft", status_code=201)
def draft_from_version(
    content_id: uuid.UUID,
    version_id: uuid.UUID,
    payload: DraftFromVersionRequest,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    require_permission(db, auth, "content.create_version")
    content, source = owned_version(db, auth, content_id, version_id)
    draft = create_draft_from_version(
        db, source, auth.user.id, payload.version, payload.change_summary
    )
    audit(
        db,
        "cms.version.create",
        "success",
        auth.user.id,
        auth.organization_id,
        request_id(request),
        "cms_content_version",
        str(draft.id),
        json.dumps({"fromRevision": source.revision, "revision": draft.revision}),
    )
    db.commit()
    return version_detail(db, content, draft)


@router.post("/contents/{content_id}/versions/{version_id}/validate")
def validate_managed_version(
    content_id: uuid.UUID,
    version_id: uuid.UUID,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    require_permission(db, auth, "content.validate")
    content, version = owned_version(db, auth, content_id, version_id)
    results = validate_version(db, content, version)
    failures = len(blocking_results(results))
    audit(
        db,
        "cms.content.validate",
        "failure" if failures else "success",
        auth.user.id,
        auth.organization_id,
        request_id(request),
        "cms_content_version",
        str(version.id),
        json.dumps({"failures": failures, "results": len(results)}),
    )
    db.commit()
    return {"failures": failures, "results": version_detail(db, content, version)["validation"]}


@router.post("/contents/{content_id}/versions/{version_id}/submit-review")
def submit_review(
    content_id: uuid.UUID,
    version_id: uuid.UUID,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    require_permission(db, auth, "content.submit_review")
    content, version = owned_version(db, auth, content_id, version_id)
    assert_editable(version)
    results = validate_version(db, content, version)
    if blocking_results(results):
        raise AppError(409, "cms_review_blocked", "Resolve validation failures first.")
    version.lifecycle_status = "in_review"
    version.review_state = "ready_for_review"
    content.lifecycle_status = "in_review"
    audit(
        db,
        "cms.review.submit",
        "success",
        auth.user.id,
        auth.organization_id,
        request_id(request),
        "cms_content_version",
        str(version.id),
    )
    db.commit()
    return version_detail(db, content, version)


@router.post("/contents/{content_id}/versions/{version_id}/reviewers", status_code=201)
def assign_reviewer(
    content_id: uuid.UUID,
    version_id: uuid.UUID,
    payload: ReviewerAssignmentRequest,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    require_permission(db, auth, "content.assign_reviewer")
    content, version = owned_version(db, auth, content_id, version_id)
    if version.lifecycle_status != "in_review":
        raise AppError(409, "cms_review_state_invalid", "Submit this version for review first.")
    reviewer = db.scalar(select(User).where(User.email == payload.reviewer_email.casefold()))
    if reviewer is None or not user_has_permission(
        db, reviewer.id, auth.organization_id, "content.review"
    ):
        raise AppError(
            400, "cms_reviewer_invalid", "The selected user is not an authorized reviewer."
        )
    if reviewer.id == version.created_by_user_id:
        raise AppError(409, "cms_self_review_denied", "Authors cannot review their own version.")
    assignment = db.scalar(
        select(CmsReviewAssignment).where(
            CmsReviewAssignment.version_id == version.id,
            CmsReviewAssignment.reviewer_type == payload.reviewer_type,
        )
    )
    if assignment is None:
        assignment = CmsReviewAssignment(
            version_id=version.id,
            reviewer_type=payload.reviewer_type,
            reviewer_user_id=reviewer.id,
            assigned_by_user_id=auth.user.id,
            status="assigned",
            due_at=payload.due_at,
        )
        db.add(assignment)
    else:
        assignment.reviewer_user_id = reviewer.id
        assignment.assigned_by_user_id = auth.user.id
        assignment.status = "assigned"
        assignment.decision = None
        assignment.notes = None
        assignment.due_at = payload.due_at
    version.review_state = "review_assigned"
    notify(
        db,
        auth.organization_id,
        reviewer.id,
        "cms_review_assigned",
        "Content review assigned",
        f"Review {version.title} as {payload.reviewer_type.replace('_', ' ')}.",
        f"/admin/reviews/{content.id}/{version.id}",
    )
    audit(
        db,
        "cms.review.assign",
        "success",
        auth.user.id,
        auth.organization_id,
        request_id(request),
        "cms_review_assignment",
        str(assignment.id),
        json.dumps({"reviewerType": payload.reviewer_type, "reviewer": str(reviewer.id)}),
    )
    db.commit()
    return version_detail(db, content, version)


@router.delete("/contents/{content_id}/versions/{version_id}/reviewers/{assignment_id}")
def remove_reviewer(
    content_id: uuid.UUID,
    version_id: uuid.UUID,
    assignment_id: uuid.UUID,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    require_permission(db, auth, "content.assign_reviewer")
    content, version = owned_version(db, auth, content_id, version_id)
    assignment = db.scalar(
        select(CmsReviewAssignment).where(
            CmsReviewAssignment.id == assignment_id,
            CmsReviewAssignment.version_id == version.id,
        )
    )
    if assignment is None:
        raise AppError(404, "cms_review_assignment_not_found", "Review assignment was not found.")
    if assignment.status == "approved":
        raise AppError(
            409, "cms_review_assignment_immutable", "Approved reviews cannot be removed."
        )
    db.delete(assignment)
    audit(
        db,
        "cms.review.unassign",
        "success",
        auth.user.id,
        auth.organization_id,
        request_id(request),
        "cms_review_assignment",
        str(assignment_id),
    )
    db.commit()
    return version_detail(db, content, version)


@router.get("/review-requirements")
def list_review_requirements(
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> list[dict[str, Any]]:
    require_permission(db, auth, "content.view")
    configured = list(
        db.scalars(
            select(CmsReviewRequirement).order_by(
                CmsReviewRequirement.content_type, CmsReviewRequirement.reviewer_type
            )
        ).all()
    )
    if configured:
        return [
            {
                "id": str(item.id),
                "content_type": item.content_type,
                "reviewer_type": item.reviewer_type,
                "required": item.required,
                "active": item.active,
            }
            for item in configured
        ]
    return [
        {
            "id": None,
            "content_type": content_type,
            "reviewer_type": reviewer_type,
            "required": True,
            "active": True,
        }
        for content_type, reviewer_types in sorted(REQUIRED_REVIEWERS.items())
        for reviewer_type in sorted(reviewer_types)
    ]


@router.put("/review-requirements")
def upsert_review_requirement(
    payload: ReviewRequirementRequest,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    require_permission(db, auth, "content.assign_reviewer")
    item = db.scalar(
        select(CmsReviewRequirement).where(
            CmsReviewRequirement.content_type == payload.content_type,
            CmsReviewRequirement.reviewer_type == payload.reviewer_type,
        )
    )
    if item is None:
        item = CmsReviewRequirement(
            content_type=payload.content_type,
            reviewer_type=payload.reviewer_type,
            required=payload.required,
            active=payload.active,
            created_by_user_id=auth.user.id,
        )
        db.add(item)
        db.flush()
    else:
        item.required = payload.required
        item.active = payload.active
    audit(
        db,
        "cms.review.requirement_update",
        "success",
        auth.user.id,
        auth.organization_id,
        request_id(request),
        "cms_review_requirement",
        str(item.id),
        json.dumps(payload.model_dump()),
    )
    db.commit()
    return {
        "id": str(item.id),
        "content_type": item.content_type,
        "reviewer_type": item.reviewer_type,
        "required": item.required,
        "active": item.active,
    }


@router.post("/contents/{content_id}/versions/{version_id}/comments", status_code=201)
def add_review_comment(
    content_id: uuid.UUID,
    version_id: uuid.UUID,
    payload: ReviewCommentRequest,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    if not user_has_permission(
        db, auth.user.id, auth.organization_id, "content.review"
    ) and not user_has_permission(db, auth.user.id, auth.organization_id, "content.edit_draft"):
        raise AppError(403, "permission_denied", "A required permission is missing.")
    content, version = owned_version(db, auth, content_id, version_id)
    if payload.parent_comment_id:
        parent = db.get(CmsReviewComment, payload.parent_comment_id)
        if parent is None or parent.version_id != version.id:
            raise AppError(404, "cms_comment_not_found", "Parent review comment was not found.")
    comment = CmsReviewComment(
        version_id=version.id,
        parent_comment_id=payload.parent_comment_id,
        author_user_id=auth.user.id,
        body=payload.body,
        location_type=payload.location_type,
        location_key=payload.location_key,
        severity=payload.severity,
        suggested_change=payload.suggested_change,
        status="open",
    )
    db.add(comment)
    audit(
        db,
        "cms.review.comment",
        "success",
        auth.user.id,
        auth.organization_id,
        request_id(request),
        "cms_review_comment",
        str(comment.id),
        json.dumps({"severity": payload.severity, "location": payload.location_key}),
    )
    db.commit()
    return version_detail(db, content, version)


@router.patch("/comments/{comment_id}")
def update_comment_status(
    comment_id: uuid.UUID,
    payload: CommentStatusRequest,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    if not user_has_permission(
        db, auth.user.id, auth.organization_id, "content.review"
    ) and not user_has_permission(db, auth.user.id, auth.organization_id, "content.edit_draft"):
        raise AppError(403, "permission_denied", "A required permission is missing.")
    comment = db.get(CmsReviewComment, comment_id)
    if comment is None:
        raise AppError(404, "cms_comment_not_found", "Review comment was not found.")
    version = get_version(db, comment.version_id)
    content = get_content(db, version.content_id)
    assert_scope(content, auth.organization_id, auth.user.is_platform_admin)
    comment.status = "resolved" if payload.resolved else "open"
    comment.resolved_at = datetime.now(UTC) if payload.resolved else None
    comment.resolved_by_user_id = auth.user.id if payload.resolved else None
    audit(
        db,
        "cms.review.comment_resolve" if payload.resolved else "cms.review.comment_reopen",
        "success",
        auth.user.id,
        auth.organization_id,
        request_id(request),
        "cms_review_comment",
        str(comment.id),
    )
    db.commit()
    return {"id": str(comment.id), "status": comment.status}


@router.put("/comments/{comment_id}")
def edit_review_comment(
    comment_id: uuid.UUID,
    payload: CommentEditRequest,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    if not user_has_permission(
        db, auth.user.id, auth.organization_id, "content.review"
    ) and not user_has_permission(db, auth.user.id, auth.organization_id, "content.edit_draft"):
        raise AppError(403, "permission_denied", "A required permission is missing.")
    comment = db.get(CmsReviewComment, comment_id)
    if comment is None or comment.author_user_id != auth.user.id:
        raise AppError(404, "cms_comment_not_found", "Editable review comment was not found.")
    if comment.status != "open":
        raise AppError(409, "cms_comment_resolved", "Resolved comments cannot be edited.")
    version = get_version(db, comment.version_id)
    content = get_content(db, version.content_id)
    assert_scope(content, auth.organization_id, auth.user.is_platform_admin)
    comment.body = payload.body
    comment.suggested_change = payload.suggested_change
    audit(
        db,
        "cms.review.comment_edit",
        "success",
        auth.user.id,
        auth.organization_id,
        request_id(request),
        "cms_review_comment",
        str(comment.id),
    )
    db.commit()
    return {"id": str(comment.id), "body": comment.body, "updated_at": comment.updated_at}


@router.post("/reviewers/{assignment_id}/start")
def start_review(
    assignment_id: uuid.UUID,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    require_permission(db, auth, "content.review")
    assignment = db.get(CmsReviewAssignment, assignment_id)
    if assignment is None or assignment.reviewer_user_id != auth.user.id:
        raise AppError(404, "cms_review_not_found", "Assigned review was not found.")
    version = get_version(db, assignment.version_id)
    content = get_content(db, version.content_id)
    assert_scope(content, auth.organization_id, auth.user.is_platform_admin)
    if assignment.status != "assigned":
        raise AppError(409, "cms_review_state_invalid", "Only assigned reviews can be started.")
    assignment.status = "in_review"
    audit(
        db,
        "cms.review.start",
        "success",
        auth.user.id,
        auth.organization_id,
        request_id(request),
        "cms_review_assignment",
        str(assignment.id),
    )
    db.commit()
    return {"id": str(assignment.id), "status": assignment.status}


@router.post("/contents/{content_id}/versions/{version_id}/decision")
def decide_review(
    content_id: uuid.UUID,
    version_id: uuid.UUID,
    payload: ReviewDecisionRequest,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    require_permission(db, auth, "content.review")
    content, version = owned_version(db, auth, content_id, version_id)
    if version.created_by_user_id == auth.user.id:
        raise AppError(409, "cms_self_review_denied", "Authors cannot approve their own version.")
    assignment = db.scalar(
        select(CmsReviewAssignment).where(
            CmsReviewAssignment.version_id == version.id,
            CmsReviewAssignment.reviewer_user_id == auth.user.id,
            CmsReviewAssignment.status.in_(["assigned", "in_review", "changes_requested"]),
        )
    )
    if assignment is None:
        raise AppError(403, "cms_review_not_assigned", "No active review is assigned to you.")
    if payload.decision == "approve":
        validation = validate_version(db, content, version)
        if blocking_results(validation):
            raise AppError(
                409,
                "cms_approval_validation_failed",
                "Approval is blocked until server-side content validation passes.",
            )
    if payload.decision == "approve" and any(
        item.get("required") and not item.get("passed") for item in payload.checklist
    ):
        raise AppError(409, "cms_checklist_failed", "Required review checklist items must pass.")
    now = datetime.now(UTC)
    assignment.decision = payload.decision
    assignment.notes = payload.notes
    assignment.checklist = payload.checklist
    assignment.decided_at = now
    assignment.status = {
        "approve": "approved",
        "request_changes": "changes_requested",
        "reject": "rejected",
    }[payload.decision]
    db.add(
        CmsReviewDecision(
            version_id=version.id,
            assignment_id=assignment.id,
            reviewer_user_id=auth.user.id,
            reviewer_type=assignment.reviewer_type,
            decision=payload.decision,
            notes=payload.notes,
            checklist=payload.checklist,
            decided_at=now,
        )
    )
    if payload.decision == "request_changes":
        version.lifecycle_status = "revision_requested"
        version.review_state = "changes_requested"
        content.lifecycle_status = "draft"
    elif payload.decision == "reject":
        version.review_state = "rejected"
    else:
        required = required_reviewers_for_version(db, content.content_type, version)
        approved = set(
            db.scalars(
                select(CmsReviewAssignment.reviewer_type).where(
                    CmsReviewAssignment.version_id == version.id,
                    CmsReviewAssignment.status == "approved",
                )
            ).all()
        )
        approved.add(assignment.reviewer_type)
        if required.issubset(approved):
            version.lifecycle_status = "approved"
            version.review_state = "approved"
            content.lifecycle_status = "approved"
    audit(
        db,
        f"cms.review.{payload.decision}",
        "success",
        auth.user.id,
        auth.organization_id,
        request_id(request),
        "cms_review_assignment",
        str(assignment.id),
        json.dumps({"reviewerType": assignment.reviewer_type}),
    )
    db.commit()
    return version_detail(db, content, version)


@router.post("/contents/{content_id}/versions/{version_id}/schedule")
def schedule_publication(
    content_id: uuid.UUID,
    version_id: uuid.UUID,
    payload: ScheduleRequest,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    require_permission(db, auth, "content.schedule")
    content, version = owned_version(db, auth, content_id, version_id)
    if version.lifecycle_status != "approved":
        raise AppError(409, "cms_schedule_blocked", "Only approved content can be scheduled.")
    if payload.publish_at <= datetime.now(UTC):
        raise AppError(400, "cms_schedule_invalid", "Scheduled time must be in the future.")
    version.lifecycle_status = "scheduled"
    version.review_state = "scheduled"
    version.scheduled_at = payload.publish_at
    version.schedule_timezone = payload.timezone
    content.lifecycle_status = "scheduled"
    job = CmsBackgroundJob(
        job_type="scheduled_publication",
        organization_id=auth.organization_id,
        status="queued",
        progress=0,
        initiated_by_user_id=auth.user.id,
        related_content_id=content.id,
        related_version_id=version.id,
        idempotency_key=f"publish:{version.id}:{payload.publish_at.isoformat()}",
    )
    db.add(job)
    db.add(
        CmsPublicationEvent(
            content_id=content.id,
            version_id=version.id,
            event_type="scheduled",
            actor_user_id=auth.user.id,
            reason=f"Scheduled in {payload.timezone}",
            status="queued",
            created_at=datetime.now(UTC),
        )
    )
    audit(
        db,
        "cms.publication.schedule",
        "success",
        auth.user.id,
        auth.organization_id,
        request_id(request),
        "cms_content_version",
        str(version.id),
        json.dumps({"publishAt": payload.publish_at.isoformat(), "timezone": payload.timezone}),
    )
    db.commit()
    return version_detail(db, content, version)


@router.delete("/contents/{content_id}/versions/{version_id}/schedule")
def cancel_publication_schedule(
    content_id: uuid.UUID,
    version_id: uuid.UUID,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    require_permission(db, auth, "content.schedule")
    content, version = owned_version(db, auth, content_id, version_id)
    if version.lifecycle_status != "scheduled":
        raise AppError(409, "cms_schedule_not_active", "This version is not scheduled.")
    jobs = list(
        db.scalars(
            select(CmsBackgroundJob).where(
                CmsBackgroundJob.related_version_id == version.id,
                CmsBackgroundJob.job_type == "scheduled_publication",
                CmsBackgroundJob.status == "queued",
            )
        ).all()
    )
    now = datetime.now(UTC)
    for job in jobs:
        job.status = "cancelled"
        job.cancelled_at = now
        job.completed_at = now
    version.lifecycle_status = "approved"
    version.review_state = "approved"
    version.scheduled_at = None
    version.schedule_timezone = None
    content.lifecycle_status = "approved"
    audit(
        db,
        "cms.publication.schedule_cancel",
        "success",
        auth.user.id,
        auth.organization_id,
        request_id(request),
        "cms_content_version",
        str(version.id),
    )
    db.commit()
    return version_detail(db, content, version)


@router.post("/contents/{content_id}/versions/{version_id}/publish")
def publish_now(
    content_id: uuid.UUID,
    version_id: uuid.UUID,
    payload: PublishRequest,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    require_permission(db, auth, "content.publish")
    content, version = owned_version(db, auth, content_id, version_id)
    if version.lifecycle_status not in {"approved", "scheduled"}:
        raise AppError(
            409, "cms_publication_state_invalid", "Approve the version before publishing."
        )
    publish_version(db, content, version, auth.user.id, payload.reason)
    audit(
        db,
        "cms.publication.publish",
        "success",
        auth.user.id,
        auth.organization_id,
        request_id(request),
        "cms_content_version",
        str(version.id),
        json.dumps({"revision": version.revision, "checksum": version.content_checksum}),
    )
    db.commit()
    return version_detail(db, content, version)


@router.get("/contents/{content_id}/rollback-impact")
def rollback_impact(
    content_id: uuid.UUID,
    target_revision: int = Query(ge=1),
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    require_permission(db, auth, "content.rollback")
    content = get_content(db, content_id)
    assert_scope(content, auth.organization_id, auth.user.is_platform_admin)
    target = db.scalar(
        select(CmsContentVersion).where(
            CmsContentVersion.content_id == content.id,
            CmsContentVersion.revision == target_revision,
            CmsContentVersion.published_at.is_not(None),
        )
    )
    if target is None:
        raise AppError(
            404, "cms_rollback_target_invalid", "Published rollback target was not found."
        )
    dependent_ids = set(
        db.scalars(
            select(CmsContentRelation.source_content_id).where(
                CmsContentRelation.target_content_id == content.id
            )
        ).all()
    )
    dependents = (
        list(db.scalars(select(CmsContent).where(CmsContent.id.in_(dependent_ids))).all())
        if dependent_ids
        else []
    )
    return {
        "target_revision": target.revision,
        "target_version": target.version,
        "current_revision": content.current_published_revision,
        "dependent_content": [
            {"id": str(item.id), "title": item.title, "status": item.lifecycle_status}
            for item in dependents
        ],
        "historical_versions_preserved": True,
        "learner_records_remapped": False,
        "warning": "Dependent content remains pinned to its immutable target versions.",
    }


@router.post("/contents/{content_id}/rollback")
def rollback_content(
    content_id: uuid.UUID,
    payload: RollbackRequest,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    require_permission(db, auth, "content.rollback")
    content = get_content(db, content_id)
    assert_scope(content, auth.organization_id, auth.user.is_platform_admin)
    target = db.scalar(
        select(CmsContentVersion).where(
            CmsContentVersion.content_id == content.id,
            CmsContentVersion.revision == payload.target_revision,
            CmsContentVersion.published_at.is_not(None),
        )
    )
    if target is None:
        raise AppError(
            404, "cms_rollback_target_invalid", "Published rollback target was not found."
        )
    publish_version(db, content, target, auth.user.id, payload.reason, "rolled_back")
    audit(
        db,
        "cms.publication.rollback",
        "success",
        auth.user.id,
        auth.organization_id,
        request_id(request),
        "cms_content_version",
        str(target.id),
        json.dumps({"targetRevision": target.revision}),
    )
    db.commit()
    return version_detail(db, content, target)


@router.get("/contents/{content_id}/compare")
def compare_versions(
    content_id: uuid.UUID,
    from_revision: int = Query(ge=1),
    to_revision: int = Query(ge=1),
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    require_permission(db, auth, "content.view")
    content = get_content(db, content_id)
    assert_scope(content, auth.organization_id, auth.user.is_platform_admin)
    versions = {
        item.revision: item
        for item in db.scalars(
            select(CmsContentVersion).where(
                CmsContentVersion.content_id == content.id,
                CmsContentVersion.revision.in_([from_revision, to_revision]),
            )
        ).all()
    }
    if from_revision not in versions or to_revision not in versions:
        raise AppError(404, "cms_compare_version_missing", "One comparison version was not found.")
    before_sections, before_objectives = load_version_parts(db, versions[from_revision])
    after_sections, after_objectives = load_version_parts(db, versions[to_revision])
    before_relations = list(
        db.scalars(
            select(CmsContentRelation).where(
                CmsContentRelation.source_version_id == versions[from_revision].id
            )
        ).all()
    )
    after_relations = list(
        db.scalars(
            select(CmsContentRelation).where(
                CmsContentRelation.source_version_id == versions[to_revision].id
            )
        ).all()
    )
    before = version_payload(
        versions[from_revision], before_sections, before_objectives, before_relations
    )
    after = version_payload(
        versions[to_revision], after_sections, after_objectives, after_relations
    )
    before_rows = {item["key"]: item for item in before["sections"]}
    after_rows = {item["key"]: item for item in after["sections"]}
    before_goals = {item["key"]: item for item in before["objectives"]}
    after_goals = {item["key"]: item for item in after["objectives"]}

    def relation_key(item: dict[str, Any]) -> str:
        return f"{item['type']}:{item['targetContentId']}"

    before_links = {relation_key(item): item for item in before["relationships"]}
    after_links = {relation_key(item): item for item in after["relationships"]}
    before_decisions = list(
        db.scalars(
            select(CmsReviewDecision).where(
                CmsReviewDecision.version_id == versions[from_revision].id
            )
        ).all()
    )
    after_decisions = list(
        db.scalars(
            select(CmsReviewDecision).where(
                CmsReviewDecision.version_id == versions[to_revision].id
            )
        ).all()
    )
    return {
        "from_revision": from_revision,
        "to_revision": to_revision,
        "metadata_changes": {
            key: {"from": before.get(key), "to": after.get(key)}
            for key in ["title", "slug", "description", "visibility", "metadata"]
            if before.get(key) != after.get(key)
        },
        "sections_added": [after_rows[key] for key in after_rows.keys() - before_rows.keys()],
        "sections_removed": [before_rows[key] for key in before_rows.keys() - after_rows.keys()],
        "sections_modified": [
            {"section_key": key, "from": before_rows[key], "to": after_rows[key]}
            for key in before_rows.keys() & after_rows.keys()
            if {item: value for item, value in before_rows[key].items() if item != "order"}
            != {item: value for item, value in after_rows[key].items() if item != "order"}
        ],
        "sections_reordered": [
            {
                "section_key": key,
                "title": after_rows[key]["title"],
                "from": before_rows[key]["order"],
                "to": after_rows[key]["order"],
            }
            for key in before_rows.keys() & after_rows.keys()
            if before_rows[key]["order"] != after_rows[key]["order"]
        ],
        "objectives_added": [after_goals[key] for key in after_goals.keys() - before_goals.keys()],
        "objectives_removed": [
            before_goals[key] for key in before_goals.keys() - after_goals.keys()
        ],
        "objectives_modified": [
            {"objective_key": key, "from": before_goals[key], "to": after_goals[key]}
            for key in before_goals.keys() & after_goals.keys()
            if before_goals[key] != after_goals[key]
        ],
        "relationships_added": [
            after_links[key] for key in after_links.keys() - before_links.keys()
        ],
        "relationships_removed": [
            before_links[key] for key in before_links.keys() - after_links.keys()
        ],
        "relationships_modified": [
            {"relationship_key": key, "from": before_links[key], "to": after_links[key]}
            for key in before_links.keys() & after_links.keys()
            if before_links[key] != after_links[key]
        ],
        "review_decisions": {
            "from": [
                {
                    "reviewer_type": item.reviewer_type,
                    "decision": item.decision,
                    "decided_at": item.decided_at,
                }
                for item in before_decisions
            ],
            "to": [
                {
                    "reviewer_type": item.reviewer_type,
                    "decision": item.decision,
                    "decided_at": item.decided_at,
                }
                for item in after_decisions
            ],
        },
        "publication_state": {
            "from": versions[from_revision].lifecycle_status,
            "to": versions[to_revision].lifecycle_status,
        },
    }


@router.get("/reviews")
def review_queue(
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> list[dict[str, Any]]:
    require_permission(db, auth, "content.review")
    review_filters: list[Any] = [
        CmsReviewAssignment.status.in_(["assigned", "in_review", "changes_requested"])
    ]
    if not auth.user.is_platform_admin:
        review_filters.append(CmsReviewAssignment.reviewer_user_id == auth.user.id)
    rows = db.execute(
        select(CmsReviewAssignment, CmsContentVersion, CmsContent)
        .join(CmsContentVersion, CmsContentVersion.id == CmsReviewAssignment.version_id)
        .join(CmsContent, CmsContent.id == CmsContentVersion.content_id)
        .where(*review_filters)
        .order_by(CmsReviewAssignment.created_at)
    ).all()
    return [
        {
            "assignment_id": str(assignment.id),
            "content_id": str(content.id),
            "version_id": str(version.id),
            "title": version.title,
            "reviewer_type": assignment.reviewer_type,
            "status": assignment.status,
            "due_at": assignment.due_at,
        }
        for assignment, version, content in rows
    ]


@router.get("/media")
def list_media(
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> list[dict[str, Any]]:
    require_permission(db, auth, "content.media.view")
    media_filters: list[Any] = [CmsMediaAsset.deleted_at.is_(None)]
    if not auth.user.is_platform_admin:
        media_filters.append(
            or_(
                CmsMediaAsset.organization_id == auth.organization_id,
                CmsMediaAsset.organization_id.is_(None),
            )
        )
    rows = list(
        db.scalars(
            select(CmsMediaAsset)
            .where(*media_filters)
            .order_by(CmsMediaAsset.created_at.desc())
            .limit(200)
        ).all()
    )
    return [media_response(db, item) for item in rows]


def media_response(db: DatabaseSession, asset: CmsMediaAsset) -> dict[str, Any]:
    usages = list(db.scalars(select(CmsMediaUsage).where(CmsMediaUsage.media_id == asset.id)).all())
    return {
        "id": str(asset.id),
        "filename": asset.filename,
        "title": asset.title,
        "description": asset.description,
        "media_type": asset.media_type,
        "mime_type": asset.mime_type,
        "file_size": asset.file_size,
        "checksum": asset.checksum,
        "review_state": asset.review_state,
        "version": asset.version,
        "replacement_of_media_id": str(asset.replacement_of_media_id)
        if asset.replacement_of_media_id
        else None,
        "scan_status": asset.scan_status,
        "accessibility_text": asset.accessibility_text,
        "status": asset.status,
        "usage_count": len(usages),
        "usages": [
            {"version_id": str(item.version_id), "location_key": item.location_key}
            for item in usages
        ],
        "created_at": asset.created_at,
    }


@router.post("/media", status_code=201)
async def upload_media(
    request: Request,
    file: UploadFile = File(),
    title: str = Form(min_length=2, max_length=240),
    description: str = Form(default="", max_length=2_000),
    accessibility_text: str | None = Form(default=None),
    language: str | None = Form(default=None),
    replacement_of_media_id: uuid.UUID | None = Form(default=None),
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    require_permission(db, auth, "content.media.manage")
    mime_type = (file.content_type or "").casefold()
    if mime_type not in ALLOWED_MEDIA:
        raise AppError(400, "cms_media_type_denied", "That media type is not allowed.")
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise AppError(413, "cms_media_too_large", "Media exceeds the 10 MiB limit.")
    if not media_signature_valid(mime_type, data):
        raise AppError(
            400,
            "cms_media_signature_mismatch",
            "File contents do not match the declared media type.",
        )
    if mime_type == "image/svg+xml":
        lowered = data.lower()
        if any(item in lowered for item in (b"<script", b"javascript:", b"onload=", b"onerror=")):
            raise AppError(400, "cms_media_unsafe", "Unsafe SVG content was rejected.")
    original = Path(file.filename or "upload").name
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", original).strip(".-") or "upload"
    extension = Path(safe_name).suffix.casefold()
    if extension not in MEDIA_EXTENSIONS[mime_type]:
        raise AppError(
            400,
            "cms_media_extension_mismatch",
            "File extension does not match its approved media type.",
        )
    if ALLOWED_MEDIA[mime_type] == "image" and not accessibility_text:
        raise AppError(
            422,
            "cms_media_alt_required",
            "Images require useful alternative text before upload.",
        )
    checksum = hashlib.sha256(data).hexdigest()
    duplicate = db.scalar(
        select(CmsMediaAsset).where(
            CmsMediaAsset.scope_key == str(auth.organization_id),
            CmsMediaAsset.checksum == checksum,
            CmsMediaAsset.deleted_at.is_(None),
        )
    )
    if duplicate:
        return media_response(db, duplicate)
    replacement = None
    if replacement_of_media_id:
        replacement = db.get(CmsMediaAsset, replacement_of_media_id)
        if (
            replacement is None
            or replacement.deleted_at is not None
            or replacement.organization_id != auth.organization_id
        ):
            raise AppError(404, "cms_media_not_found", "Replacement source was not found.")
    storage_key = f"{uuid.uuid4()}{extension}"
    media_root = settings.cms_media_root
    if not media_root.is_absolute():
        media_root = Path.cwd() / media_root
    media_root.mkdir(parents=True, exist_ok=True)
    destination = (media_root / storage_key).resolve()
    if destination.parent != media_root.resolve():
        raise AppError(400, "cms_media_path_invalid", "Media storage path was rejected.")
    destination.write_bytes(data)
    asset = CmsMediaAsset(
        scope_key=str(auth.organization_id),
        organization_id=auth.organization_id,
        filename=safe_name,
        storage_key=storage_key,
        media_type=ALLOWED_MEDIA[mime_type],
        mime_type=mime_type,
        file_size=len(data),
        checksum=checksum,
        owner_user_id=auth.user.id,
        title=title.strip(),
        description=description.strip(),
        version=(replacement.version + 1) if replacement else 1,
        replacement_of_media_id=replacement.id if replacement else None,
        scan_status="unconfigured",
        review_state="draft",
        accessibility_text=accessibility_text,
        language=language,
        status="active",
    )
    db.add(asset)
    db.flush()
    audit(
        db,
        "cms.media.upload",
        "success",
        auth.user.id,
        auth.organization_id,
        request_id(request),
        "cms_media_asset",
        str(asset.id),
        json.dumps({"mimeType": mime_type, "size": len(data), "checksum": checksum}),
    )
    db.commit()
    return media_response(db, asset)


@router.get("/media/{media_id}/content")
def get_media_content(
    media_id: uuid.UUID,
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    require_permission(db, auth, "content.media.view")
    asset = db.get(CmsMediaAsset, media_id)
    if (
        asset is None
        or asset.deleted_at is not None
        or (
            not auth.user.is_platform_admin
            and asset.organization_id not in {None, auth.organization_id}
        )
    ):
        raise AppError(404, "cms_media_not_found", "Media asset was not found.")
    media_root = settings.cms_media_root
    if not media_root.is_absolute():
        media_root = Path.cwd() / media_root
    source = (media_root / asset.storage_key).resolve()
    if source.parent != media_root.resolve() or not source.is_file():
        raise AppError(404, "cms_media_missing", "Media file is unavailable.")
    return FileResponse(
        source,
        media_type=asset.mime_type,
        filename=asset.filename,
        headers={"Cache-Control": "private, no-store"},
    )


@router.post("/media/{media_id}/attach", status_code=201)
def attach_media(
    media_id: uuid.UUID,
    version_id: uuid.UUID,
    location_key: str,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    require_permission(db, auth, "content.edit_draft")
    asset = db.get(CmsMediaAsset, media_id)
    version = get_version(db, version_id)
    content = get_content(db, version.content_id)
    if asset is None or asset.deleted_at is not None:
        raise AppError(404, "cms_media_not_found", "Media asset was not found.")
    assert_scope(content, auth.organization_id, auth.user.is_platform_admin)
    if not auth.user.is_platform_admin and asset.organization_id not in {
        None,
        auth.organization_id,
    }:
        raise AppError(404, "cms_media_not_found", "Media asset was not found.")
    assert_editable(version)
    usage = db.scalar(
        select(CmsMediaUsage).where(
            CmsMediaUsage.media_id == asset.id,
            CmsMediaUsage.version_id == version.id,
            CmsMediaUsage.location_key == location_key,
        )
    )
    if usage is None:
        usage = CmsMediaUsage(
            media_id=asset.id, version_id=version.id, location_key=location_key[:160]
        )
        db.add(usage)
    audit(
        db,
        "cms.media.attach",
        "success",
        auth.user.id,
        auth.organization_id,
        request_id(request),
        "cms_media_asset",
        str(asset.id),
        json.dumps({"versionId": str(version.id), "location": location_key[:160]}),
    )
    db.commit()
    return media_response(db, asset)


@router.delete("/media/{media_id}")
def delete_media(
    media_id: uuid.UUID,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, str]:
    require_permission(db, auth, "content.media.manage")
    asset = db.get(CmsMediaAsset, media_id)
    if asset is None or asset.deleted_at is not None:
        raise AppError(404, "cms_media_not_found", "Media asset was not found.")
    if not auth.user.is_platform_admin and asset.organization_id not in {
        None,
        auth.organization_id,
    }:
        raise AppError(404, "cms_media_not_found", "Media asset was not found.")
    existing_usage = db.scalar(select(CmsMediaUsage.id).where(CmsMediaUsage.media_id == asset.id))
    if existing_usage:
        audit(
            db,
            "cms.media.delete_denied",
            "denied",
            auth.user.id,
            auth.organization_id,
            request_id(request),
            "cms_media_asset",
            str(asset.id),
            json.dumps({"reason": "content_dependency"}),
        )
        db.commit()
        raise AppError(
            409,
            "cms_media_in_use",
            "Managed content depends on this asset; deletion is blocked.",
        )
    asset.deleted_at = datetime.now(UTC)
    asset.status = "deleted"
    audit(
        db,
        "cms.media.delete",
        "success",
        auth.user.id,
        auth.organization_id,
        request_id(request),
        "cms_media_asset",
        str(asset.id),
    )
    db.commit()
    return {"status": "deleted"}


@router.get("/feature-flags")
def feature_flags(
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> list[dict[str, Any]]:
    require_permission(db, auth, "platform.flags.view")
    rows = list(db.scalars(select(CmsFeatureFlag).order_by(CmsFeatureFlag.name)).all())
    now = datetime.now(UTC)
    return [
        {
            "id": str(item.id),
            "name": item.name,
            "description": item.description,
            "environment": item.environment,
            "default_state": item.default_state,
            "current_state": item.current_state,
            "starts_at": item.starts_at,
            "expires_at": item.expires_at,
            "effective_state": _flag_enabled(item, now),
            "expired": _flag_expired(item, now),
            "updated_at": item.updated_at,
        }
        for item in rows
    ]


@router.post("/feature-flags", status_code=201)
def create_feature_flag(
    payload: FeatureFlagRequest,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    require_permission(db, auth, "platform.flags.manage")
    if re.search(r"(?i)(api[_ -]?key|password|secret|token)\s*[:=]", payload.description):
        raise AppError(400, "cms_flag_secret_detected", "Flag descriptions cannot contain secrets.")
    existing = db.scalar(
        select(CmsFeatureFlag).where(
            CmsFeatureFlag.name == payload.name,
            CmsFeatureFlag.environment == payload.environment,
        )
    )
    if existing:
        raise AppError(409, "cms_flag_conflict", "That feature flag already exists.")
    flag = CmsFeatureFlag(
        name=payload.name,
        description=payload.description,
        owner_user_id=auth.user.id,
        environment=payload.environment,
        default_state=payload.default_state,
        current_state=payload.current_state,
        starts_at=payload.starts_at,
        expires_at=payload.expires_at,
    )
    db.add(flag)
    db.flush()
    audit(
        db,
        "cms.feature_flag.create",
        "success",
        auth.user.id,
        auth.organization_id,
        request_id(request),
        "cms_feature_flag",
        str(flag.id),
        json.dumps({"name": flag.name, "enabled": flag.current_state}),
    )
    db.commit()
    now = datetime.now(UTC)
    return {
        "id": str(flag.id),
        "name": flag.name,
        "description": flag.description,
        "environment": flag.environment,
        "default_state": flag.default_state,
        "current_state": flag.current_state,
        "starts_at": flag.starts_at,
        "expires_at": flag.expires_at,
        "effective_state": _flag_enabled(flag, now),
        "expired": _flag_expired(flag, now),
    }


@router.patch("/feature-flags/{flag_id}")
def update_feature_flag(
    flag_id: uuid.UUID,
    payload: FeatureFlagUpdateRequest,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    require_permission(db, auth, "platform.flags.manage")
    flag = db.get(CmsFeatureFlag, flag_id)
    if flag is None:
        raise AppError(404, "cms_flag_not_found", "Feature flag was not found.")
    if re.search(r"(?i)(api[_ -]?key|password|secret|token)\s*[:=]", payload.description):
        raise AppError(400, "cms_flag_secret_detected", "Flag descriptions cannot contain secrets.")
    previous = flag.current_state
    flag.current_state = payload.current_state
    flag.description = payload.description
    flag.starts_at = payload.starts_at
    flag.expires_at = payload.expires_at
    audit(
        db,
        "cms.feature_flag.update",
        "success",
        auth.user.id,
        auth.organization_id,
        request_id(request),
        "cms_feature_flag",
        str(flag.id),
        json.dumps({"from": previous, "to": flag.current_state}),
    )
    db.commit()
    return {"id": str(flag.id), "name": flag.name, "current_state": flag.current_state}


@public_router.get("/feature-flags/{name}")
def effective_feature_flag(
    name: str,
    environment: str = Query(default="production", pattern="^(development|test|production)$"),
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    del auth  # Authentication is required; no administrative metadata is exposed.
    flag = db.scalar(
        select(CmsFeatureFlag).where(
            CmsFeatureFlag.name == name,
            CmsFeatureFlag.environment == environment,
        )
    )
    if flag is None:
        return {"name": name, "enabled": False, "source": "production_safe_default"}
    now = datetime.now(UTC)
    enabled = _flag_enabled(flag, now)
    return {"name": flag.name, "enabled": enabled, "source": "persisted_server_evaluation"}


@router.get("/audit")
def cms_audit(
    limit: int = Query(default=100, ge=1, le=500),
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> list[dict[str, Any]]:
    require_permission(db, auth, "audit_logs.view")
    audit_filters: list[Any] = [AuditEvent.action.like("cms.%")]
    if not auth.user.is_platform_admin:
        audit_filters.append(
            or_(
                AuditEvent.organization_id == auth.organization_id,
                AuditEvent.organization_id.is_(None),
            )
        )
    rows = list(
        db.scalars(
            select(AuditEvent)
            .where(*audit_filters)
            .order_by(AuditEvent.created_at.desc())
            .limit(limit)
        ).all()
    )
    return [
        {
            "id": str(item.id),
            "actor_user_id": str(item.actor_user_id) if item.actor_user_id else None,
            "action": item.action,
            "outcome": item.outcome,
            "target_type": item.target_type,
            "target_id": item.target_id,
            "request_id": item.request_id,
            "detail": item.detail,
            "created_at": item.created_at,
        }
        for item in rows
    ]


@router.get("/jobs")
def background_jobs(
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> list[dict[str, Any]]:
    require_permission(db, auth, "platform.jobs.view")
    job_filters = (
        []
        if auth.user.is_platform_admin
        else [CmsBackgroundJob.organization_id == auth.organization_id]
    )
    rows = list(
        db.scalars(
            select(CmsBackgroundJob)
            .where(*job_filters)
            .order_by(CmsBackgroundJob.created_at.desc())
            .limit(200)
        ).all()
    )
    return [
        {
            "id": str(item.id),
            "job_type": item.job_type,
            "status": item.status,
            "progress": item.progress,
            "related_content_id": str(item.related_content_id) if item.related_content_id else None,
            "error_detail": item.error_detail,
            "created_at": item.created_at,
            "completed_at": item.completed_at,
            "retry_count": item.retry_count,
            "cancelled_at": item.cancelled_at,
        }
        for item in rows
    ]


@router.post("/jobs/{job_id}/retry")
def retry_background_job(
    job_id: uuid.UUID,
    payload: JobActionRequest,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    require_permission(db, auth, "platform.jobs.manage")
    job = db.get(CmsBackgroundJob, job_id)
    if job is None or (
        not auth.user.is_platform_admin and job.organization_id != auth.organization_id
    ):
        raise AppError(404, "cms_job_not_found", "Background job was not found.")
    if job.status not in {"failed", "cancelled"}:
        raise AppError(409, "cms_job_retry_invalid", "Only failed or cancelled jobs can retry.")
    job.status = "queued"
    job.progress = 0
    job.error_detail = None
    job.started_at = None
    job.completed_at = None
    job.cancelled_at = None
    job.retry_count += 1
    audit(
        db,
        "cms.jobs.retry",
        "success",
        auth.user.id,
        auth.organization_id,
        request_id(request),
        "cms_background_job",
        str(job.id),
        payload.reason,
    )
    db.commit()
    return {"id": str(job.id), "status": job.status, "retry_count": job.retry_count}


@router.post("/jobs/{job_id}/cancel")
def cancel_background_job(
    job_id: uuid.UUID,
    payload: JobActionRequest,
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    require_permission(db, auth, "platform.jobs.manage")
    job = db.get(CmsBackgroundJob, job_id)
    if job is None or (
        not auth.user.is_platform_admin and job.organization_id != auth.organization_id
    ):
        raise AppError(404, "cms_job_not_found", "Background job was not found.")
    if job.status not in {"queued", "retrying"}:
        raise AppError(409, "cms_job_cancel_invalid", "Only queued jobs can be cancelled.")
    now = datetime.now(UTC)
    job.status = "cancelled"
    job.cancelled_at = now
    job.completed_at = now
    audit(
        db,
        "cms.jobs.cancel",
        "success",
        auth.user.id,
        auth.organization_id,
        request_id(request),
        "cms_background_job",
        str(job.id),
        payload.reason,
    )
    db.commit()
    return {"id": str(job.id), "status": job.status}


@router.post("/jobs/run-due")
def run_due_jobs(
    request: Request,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, int]:
    require_permission(db, auth, "platform.jobs.manage")
    jobs = list(
        db.scalars(
            select(CmsBackgroundJob).where(
                CmsBackgroundJob.job_type == "scheduled_publication",
                CmsBackgroundJob.status == "queued",
                *(
                    []
                    if auth.user.is_platform_admin
                    else [CmsBackgroundJob.organization_id == auth.organization_id]
                ),
            )
        ).all()
    )
    completed = 0
    failed = 0
    for job in jobs:
        version = db.get(CmsContentVersion, job.related_version_id)
        content = db.get(CmsContent, job.related_content_id)
        if version is None or content is None or not version.scheduled_at:
            job.status = "failed"
            job.error_detail = "Scheduled content is unavailable."
            failed += 1
            continue
        scheduled = version.scheduled_at
        if scheduled.tzinfo is None:
            scheduled = scheduled.replace(tzinfo=UTC)
        if scheduled > datetime.now(UTC):
            continue
        job.status = "running"
        job.started_at = datetime.now(UTC)
        try:
            publish_version(db, content, version, auth.user.id, "Scheduled publication")
            job.status = "completed"
            job.progress = 100
            job.completed_at = datetime.now(UTC)
            completed += 1
        except AppError as error:
            job.status = "failed"
            job.error_detail = error.message
            job.completed_at = datetime.now(UTC)
            failed += 1
    audit(
        db,
        "cms.jobs.run_due",
        "failure" if failed else "success",
        auth.user.id,
        auth.organization_id,
        request_id(request),
        "cms_background_job",
        None,
        json.dumps({"completed": completed, "failed": failed}),
    )
    db.commit()
    return {"completed": completed, "failed": failed}


@router.get("/reports/content-lifecycle")
def lifecycle_report(
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    require_permission(db, auth, "content.reports.view")
    rows = db.execute(
        select(CmsContent.lifecycle_status, func.count(CmsContent.id))
        .where(CmsContent.deleted_at.is_(None))
        .group_by(CmsContent.lifecycle_status)
    ).all()
    return {
        "generated_at": datetime.now(UTC),
        "content_by_status": {status: count for status, count in rows},
        "pending_reviews": int(
            db.scalar(
                select(func.count(CmsReviewAssignment.id)).where(
                    CmsReviewAssignment.status.in_(["assigned", "in_review"])
                )
            )
            or 0
        ),
        "validation_failures": int(
            db.scalar(
                select(func.count(CmsValidationResult.id)).where(
                    CmsValidationResult.state == "failure"
                )
            )
            or 0
        ),
        "failed_jobs": int(
            db.scalar(
                select(func.count(CmsBackgroundJob.id)).where(CmsBackgroundJob.status == "failed")
            )
            or 0
        ),
    }


@router.get("/data-dictionary")
def data_dictionary(
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    require_permission(db, auth, "content.view")
    tables = [
        CmsContent,
        CmsContentVersion,
        CmsReviewAssignment,
        CmsReviewComment,
        CmsValidationResult,
        CmsPublicationEvent,
        CmsMediaAsset,
        CmsMediaUsage,
        CmsTranslation,
        CmsFeatureFlag,
        CmsPlatformSetting,
        CmsApiKeyMetadata,
        CmsBackgroundJob,
        CmsMaintenanceWindow,
    ]
    return {
        "generated_at": datetime.now(UTC),
        "entities": [
            {
                "entity": model.__name__,
                "table": model.__tablename__,
                "fields": [
                    {
                        "name": column.name,
                        "type": str(column.type),
                        "nullable": column.nullable,
                        "primary_key": column.primary_key,
                        "sensitive": column.name in {"secret_reference"},
                    }
                    for column in model.__table__.columns
                ],
            }
            for model in tables
        ],
    }


@public_router.get("/lessons/{slug}")
def published_lesson(
    slug: str,
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    scope_filters = []
    if not auth.user.is_platform_admin:
        scope_filters.append(
            or_(
                CmsContent.organization_id == auth.organization_id,
                CmsContent.organization_id.is_(None),
            )
        )
    content = db.scalar(
        select(CmsContent).where(
            CmsContent.public_slug == slug,
            CmsContent.content_type == "lesson",
            CmsContent.lifecycle_status == "published",
            CmsContent.visibility == "public",
            CmsContent.deleted_at.is_(None),
            *scope_filters,
        )
    )
    if content is None or content.current_published_revision is None:
        raise AppError(404, "managed_lesson_not_found", "Published lesson was not found.")
    version = db.scalar(
        select(CmsContentVersion).where(
            CmsContentVersion.content_id == content.id,
            CmsContentVersion.revision == content.current_published_revision,
            CmsContentVersion.lifecycle_status == "published",
        )
    )
    if version is None:
        raise AppError(404, "managed_lesson_not_found", "Published lesson was not found.")
    sections, objectives = load_version_parts(db, version)
    return {
        "id": str(content.id),
        "slug": content.public_slug,
        "title": version.title,
        "description": version.description,
        "version": version.version,
        "revision": version.revision,
        "language": version.language,
        "sections": [
            item
            for item in version_payload(version, sections, objectives)["sections"]
            if item["visibility"] == "visible"
        ],
        "objectives": [
            {key: value for key, value in objective.items() if key != "reviewStatus"}
            for objective in version_payload(version, sections, objectives)["objectives"]
        ],
    }


@public_router.get("/{content_type}/{slug}")
def published_managed_content(
    content_type: str,
    slug: str,
    auth: AuthContext = Depends(require_auth),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    scope_filters = []
    if not auth.user.is_platform_admin:
        scope_filters.append(
            or_(
                CmsContent.organization_id == auth.organization_id,
                CmsContent.organization_id.is_(None),
            )
        )
    content = db.scalar(
        select(CmsContent).where(
            CmsContent.public_slug == slug,
            CmsContent.content_type == content_type,
            CmsContent.lifecycle_status == "published",
            CmsContent.visibility == "public",
            CmsContent.deleted_at.is_(None),
            *scope_filters,
        )
    )
    if content is None or content.current_published_revision is None:
        raise AppError(404, "managed_content_not_found", "Published content was not found.")
    version = db.scalar(
        select(CmsContentVersion).where(
            CmsContentVersion.content_id == content.id,
            CmsContentVersion.revision == content.current_published_revision,
            CmsContentVersion.lifecycle_status == "published",
        )
    )
    if version is None:
        raise AppError(404, "managed_content_not_found", "Published content was not found.")
    result = learner_preview_payload(version_detail(db, content, version))
    if content_type == "assessment":
        question_rows = db.scalars(
            select(CmsContentRelation)
            .where(
                CmsContentRelation.source_version_id == version.id,
                CmsContentRelation.relation_type == "question",
            )
            .order_by(CmsContentRelation.sort_order)
        ).all()
        questions: list[dict[str, Any]] = []
        for relation in question_rows:
            question_content = db.get(CmsContent, relation.target_content_id)
            if question_content is None:
                continue
            question_version = (
                db.get(CmsContentVersion, relation.target_version_id)
                if relation.target_version_id
                else None
            )
            if question_version is None or question_version.lifecycle_status != "published":
                continue
            question = learner_preview_payload(
                version_detail(db, question_content, question_version)
            )
            question["question_id"] = str(question_content.id)
            questions.append(question)
        result["questions"] = questions
    return result


def _normalized_answer(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip().casefold()
    if isinstance(value, list):
        return [_normalized_answer(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalized_answer(item) for key, item in sorted(value.items())}
    return value


def _question_credit(question_type: object, received: Any, expected: Any, partial: bool) -> float:
    if question_type == "multiple_choice":
        received_set = set(received or [])
        expected_set = set(expected or [])
        if not partial:
            return 1.0 if received_set == expected_set else 0.0
        if not expected_set:
            return 0.0
        correct = len(received_set & expected_set)
        incorrect = len(received_set - expected_set)
        return max(0.0, (correct - incorrect) / len(expected_set))
    if question_type in {"ordering", "matching"} and isinstance(expected, list):
        if not isinstance(received, list) or not expected:
            return 0.0
        if not partial:
            return 1.0 if received == expected else 0.0
        matches = sum(
            1
            for index, item in enumerate(expected)
            if index < len(received) and received[index] == item
        )
        return matches / len(expected)
    if question_type == "short_response" and isinstance(expected, list):
        return 1.0 if received in expected else 0.0
    correct = received == expected or (
        isinstance(expected, list) and len(expected) == 1 and received == expected[0]
    )
    return 1.0 if correct else 0.0


@public_router.post("/assessments/{slug}/submit")
def submit_managed_assessment(
    slug: str,
    payload: ManagedAssessmentSubmissionRequest,
    auth: AuthContext = Depends(require_csrf),
    db: DatabaseSession = Depends(get_db),
) -> dict[str, Any]:
    content = db.scalar(
        select(CmsContent).where(
            CmsContent.public_slug == slug,
            CmsContent.content_type == "assessment",
            CmsContent.lifecycle_status == "published",
            CmsContent.visibility == "public",
            CmsContent.deleted_at.is_(None),
            or_(
                CmsContent.organization_id == auth.organization_id,
                CmsContent.organization_id.is_(None),
            ),
        )
    )
    if content is None or content.current_published_revision is None:
        raise AppError(404, "managed_assessment_not_found", "Published assessment was not found.")
    version = db.scalar(
        select(CmsContentVersion).where(
            CmsContentVersion.content_id == content.id,
            CmsContentVersion.revision == content.current_published_revision,
            CmsContentVersion.lifecycle_status == "published",
        )
    )
    if version is None:
        raise AppError(404, "managed_assessment_not_found", "Published assessment was not found.")
    existing = db.scalar(
        select(LearningActivityAttempt).where(
            LearningActivityAttempt.organization_id == auth.organization_id,
            LearningActivityAttempt.user_id == auth.user.id,
            LearningActivityAttempt.idempotency_key == payload.idempotency_key,
        )
    )
    if existing is not None:
        return {"attempt_id": str(existing.id), "score": existing.score, "passed": existing.passed}
    attempt_limit = int(version.metadata_json.get("attemptLimit") or 0)
    attempts = int(
        db.scalar(
            select(func.count(LearningActivityAttempt.id)).where(
                LearningActivityAttempt.organization_id == auth.organization_id,
                LearningActivityAttempt.user_id == auth.user.id,
                LearningActivityAttempt.activity_id == str(content.id),
            )
        )
        or 0
    )
    if attempt_limit and attempts >= attempt_limit:
        raise AppError(409, "assessment_attempt_limit", "The assessment attempt limit was reached.")
    relations = db.scalars(
        select(CmsContentRelation)
        .where(
            CmsContentRelation.source_version_id == version.id,
            CmsContentRelation.relation_type == "question",
        )
        .order_by(CmsContentRelation.sort_order)
    ).all()
    outcomes: list[dict[str, Any]] = []
    partial_credit = bool(version.metadata_json.get("partialCredit"))
    for relation in relations:
        question_version = (
            db.get(CmsContentVersion, relation.target_version_id)
            if relation.target_version_id
            else None
        )
        if question_version is None or question_version.lifecycle_status != "published":
            raise AppError(
                409,
                "assessment_question_unavailable",
                "A versioned question is unavailable.",
            )
        expected = _normalized_answer(question_version.metadata_json.get("answerKey", []))
        received = _normalized_answer(payload.answers.get(str(relation.target_content_id)))
        question_type = question_version.metadata_json.get("questionType")
        credit = _question_credit(question_type, received, expected, partial_credit)
        outcomes.append(
            {
                "question_id": str(relation.target_content_id),
                "correct": credit == 1.0,
                "credit": credit,
                "_explanation": question_version.metadata_json.get("explanation", ""),
            }
        )
    if not outcomes:
        raise AppError(409, "assessment_questions_missing", "The assessment has no questions.")
    score = sum(float(item["credit"]) for item in outcomes) / len(outcomes)
    passing_score = float(version.metadata_json.get("passingScore") or 0.7)
    passed = score >= passing_score
    explanation_policy = str(version.metadata_json.get("explanationPolicy") or "after_attempt")
    feedback_policy = str(version.metadata_json.get("feedbackPolicy") or "after_attempt")
    reveal_explanations = explanation_policy == "after_attempt" or (
        explanation_policy == "after_pass" and passed
    )
    reveal_correctness = feedback_policy == "after_attempt" or (
        feedback_policy == "after_pass" and passed
    )
    public_outcomes = [
        {
            "question_id": item["question_id"],
            "credit": item["credit"],
            **({"correct": item["correct"]} if reveal_correctness else {}),
            **({"explanation": item["_explanation"]} if reveal_explanations else {}),
        }
        for item in outcomes
    ]
    attempt = LearningActivityAttempt(
        organization_id=auth.organization_id,
        user_id=auth.user.id,
        activity_id=str(content.id),
        activity_version=version.version,
        activity_type="cms_assessment",
        module_id=str(content.id),
        response={"answers": payload.answers, "cms_version_id": str(version.id)},
        score=score,
        passed=passed,
        hints_used=0,
        evaluator="cms-deterministic-v1",
        feedback="Server-graded against the immutable published question versions.",
        idempotency_key=payload.idempotency_key,
        submitted_at=datetime.now(UTC),
    )
    db.add(attempt)
    db.commit()
    return {
        "attempt_id": str(attempt.id),
        "content_version_id": str(version.id),
        "score": score,
        "passed": attempt.passed,
        "outcomes": public_outcomes,
    }
