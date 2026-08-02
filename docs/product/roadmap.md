# Product roadmap

## Implemented and verified locally

Responsive frontend shell; five roadmap shells; local enrollment, progress, notes, bookmarks, and recommendation dismissal; a verified-only content repository and learner API; server-only assessment keys and lab verification rules; structured content blocks; deterministic Sentinel safeguards; source-backed import/review/publish/sync/rollback pipeline; draft skill graph; deterministic mastery, recency, diagnostic, hint, and recommendation rules; six adaptive learner-profile acceptance tests; request security controls; and lint/type/build/test gates.

## Implemented but environment verification pending

Nginx production container, Compose, and GitHub Actions workflow. Docker was unavailable locally. The adaptive PostgreSQL migration is present but no database service or migration runner exists, so it is unapplied architecture.

## Release blockers

- Enroll accountable subject-matter, instructional, accessibility, licensing, safety, and publisher reviewers; author, review, and publish the substantial 12-course curriculum and every associated question, lab, project, scenario, rubric, completion rule, and practice variant.
- Add authenticated user lifecycle, server sessions, RBAC, organization isolation, PostgreSQL persistence, migrations/seeds, and auditable instructor controls.
- Add real project/rubric workflows, isolated lab compute and lifecycle enforcement, queues/workers, uploads, analytics, billing/entitlements, and operational observability.
- Add real-browser E2E/accessibility coverage and verify Docker/Compose in a capable environment.

## Recommended next release milestone

Ship a reviewable vertical slice for one foundational course: versioned course/module/lesson publications, an independently reviewed question bank, one defensive local lab with bounded verification, a workplace project and rubric, authenticated learner/instructor roles, durable mastery evidence, and E2E tests. Do not expand to all 12 courses until that slice passes publication, security, accessibility, and learning-quality review.

## Later expansion

SSO-backed authoring CMS, cohort analytics, safe adaptive low-stakes assessment, isolated lab orchestration, live citation-validated RAG, validated certificates, organization billing, localization/RTL, data export/deletion, and additional expert-reviewed domains.
