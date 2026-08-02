import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamped, UUIDPrimaryKey


class CmsContent(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "cms_contents"
    __table_args__ = (
        UniqueConstraint("scope_key", "public_slug", "default_language"),
        Index("ix_cms_content_type_status", "content_type", "lifecycle_status"),
        Index("ix_cms_content_title", "title"),
    )

    scope_key: Mapped[str] = mapped_column(String(80), default="platform")
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    content_type: Mapped[str] = mapped_column(String(40))
    public_slug: Mapped[str] = mapped_column(String(160))
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(Text, default="")
    lifecycle_status: Mapped[str] = mapped_column(String(40), default="draft")
    visibility: Mapped[str] = mapped_column(String(30), default="private")
    owner_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    creator_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    default_language: Mapped[str] = mapped_column(String(16), default="en")
    fallback_language: Mapped[str | None] = mapped_column(String(16))
    current_published_revision: Mapped[int | None] = mapped_column(Integer)
    replacement_content_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cms_contents.id", ondelete="RESTRICT")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CmsContentVersion(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "cms_content_versions"
    __table_args__ = (
        UniqueConstraint("content_id", "revision"),
        UniqueConstraint("content_id", "version"),
        Index("ix_cms_version_status_schedule", "lifecycle_status", "scheduled_at"),
    )

    content_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cms_contents.id", ondelete="CASCADE"), index=True
    )
    revision: Mapped[int] = mapped_column(Integer)
    version: Mapped[str] = mapped_column(String(40))
    parent_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cms_content_versions.id", ondelete="RESTRICT")
    )
    created_from_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cms_content_versions.id", ondelete="RESTRICT")
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    title: Mapped[str] = mapped_column(String(240))
    public_slug: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    lifecycle_status: Mapped[str] = mapped_column(String(40), default="draft")
    review_state: Mapped[str] = mapped_column(String(40), default="draft")
    visibility: Mapped[str] = mapped_column(String(30), default="private")
    language: Mapped[str] = mapped_column(String(16), default="en")
    change_summary: Mapped[str] = mapped_column(Text, default="Initial draft")
    migration_notes: Mapped[str | None] = mapped_column(Text)
    breaking_change: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    content_checksum: Mapped[str] = mapped_column(String(64), index=True)
    lock_version: Mapped[int] = mapped_column(Integer, default=1)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    schedule_timezone: Mapped[str | None] = mapped_column(String(64))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    soft_deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CmsLessonSection(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "cms_lesson_sections"
    __table_args__ = (
        UniqueConstraint("version_id", "section_key"),
        UniqueConstraint("version_id", "sort_order"),
    )

    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cms_content_versions.id", ondelete="CASCADE"), index=True
    )
    section_key: Mapped[uuid.UUID] = mapped_column(index=True)
    section_type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(240), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    structured_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    visibility: Mapped[str] = mapped_column(String(30), default="visible")
    accessibility_label: Mapped[str | None] = mapped_column(String(300))
    sort_order: Mapped[int] = mapped_column(Integer)


class CmsLearningObjective(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "cms_learning_objectives"
    __table_args__ = (UniqueConstraint("version_id", "objective_key"),)

    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cms_content_versions.id", ondelete="CASCADE"), index=True
    )
    objective_key: Mapped[uuid.UUID] = mapped_column(index=True)
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(Text)
    bloom_level: Mapped[str] = mapped_column(String(30))
    linked_skill_keys: Mapped[list[str]] = mapped_column(JSON, default=list)
    assessment_coverage: Mapped[bool] = mapped_column(Boolean, default=False)
    practical_coverage: Mapped[bool] = mapped_column(Boolean, default=False)
    review_status: Mapped[str] = mapped_column(String(30), default="pending")


class CmsContentRelation(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "cms_content_relations"
    __table_args__ = (
        UniqueConstraint(
            "source_content_id", "source_version_id", "target_content_id", "relation_type"
        ),
    )

    source_content_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cms_contents.id", ondelete="CASCADE"), index=True
    )
    source_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cms_content_versions.id", ondelete="CASCADE")
    )
    target_content_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cms_contents.id", ondelete="RESTRICT"), index=True
    )
    target_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cms_content_versions.id", ondelete="RESTRICT")
    )
    relation_type: Mapped[str] = mapped_column(String(50))
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class CmsReviewRequirement(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "cms_review_requirements"
    __table_args__ = (UniqueConstraint("content_type", "reviewer_type"),)

    content_type: Mapped[str] = mapped_column(String(40), index=True)
    reviewer_type: Mapped[str] = mapped_column(String(50))
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )


class CmsReviewAssignment(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "cms_review_assignments"
    __table_args__ = (UniqueConstraint("version_id", "reviewer_type"),)

    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cms_content_versions.id", ondelete="CASCADE"), index=True
    )
    reviewer_type: Mapped[str] = mapped_column(String(50))
    reviewer_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    assigned_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(String(30), default="assigned")
    decision: Mapped[str | None] = mapped_column(String(30))
    notes: Mapped[str | None] = mapped_column(Text)
    checklist: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CmsReviewComment(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "cms_review_comments"
    __table_args__ = (Index("ix_cms_comment_version_status", "version_id", "status"),)

    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cms_content_versions.id", ondelete="CASCADE")
    )
    parent_comment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cms_review_comments.id", ondelete="CASCADE")
    )
    author_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    body: Mapped[str] = mapped_column(Text)
    location_type: Mapped[str] = mapped_column(String(40), default="version")
    location_key: Mapped[str | None] = mapped_column(String(160))
    severity: Mapped[str] = mapped_column(String(30), default="suggestion")
    suggested_change: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="open")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )


class CmsReviewDecision(UUIDPrimaryKey, Base):
    __tablename__ = "cms_review_decisions"
    __table_args__ = (Index("ix_cms_decision_version_time", "version_id", "decided_at"),)

    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cms_content_versions.id", ondelete="RESTRICT")
    )
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cms_review_assignments.id", ondelete="RESTRICT")
    )
    reviewer_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    reviewer_type: Mapped[str] = mapped_column(String(50))
    decision: Mapped[str] = mapped_column(String(30))
    notes: Mapped[str] = mapped_column(Text)
    checklist: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CmsValidationResult(UUIDPrimaryKey, Base):
    __tablename__ = "cms_validation_results"
    __table_args__ = (Index("ix_cms_validation_version_state", "version_id", "state"),)

    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cms_content_versions.id", ondelete="CASCADE")
    )
    category: Mapped[str] = mapped_column(String(40))
    rule_id: Mapped[str] = mapped_column(String(100))
    severity: Mapped[str] = mapped_column(String(20))
    state: Mapped[str] = mapped_column(String(20))
    field_location: Mapped[str | None] = mapped_column(String(240))
    explanation: Mapped[str] = mapped_column(Text)
    remediation: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CmsPublicationEvent(UUIDPrimaryKey, Base):
    __tablename__ = "cms_publication_events"
    __table_args__ = (Index("ix_cms_publication_content_time", "content_id", "created_at"),)

    content_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cms_contents.id", ondelete="RESTRICT")
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cms_content_versions.id", ondelete="RESTRICT")
    )
    event_type: Mapped[str] = mapped_column(String(40))
    actor_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CmsMediaAsset(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "cms_media_assets"
    __table_args__ = (
        UniqueConstraint("scope_key", "checksum"),
        Index("ix_cms_media_status_type", "status", "media_type"),
    )

    scope_key: Mapped[str] = mapped_column(String(80), default="platform")
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(255), unique=True)
    media_type: Mapped[str] = mapped_column(String(40))
    mime_type: Mapped[str] = mapped_column(String(120))
    file_size: Mapped[int] = mapped_column(Integer)
    checksum: Mapped[str] = mapped_column(String(64))
    owner_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    title: Mapped[str] = mapped_column(String(240), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    replacement_of_media_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cms_media_assets.id", ondelete="RESTRICT")
    )
    scan_status: Mapped[str] = mapped_column(String(40), default="unconfigured")
    review_state: Mapped[str] = mapped_column(String(30), default="draft")
    accessibility_text: Mapped[str | None] = mapped_column(String(500))
    language: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(30), default="active")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CmsMediaUsage(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "cms_media_usages"
    __table_args__ = (UniqueConstraint("media_id", "version_id", "location_key"),)

    media_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cms_media_assets.id", ondelete="RESTRICT"), index=True
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cms_content_versions.id", ondelete="CASCADE"), index=True
    )
    location_key: Mapped[str] = mapped_column(String(160))


class CmsTaxonomyTerm(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "cms_taxonomy_terms"
    __table_args__ = (UniqueConstraint("category", "slug"),)

    category: Mapped[str] = mapped_column(String(60))
    slug: Mapped[str] = mapped_column(String(100))
    label: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="active")
    replacement_term_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cms_taxonomy_terms.id", ondelete="RESTRICT")
    )


class CmsContentTaxonomy(Base):
    __tablename__ = "cms_content_taxonomy"

    content_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cms_contents.id", ondelete="CASCADE"), primary_key=True
    )
    term_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cms_taxonomy_terms.id", ondelete="RESTRICT"), primary_key=True
    )


class CmsTranslation(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "cms_translations"
    __table_args__ = (UniqueConstraint("content_id", "language"),)

    content_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cms_contents.id", ondelete="CASCADE"))
    language: Mapped[str] = mapped_column(String(16))
    source_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cms_content_versions.id", ondelete="RESTRICT")
    )
    translated_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cms_content_versions.id", ondelete="RESTRICT")
    )
    translator_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    reviewer_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(String(30), default="not_started")


class CmsFeatureFlag(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "cms_feature_flags"
    __table_args__ = (UniqueConstraint("environment", "name"),)

    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    environment: Mapped[str] = mapped_column(String(30))
    default_state: Mapped[bool] = mapped_column(Boolean, default=False)
    current_state: Mapped[bool] = mapped_column(Boolean, default=False)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CmsPlatformSetting(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "cms_platform_settings"

    key: Mapped[str] = mapped_column(String(120), unique=True)
    category: Mapped[str] = mapped_column(String(60))
    value_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    secret_reference: Mapped[str | None] = mapped_column(String(240))
    updated_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )


class CmsApiKeyMetadata(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "cms_api_key_metadata"

    provider_name: Mapped[str] = mapped_column(String(100))
    key_label: Mapped[str] = mapped_column(String(120))
    owner_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    environment: Mapped[str] = mapped_column(String(30))
    secret_reference: Mapped[str] = mapped_column(String(240))
    last_rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class CmsBackgroundJob(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "cms_background_jobs"
    __table_args__ = (
        UniqueConstraint("idempotency_key"),
        Index("ix_cms_job_status_created", "status", "created_at"),
    )

    job_type: Mapped[str] = mapped_column(String(60))
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[str] = mapped_column(String(30), default="queued")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    initiated_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    related_content_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cms_contents.id", ondelete="RESTRICT")
    )
    related_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cms_content_versions.id", ondelete="RESTRICT")
    )
    idempotency_key: Mapped[str] = mapped_column(String(160))
    error_detail: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CmsSavedSearch(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "cms_saved_searches"
    __table_args__ = (UniqueConstraint("owner_user_id", "name"),)

    owner_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(120))
    query: Mapped[str] = mapped_column(String(240), default="")
    filters_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class CmsMaintenanceWindow(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "cms_maintenance_windows"

    reason: Mapped[str] = mapped_column(Text)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    affected_surfaces: Mapped[list[str]] = mapped_column(JSON, default=list)
    admin_bypass: Mapped[bool] = mapped_column(Boolean, default=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )


class CmsNotificationTemplate(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "cms_notification_templates"
    __table_args__ = (UniqueConstraint("stable_key", "language", "version"),)

    stable_key: Mapped[str] = mapped_column(String(120))
    event_type: Mapped[str] = mapped_column(String(80))
    subject: Mapped[str] = mapped_column(String(240))
    body: Mapped[str] = mapped_column(Text)
    supported_variables: Mapped[list[str]] = mapped_column(JSON, default=list)
    language: Mapped[str] = mapped_column(String(16), default="en")
    version: Mapped[int] = mapped_column(Integer, default=1)
    review_status: Mapped[str] = mapped_column(String(30), default="draft")
    active: Mapped[bool] = mapped_column(Boolean, default=False)
