from sqlalchemy import inspect, text

from app.db.session import engine

REQUIRED_TABLES = {
    "alembic_version",
    "users",
    "user_profiles",
    "organizations",
    "organization_memberships",
    "roles",
    "permissions",
    "skills",
    "diagnostic_attempts",
    "missions",
    "mission_sessions",
    "projects",
    "project_submissions",
    "mentor_threads",
    "mentor_messages",
    "cms_contents",
    "cms_content_versions",
    "cms_lesson_sections",
    "cms_learning_objectives",
    "cms_content_relations",
    "cms_review_requirements",
    "cms_review_assignments",
    "cms_review_comments",
    "cms_review_decisions",
    "cms_validation_results",
    "cms_publication_events",
    "cms_media_assets",
    "cms_media_usages",
    "cms_feature_flags",
    "cms_background_jobs",
    "professional_profiles",
    "learner_reflections",
    "career_certificates",
    "career_timeline_events",
}


def main() -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    missing = sorted(REQUIRED_TABLES - tables)
    if missing:
        raise SystemExit(f"Database verification failed; missing tables: {', '.join(missing)}")

    with engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()

    print(
        {
            "event": "database_verified",
            "migration": revision,
            "tableCount": len(tables),
            "requiredTables": sorted(REQUIRED_TABLES),
        }
    )


if __name__ == "__main__":
    main()
