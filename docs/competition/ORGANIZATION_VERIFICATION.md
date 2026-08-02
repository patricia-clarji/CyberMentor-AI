# Organization milestone verification

Automated coverage includes:

- invitation token hashing, intended-email binding, single-use state, role restrictions, and inactive membership;
- permission failures for role escalation, audit access, reviews, and exports;
- programme/cohort creation, enrolment, staff and curriculum assignment, archive preservation;
- assignment publication, learner visibility, submission, revision request, resubmission, approval, and history;
- analytics calculated from persisted learner-assignment and review rows;
- learner-selected recruiter evidence, private-email default, access logs, expiry, revocation, and tenant isolation;
- migration from an empty database, strict backend typing, frontend type checking, lint, tests, content validation, and production build.

Metric definitions:

- Assignment completion rate: completed learner-assignment rows divided by all learner-assignment rows in the active organization.
- Pending reviews: assignment reviews in pending, in-review, or resubmitted state.
- Active learners: active cohort-enrolment rows.
- Active cohorts and assignments: records with active status.

CSV exports contain report type, organization ID, generated timestamp, definition, limitations, and tenant-scoped rows. Export actions are audited.

Browser verification results and any unavailable flows are recorded in the milestone completion report; they are not inferred from automated tests.

Latest automated run: 54 backend tests, 121 application/server/UI tests, 54 AI evaluation tests, and 12 content validation tests passed. Ruff, strict mypy, ESLint, TypeScript, the production build, and empty-database migration to `20260730_0005` passed. No browser backend was connected to the workspace, so real-browser and restart-persistence walkthroughs remain unverified.
