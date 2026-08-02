# CyberMentor AI Project Audit

**Audit date:** 2026-07-26  
**Audit type:** Documentation-only architecture and readiness review  
**Target:** Current workspace implementation  
**Production readiness:** **39/100 - not production ready**

## 1. Executive summary

CyberMentor AI is a substantial local-first learning prototype with a polished React learner interface, a dependency-light Node.js API, a versioned content publication pipeline, deterministic adaptive recommendations, server-side quiz and lab verification, 12 seeded courses, 144 published lessons, and 80 bounded Cyber Range activities.

The application is suitable for a controlled local demonstration and continued fellowship development. It is not ready to operate as a production multi-user learning platform.

The largest blockers are:

1. no registration, login, email verification, password reset, secure session, or MFA implementation;
2. no server-enforced roles, organization membership, or tenant boundary;
3. no applied production database or durable server-side learner state;
4. a broken Docker content path: the runtime image does not copy `content/published/`;
5. no real LLM, embedding retrieval, vector store, or runtime RAG implementation;
6. lab ownership is based on a forgeable browser-generated guest identifier;
7. Cyber Range sessions and adaptive decision logs exist only in process memory;
8. no instructor, administrator, upload, worker, analytics, billing, or entitlement implementation;
9. no production observability, backup, disaster-recovery, or deployment validation;
10. incomplete real-browser, accessibility, mobile, and cross-browser evidence.

The previous recorded verification pass reported 108 passing automated tests, clean linting and formatting, successful TypeScript compilation, a successful Vite production build, zero content-schema errors, and zero moderate-or-higher dependency audit findings. This documentation pass did not rerun those gates.

---

## 2. Current folder structure

```text
CyberMentor/
├── content/
│   ├── adaptive/
│   │   ├── practice-activities.json
│   │   └── skills.json
│   ├── drafts/
│   ├── published/
│   │   ├── manifest.json
│   │   └── ...488 generated publication records
│   ├── reports/
│   ├── schema/
│   ├── snapshots/
│   ├── templates/
│   ├── reviewers.json
│   ├── sources.json
│   └── terminology.json
├── db/
│   ├── migrations/
│   │   └── 001_adaptive_learning.sql
│   └── seeds/
│       └── 001_v1_academy.seed.json
├── docs/
│   ├── ai/
│   ├── architecture/
│   ├── audit/
│   ├── content/
│   ├── operations/
│   ├── product/
│   ├── security/
│   └── PROJECT_AUDIT.md
├── scripts/
│   ├── content-pipeline.mjs
│   ├── seed-v1-academy.mjs
│   ├── test-all.mjs
│   ├── v1-lab-library.mjs
│   ├── verify-live.mjs
│   └── associated tests
├── server/
│   ├── adaptive.mjs
│   ├── content-repository.mjs
│   ├── core.mjs
│   ├── lab-runtime.mjs
│   ├── server.mjs
│   └── associated tests
├── src/
│   ├── components/
│   │   └── ContentBlocks.tsx
│   ├── data/
│   │   ├── courses.ts
│   │   └── verified-content.ts
│   ├── lib/
│   │   ├── sentinel.ts
│   │   └── store.ts
│   ├── test/
│   ├── App.tsx
│   ├── main.tsx
│   ├── project-styles.css
│   ├── styles.css
│   └── types.ts
├── tmp/
│   └── pdfs/
│       └── temporary lecture-review renders and a local PyMuPDF installation
├── Dockerfile
├── docker-compose.yml
├── package.json
├── README.md
├── vite.config.ts
└── TypeScript, ESLint, and formatting configuration
```

### Structure observations

- `content/published/` is the runtime content source of truth, but it contains hundreds of generated files.
- `db/seeds/001_v1_academy.seed.json` is a normalized export, not an applied database.
- The only SQL migration models adaptive learning. It does not provide the complete platform schema.
- `tmp/pdfs/` is tooling residue from reviewing course material and should not be included in source control or Docker build contexts.
- No `.dockerignore` was found in the inspected tree. This risks sending `node_modules`, generated publications, temporary renderer binaries, and other unnecessary files into Docker build context.
- No conventional router, controller, service, repository, authentication, worker, or database-adapter directory exists.

---

## 3. Frontend architecture

### Technology

- React 19
- TypeScript
- Vite
- Lucide React icons
- Plain CSS
- Native `fetch`
- Browser `localStorage`
- Vitest and Testing Library

### Runtime design

`src/main.tsx` mounts a single `App` component. `src/App.tsx` owns navigation, selected course and lesson state, learner progress, the mentor modal, menu state, content loading, and most feature rendering.

Navigation is implemented through a local `Page` union and `setPage()`. There is no URL router.

```text
Browser loads application
    ↓
App initializes legacy course shells
    ↓
GET /api/content/catalog
    ↓
applyVerifiedContent() replaces matching legacy lessons
    ↓
Only verified lessons are displayed as deliverable lessons
```

### Strengths

- TypeScript is used throughout the learner application.
- Published content fails closed at the lesson-delivery boundary.
- Quiz grading and lab verification are sent to the server.
- React escapes learner-entered notes and evidence by default.
- Accessible labels exist for several icon-only controls.
- Loading and failure states exist for important content and adaptive features.
- The UI communicates that progress and credentials are browser-local.

### Architectural weaknesses

- `src/App.tsx` is 2,259 lines and contains almost the entire application.
- Presentation, network access, state transitions, domain rules, and page composition are mixed together.
- There is no router, so browser back/forward navigation, deep linking, bookmarking a page, and route-level code splitting are unavailable.
- There is no shared API client, request schema, error type, retry policy, cancellation layer, or authentication interceptor.
- Eleven direct `fetch()` calls are distributed through `App.tsx`.
- There is no error boundary.
- There is no server-state library or normalized query cache.
- The app loads all published lesson content at startup rather than fetching a course or lesson on demand.

---

## 4. Backend architecture

### Technology

- Native Node.js `http` server
- ECMAScript modules
- Native filesystem APIs
- In-memory maps and arrays
- No web framework
- No ORM
- No database driver
- No queue or worker framework

### Main modules

| Module                          | Responsibility                                                                                     |
| ------------------------------- | -------------------------------------------------------------------------------------------------- |
| `server/server.mjs`             | HTTP listener, routing, body parsing, rate limiting, static-file serving, logging                  |
| `server/core.mjs`               | Quiz grading, normalized lab verification, formative project assessment, CORS and security headers |
| `server/content-repository.mjs` | Manifest-based publication loading, approval checks, caching, public projections                   |
| `server/lab-runtime.mjs`        | In-memory lab session lifecycle and owner checks                                                   |
| `server/adaptive.mjs`           | Rule-based mastery updates, recommendations, hints, diagnostics, decision logs                     |

### Request lifecycle

```text
HTTP request
    ↓
Generate request ID and security headers
    ↓
Origin check
    ↓
In-memory IP rate limit
    ↓
Manual path and method matching
    ↓
Manual request-body validation
    ↓
Filesystem content or in-memory state
    ↓
JSON response
    ↓
Structured request log to stdout
```

### Strengths

- Small dependency surface.
- Request bodies are limited to 16 KiB.
- API responses use `Cache-Control: no-store`.
- Public lesson, project, and lab representations protect private verifier fields.
- Quiz answers and lab expected values are kept out of client publications.
- Security headers, same-origin checks, request IDs, and structured request logs exist.
- Static assets receive immutable caching.
- Unknown API routes return JSON 404 responses.

### Architectural weaknesses

- All routes are contained in one 379-line handler.
- Route matching, validation, authorization, business logic, persistence, and serialization are not separated into layers.
- Validation is manual and inconsistent rather than schema-driven.
- Every thrown application error is generally converted to HTTP 400, including unexpected server failures.
- Error logs do not include a safe diagnostic code, exception class, or stack for operators.
- There is no graceful shutdown, connection draining, or startup dependency check.
- `/readyz` always returns ready and does not verify content availability, database state, or other dependencies.
- There is no API versioning.

---

## 5. Database schema

### Actual runtime persistence

There is no active production database.

Runtime data is split between:

| Data                      | Current storage                                          |
| ------------------------- | -------------------------------------------------------- |
| Published curriculum      | Version-controlled JSON files under `content/published/` |
| Normalized academy export | `db/seeds/001_v1_academy.seed.json`                      |
| Learner progress          | Browser `localStorage`                                   |
| Lab sessions              | In-memory `Map` inside one Node process                  |
| Adaptive decision logs    | In-memory array inside one Node process                  |
| Quiz attempts             | Browser progress summary only                            |
| Project submissions       | Browser `localStorage`                                   |
| Notes and bookmarks       | Browser `localStorage`                                   |

### Architecture-only PostgreSQL migration

`db/migrations/001_adaptive_learning.sql` defines ten tables:

1. `skill`
2. `skill_prerequisite`
3. `learning_objective`
4. `learner_skill_state`
5. `mastery_evidence`
6. `practice_activity`
7. `practice_activity_skill`
8. `adaptive_recommendation`
9. `adaptive_decision_log`
10. `instructor_adaptive_policy`

The migration includes:

- organization and learner composite keys;
- mastery and confidence constraints;
- skill prerequisites;
- evidence weights and hint counts;
- recommendation status;
- instructor override policy;
- a guard against storing chain-of-thought in decision features;
- indexes for evidence history and active recommendations.

### Missing database entities

The SQL does not define:

- users;
- credentials or external identities;
- email-verification tokens;
- password-reset tokens;
- sessions or refresh tokens;
- organizations;
- organization memberships;
- roles and permissions;
- courses, modules, lessons, questions, labs, projects, or rubrics;
- enrollment;
- lesson progress;
- quiz attempts;
- lab instances and attempts;
- project submissions and reviews;
- notes and bookmarks;
- portfolio evidence;
- certificates;
- file uploads;
- content drafts and review workflow;
- audit events;
- billing, plans, subscriptions, or entitlements;
- notifications;
- background jobs;
- analytics events.

### Database readiness

The migration is a useful design artifact, but it is not connected to the application. There is no PostgreSQL service, database client, migration runner, rollback verification, transaction boundary, seed importer, backup procedure, or integration test against a real database.

---

## 6. API endpoints

All current endpoints are unauthenticated.

| Method | Endpoint                        | Purpose                                    | Persistence        | Production concern                                                 |
| ------ | ------------------------------- | ------------------------------------------ | ------------------ | ------------------------------------------------------------------ |
| `GET`  | `/healthz`                      | Liveness response                          | None               | Does not prove content or dependency health                        |
| `GET`  | `/api/health`                   | API health and demo mode                   | None               | Always reports deterministic demo mode                             |
| `GET`  | `/readyz`                       | Readiness response                         | None               | Always ready; no dependency checks                                 |
| `GET`  | `/api/content/catalog`          | Returns published lessons                  | Filesystem/cache   | Returns the complete lesson catalog in one response                |
| `GET`  | `/api/labs`                     | Returns published labs                     | Filesystem/cache   | No pagination                                                      |
| `POST` | `/api/labs/launch`              | Launches or resumes a lab                  | Process memory     | Trusts client-provided guest owner ID                              |
| `GET`  | `/api/labs/session`             | Reads a lab session                        | Process memory     | Guest owner ID is forgeable                                        |
| `POST` | `/api/labs/action`              | Pauses, resumes, resets, or closes a lab   | Process memory     | No authenticated audit actor                                       |
| `POST` | `/api/labs/hint`                | Reveals the next progressive hint          | Process memory     | Hint state disappears on restart                                   |
| `POST` | `/api/labs/verify`              | Performs server-side evidence verification | Files + memory     | Verifier is intentionally simple normalized equality               |
| `GET`  | `/api/projects`                 | Returns published projects                 | Filesystem/cache   | No pagination                                                      |
| `POST` | `/api/projects/submit`          | Formative project completeness check       | None durable       | Checks length and deliverable acknowledgement, not project quality |
| `POST` | `/api/checks/grade`             | Grades one published question              | Filesystem         | No durable attempt record or authenticated learner                 |
| `POST` | `/api/adaptive/mastery`         | Calculates mastery state                   | Stateless          | Client supplies prior state and evidence                           |
| `POST` | `/api/adaptive/recommendations` | Produces rule-based recommendations        | Files + memory log | Client can supply arbitrary skill state                            |
| `POST` | `/api/adaptive/diagnostic/next` | Selects the next diagnostic question       | Filesystem         | No durable diagnostic session                                      |

### Missing API groups

- `/auth/*`
- `/users/*`
- `/organizations/*`
- `/memberships/*`
- `/roles/*`
- `/enrollments/*`
- `/progress/*`
- `/notes/*`
- `/bookmarks/*`
- `/attempts/*`
- `/portfolio/*`
- `/certificates/*`
- `/uploads/*`
- `/instructor/*`
- `/admin/*`
- `/content/drafts/*`
- `/reviews/*`
- `/analytics/*`
- `/billing/*`
- `/entitlements/*`
- `/notifications/*`
- `/mentor/*`

Sentinel has no backend endpoint. It runs entirely in the browser.

---

## 7. Authentication flow

### Current flow

There is no authentication flow.

```text
User opens browser
    ↓
Application loads without identity
    ↓
Progress is read from "cm-progress" in localStorage
    ↓
Cyber Range creates "guest_<random UUID>" in localStorage
    ↓
Browser sends ownerId in lab requests
    ↓
Server compares ownerId with the in-memory session ownerId
```

The server-side comparison prevents accidental access when two different guest IDs are used. It does not establish identity because a client can submit any syntactically valid owner ID.

### Missing production flow

```text
Register
    ↓
Verify email
    ↓
Authenticate
    ↓
Issue secure server-managed session
    ↓
Resolve user, organization, membership, and role
    ↓
Authorize each resource and action
    ↓
Rotate/revoke session and record audit event
```

Required controls include:

- password hashing or managed identity provider;
- verified email ownership;
- short-lived verification and reset tokens;
- secure, HTTP-only, same-site cookies;
- session rotation after login and privilege changes;
- logout and server-side revocation;
- MFA for privileged roles;
- brute-force protection;
- account recovery controls;
- organization membership checks;
- server-side RBAC;
- resource-level authorization;
- cross-tenant integration tests;
- security audit events.

---

## 8. AI architecture

### Current Sentinel implementation

Sentinel is a deterministic browser-side helper in `src/lib/sentinel.ts`.

It:

- receives a learner question and optional course/lesson context;
- truncates the question to 4,000 characters;
- applies regular expressions for policy manipulation, unsafe external targeting, and graded-answer requests;
- selects a verified lesson;
- returns a templated explanation, worked example, Socratic question, and lesson citations.

It does not:

- call an LLM;
- use `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, or `EMBEDDING_MODEL`;
- create embeddings;
- query a vector database;
- perform BM25 or semantic retrieval;
- rerank passages;
- validate citation entailment;
- maintain conversation memory;
- call tools;
- run an agent loop;
- stream responses;
- perform server-side prompt-security enforcement.

Because the mentor logic runs in the browser, it is inspectable and replaceable by the user. That is acceptable for a demo tutor, but not for enforcement or protected model access.

### Current adaptive-learning implementation

The adaptive service is a transparent rule engine, not a trained ML model.

Inputs include:

- skill mastery;
- confidence;
- evidence count;
- prerequisites;
- recent mistakes;
- failure counts;
- goals;
- role track;
- available time;
- activity difficulty.

Outputs include:

- ranked published activities;
- human-readable reasons;
- suggested hint level;
- a bounded in-memory decision log.

This design is explainable and works without learner training data. It should be described as deterministic personalization, not machine learning.

### Content intelligence architecture

The content pipeline provides:

- authoritative source registry;
- source snapshots;
- content hashes;
- versioned drafts and publications;
- schema validation;
- review roles;
- publication-state checks;
- provenance and citations;
- a narrow initial Version 1 release-approval path.

This is the strongest current foundation for future RAG.

### Missing AI production architecture

- server-side mentor endpoint;
- approved model provider and model version;
- hybrid lexical and embedding retrieval;
- vector index;
- chunking and embedding lifecycle;
- source-level access controls;
- retrieval evaluation dataset;
- citation precision and entailment evaluation;
- hallucination monitoring;
- prompt-injection and indirect-injection defenses on retrieved data;
- model-output schema enforcement;
- conversation retention and deletion policy;
- token, latency, and cost budgets;
- provider outage fallback;
- multilingual evaluation;
- human feedback and escalation;
- model and prompt version tracking;
- consented learner-data policy;
- production AI observability.

---

## 9. Component hierarchy

```text
main.tsx
└── App
    ├── Header
    ├── Home
    ├── Catalog
    │   └── CourseCard
    ├── Tracks
    │   └── CourseCard
    ├── Dashboard
    │   └── AdaptivePanel
    ├── CoursePage
    ├── LessonPage
    │   └── ContentBlocks
    │       └── ContentBlockView
    │           ├── ListBlock
    │           └── Box
    ├── Labs
    ├── Portfolio
    ├── Mentor
    └── Footer
```

### Hierarchy concerns

- `App` owns most state and passes mutable progress objects through multiple levels.
- `Labs`, `LessonPage`, `Portfolio`, and `Mentor` each include substantial feature logic rather than delegating to hooks and services.
- There are no route-level boundaries.
- There is no component-level error boundary.
- There is no dedicated design-system component layer.
- The small number of extracted components makes testing and reuse harder as features expand.

---

## 10. State management

### React state

`App` stores:

- current catalog;
- content load status;
- active page;
- selected course;
- selected lesson;
- full learner progress;
- mentor visibility;
- mobile menu visibility.

Feature components store their own temporary network and form state.

### Persistent browser state

The `cm-progress` record contains:

- completed lessons;
- enrolled courses;
- lesson bookmarks;
- lesson notes;
- quiz scores;
- completed labs;
- lab bookmarks;
- lab reflections;
- lab-attempt summaries;
- completed projects;
- project submissions;
- skill states;
- dismissed recommendations.

`cm-range-owner` stores the guest lab owner ID.

### Server state

- Published content cache: in-memory, derived from filesystem publications.
- Publication in-flight loads: in-memory.
- Lab sessions: in-memory, capped at 2,000.
- Lab attempt history: in-memory, capped at 50 per session.
- Adaptive decision logs: in-memory, capped at 500.
- Rate-limit counters: in-memory and not globally bounded.

### State-management risks

- Clearing browser storage erases the learner record.
- Different browsers and devices do not share progress.
- A user can edit all browser-stored mastery and completion data.
- A server restart destroys active lab sessions and decision logs.
- Multiple server processes do not share state.
- No optimistic-concurrency or idempotency mechanism exists.
- There is no migration/versioning mechanism for `cm-progress`.
- Entire progress state is serialized after each update.

---

## 11. Current features

### Published academy

- 12 courses
- 48 modules
- 144 lessons
- 144 server-graded questions
- 80 Cyber Range activities
- 24 adaptive practice activities
- 12 projects
- 12 rubrics
- 12 completion rules
- 488 total published artifacts

### Learner features

- course catalog;
- search and category filters;
- career-track pages;
- enrollment stored locally;
- verified lesson player;
- lesson completion;
- lesson notes;
- lesson bookmarks;
- server-side quiz grading;
- learner dashboard;
- browser-local progress;
- recommended next lesson;
- adaptive practice recommendations;
- project catalog and formative submissions;
- local portfolio records.

### Cyber Range

- 80 bounded simulations, artifact analyses, and configuration activities;
- search and filtering;
- category, difficulty, and environment metadata;
- guided and independent modes;
- launch and resume;
- pause, reset, and close;
- expiration;
- five-level progressive hints;
- attempt history;
- server-side normalized-evidence verification;
- wrong-answer rejection;
- defensive debriefs;
- reflections;
- portfolio skill tags;
- cross-owner checks within the guest-ID model.

### Content operations

- source registry;
- source snapshots;
- drafts;
- versioned publications;
- provenance;
- content hashes;
- schema validation;
- review workflow;
- publication and rollback commands;
- deterministic Version 1 seeding.

### Quality and defensive controls

- automated unit, integration, content, security, and component tests;
- TypeScript;
- ESLint;
- Prettier;
- production build;
- dependency audit workflow;
- server-side answer keys;
- private lab verifier projection;
- security headers;
- same-origin validation;
- request-body size limit;
- rate limiting;
- structured request logging;
- deterministic no-key mentor mode.

---

## 12. Missing features

### Priority 0 - production blockers

- authentication and account recovery;
- secure sessions;
- server-side RBAC;
- organizations and tenant isolation;
- durable PostgreSQL persistence;
- complete database schema and applied migrations;
- durable progress and assessment attempts;
- Docker image containing runtime publications;
- truthful readiness probes;
- production secrets management;
- HTTPS deployment and HSTS;
- centralized audit trail;
- backup and restore;
- real-browser end-to-end security testing.

### Priority 1 - required product capabilities

- instructor dashboard;
- administrator CMS;
- content review UI;
- human project grading;
- durable portfolio evidence;
- certificate generation and verification;
- secure uploads;
- malware scanning;
- background job processing;
- transactional email;
- analytics;
- notifications;
- real RAG mentor;
- retrieval and citation evaluation;
- hardened executable lab isolation;
- container or microVM lifecycle orchestration.

### Priority 2 - commercial and scale capabilities

- billing;
- subscriptions;
- entitlements;
- plans and quotas;
- organization administration;
- enterprise identity federation;
- support tooling;
- data export and deletion;
- localization;
- CDN and distributed caching;
- multi-region recovery.

### Curriculum gap

The broader target described elsewhere calls for 18 courses with 20 lessons per course. The current implementation contains 12 courses and 144 lessons. The current 80 activities are non-executable training simulations; zero Docker or microVM labs are shipped.

---

## 13. Technical debt

| Severity | Debt                                                                                  | Impact                                                           |
| -------- | ------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| High     | `App.tsx` is 2,259 lines                                                              | High change risk, difficult ownership, slower review and testing |
| High     | Runtime uses legacy client course shells plus publication replacement                 | Two content representations can drift                            |
| High     | Seed script extracts course specifications from TypeScript using a regular expression | Fragile coupling to source formatting                            |
| High     | No shared request/response schema between frontend and backend                        | Contract drift is likely                                         |
| High     | No persistence adapter                                                                | Business logic is tied to browser/filesystem/memory storage      |
| High     | One HTTP handler owns all backend routes                                              | Difficult authorization and validation hardening                 |
| Medium   | `styles.css` is 1,868 lines                                                           | Hard to isolate feature styles and prevent regressions           |
| Medium   | `seed-v1-academy.mjs` is 1,122 lines                                                  | Content generation and publication responsibilities are mixed    |
| Medium   | `v1-lab-library.mjs` is 816 lines                                                     | Large hand-maintained catalog module                             |
| Medium   | Manual runtime validation                                                             | Inconsistent validation and error messages                       |
| Medium   | No API client abstraction                                                             | Repeated fetch/error patterns                                    |
| Medium   | No localStorage schema version                                                        | Future progress changes can silently discard data                |
| Medium   | No database/content repository interface                                              | Migration to PostgreSQL will require broad changes               |
| Low      | Temporary PDF tooling exists under repository `tmp/`                                  | Build-context and source-control noise                           |
| Low      | Documentation spans future and current architecture                                   | Readers can confuse planned components with implemented ones     |

---

## 14. Duplicate code and duplicate representations

No clone-detection tool was run in this documentation pass. The following duplication was identified by static inspection.

### Repeated network code

`App.tsx` contains eleven direct `fetch()` calls with repeated patterns for:

- JSON headers;
- `response.ok` checks;
- JSON parsing;
- local error text;
- loading flags.

A typed API client would centralize these concerns.

### Duplicate content models

There are at least three related representations:

1. legacy course shells in `src/data/courses.ts`;
2. publication records under `content/published/`;
3. normalized seed data under `db/seeds/`.

`src/data/verified-content.ts` merges publication lessons into legacy shells at runtime. This supports fail-closed migration, but it creates duplicate identifiers, metadata, and model conversion logic.

### Duplicate learner/server evidence models

Quiz, lab, and project endpoints each construct similar mastery-evidence objects independently. These share:

- source type;
- source ID;
- score;
- independence level;
- hints;
- attempts;
- evidence weight;
- timestamp.

The model should be created by one domain service and validated by one schema.

### Duplicate publication projections

Lesson, lab, and project public projections repeat publication version, verification, publication status, metadata, and provenance decisions. Explicit projections are good for security, but common safe metadata could be centralized without exposing private fields.

### Duplicate progress updates

Components repeatedly create full `ProgressState` objects with object spread. A reducer or domain-specific update functions would reduce accidental field loss.

---

## 15. Dead code and unused runtime paths

### Confirmed or strongly indicated

| Item                          | Finding                                                                               |
| ----------------------------- | ------------------------------------------------------------------------------------- |
| `server/core.mjs: legacyLabs` | Imported by tests but not used by the production server                               |
| `Module.quiz` legacy data     | Generated in `src/data/courses.ts`, but no production rendering reference was found   |
| Legacy lesson bodies          | Used as planning/fallback shells but filtered from learner delivery when not verified |
| `LLM_API_KEY`                 | Declared in `.env.example` but not read by runtime code                               |
| `LLM_BASE_URL`                | Declared but not read                                                                 |
| `LLM_MODEL`                   | Declared but not read                                                                 |
| `EMBEDDING_MODEL`             | Declared but not read                                                                 |
| Adaptive SQL migration        | Not connected to runtime application code                                             |

### Misleading rather than dead

- Course `rating` and `students` fields are displayed, but generated through formulas rather than sourced from real usage data.
- `docker-compose.yml` starts only the web/API container and does not represent the broader PostgreSQL/Redis/MinIO/Mailpit architecture described in planning documents.

---

## 16. Security issues

### Critical

| Issue                         | Risk                                                                          |
| ----------------------------- | ----------------------------------------------------------------------------- |
| No authentication             | Anyone reaching the application is treated as an unauthenticated learner      |
| No tenant authorization       | Organization isolation cannot be claimed or tested                            |
| Forgeable lab owner ID        | A user who obtains another guest ID and session ID can impersonate that guest |
| No durable security audit log | Privileged or suspicious actions cannot be investigated reliably              |

### High

| Issue                                  | Risk                                                                        |
| -------------------------------------- | --------------------------------------------------------------------------- |
| Browser-local completion and mastery   | Learners can alter completion, scores, project evidence, and mastery        |
| Client-supplied adaptive state         | Recommendation and mastery inputs are not trusted evidence                  |
| Docker runtime omits published content | Healthy container may provide an empty academy                              |
| `/readyz` does not check dependencies  | Orchestrators may route traffic to an unusable instance                     |
| No upload security architecture        | Future evidence uploads cannot safely launch without scanning and isolation |
| No secure session/cookie controls      | Required before adding identity                                             |
| No external penetration test           | Current controls have only repository-level evidence                        |

### Medium

| Issue                                       | Risk                                                              |
| ------------------------------------------- | ----------------------------------------------------------------- |
| In-memory IP rate limiting                  | Bypassable across processes and unreliable behind a proxy         |
| Rate-limit map has no global pruning        | Many unique addresses can increase memory use                     |
| Proxy identity is not explicitly configured | Remote address may represent a load balancer rather than the user |
| CSP permits `'unsafe-inline'` styles        | Weakens CSP protection                                            |
| No HSTS                                     | Production HTTPS downgrade protection is absent                   |
| Regex-only mentor safety                    | Easy to bypass semantically and runs only in the client           |
| Manual validation                           | Unexpected object shapes may reach business logic                 |
| Generic 400 for server faults               | Conceals security-relevant operational failures                   |

### Positive controls

- No hard-coded private key or populated API secret was found in the checked source.
- Answer keys and lab expected values remain server-side.
- Public projections explicitly omit lab verification logic.
- Request bodies are bounded.
- Same-origin checks and a restrictive baseline CSP exist.
- Static path normalization exists.
- React rendering limits direct stored-XSS exposure for current text fields.
- External mentor citation links use `rel="noreferrer"`.

---

## 17. Performance issues

### Frontend

- All 144 published lessons, including full lesson blocks and references, are fetched at initial application load.
- Legacy course shells are bundled before being replaced by fetched publications.
- The main application bundle cannot use route-level code splitting because navigation is state-based.
- Large monolithic components increase render and reconciliation scope.
- Entire progress state is written to `localStorage` after each change.
- No virtualized lists exist for future large catalogs.
- No request deduplication or shared cache exists in the browser.
- Active flags prevent stale state assignment but do not cancel network requests.

### Backend

- Cold content loading reads many individual JSON files concurrently.
- Publication caching improves subsequent reads, but cache invalidation depends on manifest modification time and review date.
- Catalog, lab, and project endpoints have no pagination, field selection, or compression configuration in the application server.
- Rate limiting applies before route classification, including health and static traffic.
- Rate-limit entries are not periodically pruned.
- Content APIs always use `no-store`, preventing client/CDN caching of immutable publication versions.
- Every request writes a synchronous console record.

### Current scale

The current bundle and 488-publication catalog are manageable for a local prototype. The architecture will degrade as the platform approaches thousands of labs, larger lesson media, concurrent learners, and multiple server processes.

---

## 18. Scalability issues

- Process memory is the source of truth for lab sessions and decision logs.
- Horizontal server replicas would not share sessions, rate limits, or logs.
- Filesystem publications assume every server has the same local content tree.
- There is no database connection pool or transactional persistence.
- There is no Redis or other shared ephemeral-state service.
- There is no background queue.
- There is no object storage.
- There is no distributed lock or idempotency key.
- There is no event architecture for analytics or mastery updates.
- There is no API pagination.
- There is no tenant partition strategy beyond columns in an unapplied migration.
- There is no lifecycle mechanism for thousands of executable lab environments.
- There is no resource quota or entitlement system.
- There is no tested deployment topology.
- The in-memory rate limit cannot enforce a global policy.
- The file-per-publication model creates increasing filesystem overhead.

---

## 19. UX issues

### Navigation

- Pages have no stable URLs.
- Browser back and forward controls do not represent application navigation.
- Courses, lessons, labs, and projects cannot be deep-linked.
- Refreshing resets navigation to the home page.

### Trust and clarity

- Formula-generated ratings and learner counts look like real platform statistics.
- “Learner dashboard” can imply an account even though there is no login.
- Project “accepted” status is based on length and checked deliverables, not instructor grading.
- Local completion evidence is not identity verified.
- The catalog may show course shells when the publication API is unavailable, while verified lessons remain inaccessible.

### Learning experience

- Sentinel responses are templated and only loosely matched to the learner’s question.
- Sentinel has no conversation memory.
- There is no genuine semantic retrieval.
- Adaptive recommendations can be dismissed but cannot be accepted into a persistent learning plan.
- There is no instructor feedback loop.
- There are no notifications or deadlines.
- There is no durable certificate or credential.

### Accessibility

- Several controls have accessible names and semantic elements.
- No current real-browser screen-reader audit is documented.
- Modal focus trapping and focus restoration are not evident.
- Escape-key dismissal is not evident for the mentor dialog.
- Page changes do not announce a new view to assistive technology.
- Keyboard-only, zoom, reduced-motion, contrast, and mobile-device evidence remains incomplete.

### Internationalization

- The interface is English-only.
- There is no localization architecture.
- Right-to-left rendering is not supported.
- Multilingual mentor retrieval is not implemented.

---

## 20. Docker and deployment findings

### Current image

The Dockerfile:

1. installs dependencies;
2. copies the workspace;
3. builds the Vite client;
4. copies `dist/` and `server/` into a Node 22 Alpine runtime;
5. runs as the `node` user;
6. exposes port 8080;
7. defines a health check.

### Positive properties

- multi-stage build;
- non-root runtime user;
- read-only container configured by Compose;
- `no-new-privileges`;
- health check;
- minimal Node runtime.

### Blocking defects

The server loads publications from:

```text
content/published/
```

The runtime stage copies only:

```text
dist/
server/
```

Therefore, a container built from the current Dockerfile does not contain the academy publication files. `/healthz` can still return 200 because it does not verify content. The result can be a nominally healthy deployment with empty lesson, lab, question, and project banks.

No `.dockerignore` was found, so the build context can also include local dependencies, generated files, and temporary review tooling.

---

## 21. Overall readiness score

### Scoring method

The score evaluates production multi-user readiness, not local demonstration quality.

| Area                            |  Weight |      Score | Notes                                                                            |
| ------------------------------- | ------: | ---------: | -------------------------------------------------------------------------------- |
| Learner functionality           |      15 |         12 | Strong local course, quiz, lab, project, and progress experience                 |
| Frontend architecture and UX    |      10 |          6 | Functional but monolithic, no routing, incomplete browser/accessibility evidence |
| Backend and API correctness     |      15 |          8 | Good bounded demo controls; weak layering and error semantics                    |
| Data durability and integrity   |      15 |          3 | Files, localStorage, and memory; SQL is not applied                              |
| Security, identity, and tenancy |      20 |          3 | Security headers exist, but identity and tenant boundaries are absent            |
| AI maturity                     |      10 |          3 | Deterministic mentor and rules engine; no LLM or RAG runtime                     |
| Testing and content validation  |       8 |          7 | Strong recorded automated coverage and publication validation                    |
| Operations and scalability      |       7 |          1 | Docker content defect, no observability stack, recovery, or scale architecture   |
| **Total**                       | **100** | **43 raw** | Critical blockers apply                                                          |

### Production-blocker cap

Because authentication, tenant authorization, durable persistence, and a working production content image are absent, the final readiness score is capped below 40.

## **Final readiness score: 39/100**

### Interpretation

| Score range | Meaning                                            |
| ----------- | -------------------------------------------------- |
| 0-24        | Concept or incomplete prototype                    |
| 25-49       | Functional prototype with production blockers      |
| 50-69       | Beta-capable after targeted hardening              |
| 70-84       | Production candidate requiring release validation  |
| 85-100      | Production-ready with ongoing operational controls |

CyberMentor is in the **functional prototype with production blockers** category.

For a supervised local fellowship demonstration, its readiness is materially higher, approximately **82/100**, because the local learner journey, seeded content, bounded simulations, and automated checks are already substantial.

---

## 22. Recommended production sequence

### Milestone 1 - trustworthy identity and persistence

- Add PostgreSQL.
- Define the complete schema.
- Add migrations and rollback tests.
- Implement registration, verification, login, reset, and secure sessions.
- Add organizations, memberships, roles, and authorization.
- Move learner progress and attempts to server persistence.

### Milestone 2 - reliable deployment

- Correct the Docker runtime content copy.
- Add `.dockerignore`.
- Make readiness depend on publications and database availability.
- Add CI/CD release gates.
- Add centralized logs, metrics, alerts, backups, and restore tests.
- Run real-browser E2E and accessibility checks.

### Milestone 3 - server-side AI

- Add a protected mentor API.
- Implement hybrid retrieval over approved publications.
- Add embeddings and a vector index.
- Preserve deterministic no-key fallback.
- Build citation, hallucination, injection, leakage, latency, and cost evaluations.

### Milestone 4 - durable practical platform

- Persist lab attempts and evidence.
- Add instructor project review.
- Add safe uploads and malware scanning.
- Introduce the first isolated executable lab only after container or microVM security controls are tested.

### Milestone 5 - product operations

- Add instructor and administrator workflows.
- Add analytics and learner support tools.
- Add verified certificates and portfolio evidence.
- Add billing and entitlements only if required by the business model.

---

## 23. Final disposition

CyberMentor AI should currently be described as:

> A verified, local-first cybersecurity academy prototype with deterministic adaptive learning, a bounded demo mentor, and server-verified simulation-based practical activities.

It should not currently be described as:

- a production multi-tenant SaaS;
- an authenticated learning-management system;
- a live RAG or LLM platform;
- a hardened executable cyber range;
- a durable credentialing platform;
- an instructor/admin-ready commercial academy.

The next release should prioritize identity, authorization, persistence, and deployability before expanding decorative functionality or representing planned AI and lab infrastructure as complete.
