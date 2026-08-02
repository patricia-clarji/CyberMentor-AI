# CyberMentor AI Implementation Roadmap

**Status:** Proposed; requires approval  
**Created:** 2026-07-28  
**Current authorization:** Documentation only

## 1. Roadmap principles

1. Production trust boundaries precede feature expansion.
2. One complete vertical slice is preferable to many partial pages.
3. No phase begins while a required product/security/provider/legal decision for that phase is unresolved.
4. Existing verified local behavior is retained until its replacement passes equivalent or stronger tests.
5. Migrations use expand/migrate/contract and preserve rollback.
6. Local adapters are labeled local; production providers require explicit approval.
7. Every phase ends with automated checks, manual browser verification, documentation, and a self-audit.
8. No dates are promised until scope, team capacity, provider accounts, and deployment target are approved.
9. The competition/private-beta, full-academy, and long-term-company profiles are separate gates; deferring a requirement from the competition profile does not remove it from the approved product.

## 2. Approved release profiles

| Profile                  | Release boundary                                                                                                                                            | Gate                                                                      |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| Competition/private beta | Controlled private single-organization beta with tenant-aware foundations and one complete Junior SOC Analyst Readiness vertical slice                      | REL-001 through REL-020                                                   |
| Full academy             | 18 courses, at least 360 reviewed lessons, at least 80 reviewed practical activities, full assessment/evidence/CMS capability, and additional role pathways | Approved after the competition slice is proven; not a competition blocker |
| Long-term company        | University, enterprise, Kids Academy, billing, recruiter discovery, multilingual content, public cyber range, and comprehensive intelligence                | Separately approved future releases                                       |

## 3. Reduced competition critical path

| Phase | Goal                                                             | Depends on                                                                           | Competition exit evidence                                                                                                                                 |
| ----- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| C0    | Governance, version-control provenance, release claim correction | Authoritative Git remote/branch and implementation approval                          | Approved scope, protected history, truthful claims                                                                                                        |
| C1    | Trusted platform foundation                                      | Hosting envelope; production email can remain provider-swappable until domain exists | FastAPI/SQLAlchemy/Alembic trusted domains, PostgreSQL, first-party IAM, personal tenant, RBAC, sessions, migrations, seed, audit events                  |
| C2    | Complete SOC learner vertical                                    | C1 and accountable reviewers                                                         | Diagnostic, roadmap, one reviewed course, connected practice, flagship mission, action/mistake evidence, replay, project, skill report, completion record |
| C3    | Evaluated Sentinel and adaptation                                | Approved LLM/model/budget, embedding choice, privacy policy                          | Live grounded mentor, deterministic fallback, citation/leakage/safety evaluation, trusted prerequisite/remediation and learning-mode decisions            |
| C4    | Release hardening and pilot                                      | Hosting/domain, storage/scanning, observability, pilot approval/recruitment          | Reproducible deployment, responsive/accessibility/security evidence, consented pilot report, release limitations                                          |

The critical path is `C0 → C1 → C2 → C3 → C4`. Work within a phase may run in parallel only when it does not bypass its trust boundary. The 18/360 curriculum expansion, 80-lab productionization, billing, institutional editions, Kids Academy, public recruiter marketplace, multilingual publication, public hostile-workload range, and intelligence feed are deliberately outside this competition path.

## 4. Phase C0 — Governance and source-of-truth correction

### Retain

- current learner experience;
- publication pipeline;
- adaptive rules;
- current safe simulations;
- historical audit evidence.

### Documentation/actions after approval

- approve [MASTER_REQUIREMENTS.md](MASTER_REQUIREMENTS.md);
- answer or defer each blocking item in [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md);
- accept or revise proposed decisions in [DECISION_LOG.md](DECISION_LOG.md);
- make the current repository a valid version-controlled checkout;
- update stale architecture/content documents to current counts and truth;
- remove unsupported product claims from release-facing copy;
- remove invented ratings and learner counts;
- define release environments and claim vocabulary.

### Exit criteria

- requirement registry approved;
- Phase 1 questions answered;
- functional Git history available;
- no documentation contradicts current implementation;
- every retained claim has an evidence owner.

### Blocking questions

OQ-025. OQ-006 must be answered before deployment design is finalized but does not block documentation or local foundation work.

## 5. Phase C1 — Production foundation

### Objective

Create the minimum trusted platform boundary: durable data, authenticated identity, tenant authorization, environment configuration, jobs, storage, and operations.

### Proposed sequence

1. Preserve working Node content delivery and validation behind stable contracts.
2. Incrementally introduce FastAPI, SQLAlchemy 2, and Alembic for identity, persistence, progress, evidence, AI, and other trusted domains.
3. Define versioned API contracts and domain modules.
4. Create the competition PostgreSQL model and tenant-aware extension points.
5. Add Alembic migrations and verified seed/import path.
6. Add personal organizations, many-to-many memberships, active organization context, roles, and permissions.
7. Add registration, Mailpit verification, login/logout, reset, Argon2id credentials, secure cookie sessions, rotation, revocation, and invitations.
8. Add server-side policy enforcement and audit events.
9. Add Celery and Redis for justified durable jobs.
10. Add MinIO local object-storage adapter and a private S3-compatible production abstraction.
11. Correct Docker runtime content and dependency-aware readiness.
12. Add secret configuration, health, structured logs, OpenTelemetry-ready instrumentation, backups, and restore test.

### Initial domain model

- user;
- credential/external identity;
- email verification;
- password reset;
- session;
- organization;
- membership;
- role/permission;
- audit event;
- course/version/module/lesson;
- enrollment/progress/note/bookmark;
- skill/evidence/recommendation;
- question/assessment/attempt;
- lab definition/instance/attempt/evidence;
- project/rubric/submission/review;
- content draft/review/publication;
- file object;
- job;
- notification;
- consent.

### Required tests

- migrations up/down;
- transaction-safe seed;
- registration/verification/login/reset/logout;
- cookie/CSRF/session rotation/revocation;
- horizontal/vertical privilege escalation;
- tenant isolation;
- readiness failure when dependencies fail;
- backup/restore smoke test;
- Docker/Compose startup;
- production configuration rejection for development credentials.

### Exit criteria

- authenticated learner and instructor accounts persist;
- every protected record is tenant/owner authorized;
- learner progress survives browser/server restart;
- production container contains publications;
- readiness reflects database/content/queue/storage requirements;
- no critical/high IAM or tenancy defect remains.

### Blocking questions

OQ-005, OQ-006, OQ-010, and OQ-012 block production deployment of their affected capabilities. Mailpit and MinIO remain accurately labeled local adapters. OQ-025 blocks implementation provenance.

## 6. Phase C2 — Complete Junior SOC Analyst vertical slice

### Objective

Prove the definition of done on one coherent Junior SOC Analyst Readiness path before expanding the academy.

### Scope

- authenticated learner onboarding and goals;
- one diagnostic;
- one complete course;
- stable course/lesson routes;
- structured lesson player;
- notes/bookmarks/progress;
- multiple assessment types;
- one safe interactive lab;
- one artifact lab;
- one complete workplace scenario;
- trusted action, mistake, retry, and hint observation;
- investigation replay;
- one project and rubric;
- instructor assignment/review/feedback;
- mastery evidence;
- portfolio evidence;
- completion criteria;
- one identity-bound, revocable, verifiable CyberMentor Verified Completion Record;
- deterministic mentor fallback.

### Refactors

- split `App.tsx` by route/feature;
- create typed API client;
- remove legacy runtime content overlay;
- load course/lesson content on demand;
- use server state as authority;
- add error boundaries and accessible route/dialog behavior.

### Required manual journey

1. Register.
2. Verify through Mailpit.
3. Log in.
4. Select organization/goal.
5. Take diagnostic.
6. Enroll.
7. Read lesson.
8. Save note/bookmark.
9. Complete check and quiz.
10. Launch lab.
11. Fail then pass verification.
12. Complete scenario.
13. Submit project.
14. Instructor reviews and scores rubric.
15. Learner receives feedback.
16. Skill and portfolio evidence update.
17. Session is revoked and access fails.

### Exit criteria

One vertical slice satisfies GOV-001 with tests, browser evidence, documentation, and no critical/high defects.

### Blocking questions

OQ-015 is required to establish accountable review. OQ-017 remains open only for any activity that requires executable Docker; browser simulations may satisfy most competition practice when truthfully labeled.

## 7. Phase C3 — Evaluated Sentinel and adaptive behavior

### Objective

Add a real server-side mentor and evidence-driven adaptation without making either system the source of official curriculum or grading authority.

### Scope

- provider-neutral server-side model adapter with one approved live hosted model;
- grounded hybrid retrieval over reviewed competition content;
- English embedding benchmark and versioned re-index path;
- deterministic no-key/timeout/outage/budget fallback;
- prompt-injection, graded-answer leakage, citation validity, safety, latency, and cost evaluation;
- prerequisite remediation and guided/independent mode switching from trusted evidence;
- learner-visible rationale and instructor policy controls;
- minimal retention, no provider training, explicit research consent, deletion controls, and redacted evaluation logs.

### Exit criteria

- live model use is proven with provider evidence and a fixed evaluation set;
- fallback is automatically exercised and truthfully identified;
- graded answers and cross-tenant content do not leak;
- citations resolve to reviewed sources and support the response;
- adaptive decisions are reproducible, explainable, persisted, and reversible.

### Blocking questions

OQ-007 and OQ-008.

## 8. Phase C4 — Release hardening and consented pilot

### Objective

Deploy the exact competition slice reproducibly, verify it under production-oriented controls, and evaluate it with a small approved Lebanese learner pilot.

### Scope

- local, test/CI, and one private-beta environment;
- managed container platform and managed PostgreSQL; no Kubernetes;
- production email, private object storage, scanning, logs, traces, errors, alerts, backup and restore;
- responsive browser coverage, WCAG audit, security tests, dependency checks, and release evidence;
- teaching-team/ethics approval, consent materials, approximately 5–15 participants, minimal first-party event collection, pre/post task comparison, mentor usefulness feedback, and a limitations report.

### Blocking questions

OQ-005, OQ-006, OQ-010, OQ-012, OQ-021, and OQ-025.

## 9. Post-competition — Full academy, assessments, evidence, and CMS

### Objective

Reach the approved 18-course/360-lesson academy, productionize the minimum 80-activity library, and remove seeded-review ambiguity. This is an approved full-academy target, not a competition release blocker.

### Workstreams

#### Curriculum

- add the six missing courses;
- reach at least 20 meaningful lessons per course;
- remove generic duplication;
- align objectives, skills, practice, labs, scenarios, projects, and completion;
- validate all sources, commands, links, versions, and accessibility.

#### Assessment

- implement required question types;
- question banks and versions;
- quizzes and final exams;
- timing, limits, partial credit, randomization;
- explanations, overrides, and audit history;
- durable mastery evidence.

#### CMS

- authenticated author/reviewer/publisher roles;
- draft editor and preview;
- source/evidence view;
- diff and version history;
- review assignments and decisions;
- broken-link/freshness status;
- publication/rollback;
- append-only audit.

#### Human governance

- enroll accountable reviewers;
- define conflict-of-interest policy;
- complete technical, instructional, accessibility, licensing, and safety reviews;
- obtain legal sampling for originality/licensing.

### Exit criteria

- 18/18 courses published;
- at least 360 meaningful lessons;
- no generic duplicate-body failure;
- every course has assessment, labs, scenario, project, rubric, and completion rule;
- all content passes automated and accountable human gates;
- no seeded metadata is presented as external certification.

### Blocking questions

OQ-015, OQ-018, OQ-023, OQ-024.

## 10. Post-competition — Expanded Sentinel and evaluated RAG

### Objective

Earn the “AI-powered” claim through a grounded, secure, measurable server implementation.

### Baselines

- deterministic current-lesson fallback;
- lexical/BM25 retrieval;
- popularity/rule recommendation baseline.

### Target implementation

- model-provider abstraction;
- selected production and local/degraded adapters;
- approved chunking metadata;
- pgvector embeddings;
- hybrid retrieval;
- tenant and learner authorization filters;
- reranking;
- citation support validation;
- conversation/thread persistence and deletion;
- safe tool registry;
- prompt/tool/output policies;
- streaming with cancellation;
- rate, token, latency, and cost budgets;
- provider circuit breaker;
- model/prompt/retrieval versioning.

### Evaluation

- reviewed cybersecurity question set;
- Recall@5;
- citation precision;
- unsupported-claim rate;
- answer leakage;
- prompt/indirect injection;
- cross-user/tenant leakage;
- safe refusal and harmless-query helpfulness;
- multilingual behavior if approved;
- latency and cost;
- deterministic fallback continuity.

### Exit criteria

- provider and privacy decisions approved;
- no learner content leaves approved boundaries unexpectedly;
- citations support material claims;
- zero confirmed answer-key/cross-tenant disclosure in release suite;
- published evaluation report;
- UI labels live AI only when adapter is active.

### Blocking questions

OQ-007, OQ-008, OQ-009, OQ-020, OQ-021, OQ-022.

## 11. Post-competition — Durable Cyber Range

### Objective

Turn the existing simulation library into a durable, authorized practical platform and add the first genuinely isolated executable labs.

### Retain

- 80 activity definitions as review candidates;
- search/filter/catalog UI;
- progressive hints;
- safe target rules;
- defensive debriefs;
- server-side verifier boundary.

### Rebuild/refactor

- persist lab instances, ownership, attempts, hints, evidence, and audits;
- enforce authenticated tenant ownership;
- add lab-definition schema to database;
- add signed evidence downloads;
- add instructor review;
- add lifecycle worker;
- add quotas and health;
- add environment adapter interface.

### Executable-lab pilot

Start with a small approved set such as:

- Linux permissions;
- authentication-log analysis;
- security-header remediation;
- local API authorization flaw;
- Dockerfile hardening.

Each must prove:

- image build;
- isolated network;
- outbound restrictions;
- limits;
- non-root/no privilege where possible;
- safe mounts;
- no Docker socket;
- health;
- task feasibility;
- wrong/correct verification;
- reset;
- expiration;
- cleanup;
- cross-user denial;
- logs.

### Exit criteria

- all visible activities persist attempts and completion;
- planned labs are not shown as available;
- first executable labs pass the full environment matrix;
- production isolation limitations are explicit;
- no arbitrary public targets exist.

### Blocking questions

OQ-010, OQ-011, OQ-017.

## 12. Long-term — Institutional and professional editions

### University

- institutions/programs/sections;
- instructor assignment;
- due dates and grading;
- cohort/outcome reports;
- exports and retention.

### Enterprise and awareness

- organizations/groups;
- assignments/campaigns;
- completion and manager reporting;
- tenant entitlements;
- legally approved simulation policies.

### Student and Kids

- student career exploration;
- approved age bands;
- guardian consent;
- child-safe content and moderation;
- restricted data collection;
- legal approval before launch.

### Career, portfolio, and credentials

- role maps;
- interview simulations;
- professional reports;
- identity-bound portfolio evidence;
- visibility controls;
- verifiable/revocable credentials;
- no employment guarantee.

### Exit criteria

Each edition has its own authorized roles, data model, tested workflows, privacy policy, and truthful product copy.

### Blocking questions

OQ-004, OQ-013, OQ-014, OQ-016, OQ-020, OQ-023.

## 13. Long-term — Commercial production hardening

### Work

- billing and webhook idempotency;
- entitlements and quotas;
- production email/domain/DNS/TLS;
- managed secrets;
- observability/SLOs/on-call;
- load/capacity tests;
- SBOM/license policy;
- dependency/container scanning;
- external penetration test;
- privacy/legal documents;
- incident response;
- disaster recovery and restore drills;
- data export/deletion;
- production browser matrix;
- release/rollback drills.

### Exit criteria

- all launch-critical traceability rows implemented;
- no critical/high defect;
- accepted medium-risk register;
- external security and legal review complete;
- production readiness evidence generated from the deployed release;
- product claims match verified capability.

## 14. Cross-phase verification checklist

Every phase report must contain:

- requirements implemented;
- files changed;
- migrations;
- seed/import changes;
- API changes;
- authorization policies;
- external services/credentials;
- tests added;
- commands and exact results;
- manual browser evidence;
- console/server/worker logs;
- accessibility evidence;
- security self-audit;
- documentation changes;
- limitations and blockers;
- rollback plan.

## 15. Approval gate

No implementation phase starts from this roadmap until the user:

1. approves or revises the roadmap;
2. answers the phase-blocking questions;
3. confirms the first authorized phase and scope.
