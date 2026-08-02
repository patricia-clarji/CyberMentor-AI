import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.seed import seed_roles
from app.models import (
    MembershipRole,
    Organization,
    OrganizationMembership,
    Role,
    User,
    UserProfile,
)
from app.models.cms import CmsBackgroundJob
from app.models.learning import LearningActivityAttempt
from app.security.passwords import hash_password

PASSWORD = "Strong-Password-42!"  # noqa: S105


def setup_cms_users(db: Session) -> dict[str, str]:
    seed_roles(db)
    organization = Organization(
        name="CMS Test Organization",
        slug=f"cms-test-{uuid.uuid4().hex[:8]}",
        kind="training_provider",
        status="active",
    )
    db.add(organization)
    db.flush()
    accounts = {
        "admin@example.com": "content_admin",
        "author@example.com": "content_author",
        "reviewer-one@example.com": "technical_reviewer",
        "reviewer-two@example.com": "instructional_reviewer",
        "learner@example.com": "learner",
        "organization-admin@example.com": "organization_admin",
        "auditor@example.com": "read_only_auditor",
        "support@example.com": "platform_support",
    }
    for email, role_key in accounts.items():
        user = User(
            email=email,
            password_hash=hash_password(PASSWORD),
            email_verified_at=datetime.now(UTC),
            is_active=True,
        )
        db.add(user)
        db.flush()
        db.add(UserProfile(user_id=user.id, display_name=email.split("@")[0]))
        membership = OrganizationMembership(
            organization_id=organization.id,
            user_id=user.id,
            is_active=True,
        )
        db.add(membership)
        db.flush()
        role = db.scalar(select(Role).where(Role.key == role_key))
        assert role is not None
        db.add(MembershipRole(membership_id=membership.id, role_id=role.id))
    db.commit()
    return accounts


def login(client: TestClient, email: str) -> str:
    client.cookies.clear()
    response = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    csrf = response.cookies.get("cm_csrf")
    assert csrf
    return csrf


def h(csrf: str) -> dict[str, str]:
    return {"X-CSRF-Token": csrf}


def lesson_payload(slug: str = "defensive-log-triage") -> dict[str, object]:
    return {
        "content_type": "lesson",
        "title": "Defensive log triage",
        "public_slug": slug,
        "description": "Correlate synthetic authentication evidence safely.",
        "language": "en",
        "visibility": "public",
        "version": "1.0.0",
        "change_summary": "Initial reviewed lesson",
        "metadata": {
            "difficulty": "beginner",
            "estimatedMinutes": 20,
            "skillKeys": ["soc-evidence-analysis"],
        },
        "sections": [
            {
                "section_type": "introduction",
                "title": "Start with evidence",
                "body": "Separate timestamped observations from conclusions.",
                "sort_order": 0,
            },
            {
                "section_type": "concept_explanation",
                "title": "Correlate records",
                "body": "Compare authentication events from the synthetic host.",
                "sort_order": 1,
            },
            {
                "section_type": "references",
                "title": "Reviewed references",
                "body": "NIST Cybersecurity Framework 2.0, retrieved 2026-07-19.",
                "sort_order": 2,
            },
        ],
        "objectives": [
            {
                "title": "Correlate authentication evidence",
                "description": "Analyze multiple synthetic records before escalation.",
                "bloom_level": "analyze",
                "linked_skill_keys": ["soc-evidence-analysis"],
                "assessment_coverage": True,
                "practical_coverage": True,
                "review_status": "reviewed",
            }
        ],
    }


def create_lesson(client: TestClient, email: str = "author@example.com") -> dict[str, object]:
    csrf = login(client, email)
    response = client.post("/api/v1/cms/contents", headers=h(csrf), json=lesson_payload())
    assert response.status_code == 201, response.text
    return response.json()


def submit_and_assign(client: TestClient, item: dict[str, object]) -> None:
    content_id = item["id"]
    version_id = item["version_id"]
    csrf = login(client, "author@example.com")
    validated = client.post(
        f"/api/v1/cms/contents/{content_id}/versions/{version_id}/validate",
        headers=h(csrf),
    )
    assert validated.status_code == 200
    assert validated.json()["failures"] == 0
    assert (
        client.post(
            f"/api/v1/cms/contents/{content_id}/versions/{version_id}/submit-review",
            headers=h(csrf),
        ).status_code
        == 200
    )
    csrf = login(client, "admin@example.com")
    for email, reviewer_type in [
        ("reviewer-one@example.com", "technical_reviewer"),
        ("reviewer-two@example.com", "instructional_reviewer"),
    ]:
        response = client.post(
            f"/api/v1/cms/contents/{content_id}/versions/{version_id}/reviewers",
            headers=h(csrf),
            json={"reviewer_email": email, "reviewer_type": reviewer_type},
        )
        assert response.status_code == 201, response.text


def approve(client: TestClient, item: dict[str, object], email: str) -> dict[str, object]:
    csrf = login(client, email)
    response = client.post(
        f"/api/v1/cms/contents/{item['id']}/versions/{item['version_id']}/decision",
        headers=h(csrf),
        json={
            "decision": "approve",
            "notes": "Required review checks passed.",
            "checklist": [
                {"key": "technical_correctness", "required": True, "passed": True},
                {"key": "accessibility", "required": True, "passed": True},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_lesson_review_revision_publication_versioning_and_rollback(
    client: TestClient, db: Session
) -> None:
    setup_cms_users(db)
    item = create_lesson(client)
    submit_and_assign(client, item)

    csrf = login(client, "reviewer-one@example.com")
    queue = client.get("/api/v1/cms/reviews")
    assert queue.status_code == 200
    assignment_id = next(
        row["assignment_id"] for row in queue.json() if row["version_id"] == item["version_id"]
    )
    started = client.post(f"/api/v1/cms/reviewers/{assignment_id}/start", headers=h(csrf))
    assert started.status_code == 200
    assert started.json()["status"] == "in_review"
    comment = client.post(
        f"/api/v1/cms/contents/{item['id']}/versions/{item['version_id']}/comments",
        headers=h(csrf),
        json={
            "body": "Clarify the evidence ordering.",
            "location_type": "section",
            "location_key": item["sections"][1]["key"],
            "severity": "blocking",
        },
    )
    assert comment.status_code == 201
    comment_id = comment.json()["comments"][0]["id"]
    requested = client.post(
        f"/api/v1/cms/contents/{item['id']}/versions/{item['version_id']}/decision",
        headers=h(csrf),
        json={
            "decision": "request_changes",
            "notes": "Evidence ordering needs clarification.",
            "checklist": [],
        },
    )
    assert requested.status_code == 200
    assert requested.json()["version_status"] == "revision_requested"

    csrf = login(client, "author@example.com")
    changed = requested.json()
    original_created_at = changed["sections"][1]["createdAt"]
    reply = client.post(
        f"/api/v1/cms/contents/{item['id']}/versions/{item['version_id']}/comments",
        headers=h(csrf),
        json={
            "body": "I will clarify the timestamp ordering.",
            "parent_comment_id": comment_id,
            "location_type": "section",
            "location_key": item["sections"][1]["key"],
            "severity": "suggestion",
        },
    )
    assert reply.status_code == 201
    reply_id = next(
        row["id"] for row in reply.json()["comments"] if row["parent_comment_id"] == comment_id
    )
    edited_reply = client.put(
        f"/api/v1/cms/comments/{reply_id}",
        headers=h(csrf),
        json={"body": "I clarified the timestamp ordering.", "suggested_change": None},
    )
    assert edited_reply.status_code == 200
    changed["sections"][1]["body"] = "Order records by timestamp, then compare the source."
    saved = client.put(
        f"/api/v1/cms/contents/{item['id']}/versions/{item['version_id']}",
        headers=h(csrf),
        json={
            "expected_lock_version": changed["lock_version"],
            "title": changed["title"],
            "public_slug": changed["public_slug"],
            "description": changed["description"],
            "visibility": changed["visibility"],
            "change_summary": "Clarified evidence ordering",
            "metadata": changed["metadata"],
            "sections": [
                {
                    "section_key": section["key"],
                    "section_type": section["type"],
                    "title": section["title"],
                    "body": section["body"],
                    "structured_data": section["data"],
                    "visibility": section["visibility"],
                    "accessibility_label": section["accessibilityLabel"],
                    "sort_order": section["order"],
                }
                for section in changed["sections"]
            ],
            "objectives": [
                {
                    "objective_key": objective["key"],
                    "title": objective["title"],
                    "description": objective["description"],
                    "bloom_level": objective["bloomLevel"],
                    "linked_skill_keys": objective["skills"],
                    "assessment_coverage": objective["assessmentCoverage"],
                    "practical_coverage": objective["practicalCoverage"],
                    "review_status": objective["reviewStatus"],
                }
                for objective in changed["objectives"]
            ],
        },
    )
    assert saved.status_code == 200
    assert saved.json()["sections"][1]["createdAt"] == original_created_at
    assert (
        client.patch(
            f"/api/v1/cms/comments/{comment_id}",
            headers=h(csrf),
            json={"resolved": True},
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/v1/cms/comments/{comment_id}",
            headers=h(csrf),
            json={"resolved": False},
        ).json()["status"]
        == "open"
    )
    assert (
        client.patch(
            f"/api/v1/cms/comments/{comment_id}",
            headers=h(csrf),
            json={"resolved": True},
        ).json()["status"]
        == "resolved"
    )
    submit_and_assign(client, saved.json())
    approve(client, saved.json(), "reviewer-one@example.com")
    approved = approve(client, saved.json(), "reviewer-two@example.com")
    assert approved["version_status"] == "approved"

    csrf = login(client, "admin@example.com")
    scheduled = client.post(
        f"/api/v1/cms/contents/{item['id']}/versions/{item['version_id']}/schedule",
        headers=h(csrf),
        json={
            "publish_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            "timezone": "Asia/Beirut",
        },
    )
    assert scheduled.status_code == 200
    published = client.post(
        f"/api/v1/cms/contents/{item['id']}/versions/{item['version_id']}/publish",
        headers=h(csrf),
        json={"reason": "Verified publication"},
    )
    assert published.status_code == 200, published.text
    assert published.json()["version_status"] == "published"

    csrf = login(client, "learner@example.com")
    learner = client.get("/api/v1/managed-content/lessons/defensive-log-triage")
    assert learner.status_code == 200
    learner_payload = learner.json()
    serialized = learner.text.casefold()
    assert "reviews" not in learner_payload
    assert "reviewstatus" not in serialized
    assert "checksum" not in serialized
    assert "answer" not in serialized

    csrf = login(client, "admin@example.com")
    draft = client.post(
        f"/api/v1/cms/contents/{item['id']}/versions/{item['version_id']}/draft",
        headers=h(csrf),
        json={"version": "1.1.0", "change_summary": "Second edition"},
    )
    assert draft.status_code == 201
    assert draft.json()["revision"] == 2
    client.cookies.clear()
    assert client.get("/api/v1/managed-content/lessons/defensive-log-triage").status_code == 401
    login(client, "learner@example.com")
    assert (
        client.get("/api/v1/managed-content/lessons/defensive-log-triage").json()["version"]
        == "1.0.0"
    )

    csrf = login(client, "admin@example.com")
    comparison = client.get(
        f"/api/v1/cms/contents/{item['id']}/compare?from_revision=1&to_revision=2"
    )
    assert comparison.status_code == 200
    rollback = client.post(
        f"/api/v1/cms/contents/{item['id']}/rollback",
        headers=h(csrf),
        json={"target_revision": 1, "reason": "Verified rollback keeps history"},
    )
    assert rollback.status_code == 200
    assert rollback.json()["revision"] == 1


def test_permissions_conflicts_validation_and_draft_exposure(
    client: TestClient, db: Session
) -> None:
    setup_cms_users(db)
    csrf = login(client, "learner@example.com")
    assert (
        client.post(
            "/api/v1/cms/contents", headers=h(csrf), json=lesson_payload("denied")
        ).status_code
        == 403
    )
    assert client.get("/api/v1/cms/contents").status_code == 403

    item = create_lesson(client)
    other_org = Organization(
        name="Other CMS Tenant",
        slug=f"other-cms-{uuid.uuid4().hex[:8]}",
        kind="training_provider",
        status="active",
    )
    other_user = User(
        email="other-admin@example.com",
        password_hash=hash_password(PASSWORD),
        email_verified_at=datetime.now(UTC),
        is_active=True,
    )
    db.add_all([other_org, other_user])
    db.flush()
    db.add(UserProfile(user_id=other_user.id, display_name="Other admin"))
    other_membership = OrganizationMembership(
        organization_id=other_org.id,
        user_id=other_user.id,
        is_active=True,
    )
    db.add(other_membership)
    db.flush()
    content_admin_role = db.scalar(select(Role).where(Role.key == "content_admin"))
    assert content_admin_role is not None
    db.add(MembershipRole(membership_id=other_membership.id, role_id=content_admin_role.id))
    db.commit()
    login(client, "other-admin@example.com")
    assert client.get(f"/api/v1/cms/contents/{item['id']}").status_code == 404
    assert (
        client.get(f"/api/v1/cms/contents/{item['id']}/versions/{item['version_id']}").status_code
        == 404
    )
    csrf = login(client, "author@example.com")
    update = lesson_payload()
    response = client.put(
        f"/api/v1/cms/contents/{item['id']}/versions/{item['version_id']}",
        headers=h(csrf),
        json={
            "expected_lock_version": 999,
            "title": update["title"],
            "public_slug": update["public_slug"],
            "description": update["description"],
            "visibility": update["visibility"],
            "change_summary": "Stale update",
            "metadata": update["metadata"],
            "sections": update["sections"],
            "objectives": update["objectives"],
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "cms_edit_conflict"
    login(client, "learner@example.com")
    assert client.get("/api/v1/managed-content/lessons/defensive-log-triage").status_code == 404

    csrf = login(client, "auditor@example.com")
    assert client.get("/api/v1/cms/contents").status_code == 200
    assert (
        client.post(
            "/api/v1/cms/contents", headers=h(csrf), json=lesson_payload("auditor-write")
        ).status_code
        == 403
    )


def test_media_dependency_deletion_and_feature_flag_audit(
    client: TestClient, db: Session, tmp_path: Path
) -> None:
    setup_cms_users(db)
    settings = get_settings()
    previous_root = settings.cms_media_root
    settings.cms_media_root = tmp_path
    try:
        item = create_lesson(client, "admin@example.com")
        csrf = login(client, "admin@example.com")
        uploaded = client.post(
            "/api/v1/cms/media",
            headers=h(csrf),
            files={"file": ("safe diagram.png", b"\x89PNG\r\n\x1a\n", "image/png")},
            data={
                "title": "Authentication event diagram",
                "description": "A synthetic event sequence for the lesson.",
                "accessibility_text": "Synthetic authentication event diagram",
            },
        )
        assert uploaded.status_code == 201, uploaded.text
        media_id = uploaded.json()["id"]
        attached = client.post(
            f"/api/v1/cms/media/{media_id}/attach",
            headers=h(csrf),
            params={"version_id": item["version_id"], "location_key": "lesson-diagram"},
        )
        assert attached.status_code == 201
        assert attached.json()["usage_count"] == 1
        denied_delete = client.delete(f"/api/v1/cms/media/{media_id}", headers=h(csrf))
        assert denied_delete.status_code == 409
        assert denied_delete.json()["error"]["code"] == "cms_media_in_use"

        flag = client.post(
            "/api/v1/cms/feature-flags",
            headers=h(csrf),
            json={
                "name": "cms.lesson-preview",
                "description": "Enable the reviewed lesson preview.",
                "environment": "development",
                "current_state": True,
                "starts_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
                "expires_at": (datetime.now(UTC) + timedelta(hours=2)).isoformat(),
            },
        )
        assert flag.status_code == 201
        assert flag.json()["effective_state"] is False
        effective = client.get(
            "/api/v1/managed-content/feature-flags/cms.lesson-preview?environment=development"
        )
        assert effective.status_code == 200
        assert effective.json()["name"] == "cms.lesson-preview"
        assert effective.json()["enabled"] is False
        changed = client.patch(
            f"/api/v1/cms/feature-flags/{flag.json()['id']}",
            headers=h(csrf),
            json={
                "current_state": False,
                "description": "Pause preview during verification.",
            },
        )
        assert changed.status_code == 200
        events = client.get("/api/v1/cms/audit")
        assert events.status_code == 200
        actions = {event["action"] for event in events.json()}
        assert "cms.media.upload" in actions
        assert "cms.media.delete_denied" in actions
        assert "cms.feature_flag.update" in actions
    finally:
        settings.cms_media_root = previous_root


def test_invalid_content_is_blocked_and_dashboard_is_derived(
    client: TestClient, db: Session
) -> None:
    setup_cms_users(db)
    payload = lesson_payload("invalid-lesson")
    payload["metadata"] = {}
    payload["sections"] = []
    payload["objectives"] = []
    csrf = login(client, "author@example.com")
    created = client.post("/api/v1/cms/contents", headers=h(csrf), json=payload)
    assert created.status_code == 201
    content = created.json()
    validation = client.post(
        f"/api/v1/cms/contents/{content['id']}/versions/{content['version_id']}/validate",
        headers=h(csrf),
    )
    assert validation.status_code == 200
    assert validation.json()["failures"] >= 4
    blocked = client.post(
        f"/api/v1/cms/contents/{content['id']}/versions/{content['version_id']}/submit-review",
        headers=h(csrf),
    )
    assert blocked.status_code == 409

    csrf = login(client, "admin@example.com")
    dashboard = client.get("/api/v1/cms/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["counts"]["draft"] == 1
    assert dashboard.json()["validation_failures"] >= 4
    assert dashboard.json()["worker_status"] == "unknown"


def generic_payload(content_type: str, slug: str, metadata: dict[str, object]) -> dict[str, object]:
    return {
        "content_type": content_type,
        "title": f"CMS {content_type.replace('_', ' ').title()}",
        "public_slug": slug,
        "description": f"A durable {content_type} builder test record.",
        "language": "en",
        "visibility": "private",
        "version": "1.0.0",
        "change_summary": "Builder contract coverage",
        "metadata": metadata,
        "sections": [],
        "objectives": [],
        "relationships": [],
    }


def test_all_dedicated_builder_contracts_and_protected_engine_previews(
    client: TestClient, db: Session
) -> None:
    setup_cms_users(db)
    csrf = login(client, "author@example.com")
    metadata_by_type: dict[str, dict[str, object]] = {
        "course": {
            "summary": "Course summary",
            "audience": "Aspiring analysts",
            "difficulty": "beginner",
            "estimatedMinutes": 120,
            "outcomes": ["Triage evidence"],
            "skillKeys": ["soc-evidence-analysis"],
            "completionRule": "Complete every required item.",
        },
        "module": {
            "purpose": "Build evidence triage skill.",
            "estimatedMinutes": 45,
            "completionRule": "Complete the lesson and practice.",
        },
        "assessment": {
            "purpose": "Check evidence triage.",
            "instructions": "Answer every question.",
            "passingScore": 0.7,
            "attemptLimit": 2,
            "feedbackPolicy": "after_attempt",
        },
        "lab": {
            "scenario": "Inspect a synthetic event file.",
            "difficulty": "beginner",
            "estimatedMinutes": 20,
            "allowedCommands": ["ls", "cat"],
            "commandResponses": {"cat evidence.txt": "synthetic event"},
            "expectedEvidence": ["Identify the event"],
            "validationRules": ["mention event"],
            "hints": ["List the home directory"],
            "completionRule": "Submit the identified event.",
            "virtualFiles": [
                {
                    "id": "file-1",
                    "path": "/home/analyst/evidence.txt",
                    "content": "synthetic event",
                    "mode": "0644",
                    "owner": "analyst",
                    "group": "analyst",
                }
            ],
        },
        "mission": {
            "briefing": "Investigate a synthetic alert.",
            "fictionalOrganization": "Northstar Foods",
            "learnerRole": "SOC analyst",
            "stages": [
                {
                    "id": "stage-1",
                    "title": "Triage",
                    "goal": "Identify the source",
                    "evidence": ["auth.log"],
                    "actions": ["inspect log"],
                    "hints": ["Compare timestamps"],
                }
            ],
            "scoring": ["evidence quality"],
            "completionRule": "Finish every stage.",
        },
        "learning_path": {
            "targetRole": "Junior SOC analyst",
            "completionCriteria": "Complete all required nodes.",
            "readinessCriteria": "Pass assessment and lab.",
        },
        "skill": {
            "stableSkillId": "cms-soc-triage",
            "category": "security-operations",
            "evidenceRequirements": ["one assessment", "one lab"],
        },
        "reference": {
            "publisher": "NIST",
            "url": "https://www.nist.gov/cyberframework",
            "retrievalDate": "2026-08-02",
            "freshnessDays": 90,
        },
    }
    created: dict[str, dict[str, object]] = {}
    for content_type, metadata in metadata_by_type.items():
        response = client.post(
            "/api/v1/cms/contents",
            headers=h(csrf),
            json=generic_payload(
                content_type, f"builder-{content_type.replace('_', '-')}", metadata
            ),
        )
        assert response.status_code == 201, response.text
        created[content_type] = response.json()
        validation = client.post(
            f"/api/v1/cms/contents/{response.json()['id']}/versions/{response.json()['version_id']}/validate",
            headers=h(csrf),
        )
        assert validation.status_code == 200, validation.text
        assert validation.json()["failures"] == 0, validation.text

    lab = created["lab"]
    command = client.post(
        f"/api/v1/cms/contents/{lab['id']}/versions/{lab['version_id']}/test-lab/command",
        headers=h(csrf),
        json={"command": "cat evidence.txt", "cwd": "/home/analyst"},
    )
    assert command.status_code == 200, command.text
    assert command.json()["output"] == "synthetic event"
    assert command.json()["creates_evidence"] is False
    mission = created["mission"]
    mission_preview = client.get(
        f"/api/v1/cms/contents/{mission['id']}/versions/{mission['version_id']}/test-mission"
    )
    assert mission_preview.status_code == 200
    assert mission_preview.json()["preview"] is True
    assert mission_preview.json()["creates_evidence"] is False
    mission_action = client.post(
        f"/api/v1/cms/contents/{mission['id']}/versions/{mission['version_id']}/test-mission/action",
        headers=h(csrf),
        json={
            "stage_id": "stage-1",
            "action_type": "decision",
            "decision_id": "inspect log",
        },
    )
    assert mission_action.status_code == 200, mission_action.text
    assert mission_action.json()["outcome"] == "correct"
    assert mission_action.json()["mission_ready"] is True
    assert mission_action.json()["creates_evidence"] is False

    author_publish = client.post(
        f"/api/v1/cms/contents/{lab['id']}/versions/{lab['version_id']}/publish",
        headers=h(csrf),
        json={"reason": "Author must not publish"},
    )
    assert author_publish.status_code == 403


def test_question_types_answer_safety_and_published_assessment_evidence_version(
    client: TestClient, db: Session
) -> None:
    setup_cms_users(db)
    csrf = login(client, "author@example.com")
    question_types = [
        "single_choice",
        "multiple_choice",
        "true_false",
        "ordering",
        "matching",
        "command_interpretation",
        "log_interpretation",
        "scenario_decision",
        "short_response",
    ]
    questions: list[dict[str, object]] = []
    for index, question_type in enumerate(question_types):
        metadata: dict[str, object] = {
            "questionType": question_type,
            "prompt": f"Question {index + 1}",
            "answerKey": ["alpha"],
            "explanation": "Alpha is supported by the synthetic evidence.",
            "skillKeys": ["soc-evidence-analysis"],
        }
        if question_type in {
            "single_choice",
            "multiple_choice",
            "ordering",
            "matching",
            "scenario_decision",
        }:
            metadata["options"] = ["alpha", "beta"]
        response = client.post(
            "/api/v1/cms/contents",
            headers=h(csrf),
            json=generic_payload(
                "question", f"question-{question_type.replace('_', '-')}", metadata
            ),
        )
        assert response.status_code == 201, response.text
        item = response.json()
        questions.append(item)
        validation = client.post(
            f"/api/v1/cms/contents/{item['id']}/versions/{item['version_id']}/validate",
            headers=h(csrf),
        )
        assert validation.json()["failures"] == 0
        preview = client.get(
            f"/api/v1/cms/contents/{item['id']}/versions/{item['version_id']}/preview"
        )
        assert preview.status_code == 200
        assert "answerkey" not in preview.text.casefold()
        assert "explanation" not in preview.text.casefold()

    question = questions[0]
    assert (
        client.post(
            f"/api/v1/cms/contents/{question['id']}/versions/{question['version_id']}/submit-review",
            headers=h(csrf),
        ).status_code
        == 200
    )
    csrf = login(client, "admin@example.com")
    assert (
        client.post(
            f"/api/v1/cms/contents/{question['id']}/versions/{question['version_id']}/reviewers",
            headers=h(csrf),
            json={
                "reviewer_email": "reviewer-two@example.com",
                "reviewer_type": "instructional_reviewer",
            },
        ).status_code
        == 201
    )
    approve(client, question, "reviewer-two@example.com")
    csrf = login(client, "admin@example.com")
    assert (
        client.post(
            f"/api/v1/cms/contents/{question['id']}/versions/{question['version_id']}/publish",
            headers=h(csrf),
            json={"reason": "Publish versioned question"},
        ).status_code
        == 200
    )

    csrf = login(client, "author@example.com")
    assessment_payload = generic_payload(
        "assessment",
        "cms-versioned-assessment",
        {
            "purpose": "Verify server-side assessment grading.",
            "instructions": "Choose the evidence-supported answer.",
            "passingScore": 0.7,
            "attemptLimit": 2,
            "feedbackPolicy": "after_attempt",
        },
    )
    assessment_payload["relationships"] = [
        {
            "target_content_id": question["id"],
            "target_version_id": question["version_id"],
            "relation_type": "question",
            "required": True,
            "sort_order": 0,
            "configuration": {},
        }
    ]
    created = client.post("/api/v1/cms/contents", headers=h(csrf), json=assessment_payload)
    assert created.status_code == 201, created.text
    assessment = created.json()
    submit_and_assign(client, assessment)
    approve(client, assessment, "reviewer-one@example.com")
    approve(client, assessment, "reviewer-two@example.com")
    csrf = login(client, "admin@example.com")
    assert (
        client.post(
            f"/api/v1/cms/contents/{assessment['id']}/versions/{assessment['version_id']}/publish",
            headers=h(csrf),
            json={"reason": "Publish real learner assessment"},
        ).status_code
        == 200
    )

    csrf = login(client, "learner@example.com")
    learner = client.get("/api/v1/managed-content/assessment/cms-versioned-assessment")
    assert learner.status_code == 200, learner.text
    assert learner.json()["questions"][0]["metadata"]["options"] == ["alpha", "beta"]
    assert "answerkey" not in learner.text.casefold()
    submitted = client.post(
        "/api/v1/managed-content/assessments/cms-versioned-assessment/submit",
        headers=h(csrf),
        json={
            "answers": {str(question["id"]): "alpha"},
            "idempotency_key": "cms-test-attempt-0001",
        },
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["passed"] is True
    assert submitted.json()["content_version_id"] == str(assessment["version_id"])
    attempt = db.get(LearningActivityAttempt, uuid.UUID(submitted.json()["attempt_id"]))
    assert attempt is not None
    assert attempt.response["cms_version_id"] == str(assessment["version_id"])
    assert attempt.activity_version == "1.0.0"


def test_reference_normalization_skill_merge_and_job_authorization(
    client: TestClient, db: Session
) -> None:
    setup_cms_users(db)
    csrf = login(client, "author@example.com")
    reference = generic_payload(
        "reference",
        "normalized-reference",
        {
            "publisher": "NIST",
            "url": "https://NIST.GOV/cyberframework#overview",
            "retrievalDate": "2026-08-02",
            "freshnessDays": 90,
        },
    )
    created_reference = client.post("/api/v1/cms/contents", headers=h(csrf), json=reference)
    assert created_reference.status_code == 201, created_reference.text
    assert created_reference.json()["metadata"]["url"] == "https://nist.gov/cyberframework"
    duplicate = dict(reference)
    duplicate["public_slug"] = "duplicate-reference"
    duplicate["metadata"] = {
        **reference["metadata"],
        "url": "https://nist.gov/cyberframework",
    }
    duplicate_response = client.post("/api/v1/cms/contents", headers=h(csrf), json=duplicate)
    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["error"]["code"] == "cms_reference_duplicate"

    source = client.post(
        "/api/v1/cms/contents",
        headers=h(csrf),
        json=generic_payload(
            "skill",
            "legacy-triage-skill",
            {
                "stableSkillId": "legacy-triage",
                "category": "security-operations",
                "evidenceRequirements": ["one lab"],
            },
        ),
    ).json()
    target = client.post(
        "/api/v1/cms/contents",
        headers=h(csrf),
        json=generic_payload(
            "skill",
            "current-triage-skill",
            {
                "stableSkillId": "current-triage",
                "category": "security-operations",
                "evidenceRequirements": ["one lab", "one assessment"],
            },
        ),
    ).json()
    csrf = login(client, "admin@example.com")
    merged = client.post(
        f"/api/v1/cms/contents/{source['id']}/merge-skill",
        headers=h(csrf),
        json={"target_skill_id": target["id"], "reason": "Consolidate duplicate taxonomy"},
    )
    assert merged.status_code == 200, merged.text
    assert merged.json()["published_history_preserved"] is True

    organization = db.scalar(select(Organization).where(Organization.slug.like("cms-test-%")))
    admin = db.scalar(select(User).where(User.email == "admin@example.com"))
    assert organization is not None and admin is not None
    job = CmsBackgroundJob(
        organization_id=organization.id,
        job_type="link_checking",
        status="failed",
        progress=20,
        initiated_by_user_id=admin.id,
        idempotency_key=f"test-job:{uuid.uuid4()}",
        error_detail="Remote source timed out without exposing secrets.",
    )
    db.add(job)
    db.commit()
    csrf = login(client, "support@example.com")
    visible = client.get("/api/v1/cms/jobs")
    assert visible.status_code == 200
    assert str(job.id) in {item["id"] for item in visible.json()}
    denied = client.post(
        f"/api/v1/cms/jobs/{job.id}/retry",
        headers=h(csrf),
        json={"reason": "Support cannot mutate jobs"},
    )
    assert denied.status_code == 403
    csrf = login(client, "admin@example.com")
    retried = client.post(
        f"/api/v1/cms/jobs/{job.id}/retry",
        headers=h(csrf),
        json={"reason": "Retry disposable test job"},
    )
    assert retried.status_code == 200
    assert retried.json()["retry_count"] == 1
    cancelled = client.post(
        f"/api/v1/cms/jobs/{job.id}/cancel",
        headers=h(csrf),
        json={"reason": "Cancel disposable test job"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"


def test_media_rejects_mime_mismatch_and_dangerous_extension(
    client: TestClient, db: Session, tmp_path: Path
) -> None:
    setup_cms_users(db)
    settings = get_settings()
    previous_root = settings.cms_media_root
    settings.cms_media_root = tmp_path
    try:
        csrf = login(client, "admin@example.com")
        mismatch = client.post(
            "/api/v1/cms/media",
            headers=h(csrf),
            files={"file": ("diagram.jpg", b"not-an-image", "image/png")},
            data={"title": "Mismatched diagram", "accessibility_text": "Diagram"},
        )
        assert mismatch.status_code == 400
        dangerous = client.post(
            "/api/v1/cms/media",
            headers=h(csrf),
            files={"file": ("payload.exe", b"MZ", "application/octet-stream")},
            data={"title": "Dangerous payload"},
        )
        assert dangerous.status_code == 400
    finally:
        settings.cms_media_root = previous_root
