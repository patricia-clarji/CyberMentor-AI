# Competition Code Checkpoint

## Implemented features

- React/TypeScript learner interface with registration, email verification, login, onboarding, diagnostic, adaptive roadmap, reviewed course delivery, workplace mission, investigation replay, Sentinel fallback, project submission, portfolio evidence, and completion-record verification.
- FastAPI trusted backend with durable SQLAlchemy persistence, Alembic migrations, Argon2id credentials, secure sessions, CSRF protection, personal organizations, tenant-scoped authorization, server-side evaluation, rate limiting, and structured health endpoints.
- Existing Node content service and versioned published academy repository containing 12 courses, 144 lessons, and reviewed activity definitions.
- Strict backend typing corrections for JSON fields, SQLAlchemy results, tenant-owner filters, request middleware, cookies, diagnostic data, mission data, retrieval data, and Celery integration.

## Latest test results

- Backend strict type check: passed with zero errors (`python -m mypy app --strict` through the repository configuration).
- Backend tests: 31 passed in 46.50 seconds.
- Frontend type check: passed (`tsc -b`).
- Existing frontend/server tests: all 13 discovered files passed; 110 tests passed (94 server/data/Sentinel/store tests, 6 content-pipeline tests, and 10 React/component tests).
- Frontend production build: passed; 1,839 modules transformed. Output: 330.23 kB JavaScript (99.88 kB gzip) and 35.91 kB CSS (8.58 kB gzip).

## Remaining broken functionality

- No failure remains in the strict typing corrections or in the five checks executed for this checkpoint.
- A real external LLM path, production email delivery, Docker services, worker execution, object storage, and production deployment were not exercised by this checkpoint and must not be described as working.
- The local fallback mentor and console email adapter are development behavior, not production integrations.

## Remaining competition functionality

- Configure and evaluate an approved live LLM provider while retaining the deterministic fallback.
- Configure production email, hosting, domain/TLS, object storage, and observability.
- Obtain named human course/project reviewers and record their approvals.
- Run the consented Lebanese learner pilot and document its results.
- Execute the PostgreSQL/Redis/Celery/MinIO Docker profile on a machine with Docker.
- Provide and verify the production isolated executable lab worker if it remains in competition scope.

## Exact local startup commands

```powershell
npm install
npm run prepare:trusted
npm run dev
```

- Learner interface: `http://127.0.0.1:5173`
- Trusted FastAPI: `http://127.0.0.1:8010`
- Legacy content API: `http://127.0.0.1:8787`

## Files currently being edited

- `backend/app/api/v1/auth.py`
- `backend/app/api/v1/diagnostic.py`
- `backend/app/api/v1/learning.py`
- `backend/app/identity/dependencies.py`
- `backend/app/jobs/celery_app.py`
- `backend/app/learning/diagnostic.py`
- `backend/app/learning/flagship_mission.py`
- `backend/app/learning/flagship_project.py`
- `backend/app/learning/mission_service.py`
- `backend/app/learning/soc_profile.py`
- `backend/app/main.py`
- `backend/app/mentor/provider.py`
- `backend/app/mentor/retrieval.py`
- `backend/app/models/assessment.py`
- `backend/app/models/mentor.py`
- `backend/app/models/mission.py`
- `backend/app/models/portfolio.py`
- `backend/app/schemas/diagnostic.py`
- `backend/app/schemas/learning.py`
- `backend/app/schemas/mission.py`
- `docs/competition/CODE_CHECKPOINT.md`

## Environmental blockers

- Docker is not installed, so the Compose profile is unverified on this machine.
- No approved production LLM provider/model/key/budget is configured.
- No production email provider/domain, hosting/domain/TLS, object-storage account, or observability account is configured.
- Reviewer identities, pilot approval/recruitment, and the authoritative Git remote remain unresolved.
- The Windows restricted runner currently cannot spawn PowerShell processes (`CreateProcessAsUserW: Access is denied`); the requested checks required approved execution outside that runner.
