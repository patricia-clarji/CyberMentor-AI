# CyberMentor AI Current State Audit

**Audit date:** 2026-07-28  
**Mode:** Documentation-only takeover audit  
**Implementation changes:** None  
**Production readiness:** Not production ready

## 1. Audit scope and evidence

This audit reconciles:

- the current repository;
- the approved CyberMentor AI proposal supplied in conversation;
- all existing repository audits;
- the approved final-integration, content, adaptation, and Cyber Range directives;
- the current [Master Requirements](MASTER_REQUIREMENTS.md).

Evidence inspected:

- React/TypeScript frontend source and tests;
- Node API source and tests;
- publication manifest and schemas;
- content source registry, snapshots, reports, drafts, and reviewer registry;
- SQL migration and generated normalized seed;
- Docker, Compose, environment, CI, and runtime logs;
- architecture, AI, security, operations, product, content, and audit documents;
- package scripts and current root inventory.

This pass did not install dependencies, run the test suite, start services, apply migrations, build containers, or perform browser testing. Results from 2026-07-19 are historical evidence, not newly executed checks.

## 2. Evidence precedence and contradictions

| Conflict                                                       | Current conclusion                                                                                            |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Older content documents say the manifest is empty              | Superseded. Current manifest contains 488 publications                                                        |
| Older roadmap says published activity/question pools are empty | Superseded for counts; current seed contains 80 labs, 144 questions, and 24 practice activities               |
| README describes 12 complete courses                           | Current seed has 12 courses, but approved final scope requires 18 courses and at least 360 meaningful lessons |
| Publications contain seeded approval metadata                  | This is not evidence of accountable external human SME review                                                 |
| System architecture calls Sentinel bounded retrieval           | Current code selects a lesson and returns a template; there is no lexical/vector retrieval                    |
| Earlier project audit says `.dockerignore` is absent           | Corrected. `.dockerignore` exists and excludes `node_modules`, `dist`, `.git`, `.env`, and `coverage`         |
| Roadmap mentions a production/Nginx container                  | Current Dockerfile is a Node 22 Alpine runtime, not Nginx                                                     |
| Product branding says AI                                       | Current mentor is deterministic client-side code; a live AI claim is unsupported                              |
| Git directory exists                                           | `git rev-parse` and `git status` fail; repository history/integrity is not usable                             |

## 3. Current repository inventory

### Application

- React 19 + TypeScript + Vite frontend
- Native Node.js HTTP API
- No frontend router
- No backend framework
- No ORM or database driver
- No queue, worker, object-store client, email client, analytics SDK, billing SDK, or LLM SDK

### Published content

| Artifact            |   Count |
| ------------------- | ------: |
| Courses             |      12 |
| Modules             |      48 |
| Lessons             |     144 |
| Questions           |     144 |
| Labs                |      80 |
| Practice activities |      24 |
| Projects            |      12 |
| Rubrics             |      12 |
| Completion rules    |      12 |
| **Total**           | **488** |

### Current 12 courses

1. Cybersecurity Foundations
2. Networking for Cybersecurity
3. Linux for Cybersecurity Professionals
4. Introduction to Security Operations and SOC Analysis
5. Incident Response Foundations
6. Digital Forensics Foundations
7. Ethical Hacking and Penetration Testing Foundations
8. Web Application Security Foundations
9. Python for Cybersecurity
10. Cloud Security Foundations
11. AI and LLM Security Foundations
12. Cybersecurity Career and Interview Preparation

Missing from the approved 18-course catalog as independent courses:

- Windows Security Foundations
- SIEM and Log Analysis
- API Security Foundations
- Active Directory Security Foundations
- DevSecOps and Container Security
- Threat Intelligence and Threat Hunting

Several existing names also differ from the approved canonical titles.

## 4. Frontend state

### Implemented

- landing page;
- catalog and search;
- career-track presentation;
- local enrollment;
- verified lesson overlay;
- structured lesson blocks;
- notes and bookmarks;
- server-graded single-choice checks;
- learner dashboard derived from browser state;
- rule-based recommendation cards;
- Cyber Range catalog, filters, bookmarks, launch, pause, resume, reset, close, hints, verification, debrief, and reflection;
- project listing and formative completeness submission;
- local portfolio summary;
- deterministic Sentinel modal;
- responsive CSS and several accessible control labels.

### Architecture

`src/App.tsx` contains 2,259 lines and owns navigation, API calls, domain state, page rendering, labs, projects, recommendations, and mentor UI. Eleven direct `fetch()` calls are embedded in feature components.

### Problems

- no stable URLs, deep links, browser history, or route guards;
- no authentication UI;
- no instructor, reviewer, organization, university, enterprise, awareness-management, Kids Academy, or administrator UI;
- progress is editable browser data;
- full lesson catalog loads at startup;
- no shared API client or error contract;
- no error boundary;
- mentor has no real retrieval or model call;
- modal focus trapping/restoration and route announcements are not evident;
- real screen-reader/mobile/browser verification is absent;
- English-only UI;
- formula-generated ratings and learner counts are displayed as if real, violating GOV-004;
- “Learner dashboard” can imply an account even though no account exists;
- project acceptance is only a length/deliverable check.

## 5. Backend and API state

### Implemented API routes

| Method | Endpoint                        | Current behavior                                        |
| ------ | ------------------------------- | ------------------------------------------------------- |
| GET    | `/healthz`                      | Always returns process health                           |
| GET    | `/api/health`                   | Returns `deterministic-demo` mode                       |
| GET    | `/readyz`                       | Always returns ready                                    |
| GET    | `/api/content/catalog`          | Returns all published lesson records                    |
| GET    | `/api/labs`                     | Returns all public lab projections                      |
| POST   | `/api/labs/launch`              | Creates/resumes an in-memory lab session                |
| GET    | `/api/labs/session`             | Reads a session using guest owner ID                    |
| POST   | `/api/labs/action`              | Pause/resume/reset/close                                |
| POST   | `/api/labs/hint`                | Reveals ordered stored hint                             |
| POST   | `/api/labs/verify`              | Authorizes guest session and checks normalized evidence |
| GET    | `/api/projects`                 | Returns public project projections                      |
| POST   | `/api/projects/submit`          | Checks text length and deliverable acknowledgement      |
| POST   | `/api/checks/grade`             | Grades one published single-choice question             |
| POST   | `/api/adaptive/mastery`         | Calculates mastery from client-supplied evidence        |
| POST   | `/api/adaptive/recommendations` | Ranks approved activities using rules                   |
| POST   | `/api/adaptive/diagnostic/next` | Selects a diagnostic question                           |

### Positive controls

- 16 KiB request body limit;
- same-origin enforcement;
- in-memory rate limit;
- CSP and baseline security headers;
- request IDs and JSON request logs;
- server-side question keys and lab expected values;
- public publication projections;
- static path normalization;
- immutable static-asset caching.

### Problems

- no authentication or authorization middleware;
- no database;
- no durable attempts, sessions, logs, progress, or decisions;
- all route logic is in one handler;
- manual validation;
- unexpected server errors are commonly returned as 400;
- no API versioning or pagination;
- no idempotency;
- no OpenAPI or shared schemas;
- no graceful shutdown;
- no dependency-aware readiness;
- in-memory rate-limit keys are not globally bounded;
- proxy-aware client identity is undefined;
- no Sentinel API;
- no content author/reviewer/admin API;
- no upload, worker, analytics, billing, entitlement, email, or notification API.

## 6. Authentication, authorization, and tenancy

### Current behavior

There is no account lifecycle.

The browser stores:

- `cm-progress`;
- `cm-range-owner`, generated as `guest_<UUID>`.

The server trusts the client-supplied guest owner string and compares it with an in-memory lab session. This prevents accidental mismatches but is not authentication.

### Missing

- registration;
- email verification;
- login/logout;
- Argon2id password hashing;
- forgot/reset/change password;
- secure cookies;
- CSRF controls;
- session rotation/revocation;
- MFA;
- account deletion/export;
- organization invitations;
- required roles;
- permission policies;
- organizations and memberships;
- cross-tenant enforcement;
- identity-bound audit events.

### Disposition

IAM-001 through IAM-008 are missing or architecture-only. A public or multi-user production deployment is prohibited until this boundary exists and is tested.

## 7. Data and persistence

### Runtime data stores

| Data                  | Store                            |
| --------------------- | -------------------------------- |
| Curriculum            | Files under `content/published/` |
| Learner state         | Browser `localStorage`           |
| Lab sessions/attempts | Node process memory              |
| Adaptive logs         | Node process memory              |
| Rate limits           | Node process memory              |
| Normalized academy    | Generated JSON seed only         |

### SQL artifact

`db/migrations/001_adaptive_learning.sql` defines ten adaptive-learning tables with organization/learner keys, but it is unapplied and does not cover the complete product.

No PostgreSQL, SQLAlchemy, Alembic, pgvector, Redis, MinIO, migration runner, database seed importer, connection pool, backup, or restore implementation exists.

### Disposition

DAT-001 through DAT-006 are mostly missing. The explicit SQLAlchemy/Alembic requirement conflicts with the current Node backend and requires decision OQ-002 before implementation.

## 8. Content architecture and governance

### Implemented

- allowlisted authoritative source registry;
- source metadata/digest snapshots;
- draft/publication schemas;
- content hashes;
- semantic versions;
- claim/evidence validation;
- content status/refresh/import/review/publish/sync/rollback commands;
- public manifest;
- learner-safe projections;
- review-role rules;
- current 488-record seeded baseline;
- automated content tests and validation reports.

### Current reviewer truth

`content/reviewers.json` contains zero enrolled reviewers.

The initial publications use a product-owner release baseline. That satisfies the local seed policy created during the earlier implementation pass, but it does not prove external technical, instructional, accessibility, licensing, or safety review.

### Problems

- old content documentation still says zero publications;
- current course count/depth does not meet CUR-002/CUR-003;
- no authenticated CMS;
- no real reviewer identities;
- no protected publication API or append-only review audit;
- no proof of commercial-release SME review;
- no independently verified originality/legal sign-off;
- course source data is duplicated between TypeScript shells, publications, and a normalized JSON seed;
- the seed script parses TypeScript specifications with a regular expression;
- claims such as “substantial” need independent curriculum review.

## 9. Assessment state

### Implemented

- 144 published single-choice question records;
- server-side correct option;
- distractor explanations;
- objective/skill metadata;
- sanitized public diagnostic payload;
- versioned mastery evidence response;
- answer-leakage tests in the historical suite.

### Missing

- required assessment types beyond single choice;
- durable question/quiz/exam attempts;
- timing and attempt limits;
- randomized exam assembly;
- partial credit;
- final exams;
- authenticated instructor override;
- audit history;
- psychometric analysis;
- identity-bound results.

### Disposition

ASM-001 and ASM-004 are partial. ASM-002, ASM-003, and durable ASM-005 are missing.

## 10. Adaptive-learning state

### Implemented

- 23-node draft skill graph;
- transparent mastery/confidence formulas;
- evidence source weights;
- recency adjustment;
- verified activity filtering;
- prerequisite, difficulty, goal, role, time, mistake, and failure signals;
- stored progressive hint selection;
- diagnostic branching;
- human-readable recommendation reasons;
- historical tests for required learner profiles.

### Missing or untrusted

- client supplies current skill state and evidence;
- browser state is editable;
- no durable evidence;
- no authenticated instructor policy;
- no cohort experiment framework;
- no persistent recommendation acceptance;
- no production audit trail;
- no credential authority.

### Disposition

The system demonstrates deterministic personalization logic. It does not satisfy the production “adaptive” claim under GOV-001/GOV-003.

## 11. Sentinel and AI state

### Current implementation

`src/lib/sentinel.ts`:

- runs in the browser;
- uses regular expressions for obvious unsafe/answer requests;
- chooses a verified lesson from explicit context or simple title-word matching;
- returns a fixed explanatory template and stored lesson citations.

### Environment variables

The example environment declares:

- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL`
- `EMBEDDING_MODEL`

No runtime code reads them.

### Missing

- server-side model adapter;
- provider credentials;
- model choice;
- embeddings;
- vector store;
- lexical/hybrid retrieval;
- citation entailment;
- conversation persistence;
- tools;
- streaming;
- budgets;
- provider fallback orchestration;
- server-side prompt security;
- production AI evaluation.

### Disposition

AI-001 through AI-008 are mostly missing. The current feature must remain labeled deterministic demo mentor. “AI-powered” is not currently proven.

## 12. Cyber Range state

### Current inventory

- 80 usable non-executable activities;
- 40 interactive browser/awareness/career simulations;
- 20 artifact-analysis activities;
- 20 secure configuration/remediation activities;
- 10 awareness simulations included in the interactive count;
- 10 career/interview simulations included in the interactive count;
- 59 category labels;
- zero Docker or microVM learner environments.

### Implemented

- catalog/search/selected filters;
- guided/independent mode;
- launch/resume;
- pause/reset/close;
- expiration;
- ordered hints;
- wrong/correct normalized evidence;
- debrief/reflection;
- local portfolio updates;
- guest-owner mismatch denial.

### Missing

- durable sessions, attempts, evidence, and audit logs;
- authenticated ownership;
- instructor review;
- admin management;
- actual environment health;
- isolated networking;
- resources/quotas;
- safe mounts;
- cleanup workers;
- executable Docker/microVM labs;
- production control plane.

### Disposition

The current simulations truthfully meet parts of LAB-001, LAB-002, LAB-003, and LAB-008. They do not meet the production definition of done or executable-lab requirements.

## 13. Projects, scenarios, portfolio, and career

### Implemented

- 12 project records and rubrics;
- project requirements/milestones;
- text submission and deliverable checklist;
- formative server acceptance;
- local project completion;
- local reflections/skill evidence;
- career track/course presentation;
- interview/career simulations in the lab catalog.

### Missing

- durable submissions;
- evidence files;
- instructor review and feedback;
- rubric scoring;
- scenario runtime and specialization packs;
- identity assurance;
- certificate/portfolio verification;
- public/private evidence controls;
- revocation;
- employer validation.

### Disposition

EVD-001 through EVD-005 are partial or missing.

## 14. Institutional, audience, and commercial editions

University, enterprise, organization management, instructor/cohort management, awareness campaign administration, Student Academy, Kids Cyber Safety, billing, subscriptions, and entitlements are not implemented.

The absence of child-consent, privacy, age-band, and moderation decisions blocks Kids Academy work independently of other development.

## 15. Deployment, CI, and operations

### Implemented

- GitHub Actions CI for install, lint, format, type check, tests, content validation, build, and dependency audit;
- scheduled source refresh that opens a pull request and cannot publish;
- multi-stage Node Dockerfile;
- non-root runtime;
- read-only/no-new-privileges Compose flags;
- `.dockerignore`;
- liveness/readiness routes;
- JSON request logs;
- production-style local run logs.

### Blocking Docker defect

The API loads `content/published/`. The runtime image copies only `dist/` and `server/`. It does not copy `content/published/`. The container can return healthy while content APIs are empty.

### Other gaps

- Compose contains only one web service;
- no PostgreSQL, Redis, MinIO, Mailpit, worker, or lab service;
- no deployment host/domain/DNS/TLS;
- no secret manager;
- no observability backend;
- no SLOs or alerts;
- no backup/restore;
- readiness does not inspect dependencies;
- no SBOM/license gate;
- no container-build evidence for the current Dockerfile;
- Git metadata is unusable, so CI provenance cannot be trusted from this workspace alone.

## 16. Security summary

### Positive

- no populated secret found in reviewed configuration;
- answer keys and lab expected values remain server-side;
- safe public projections;
- same-origin check;
- body limit;
- baseline CSP/security headers;
- non-root container intent;
- no arbitrary target entry;
- simulations contain authorization/defensive context.

### Critical production blockers

- no authentication;
- no server authorization;
- no tenant boundary;
- forgeable guest lab identity;
- editable learner evidence;
- no durable audit;
- no secure upload system;
- no executable-lab isolation;
- no production secrets/TLS configuration;
- no external security assessment.

## 17. Performance and scalability

- all lesson publications load at application startup;
- catalog/lab/project endpoints are unpaginated;
- publication cold load reads many files;
- API responses are `no-store`;
- no browser query cache;
- no route-level code splitting;
- process-local sessions/logs/rate limits prevent horizontal scaling;
- rate-limit map has no global bound;
- no database, Redis, queue, object storage, or isolated worker tier;
- file-per-publication overhead grows with content;
- no measured load or latency budgets.

## 18. UX and accessibility

- formula-generated ratings and learner counts violate truthful-metric rules;
- no stable routes;
- local state can disappear without account recovery;
- content API failure can leave visible planning shells but no usable lessons;
- no real instructor feedback;
- generic mentor responses;
- no real-browser evidence;
- incomplete dialog focus behavior;
- no page-change announcements;
- no confirmed WCAG target;
- no theme implementation evidence;
- no localization/RTL implementation.

## 19. Recorded quality evidence

Historical 2026-07-19 evidence reports:

- 12 discovered test files;
- 108 passing tests;
- formatting passed;
- lint passed;
- `tsc -b` passed;
- Vite production build passed;
- 488 content publications validated with zero errors/warnings;
- dependency audit reported zero moderate-or-higher findings;
- 15-check isolated live HTTP gate passed;
- real-browser testing was unavailable;
- Docker was unavailable.

These results remain useful evidence but must be rerun after approved implementation work.

## 20. Retain, refactor, remove, rebuild

### Retain

- content source registry, snapshots, schema validation, versioning, and safe projections;
- explicit curriculum/adaptive/Sentinel/range separation;
- structured content blocks;
- server-side answer and verifier boundaries;
- transparent adaptive formulas and acceptance tests;
- current 80 activity definitions as candidate reviewed content;
- deterministic no-key fallback;
- request IDs, body limit, origin checks, and baseline headers;
- CI/content-refresh intent.

### Refactor

- split `App.tsx` into routes, features, components, hooks, and an API client;
- replace state navigation with a real router;
- define shared API schemas and errors;
- separate route/controller/service/repository layers;
- unify course/publication/seed representations;
- replace regex extraction of TypeScript course specs;
- make health/readiness dependency-aware;
- paginate and version content APIs;
- move adaptive evidence to trusted durable events;
- update stale documentation.

### Remove

- invented ratings and learner counts;
- production-visible demo terminology after real identity exists;
- unused `legacyLabs` production export;
- unused LLM configuration until a provider adapter exists, or implement the adapter before retaining it;
- duplicate legacy quiz data not used by learner delivery;
- stale empty-manifest statements;
- temporary PDF review tooling from product/build contexts;
- claims of “job-ready,” live AI, production adaptation, or verified credentials without evidence.

### Rebuild

- backend persistence and domain model;
- authentication, sessions, RBAC, and tenancy;
- durable learner progress/assessment/lab/project evidence;
- instructor/reviewer/admin workflows;
- server-side Sentinel and RAG;
- lab control plane for executable environments;
- upload/object-storage pipeline;
- workers/jobs;
- analytics/observability;
- billing/entitlements;
- production deployment and recovery.

## 21. Readiness

The previous audit score of 39/100 remains directionally reasonable. This pass does not issue a new numeric score because no runtime gates were executed.

Current release classification:

> Functional local-first prototype with significant content and practical simulations, but without the identity, persistence, authorization, AI, isolation, institutional, and operational boundaries required for production.

## 22. Immediate blockers before coding

The following must be answered before their affected implementation phases:

- backend migration strategy;
- production deployment topology;
- identity/session approach;
- organization and tenancy rules;
- email provider/domain;
- LLM and embedding providers/models;
- AI retention/consent;
- object storage;
- worker/Redis design;
- observability providers;
- executable-lab isolation target;
- accountable content reviewers;
- commercial/legal/privacy posture;
- child-safety scope;
- pilot ethics/recruitment;
- localization scope;
- professional-readiness definition.

See [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).
