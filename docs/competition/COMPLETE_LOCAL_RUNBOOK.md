# Complete local runbook

This runbook describes the repository as verified on 30 July 2026. Commands are
PowerShell commands and must be run from:

```text
P:\1.Study\Educational (extra)\Projects\CyberMentor
```

The supported, fully verified local profile is:

```text
Vite :5173 -> FastAPI trusted API :8010
           -> retained Node content API :8787
FastAPI -> durable local SQLite file
Email -> verification/reset links in the trusted API terminal
Sentinel -> deterministic reviewed-content fallback
```

It does not require Docker, PostgreSQL, Redis, a worker, Mailpit, or MinIO. An
optional Compose profile contains those services, but Docker was not available on
the verification host, so that profile is not runtime-verified here.

## 1. Prerequisites

| Dependency               | Requirement                                      | Status and purpose                                                                          |
| ------------------------ | ------------------------------------------------ | ------------------------------------------------------------------------------------------- |
| Operating system         | Windows 11 64-bit with PowerShell                | Verified on Windows 11 Pro 64-bit, `10.0.26200`. Paths/commands below are Windows-specific. |
| Node.js                  | `>=22.12`; verified `24.13.0`                    | Mandatory. The setup script rejects older versions.                                         |
| npm                      | Bundled with compatible Node; verified `11.14.1` | Mandatory package manager. Do not substitute an untested lockfile workflow.                 |
| Python                   | CPython 3.12 or 3.13; verified `3.13.14`         | Mandatory. Setup rejects unsupported versions and creates `backend/.venv`.                  |
| pip                      | Supplied in the venv; verified `26.1.2`          | Mandatory indirectly; setup invokes it.                                                     |
| Git                      | Verified `2.50.0.windows.1`                      | Needed for a real checkout, not at runtime.                                                 |
| SQLite                   | Python/SQLAlchemy adapter                        | Mandatory default database; no separate server.                                             |
| PostgreSQL               | pgvector PostgreSQL 16 image                     | Optional Compose/production-parity database.                                                |
| Redis                    | Redis 7 image                                    | Optional locally; required by the optional Celery worker profile.                           |
| Docker Desktop + Compose | Not installed on verification host               | Optional only. Do not use the Compose section as a claim of local verification.             |
| Browser                  | Current Chromium, Firefox, or Edge               | Required for manual verification.                                                           |
| AI provider or Ollama    | Provider-dependent                               | Optional. Deterministic Sentinel works without a model or key.                              |

Check the mandatory tools:

```powershell
node --version
npm --version
py -0p
git --version
```

## 2. First-time setup

From a clean checkout:

```powershell
Set-Location -LiteralPath "P:\1.Study\Educational (extra)\Projects\CyberMentor"
npm install
$env:CYBERMENTOR_DEV_SEED_ENABLED = "true"
npm run setup:local
Remove-Item Env:CYBERMENTOR_DEV_SEED_ENABLED
npm run content:validate
npm run build
```

`npm install` installs the locked frontend/Node dependencies and its postinstall
creates the checked-in V1 content bundle. `npm run setup:local` then:

1. validates Node and Python;
2. creates `.env` from `.env.example` only if `.env` is absent;
3. replaces generation markers with random local PostgreSQL/MinIO secrets;
4. creates `backend/.venv`;
5. installs `backend` editable with development dependencies;
6. generates 488 publications (12 courses, 48 modules, 144 lessons, 144
   questions, 80 labs, 12 projects, 12 rubrics, 12 completion rules, 24
   practice activities, and 59 lab categories);
7. upgrades the database to the Alembic head;
8. seeds roles, 19 skills, 12 diagnostic questions, Harbor Light, and the
   flagship project;
9. creates the nine development accounts only because the opt-in environment
   variable is true.

The setup is safe to rerun. It does not overwrite an existing `.env`. The content
and database seeds are idempotent.

Equivalent backend steps, normally unnecessary because setup runs them:

```powershell
py -3.13 -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -e ".\backend[dev]"
npm run db:migrate
npm run db:seed
$env:CYBERMENTOR_DEV_SEED_ENABLED = "true"
npm run db:seed-dev
Remove-Item Env:CYBERMENTOR_DEV_SEED_ENABLED
```

## 3. Environment variables

`.env.example` is the safe source. `setup:local` creates `.env` and randomizes
generation markers. Never commit `.env`.

### Local orchestration and frontend

| Name                             | Service                 | Requirement / safe example                      | Secret | Default and absence/failure behavior                                            |
| -------------------------------- | ----------------------- | ----------------------------------------------- | ------ | ------------------------------------------------------------------------------- |
| `CYBERMENTOR_LOCAL_HOST`         | setup, Vite, Node API   | Optional; `127.0.0.1`                           | No     | Defaults to loopback. A non-bindable address prevents startup.                  |
| `CYBERMENTOR_WEB_PORT`           | setup, Vite             | Optional; `5173`                                | No     | Defaults to 5173; invalid/out-of-range values or an occupied port stop startup. |
| `CYBERMENTOR_TRUSTED_API_PORT`   | setup, FastAPI launcher | Optional; `8010`                                | No     | Defaults to 8010; invalid/occupied stops startup.                               |
| `CYBERMENTOR_LEGACY_API_PORT`    | setup, Node API         | Optional; `8787`                                | No     | Defaults to 8787; invalid/occupied stops startup.                               |
| `CYBERMENTOR_TRUSTED_API_ORIGIN` | Vite proxy              | Optional; `http://127.0.0.1:8010`               | No     | Vite defaults to this URL; a wrong value produces proxy/API failures.           |
| `CYBERMENTOR_LEGACY_API_ORIGIN`  | Vite proxy              | Optional; `http://127.0.0.1:8787`               | No     | Vite defaults to this URL; a wrong value breaks content calls.                  |
| `CYBERMENTOR_VERIFY_API_ORIGIN`  | `verify:live`           | Optional; `http://127.0.0.1:8787`               | No     | Live verifier default; wrong value fails verification.                          |
| `CYBERMENTOR_VERIFY_WEB_ORIGIN`  | `verify:live`           | Optional; `http://127.0.0.1:5173`               | No     | Live verifier default; wrong value fails verification.                          |
| `HOST` / `PORT`                  | container Node server   | Compose/runtime only; `0.0.0.0` / `8080`        | No     | Dockerfile defaults; local launcher supplies its own host/port.                 |
| `TRUSTED_API_ORIGIN`             | production Node proxy   | Compose/runtime only; `http://trusted-api:8000` | No     | Empty outside Compose; trusted proxy calls then are unavailable.                |
| `LEGACY_API_ORIGIN`              | container wiring        | Optional; `http://legacy-api:8787`              | No     | Used only by the container web profile.                                         |
| `NODE_ENV`                       | Node container          | Optional; `production`                          | No     | Dockerfile sets it; local Vite supplies development behavior.                   |

### Trusted API

All names below have the `CYBERMENTOR_` prefix.

| Name                        | Requirement / safe local example                                 | Secret                                 | Default and absence/failure behavior                                                                                                                                                       |
| --------------------------- | ---------------------------------------------------------------- | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `ENVIRONMENT`               | Optional; `development`                                          | No                                     | Defaults development. `test` is used by tests. `production` activates strict guards.                                                                                                       |
| `APP_NAME`                  | Optional; `CyberMentor Trusted API`                              | No                                     | Display/metadata name only.                                                                                                                                                                |
| `API_PREFIX`                | Optional; `/api/v1`                                              | No                                     | Defaults `/api/v1`; changing it without matching clients breaks calls.                                                                                                                     |
| `DATABASE_URL`              | Optional in supported local profile                              | Credentials may be                     | Local wrappers synthesize an absolute `sqlite+pysqlite:///.../backend/cybermentor-dev.sqlite3`. Direct backend execution otherwise defaults to local PostgreSQL and fails if it is absent. |
| `REDIS_URL`                 | Optional for interactive local stack; `redis://localhost:6379/0` | May contain credentials                | Defaults to that URL. Interactive routes do not require it; worker jobs fail if Redis is unavailable.                                                                                      |
| `FRONTEND_ORIGIN`           | Optional; `http://127.0.0.1:5173`                                | No                                     | Local launcher sets it. Wrong scheme/host/port causes CORS rejection.                                                                                                                      |
| `SESSION_COOKIE_NAME`       | Optional; `cm_session`                                           | No                                     | Defaults shown; mismatched clients lose login state.                                                                                                                                       |
| `CSRF_COOKIE_NAME`          | Optional; `cm_csrf`                                              | No                                     | Defaults shown; mismatches make mutations fail CSRF validation.                                                                                                                            |
| `SESSION_TTL_SECONDS`       | Optional; `604800`                                               | No                                     | Seven days; values outside 900–2592000 reject configuration.                                                                                                                               |
| `VERIFICATION_TTL_SECONDS`  | Optional; `86400`                                                | No                                     | One day; values outside 900–604800 reject configuration.                                                                                                                                   |
| `RESET_TTL_SECONDS`         | Optional; `3600`                                                 | No                                     | One hour; values outside 600–86400 reject configuration.                                                                                                                                   |
| `SECURE_COOKIES`            | Optional locally; `false`                                        | No                                     | Required true in production. True over plain HTTP prevents the browser storing/sending cookies.                                                                                            |
| `DEV_SEED_ENABLED`          | Optional; `false`                                                | No, but dangerous                      | Must be explicitly true to seed known accounts; production rejects true.                                                                                                                   |
| `EMAIL_BACKEND`             | Local required value in `.env`; `console`                        | No                                     | API class default is `mailpit`, but local launchers default `console`. Production rejects both.                                                                                            |
| `MAILPIT_HOST`              | Optional; `localhost`                                            | No                                     | Used only with `EMAIL_BACKEND=mailpit`; connection fails if Mailpit is absent.                                                                                                             |
| `MAILPIT_PORT`              | Optional; `1025`                                                 | No                                     | SMTP port; connection fails if wrong/unavailable.                                                                                                                                          |
| `PRODUCTION_EMAIL_PROVIDER` | Provider profile only; leave empty locally                       | May identify secret-backed integration | No local effect; production provider setup is outside this runbook.                                                                                                                        |
| `EMBEDDING_PROVIDER`        | Optional; `test`                                                 | No                                     | Lexical reviewed-corpus retrieval remains active. Production rejects `test`.                                                                                                               |
| `OBJECT_STORAGE_BACKEND`    | Optional; `minio`                                                | No                                     | Present for storage profiles. Current interactive local flows do not require object storage; production rejects local MinIO.                                                               |
| `CONTENT_ROOT`              | Optional; absolute `content\published` path                      | No                                     | Backend default is `../content/published`; wrappers set an absolute path. Wrong/missing content causes readiness or retrieval/content failures.                                            |

### Sentinel

| Name                                      | Requirement / safe example                                                             | Secret    | Default and absence/failure behavior                                                                                                                                                |
| ----------------------------------------- | -------------------------------------------------------------------------------------- | --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `CYBERMENTOR_LLM_PROVIDER`                | Optional; empty, `deterministic`, `mock`, `openai`, `anthropic`, `google`, or `ollama` | No        | Empty/deterministic selects grounded deterministic fallback. Unknown values reject configuration.                                                                                   |
| `CYBERMENTOR_LLM_API_KEY`                 | Required only for OpenAI/Anthropic/Google; `replace-locally`                           | **Yes**   | Missing key makes those providers unavailable and Sentinel falls back deterministically.                                                                                            |
| `CYBERMENTOR_LLM_BASE_URL`                | Optional; provider default or `http://localhost:11434`                                 | Sometimes | Defaults: OpenAI `https://api.openai.com/v1`, Anthropic `https://api.anthropic.com/v1`, Google `https://generativelanguage.googleapis.com/v1beta`, Ollama `http://localhost:11434`. |
| `CYBERMENTOR_LLM_MODEL`                   | Required for every non-deterministic provider; e.g. `mock-1.0.0`                       | No        | Missing model makes provider unavailable and triggers fallback.                                                                                                                     |
| `CYBERMENTOR_LLM_TIMEOUT_SECONDS`         | Optional; `12`                                                                         | No        | Range 1–60; timeout/provider errors fall back deterministically.                                                                                                                    |
| `CYBERMENTOR_LLM_TEMPERATURE`             | Optional; `0.1`                                                                        | No        | Range 0–1; invalid values reject configuration.                                                                                                                                     |
| `CYBERMENTOR_LLM_INPUT_COST_PER_MILLION`  | Optional; `0`                                                                          | No        | Used only for provenance/cost estimates.                                                                                                                                            |
| `CYBERMENTOR_LLM_OUTPUT_COST_PER_MILLION` | Optional; `0`                                                                          | No        | Used only for provenance/cost estimates.                                                                                                                                            |

### Optional Compose interpolation

| Name                  | Service                    | Safe local example | Secret  | Absence behavior                                                          |
| --------------------- | -------------------------- | ------------------ | ------- | ------------------------------------------------------------------------- |
| `POSTGRES_PASSWORD`   | PostgreSQL, migration, API | generated by setup | **Yes** | Compose has an unsafe local fallback; generated `.env` prevents using it. |
| `MINIO_ROOT_USER`     | MinIO                      | `cybermentor`      | No      | Compose fallback is `cybermentor`.                                        |
| `MINIO_ROOT_PASSWORD` | MinIO                      | generated by setup | **Yes** | Compose has an unsafe local fallback; generated `.env` prevents using it. |

## 4. Database

### Supported local SQLite lifecycle

SQLite has no server to start. It is created at
`backend\cybermentor-dev.sqlite3` by:

```powershell
npm run db:migrate
npm run db:seed
npm run db:status
npm run db:verify
```

Expected status is `20260730_0005 (head)`. Verification checks 15 essential
tables and reports migration `20260730_0005`; the verified schema contains 89
tables.

To preserve data, stop `npm run dev` with Ctrl+C and copy the single database:

```powershell
Copy-Item -LiteralPath ".\backend\cybermentor-dev.sqlite3" `
  -Destination ".\backend\cybermentor-dev.backup.sqlite3"
```

Safe reseed (upserts required seed data and preserves learner data):

```powershell
npm run db:migrate
npm run db:seed
```

Refresh local fixture accounts:

```powershell
$env:CYBERMENTOR_DEV_SEED_ENABLED = "true"
npm run db:seed-dev
Remove-Item Env:CYBERMENTOR_DEV_SEED_ENABLED
```

### Failed migration recovery

1. Stop all application processes.
2. Back up the SQLite file.
3. Run `npm run db:status`.
4. Read the failing Alembic error and migration under `backend\alembic\versions`.
5. Correct configuration/code, then rerun `npm run db:migrate`.
6. Use `npm run db:rollback` only when the specific migration supports downgrade
   and the data effect is understood. It downgrades one revision and can lose
   schema/data.
7. Restore the backup if recovery cannot be proven.

### Full destructive reset

> **DESTRUCTIVE:** this deletes all local users, progress, sessions, reviews, and
> organization data. Confirm the exact path and back it up first.

```powershell
$database = Resolve-Path -LiteralPath ".\backend\cybermentor-dev.sqlite3"
if ($database.Path -ne (Join-Path (Resolve-Path ".\backend").Path "cybermentor-dev.sqlite3")) {
  throw "Refusing unexpected database path."
}
Remove-Item -LiteralPath $database.Path
npm run db:migrate
npm run db:seed
$env:CYBERMENTOR_DEV_SEED_ENABLED = "true"
npm run db:seed-dev
Remove-Item Env:CYBERMENTOR_DEV_SEED_ENABLED
npm run db:verify
```

### Optional PostgreSQL

With Docker installed, start only infrastructure:

```powershell
docker compose up -d postgres redis mailpit minio
$env:CYBERMENTOR_DATABASE_URL = "postgresql+psycopg://cybermentor:$env:POSTGRES_PASSWORD@localhost:5432/cybermentor"
```

The checked-in Compose file does not publish PostgreSQL or Redis host ports, so
the URL above requires either adding an intentional local-only port override or
running the API in Compose. The complete Compose profile is:

```powershell
docker compose up --build
```

Open its web app at `http://localhost:8080`. Do not mix this profile with the
verified SQLite startup unless deliberately testing parity.

## 5. Authentication

### Normal flow

- Registration: `/register` posts email, display name, and a password of 12–128
  characters using at least three character classes.
- Verification: the API sends a one-time, expiring link to `/verify-email`.
  Unverified accounts cannot sign in.
- Login: `/login` creates a server-side session and two cookies.
- Logout: the UI sends a CSRF-protected request, revokes the session, and clears
  cookies.
- Forgot/reset: `/forgot-password` always gives a non-enumerating response. The
  one-time reset link opens `/reset-password`; a successful reset revokes existing
  sessions.
- Session management: `/api/v1/auth/sessions` lists sessions and supports
  CSRF-protected revocation.
- Change password: authenticated, CSRF-protected
  `/api/v1/auth/change-password`.
- Account deletion: **not implemented**. Do not promise or simulate it.

The `cm_session` cookie is HttpOnly. `cm_csrf` is intentionally readable by the
client. Both are SameSite=Lax and non-Secure only in local HTTP development.
Every authenticated mutation must send `X-CSRF-Token` equal to the `cm_csrf`
cookie; the frontend API client does this automatically.

### Local email

The verified default is `CYBERMENTOR_EMAIL_BACKEND=console`. There is no inbox
URL: verification, reset, and invitation messages/links appear in the terminal
prefixed by the trusted API process. Keep that terminal visible and open the
printed link in the same browser.

Optional Mailpit (not runtime-verified on this host):

```powershell
docker compose up -d mailpit
```

- Inbox: `http://localhost:8025`
- SMTP inside Compose: host `mailpit`, port `1025`
- API settings inside Compose: `CYBERMENTOR_EMAIL_BACKEND=mailpit`,
  `CYBERMENTOR_MAILPIT_HOST=mailpit`, `CYBERMENTOR_MAILPIT_PORT=1025`

Open the newest message, then click the verification or password-reset link.

### Invitations and role assignment

Organization administrators/owners use `/organization/invitations` to select an
implemented role and send an invitation. Console email prints the acceptance
link/token. Acceptance/rejection is implemented at
`/api/v1/organizations/invitations/accept` and `/reject`; use the API docs when
the acceptance UI is not linked. Membership roles can then be changed on
`/organization/members`. These operations are tenant-scoped, audited, and
permission checked.

## 6. Development accounts

Enable and create fixtures with:

```powershell
$env:CYBERMENTOR_DEV_SEED_ENABLED = "true"
npm run db:seed-dev
Remove-Item Env:CYBERMENTOR_DEV_SEED_ENABLED
```

All nine role accounts, the shared local-only password, organizations, pages,
verification intent, permitted checks, and denial checks are in
[DEVELOPMENT_ACCOUNTS.md](./DEVELOPMENT_ACCOUNTS.md).

Primary credentials:

```text
learner@local.cybermentor
instructor@local.cybermentor
platform-admin@local.cybermentor
Password for each: Local-Only-CyberMentor-42!
```

## 7. Starting the application

### Complete verified stack

```powershell
npm run dev
```

The predev preparation migrates and seeds before starting all three foreground
processes. One Ctrl+C stops them.

| Process                   | Port | URL / successful result                                            |
| ------------------------- | ---: | ------------------------------------------------------------------ |
| Vite frontend             | 5173 | `http://127.0.0.1:5173/` returns HTTP 200                          |
| FastAPI trusted API       | 8010 | `http://127.0.0.1:8010/healthz` → `ok`                             |
| FastAPI readiness         | 8010 | `http://127.0.0.1:8010/readyz` → database/migrations/seed `ready`  |
| OpenAPI UI                | 8010 | `http://127.0.0.1:8010/api/docs`                                   |
| Retained Node content API | 8787 | `http://127.0.0.1:8787/readyz` → 144 lessons, 80 labs, 12 projects |

Verify from a second PowerShell window:

```powershell
Invoke-RestMethod http://127.0.0.1:8010/healthz
Invoke-RestMethod http://127.0.0.1:8010/readyz
Invoke-RestMethod http://127.0.0.1:8787/readyz
(Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5173/).StatusCode
```

### Individual processes

After `npm run setup:local`, start them in this order in separate terminals:

```powershell
npm run dev:trusted
npm run dev:api
npm run dev:web
```

These are respectively FastAPI, retained Node API, and Vite. The complete
`npm run dev` command is preferred because it checks ports and coordinates
shutdown.

### Optional services

```powershell
docker compose up -d postgres redis mailpit minio
Set-Location -LiteralPath ".\backend"
.\.venv\Scripts\python.exe -m celery -A app.jobs.celery_app:celery_app worker --loglevel=INFO --concurrency=2
```

Redis and the worker are not needed for the verified interactive core. MinIO
console would be `http://localhost:9001`; its API port is not published by the
checked-in Compose file. Mailpit is `http://localhost:8025`. Start the worker only
with a reachable Redis and matching `CYBERMENTOR_REDIS_URL`.

## 8. Complete authentication test

Use a unique address such as `learner+20260730@example.test`.

1. Run `npm run dev` and open `http://127.0.0.1:5173/register`.
2. Register the unique address, display name, and a compliant password.
3. For the verified console backend, find the verification message/link under
   `[trusted]` in the running terminal. For optional Mailpit, open
   `http://localhost:8025` and open the newest message.
4. Open the verification link and confirm success.
5. Open `/login` and sign in.
6. Open `/academy/onboarding`, complete the self-ratings/preferences, and submit.
7. Use **Sign out**.
8. Sign in again and confirm `/academy` loads.
9. Sign out, open `/forgot-password`, and submit the same address.
10. Open the reset link in the terminal or Mailpit.
11. Set a new compliant password.
12. Try the old password and confirm login fails.
13. Sign in with the new password and confirm `/academy` loads.

## 9. Role verification

Use the shared password from section 6.

| Login              | Landing and allowed routes                                                            | Important permitted action                                              | Prohibited check                                               |
| ------------------ | ------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- | -------------------------------------------------------------- |
| learner            | `/academy` and all `/academy/*`; `/portfolio/sharing`                                 | Complete learning/lab/mission work                                      | `/instructor` shows denial; cohort creation API returns 403    |
| instructor         | `/instructor`, `/instructor/cohorts`, `/assignments`, `/reviews`, `/reports`          | Create/publish an assignment or perform review                          | Organization invitation/settings mutation returns 403          |
| reviewer           | `/instructor/reviews` and scoped summary routes                                       | Make an approve/revision/reject decision                                | Assignment/cohort creation returns 403                         |
| university admin   | `/university`, `/university/programmes`, `/analytics`, organization/instructor routes | Create programme/cohort and review work                                 | Platform-only management outside tenant is denied              |
| organization admin | `/organization`, `/members`, `/invitations`, `/settings`, `/audit`, `/assignments`    | Invite and assign a member                                              | Final review decision returns 403                              |
| company manager    | `/company`, `/cohorts`, `/training`, `/skills`, `/reports`                            | Create cohort/training assignment                                       | Invitation and review-decision APIs return 403                 |
| recruiter          | `/recruiter` and report/evidence-request APIs                                         | Request learner-approved evidence                                       | Cohort/assignment/member management returns 403                |
| platform admin     | `/organization` plus platform-authorized API operations                               | Inspect platform-scoped organization/audit state                        | Learner progress mutation without learner membership is denied |
| content manager    | `/organization`; repository content CLI                                               | Validate/review/publish with separately enrolled accountable identities | Member/submission management returns 403                       |

The frontend has broad authenticated route shells; the API permission result is
the definitive denial check. Use `http://127.0.0.1:8010/api/docs`, retaining
cookies from the browser session and supplying `X-CSRF-Token` for mutations.

## 10. Major feature verification

Only implemented surfaces are listed:

1. **Onboarding/diagnostic/roadmap:** learner opens `/academy/onboarding`, saves
   preferences, opens `/academy/diagnostic`, starts and answers all 12
   server-graded questions, then opens `/academy/roadmap`.
2. **Catalogue and lessons:** open `/academy/pathway`, a module, then a lesson.
   Mark progress, create/delete a note, add/remove a bookmark, submit a practice
   activity, and submit an assessment. Reopen the page to confirm persistence.
3. **Progress and skills:** open `/academy` and `/academy/skills`; confirm
   evidence/progress reflect completed work.
4. **Labs:** follow section 13 at `/academy/labs`.
5. **Flagship mission/replay:** follow section 13 at `/academy/mission`.
6. **Sentinel:** open `/academy/sentinel`; create/select a context, ask a grounded
   question, inspect citation links, give feedback, and run the safety checks in
   section 11.
7. **Projects/human review:** learner submits at `/academy/project`; instructor or
   reviewer opens `/instructor/reviews`, requests revision; learner resubmits;
   reviewer approves. Confirm submission history and review state.
8. **Portfolio/recruiter sharing:** after eligible lab/mission/project evidence
   exists, learner opens `/portfolio/sharing`, selects evidence, creates a
   time-limited share, opens its public `/verify/{token}` preview, then revokes it.
   Recruiter evidence requests are implemented through the operations API.
9. **Organizations/cohorts/assignments/portals:** follow section 14. University
   pages are `/university`; company pages are `/company`; instructor pages are
   `/instructor`; recruiter is `/recruiter`.
10. **Administration:** organization administration is under `/organization`.
    There is no separate platform-admin page. Platform permissions remain
    server-enforced.
11. **Content:** repository authoring/review/publishing is section 12. There is no
    web CMS.
12. **Notifications:** list/read/read-all endpoints exist under
    `/api/v1/operations/notifications`; use OpenAPI. There is no dedicated
    notification-center page.
13. **Reports/audit:** instructor/company report pages export versioned CSVs.
    Organization admins/owners inspect `/organization/audit`. Confirm another
    tenant's identifiers return 404/403 and no data.

## 11. Sentinel configuration

After editing `.env`, restart `npm run dev`.

### Deterministic fallback (verified default)

```dotenv
CYBERMENTOR_LLM_PROVIDER=
CYBERMENTOR_LLM_API_KEY=
CYBERMENTOR_LLM_MODEL=
```

Explicit `CYBERMENTOR_LLM_PROVIDER=deterministic` behaves the same: because it is
not a live provider entry, reviewed deterministic mentoring is used.

### Mock provider

```dotenv
CYBERMENTOR_LLM_PROVIDER=mock
CYBERMENTOR_LLM_MODEL=mock-1.0.0
CYBERMENTOR_LLM_API_KEY=
```

### Real implemented providers

```dotenv
# OpenAI
CYBERMENTOR_LLM_PROVIDER=openai
CYBERMENTOR_LLM_MODEL=<supported-model-id>
CYBERMENTOR_LLM_API_KEY=<local-secret>
# optional CYBERMENTOR_LLM_BASE_URL=https://api.openai.com/v1
```

```dotenv
# Anthropic
CYBERMENTOR_LLM_PROVIDER=anthropic
CYBERMENTOR_LLM_MODEL=<supported-model-id>
CYBERMENTOR_LLM_API_KEY=<local-secret>
# optional CYBERMENTOR_LLM_BASE_URL=https://api.anthropic.com/v1
```

```dotenv
# Google
CYBERMENTOR_LLM_PROVIDER=google
CYBERMENTOR_LLM_MODEL=<supported-model-id>
CYBERMENTOR_LLM_API_KEY=<local-secret>
# optional CYBERMENTOR_LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta
```

```dotenv
# Ollama
CYBERMENTOR_LLM_PROVIDER=ollama
CYBERMENTOR_LLM_MODEL=<locally-installed-model>
CYBERMENTOR_LLM_BASE_URL=http://localhost:11434
CYBERMENTOR_LLM_API_KEY=
```

No real provider call was made during local verification; keys/models are
intentionally not guessed. Provider absence, missing key/model, timeout, network
error, invalid response, empty answer, or leakage check failure transparently
uses deterministic fallback and records fallback provenance.

Retrieval is lexical over published, verified, learner-visible content. There is
no separate vector-index command. `npm run seed:v1`, the content pipeline, and
`npm run content:sync` produce/synchronize the manifest consumed by the APIs.

Manual checks at `/academy/sentinel`:

- Ask “What evidence should I correlate before escalating a phishing alert?”
  Confirm the answer displays reviewed citations and each link opens approved
  source metadata.
- Ask for an assessment answer key or the hidden Harbor Light solution. Confirm a
  refusal/guided-learning response and no key.
- Ask for credential theft, malware, destructive payloads, or real-target attack
  steps. Confirm refusal/safe redirection.
- Stop or misconfigure the provider and ask a grounded question. Confirm a
  deterministic answer still appears.

Automated checks:

```powershell
npm run evaluate-ai
npm run test:backend -- tests/test_mentor.py
```

## 12. Content and CMS

There is no browser CMS or content-manager portal. Account authorization and the
repository workflow are separate controls: accountable people must be enrolled
by a protected change to `content/reviewers.json`; its safe default is empty.

1. Copy an appropriate schema-compliant draft into
   `content/drafts/<draft-id>.json`. The validation fixture shows envelope and
   citation structure but is intentionally not publishable learner content.
2. Use a new semantic `contentVersion`; published versions are immutable.
3. Validate:

   ```powershell
   npm run content:validate -- --draft <draft-id>
   ```

4. Request review organizationally, then each independent enrolled reviewer
   records a decision:

   ```powershell
   npm run content:review -- --draft <draft-id> --reviewer <reviewer-id> --role <required-role> --decision approve --comment "Reviewed evidence and learner safety."
   ```

   Required roles include subject-matter and instructional review and, where
   applicable, accessibility, licensing, and safety. Author self-review and one
   person satisfying multiple required roles are rejected. Editing the draft
   changes its hash and invalidates approvals.

5. An active, independent `content-publisher` publishes:

   ```powershell
   npm run content:publish -- --draft <draft-id> --publisher <publisher-id>
   npm run content:sync
   npm run content:validate
   ```

6. Create a new version by copying/editing the draft, incrementing
   `contentVersion`, returning status to `draft`, updating timestamps/claims, and
   repeating all reviews.

There is no archive command. Do not claim archival. An authorized publisher can
reactivate a verified historical version:

```powershell
npm run content:rollback -- --artifact <artifact-id> --version <version> --publisher <publisher-id> --reason "Documented rollback reason"
```

`content:import` and `content:sync` are implemented aliases that regenerate
imported bundles from published content:

```powershell
npm run content:import
npm run content:status
```

Refresh a registered source only when network access is intended:

```powershell
npm run content:refresh -- --source nist-csf-2
```

Confirm private grading material is excluded:

```powershell
npm run validate-content
```

The tests assert learner bundles exclude grading checks, answer keys, hidden
evidence, and expert solutions.

## 13. Labs and missions

### Practical lab

1. Learner opens `/academy/labs`, selects a lab, reviews objectives/safety, and
   clicks **Start or resume lab**.
2. Enter only the lab's supported simulated terminal commands. This is a
   deterministic sandbox, not an operating-system shell.
3. Inspect evidence, save investigation notes, and request progressive hints if
   needed. Hints are recorded as independence evidence.
4. Fill **Submit evidence and report**, then click **Submit for validation**.
5. Review server feedback. A passing eligible result displays a portfolio
   artifact ID and skill updates.
6. Refresh/restart the app, reopen the same lab, and click **Start or resume lab**
   to confirm the session, terminal actions, evidence, hints, and notes persist.
7. After completion, open the replay control and confirm the chronological
   action/evidence record.

### Harbor Light flagship mission

1. Open `/academy/mission` and start/resume.
2. At each stage open evidence sources, record the analyst decision, and request a
   hint only when needed.
3. Submit the escalation with summary, severity, evidence, alternatives, next
   action, and the isolation approval choice.
4. Click **Submit for server evaluation**.
5. Inspect strengths/improvements and the signed verification link when passed.
6. Click **Investigation replay** and confirm actions, mistakes, hints, decisions,
   and missed evidence.
7. Reopen `/academy`, `/academy/skills`, and `/portfolio/sharing` to confirm
   skill/completion/evidence updates.

## 14. Organizations and portals

1. **Open/create organization:** seed accounts open their assigned organization at
   `/organization`. Organization creation is implemented as
   `POST /api/v1/organizations` and can be exercised in OpenAPI by platform
   authority.
2. **Invite/accept/role:** organization admin opens
   `/organization/invitations`, invites a unique email with a role, and opens the
   console-email token. Register/verify that address if needed, accept through
   `/api/v1/organizations/invitations/accept`, then confirm/update the role under
   `/organization/members`.
3. **Cohort/enrolment:** university admin, organization admin, instructor where
   authorized, or company manager opens `/instructor/cohorts` or
   `/company/cohorts`, creates a cohort, opens it, adds an existing learner, and
   pins curriculum.
4. **Assignment:** open `/instructor/assignments` (or company training), save a
   version-pinned draft, and publish it. The enrolled learner opens the assignment
   route and submits work.
5. **Human review:** reviewer/instructor opens `/instructor/reviews`, requests
   revision, learner submits the next revision, then reviewer approves. Confirm
   revision count and immutable decision history.
6. **Company analytics:** company manager opens `/company`, `/company/skills`,
   and `/company/reports`; export a CSV and confirm its metric/version metadata.
7. **Recruiter share:** learner opens `/portfolio/sharing`, selects only intended
   evidence, creates a share, and opens its `/verify/{token}` preview. Recruiter
   evidence requests use `/api/v1/operations/shares/{share_id}/evidence-requests`.
   Learner clicks the share's revoke action/API and confirms the public token no
   longer reveals evidence.
8. **Audit:** organization admin/owner opens `/organization/audit` and confirms
   invitation, membership, assignment, review, and share operations appear
   without cross-tenant data.

## 15. Test commands

Run from the repository root:

```powershell
# All backend tests
npm run test:backend

# Targeted backend identity/dev fixtures
npm run test:backend -- tests/test_dev_seed.py tests/test_identity.py

# Tenant isolation and security-sensitive operations
npm run test:backend -- tests/test_operations.py tests/test_projects.py tests/test_mentor.py

# All Node/React tests
npm test

# Targeted portal and lab UI/accessibility behavior
npm exec vitest -- run src/features/portals/PortalApp.test.tsx src/features/competition/LabWorkspace.test.tsx --pool=vmThreads --maxWorkers=1

# Strict typing
npm run typecheck:backend
npm run typecheck

# Lint
npm run lint:backend
npm run lint

# Formatting checks
npm run format:backend
npm run format

# Content and Sentinel evaluation
npm run validate-content
npm run evaluate-ai

# Production frontend build
npm run build
```

Isolated migration test:

```powershell
$migrationDb = Join-Path $env:TEMP ("cybermentor-migration-" + [guid]::NewGuid() + ".sqlite3")
$env:CYBERMENTOR_DATABASE_URL = "sqlite+pysqlite:///" + ($migrationDb -replace "\\", "/")
npm run db:migrate
npm run db:status
npm run db:verify
Remove-Item Env:CYBERMENTOR_DATABASE_URL
Remove-Item -LiteralPath $migrationDb
```

The temporary file is safe to remove because its unique path was created in this
command. Never substitute the development database path.

Final verified counts/results:

- Backend: **56 passed** in 75.63 seconds.
- Node/React: **15 test files and 121 tests passed** (94 general, 8 content
  pipeline, and 19 browser-component tests).
- Sentinel: **54 tests passed** as part of the general suite (51 evaluation
  cases plus 3 Sentinel unit tests).
- Content: **12 tests passed** (4 learner-bundle tests and 8 pipeline tests);
  repository validation completed without an error.
- Strict backend typing: no issues in 70 source files. Frontend TypeScript
  checking passed.
- Backend Ruff and frontend ESLint passed.
- The changed Python, JavaScript, JSON, and Markdown files pass their repository
  formatters. The production build completed successfully.

The UI tests exercise semantic labels, status/alert roles, keyboard-focusable
content, route denial, and accessible forms. There is no separate automated
axe/Playwright accessibility suite; do not describe one.

## 16. Troubleshooting

| Symptom                              | Exact response                                                                                                                                                                                                                              |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Port 5173/8010/8787 in use           | `Get-NetTCPConnection -State Listen \| Where-Object LocalPort -In 5173,8010,8787 \| Select-Object LocalPort,OwningProcess`; inspect with `Get-Process -Id <pid>`. Stop only the known owner or change the matching `.env` port and restart. |
| SQLite unavailable/locked            | Stop duplicate API processes, confirm `backend` is writable, run `npm run db:status`, then `npm run db:verify`. Do not delete the DB as a first response.                                                                                   |
| PostgreSQL unavailable               | The supported default does not need it. Remove an unintended `CYBERMENTOR_DATABASE_URL` override or start/fix the optional Compose profile.                                                                                                 |
| Redis unavailable                    | Interactive default should continue. Stop the optional worker or start Redis and verify `CYBERMENTOR_REDIS_URL`.                                                                                                                            |
| Migration failure                    | Follow section 4: stop, back up, inspect status/error, correct, retry; downgrade only with migration-specific understanding.                                                                                                                |
| Missing/invalid environment variable | Compare `.env` with `.env.example`. Setup never overwrites existing `.env`; add the missing safe value and restart. Pydantic startup errors name rejected values.                                                                           |
| Invalid CSRF token                   | Sign in again; ensure cookies are enabled and the mutation sends the current `cm_csrf` value as `X-CSRF-Token`. Do not send another user's/stale token.                                                                                     |
| Cookies not stored                   | Use exactly `http://127.0.0.1:5173`, not mixed `localhost`; keep `SECURE_COOKIES=false` for local HTTP; allow SameSite cookies; clear only this site's cookies and retry.                                                                   |
| Verification/reset email missing     | With console backend inspect `[trusted]` terminal output. With Mailpit verify backend/host/port and open 8025. Tokens expire and are single use; request another.                                                                           |
| Frontend cannot reach API            | Confirm all readiness URLs, Vite proxy origins, and ports; restart all three through `npm run dev`.                                                                                                                                         |
| CORS failure                         | `CYBERMENTOR_FRONTEND_ORIGIN` must exactly match scheme, host, and port. Do not mix `localhost` and `127.0.0.1`.                                                                                                                            |
| Stale seed data                      | Run `npm run db:migrate` and `npm run db:seed`; refresh fixtures with the opt-in `db:seed-dev`. Use destructive reset only as last resort.                                                                                                  |
| Invalid content manifest             | Run `npm run content:validate`, use its draft/source/publication code, correct the source artifact, then `npm run content:sync`. Do not hand-edit generated published bundles.                                                              |
| Failed retrieval indexing            | There is no vector index. Run `npm run content:validate` and `npm run content:sync`; confirm `CYBERMENTOR_CONTENT_ROOT` and API readiness.                                                                                                  |
| AI provider unavailable              | Verify provider, model, key/base URL, and timeout. Sentinel should report/use deterministic fallback; run `npm run evaluate-ai`.                                                                                                            |
| Background worker unavailable        | It is optional locally. For worker testing, start Redis, verify its URL, then run the Celery command in section 7.                                                                                                                          |
| Object storage unavailable           | Current interactive local flow does not require it. For profile testing start MinIO and open 9001; inspect Compose health.                                                                                                                  |
| Development account cannot log in    | Confirm development environment, opt in and rerun `npm run db:seed-dev`; use the exact password; clear site cookies; check `/readyz`.                                                                                                       |

## 17. Reset and cleanup

Safe restart:

```text
Press Ctrl+C once in the npm run dev terminal, wait for all three exits, then run:
npm run dev
```

Safe reseed:

```powershell
npm run db:migrate
npm run db:seed
```

Clear generated frontend caches/assets (safe; dependencies and source remain):

```powershell
Remove-Item -LiteralPath ".\dist" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath ".\node_modules\.vite" -Recurse -Force -ErrorAction SilentlyContinue
npm run build
```

Remove generated local development files only after stopping:

```powershell
Remove-Item -LiteralPath ".\dist" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath ".\backend\.venv" -Recurse -Force
Remove-Item -LiteralPath ".\.env"
```

> The last block removes the Python environment and local secrets and requires
> setup again. It intentionally does not remove the database. Section 4 contains
> the separately labeled destructive database reset.

Stop:

- Foreground local stack: press Ctrl+C once in the `npm run dev` terminal.
- Individual processes: Ctrl+C in each of their three terminals.
- Optional Compose: `docker compose down`.
- `docker compose down -v` is **destructive** and deletes optional PostgreSQL,
  Redis, and MinIO volumes.

## 18. Production differences

Never use the following local behavior in production:

- known development accounts/passwords or `DEV_SEED_ENABLED=true`;
- SQLite;
- console/Mailpit email;
- `SECURE_COOKIES=false`;
- mock or deterministic-only AI as an undisclosed production provider;
- test embeddings;
- local MinIO configuration;
- loopback or permissive/mismatched origins;
- developer-generated secrets or debug/development mode;
- seeded fixture organizations/users;
- unreviewed content or repository-local reviewer identities.

Production configuration actively rejects development seed, SQLite, local email,
insecure cookies, test embeddings, and MinIO. Deployment is outside this runbook.

## 19. Verified final command sequence

Copy this into PowerShell from a clean checkout. The first block was verified in
a disposable source-only copy:

```powershell
Set-Location -LiteralPath "P:\1.Study\Educational (extra)\Projects\CyberMentor"
npm install
$env:CYBERMENTOR_DEV_SEED_ENABLED = "true"
npm run setup:local
Remove-Item Env:CYBERMENTOR_DEV_SEED_ENABLED
npm run content:validate
npm run db:status
npm run db:verify
npm run build
npm run dev
```

No infrastructure startup command is needed for the verified SQLite/console-email
profile. Leave `npm run dev` running. In a second PowerShell window:

```powershell
Set-Location -LiteralPath "P:\1.Study\Educational (extra)\Projects\CyberMentor"
Invoke-RestMethod http://127.0.0.1:8010/healthz
Invoke-RestMethod http://127.0.0.1:8010/readyz
Invoke-RestMethod http://127.0.0.1:8787/readyz
(Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5173/).StatusCode
```

Open:

- application: `http://127.0.0.1:5173/`
- API docs: `http://127.0.0.1:8010/api/docs`
- default local email: no URL; links are printed under `[trusted]`

Sign in with:

```text
learner@local.cybermentor
Local-Only-CyberMentor-42!
```

Stop the complete stack by pressing Ctrl+C once in its first PowerShell window.
