from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.learning.flagship_mission import (
    EVALUATOR_VERSION,
    FLAGSHIP_MISSION,
    FLAGSHIP_MISSION_VERSION,
)
from app.learning.flagship_project import FLAGSHIP_PROJECT, FLAGSHIP_PROJECT_VERSION
from app.learning.soc_profile import (
    DIAGNOSTIC_QUESTIONS,
    SKILLS,
    SOC_PROFILE_VERSION,
)
from app.models import Permission, Role, RolePermission
from app.models.assessment import Assessment, AssessmentVersion, Question, QuestionVersion
from app.models.learning import Skill, SkillDependency
from app.models.mission import Mission, MissionObjective, MissionStage, MissionVersion
from app.models.portfolio import Project, ProjectMilestone, Rubric, RubricCriterion

CMS_AUTHOR_PERMISSIONS = {
    "organization.view",
    "content.view",
    "content.create",
    "content.edit_draft",
    "content.create_version",
    "content.submit_review",
    "content.validate",
    "content.media.view",
    "content.media.manage",
    "content.references.manage",
    "content.skills.manage",
    "content.export",
}

CMS_REVIEW_PERMISSIONS = {
    "organization.view",
    "content.view",
    "content.review",
    "content.validate",
    "content.media.view",
}

CMS_ADMIN_PERMISSIONS = (
    CMS_AUTHOR_PERMISSIONS
    | CMS_REVIEW_PERMISSIONS
    | {
        "content.assign_reviewer",
        "content.schedule",
        "content.publish",
        "content.rollback",
        "content.deprecate",
        "content.archive",
        "content.import",
        "content.reports.view",
        "platform.settings.view",
        "platform.settings.manage",
        "platform.flags.view",
        "platform.flags.manage",
        "platform.health.view",
        "platform.jobs.view",
        "platform.jobs.manage",
        "audit_logs.view",
    }
)

ROLE_PERMISSIONS = {
    "learner": {
        "organization.view",
        "learning.read",
        "learning.progress.write",
        "mission.attempt",
        "portfolio.read_own",
        "career.profile.manage",
        "career.read_own",
        "career.export",
    },
    "instructor": {
        "organization.view",
        "organization.members.view",
        "cohorts.view",
        "learners.view_summary",
        "learners.view_detailed_progress",
        "assignments.view",
        "assignments.create",
        "assignments.manage",
        "reviews.view",
        "reviews.perform",
        "reports.view",
        "learning.read",
        "cohort.read",
        "submission.review",
        "learner_evidence.read_scoped",
    },
    "reviewer": {
        "organization.view",
        "cohorts.view",
        "learners.view_summary",
        "assignments.view",
        "reviews.view",
        "reviews.perform",
    },
    "cohort_manager": {
        "organization.view",
        "organization.members.view",
        "cohorts.view",
        "cohorts.create",
        "cohorts.manage",
        "cohorts.assign",
        "learners.view_summary",
        "learners.view_detailed_progress",
        "learners.manage_enrolment",
        "assignments.view",
        "assignments.create",
        "assignments.manage",
        "reports.view",
    },
    "company_manager": {
        "organization.view",
        "organization.members.view",
        "cohorts.view",
        "cohorts.create",
        "cohorts.manage",
        "cohorts.assign",
        "learners.view_summary",
        "learners.manage_enrolment",
        "assignments.view",
        "assignments.create",
        "assignments.manage",
        "reports.view",
        "reports.export",
        "company_training.manage",
    },
    "recruiter": {
        "organization.view",
        "recruiter_evidence.view",
        "recruiter_evidence.request",
        "reports.view",
        "career.recruiter.view",
    },
    "organization_admin": {
        "organization.view",
        "organization.manage",
        "organization.members.view",
        "organization.members.invite",
        "organization.members.manage",
        "cohorts.view",
        "cohorts.create",
        "cohorts.manage",
        "cohorts.assign",
        "learners.view_summary",
        "learners.view_detailed_progress",
        "learners.manage_enrolment",
        "assignments.view",
        "assignments.create",
        "assignments.manage",
        "reviews.view",
        "reports.view",
        "reports.export",
        "company_training.manage",
        "recruiter_evidence.view",
        "recruiter_evidence.request",
        "audit_logs.view",
        "career.organization_report.view",
    },
    "organization_owner": {
        "organization.view",
        "organization.manage",
        "organization.members.view",
        "organization.members.invite",
        "organization.members.manage",
        "cohorts.view",
        "cohorts.create",
        "cohorts.manage",
        "cohorts.assign",
        "learners.view_summary",
        "learners.view_detailed_progress",
        "learners.manage_enrolment",
        "assignments.view",
        "assignments.create",
        "assignments.manage",
        "reviews.view",
        "reviews.perform",
        "reports.view",
        "reports.export",
        "company_training.manage",
        "recruiter_evidence.view",
        "recruiter_evidence.request",
        "audit_logs.view",
        "career.organization_report.view",
    },
    "platform_admin": {
        "platform.manage",
        "content.manage",
        "audit_logs.view",
    }
    | CMS_ADMIN_PERMISSIONS,
    "platform_content_manager": CMS_ADMIN_PERMISSIONS
    | {
        "content.manage",
        "organization.view",
    },
    "content_admin": CMS_ADMIN_PERMISSIONS | {"content.manage"},
    "content_reviewer": CMS_REVIEW_PERMISSIONS,
    "instructional_reviewer": CMS_REVIEW_PERMISSIONS,
    "accessibility_reviewer": CMS_REVIEW_PERMISSIONS,
    "technical_reviewer": CMS_REVIEW_PERMISSIONS,
    "content_author": CMS_AUTHOR_PERMISSIONS,
    "curriculum_designer": CMS_AUTHOR_PERMISSIONS,
    "lab_designer": CMS_AUTHOR_PERMISSIONS,
    "assessment_designer": CMS_AUTHOR_PERMISSIONS,
    "mission_designer": CMS_AUTHOR_PERMISSIONS,
    "localization_manager": CMS_AUTHOR_PERMISSIONS | {"content.localization.manage"},
    "platform_support": {
        "organization.view",
        "platform.health.view",
        "platform.jobs.view",
        "content.view",
    },
    "support_engineer": {
        "organization.view",
        "platform.health.view",
        "platform.jobs.view",
        "platform.jobs.manage",
        "content.view",
        "audit_logs.view",
    },
    "platform_auditor": {
        "audit_logs.view",
        "organization.view",
        "content.view",
        "platform.health.view",
    },
    "read_only_auditor": {
        "audit_logs.view",
        "organization.view",
        "content.view",
        "content.media.view",
        "content.reports.view",
        "platform.settings.view",
        "platform.flags.view",
        "platform.health.view",
        "platform.jobs.view",
    },
}


def seed_roles(db: Session) -> None:
    permission_records: dict[str, Permission] = {}
    for permission_key in sorted(set().union(*ROLE_PERMISSIONS.values())):
        record = db.scalar(select(Permission).where(Permission.key == permission_key))
        if record is None:
            record = Permission(
                key=permission_key,
                description=permission_key.replace(".", " ").replace("_", " "),
            )
            db.add(record)
            db.flush()
        permission_records[permission_key] = record
    for role_key, permissions in ROLE_PERMISSIONS.items():
        role = db.scalar(select(Role).where(Role.key == role_key))
        if role is None:
            role = Role(
                key=role_key,
                name=role_key.replace("_", " ").title(),
            )
            db.add(role)
            db.flush()
        existing = set(
            db.scalars(
                select(Permission.key)
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .where(RolePermission.role_id == role.id)
            ).all()
        )
        for permission_key in permissions - existing:
            db.add(
                RolePermission(
                    role_id=role.id,
                    permission_id=permission_records[permission_key].id,
                )
            )


def seed_skills(db: Session) -> None:
    records: dict[str, Skill] = {}
    for stable_key, name, description, _, relevance in SKILLS:
        record = db.scalar(select(Skill).where(Skill.stable_key == stable_key))
        if record is None:
            record = Skill(
                stable_key=stable_key,
                name=name,
                description=description,
                evidence_types=[
                    "diagnostic",
                    "assessment",
                    "guided_practice",
                    "mission",
                    "project",
                ],
                minimum_evidence=3,
                recency_days=180,
                readiness_relevance=relevance,
                profile_version=SOC_PROFILE_VERSION,
            )
            db.add(record)
            db.flush()
        records[stable_key] = record
    for stable_key, _, _, prerequisites, _ in SKILLS:
        for prerequisite in prerequisites:
            exists = db.get(
                SkillDependency,
                (records[stable_key].id, records[prerequisite].id),
            )
            if exists is None:
                db.add(
                    SkillDependency(
                        skill_id=records[stable_key].id,
                        prerequisite_skill_id=records[prerequisite].id,
                        minimum_mastery=0.6,
                    )
                )


def seed_diagnostic(db: Session) -> None:
    assessment = db.scalar(
        select(Assessment).where(Assessment.stable_key == "junior-soc-diagnostic")
    )
    if assessment is None:
        assessment = Assessment(
            stable_key="junior-soc-diagnostic",
            title="Junior SOC Analyst Readiness Diagnostic",
            purpose="diagnostic",
        )
        db.add(assessment)
        db.flush()
    version = db.scalar(
        select(AssessmentVersion).where(
            AssessmentVersion.assessment_id == assessment.id,
            AssessmentVersion.version == SOC_PROFILE_VERSION,
        )
    )
    if version is None:
        version = AssessmentVersion(
            assessment_id=assessment.id,
            version=SOC_PROFILE_VERSION,
            status="published",
            instructions=(
                "Use the supplied evidence. Choose the most defensible answer; "
                "uncertainty is preferable to unsupported certainty."
            ),
            published_at=datetime.now(UTC),
        )
        db.add(version)
        db.flush()
    for position, definition in enumerate(DIAGNOSTIC_QUESTIONS):
        question = db.scalar(select(Question).where(Question.stable_key == definition["key"]))
        if question is None:
            question = Question(
                stable_key=definition["key"],
                assessment_id=assessment.id,
                skill_key=definition["skill"],
                question_type=definition["type"],
            )
            db.add(question)
            db.flush()
        question_version = db.scalar(
            select(QuestionVersion).where(
                QuestionVersion.question_id == question.id,
                QuestionVersion.version == SOC_PROFILE_VERSION,
            )
        )
        if question_version is None:
            db.add(
                QuestionVersion(
                    question_id=question.id,
                    version=SOC_PROFILE_VERSION,
                    prompt=definition["prompt"],
                    options=definition["options"],
                    private_answer=definition["answer"],
                    explanation=definition["explanation"],
                    difficulty="foundation" if position < 4 else "guided",
                    published=True,
                )
            )


def seed_flagship_mission(db: Session) -> None:
    definition = FLAGSHIP_MISSION
    mission = db.scalar(select(Mission).where(Mission.stable_key == definition["stable_key"]))
    if mission is None:
        mission = Mission(
            stable_key=definition["stable_key"],
            title=definition["title"],
            description=definition["description"],
            safety_classification=definition["safety_classification"],
        )
        db.add(mission)
        db.flush()
    version = db.scalar(
        select(MissionVersion).where(
            MissionVersion.mission_id == mission.id,
            MissionVersion.version == FLAGSHIP_MISSION_VERSION,
        )
    )
    if version is None:
        version = MissionVersion(
            mission_id=mission.id,
            version=FLAGSHIP_MISSION_VERSION,
            fictional_organization=definition["fictional_organization"],
            business_context=definition["business_context"],
            briefing=definition["briefing"],
            status="published",
            evidence_manifest=list(definition["stages"]),
            evaluator_version=EVALUATOR_VERSION,
        )
        db.add(version)
        db.flush()
    for position, stage_definition in enumerate(definition["stages"], start=1):
        stage = db.scalar(
            select(MissionStage).where(
                MissionStage.mission_version_id == version.id,
                MissionStage.position == position,
            )
        )
        if stage is None:
            stage = MissionStage(
                mission_version_id=version.id,
                position=position,
                stable_key=stage_definition["key"],
                title=stage_definition["title"],
                objective=stage_definition["objective"],
            )
            db.add(stage)
            db.flush()
        objective = db.scalar(
            select(MissionObjective).where(
                MissionObjective.mission_stage_id == stage.id,
                MissionObjective.stable_key == f"{stage_definition['key']}-objective",
            )
        )
        if objective is None:
            db.add(
                MissionObjective(
                    mission_stage_id=stage.id,
                    stable_key=f"{stage_definition['key']}-objective",
                    description=stage_definition["objective"],
                    required=True,
                    skill_key=stage_definition["skill"],
                )
            )


def seed_flagship_project(db: Session) -> None:
    definition = FLAGSHIP_PROJECT
    project = db.scalar(select(Project).where(Project.stable_key == definition["stable_key"]))
    if project is None:
        project = Project(
            stable_key=definition["stable_key"],
            publication_id=definition["publication_id"],
            title=definition["title"],
            description=definition["description"],
            version=FLAGSHIP_PROJECT_VERSION,
        )
        db.add(project)
        db.flush()
    for position, (title, requirement) in enumerate(definition["milestones"], start=1):
        milestone = db.scalar(
            select(ProjectMilestone).where(
                ProjectMilestone.project_id == project.id,
                ProjectMilestone.position == position,
            )
        )
        if milestone is None:
            db.add(
                ProjectMilestone(
                    project_id=project.id,
                    position=position,
                    title=title,
                    requirement=requirement,
                )
            )
    rubric = db.scalar(
        select(Rubric).where(
            Rubric.project_id == project.id,
            Rubric.version == FLAGSHIP_PROJECT_VERSION,
        )
    )
    if rubric is None:
        rubric = Rubric(
            project_id=project.id,
            version=FLAGSHIP_PROJECT_VERSION,
            status="published",
        )
        db.add(rubric)
        db.flush()
    for criterion in definition["criteria"]:
        existing = db.scalar(
            select(RubricCriterion).where(
                RubricCriterion.rubric_id == rubric.id,
                RubricCriterion.stable_key == criterion["key"],
            )
        )
        if existing is None:
            db.add(
                RubricCriterion(
                    rubric_id=rubric.id,
                    stable_key=criterion["key"],
                    description=criterion["description"],
                    weight=criterion["weight"],
                    pass_standard=criterion["pass_standard"],
                )
            )


def seed() -> None:
    with SessionLocal() as db:
        seed_roles(db)
        seed_skills(db)
        seed_diagnostic(db)
        seed_flagship_mission(db)
        seed_flagship_project(db)
        db.commit()
        print(
            {
                "event": "competition_seed_complete",
                "profileVersion": SOC_PROFILE_VERSION,
                "skills": len(SKILLS),
                "diagnosticQuestions": len(DIAGNOSTIC_QUESTIONS),
                "flagshipMission": FLAGSHIP_MISSION["stable_key"],
                "flagshipProject": FLAGSHIP_PROJECT["stable_key"],
            }
        )


if __name__ == "__main__":
    seed()
