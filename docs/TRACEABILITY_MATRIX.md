# CyberMentor AI Traceability Matrix

**Created:** 2026-07-28  
**Source registry:** [MASTER_REQUIREMENTS.md](MASTER_REQUIREMENTS.md)  
**Status evidence:** [CURRENT_STATE_AUDIT.md](CURRENT_STATE_AUDIT.md)

## Legend

- `—`: no implementation exists.
- `Local`: browser-local or process-memory behavior; not production persistence.
- `Historical`: recorded test evidence from 2026-07-19; not rerun in this takeover audit.
- Blocker IDs refer to [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).

## Release-scope overlay

| Release profile          | Canonical requirements                                                                                                                    | Current release treatment                                                                                                                     |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| Competition/private beta | REL-001 through REL-020                                                                                                                   | Release blockers; all must satisfy GOV-001 before the competition release is claimed complete                                                 |
| Full academy             | CUR-001 through CUR-012, LAB-001 through LAB-010, expanded assessment/evidence/CMS requirements, and role paths beyond Junior SOC Analyst | Approved post-competition expansion; gaps remain product debt but do not block the competition slice unless a REL requirement references them |
| Long-term company        | PRD-009 through PRD-012 and related institutional, Kids, billing, recruiter, multilingual, public-range, and intelligence requirements    | Approved architectural targets; no launch claim or fake UI until promoted to a later release                                                  |

Statuses below describe current implementation, not release priority. Deferral from the competition profile does not change a requirement to “implemented” and does not remove it.

## Competition/private-beta release

| Requirement                        | Status             | Frontend component        | Backend service                    | API endpoint              | Database model     | Test coverage                    | Documentation             | Outstanding blocker                                        |
| ---------------------------------- | ------------------ | ------------------------- | ---------------------------------- | ------------------------- | ------------------ | -------------------------------- | ------------------------- | ---------------------------------------------------------- |
| REL-001 Private beta boundary      | Architecture-only  | Current single-client UI  | Node API lacks tenancy             | Existing APIs unscoped    | Adaptive DDL only  | Historical local tests           | Master/roadmap            | IAM/data foundation; OQ-006/OQ-025                         |
| REL-002 Verified identity          | Missing            | —                         | —                                  | —                         | —                  | —                                | Requirements              | OQ-005 for production delivery                             |
| REL-003 PostgreSQL learner data    | Missing            | Local-state UI            | Process memory/client state        | No durable learner API    | Unapplied DDL only | Local tests                      | Audit/roadmap             | Incremental migration and PostgreSQL deployment            |
| REL-004 Personal tenant/RBAC       | Missing            | —                         | —                                  | —                         | —                  | —                                | Requirements/decision log | Implementation; OQ-006                                     |
| REL-005 Junior SOC path            | Partial            | Courses/tracks/labs       | Content catalog                    | Existing catalog/labs     | Files/local        | Inventory/component tests        | Requirements              | Coherent reviewed readiness profile implementation; OQ-015 |
| REL-006 Diagnostic/roadmap         | Partial/local      | Onboarding/adaptive panel | Deterministic adaptive rules       | `/api/adaptive/*`         | Local/DDL          | Adaptive tests                   | Adaptive architecture     | Trusted data, persistence, validated SOC diagnostic        |
| REL-007 Reviewed course            | Blocked            | Course/lesson player      | Content repository                 | `/api/content/catalog`    | File publications  | Pipeline/inventory tests         | Content docs              | OQ-015 and accountable review evidence                     |
| REL-008 Connected practice         | Partial/local      | Lessons/labs/projects     | Lab/project gates                  | Existing practice APIs    | Files/local/memory | Component/runtime tests          | Cyber Range audit         | Persisted sequence, review, learner evidence               |
| REL-009 Flagship SOC mission       | Missing            | —                         | —                                  | —                         | —                  | —                                | Requirement only          | Original mission definition, review, verification          |
| REL-010 Action/mistake observation | Partial/memory     | Lab actions/hints         | Runtime log                        | Lab session/action routes | Memory             | Runtime tests                    | Cyber Range audit         | Trusted durable event model, consent                       |
| REL-011 Adaptive mode switching    | Partial/local      | Adaptive panel            | Rule engine                        | `/api/adaptive/*`         | Local/DDL          | Adaptive tests                   | Adaptive architecture     | Trusted evidence, persisted decisions, instructor policy   |
| REL-012 Live Sentinel/fallback     | Partial/demo       | Mentor                    | Client deterministic fallback only | —                         | —                  | Deterministic safety tests       | Mentor/threat docs        | OQ-007/OQ-008; server AI/RAG                               |
| REL-013 Evidence skill profile     | Partial/local      | Dashboard/portfolio       | Mastery calculator                 | Adaptive mastery route    | Local/DDL          | Adaptive/store tests             | Adaptive docs             | Durable provenance/confidence/recency                      |
| REL-014 Investigation replay       | Missing            | —                         | —                                  | —                         | —                  | —                                | Requirement only          | Mission timeline/evidence model and authorized UI          |
| REL-015 Professional project       | Partial/local      | Project/portfolio         | Formative gate                     | `/api/projects*`          | Local              | Component/core tests             | Audit                     | Reviewed rubric, durable submission/review; OQ-015/OQ-010  |
| REL-016 Completion record          | Missing            | Disclaimer only           | —                                  | —                         | —                  | —                                | Requirements/decision log | Identity-bound criteria, verification, revocation          |
| REL-017 Polished accessible UI     | Partial            | Responsive app            | Basic error responses              | Existing APIs             | —                  | DOM/component tests              | Audit                     | Browser/WCAG/mobile verification and complete states       |
| REL-018 Safety/AI evaluation       | Partial/historical | —                         | Deterministic rules                | Existing checks/labs      | —                  | Historical safety/privacy suites | Threat model/audits       | Live-model RAG/security/accessibility evaluation           |
| REL-019 Consented pilot            | Blocked            | —                         | First-party analytics missing      | —                         | —                  | —                                | Proposal/open questions   | OQ-021                                                     |
| REL-020 Reproducible deployment    | Noncompliant       | —                         | Docker omits publications          | Health/readiness partial  | No migrations      | Historical build/live tests      | README/audits             | OQ-005/OQ-006/OQ-010/OQ-012/OQ-025                         |

## Governance

| Requirement                   | Status                     | Frontend component                      | Backend service                | API endpoint          | Database model              | Test coverage                        | Documentation          | Outstanding blocker                                  |
| ----------------------------- | -------------------------- | --------------------------------------- | ------------------------------ | --------------------- | --------------------------- | ------------------------------------ | ---------------------- | ---------------------------------------------------- |
| GOV-001 Vertical completion   | Noncompliant               | Partial flows in `App.tsx`              | Partial route logic            | Partial learner APIs  | Unapplied adaptive DDL only | Historical unit/component/live tests | Project audit          | IAM, persistence, browser/manual verification        |
| GOV-002 No false completion   | Partial                    | Labels local/demo in several views      | Private grading boundary       | Existing APIs         | —                           | Historical privacy tests             | Audits                 | Metadata/simulation claims require continuing review |
| GOV-003 Truthful claims       | Noncompliant               | Brand says AI; generated social metrics | Health says deterministic demo | `/api/health`         | —                           | Sentinel tests                       | README/audits          | Real AI, adaptive persistence, credential evidence   |
| GOV-004 No fake data          | Noncompliant               | Generated rating and learner counts     | —                              | —                     | —                           | —                                    | Current-state audit    | Remove after approval                                |
| GOV-005 No dead interactions  | Partial                    | Core local buttons connected            | Core routes connected          | Existing learner APIs | Local/memory                | Historical component/live tests      | Cyber Range audit      | Institutional/admin routes absent                    |
| GOV-006 Question rule         | Implemented for takeover   | —                                       | —                              | —                     | —                           | —                                    | Open questions         | User decisions                                       |
| GOV-007 Dependency disclosure | Partial                    | —                                       | Only Node/env configuration    | —                     | —                           | —                                    | Open questions         | OQ-005 to OQ-012                                     |
| GOV-008 Evidence reporting    | Partial                    | —                                       | Structured request logs        | `/healthz`, `/readyz` | —                           | Historical reports                   | Audit documents        | Rerun current gates after changes                    |
| GOV-009 Safe dev accounts     | Missing                    | —                                       | —                              | —                     | —                           | —                                    | Requirements           | Implement approved production guard                  |
| GOV-010 Controlled process    | Implemented for audit only | —                                       | —                              | —                     | —                           | —                                    | Six takeover documents | Approval required                                    |

## Product definition

| Requirement                    | Status            | Frontend component                    | Backend service           | API endpoint              | Database model                | Test coverage                    | Documentation         | Outstanding blocker                              |
| ------------------------------ | ----------------- | ------------------------------------- | ------------------------- | ------------------------- | ----------------------------- | -------------------------------- | --------------------- | ------------------------------------------------ |
| PRD-001 Professional outcome   | Partial           | Lessons/labs/projects/portfolio       | Grading/verifier          | Checks/labs/projects APIs | Local evidence only           | Historical journeys              | Proposal/audits       | Implement approved Junior SOC profile            |
| PRD-002 Practice-first model   | Partial           | Course player, Labs, Portfolio        | Verifier/project gate     | Existing learner APIs     | Local                         | Component tests                  | Cyber Range audit     | Scenarios, durable evidence                      |
| PRD-003 Verified curriculum    | Partial           | `ContentBlocks`, verified overlay     | `content-repository.mjs`  | `/api/content/catalog`    | File publications             | Pipeline/repository tests        | Content docs          | Human review, 18/360                             |
| PRD-004 Adaptive subsystem     | Partial           | `AdaptivePanel`                       | `adaptive.mjs`            | `/api/adaptive/*`         | DDL architecture; local state | Adaptive tests                   | Adaptive architecture | Trusted persistence/instructor policy            |
| PRD-005 Sentinel subsystem     | Partial/demo      | `Mentor`                              | Client-only `sentinel.ts` | —                         | —                             | Sentinel tests                   | Mentor doc            | OQ-007/OQ-008; implement approved privacy policy |
| PRD-006 Cyber Range            | Partial           | `Labs`                                | Lab runtime/core          | `/api/labs*`              | Memory/local                  | Lab/runtime/component/live tests | Cyber Range audit     | OQ-017, persistence                              |
| PRD-007 Professional evidence  | Partial           | Portfolio/projects/reflections        | Formative project gate    | `/api/projects*`          | Local                         | Component/store tests            | Audits                | Durable reviewed evidence/completion record      |
| PRD-008 Career development     | Partial           | Tracks, career course, interview labs | —                         | Labs catalog only         | Local                         | Inventory/component tests        | README                | Durable plans/evaluation                         |
| PRD-009 Cyber intelligence     | Missing           | —                                     | —                         | —                         | —                             | —                                | Requirement only      | Long-term target; deferred from competition      |
| PRD-010 Institutional editions | Missing           | —                                     | —                         | —                         | —                             | —                                | Roadmap only          | Long-term target; tenant foundation only now     |
| PRD-011 Authoring/admin        | Architecture-only | —                                     | CLI pipeline              | CLI only                  | File workflow                 | Pipeline tests                   | Content docs          | OQ-015/IAM                                       |
| PRD-012 Commercial foundation  | Missing           | —                                     | —                         | —                         | —                             | —                                | Roadmap only          | Long-term target; billing deferred               |

## Curriculum and content

| Requirement                      | Status                         | Frontend component         | Backend service        | API endpoint               | Database model       | Test coverage            | Documentation        | Outstanding blocker                       |
| -------------------------------- | ------------------------------ | -------------------------- | ---------------------- | -------------------------- | -------------------- | ------------------------ | -------------------- | ----------------------------------------- |
| CUR-001 Seeded academy           | Implemented locally            | Home/Catalog/Course/Lesson | Seed + repository      | `/api/content/catalog`     | Files/JSON seed      | V1 inventory/live tests  | README/V1 audit      | Docker runtime content                    |
| CUR-002 18 courses               | Missing                        | Catalog has 12             | Seed has 12            | Catalog metadata indirect  | JSON seed has 12     | Inventory asserts 12     | Current-state audit  | Full-academy target; not competition gate |
| CUR-003 360 meaningful lessons   | Missing                        | 144 displayed              | 144 publications       | Catalog returns 144        | JSON seed            | Structural tests for 144 | Current-state audit  | Full-academy target; OQ-015 for review    |
| CUR-004 Complete course contract | Partial                        | Course/player/projects     | Publication types      | Multiple content APIs      | File artifacts       | V1/content tests         | Artifact contracts   | Missing exams/scenarios/depth             |
| CUR-005 Structured rendering     | Partial                        | `ContentBlocks`            | Safe lesson projection | `/api/content/catalog`     | File blocks          | ContentBlocks tests      | Artifact contracts   | Real browser/accessibility                |
| CUR-006 Authoritative evidence   | Partial                        | References rendered        | Pipeline/repository    | Catalog                    | File provenance      | Pipeline validation      | Ingestion/provenance | Human semantic review/freshness operation |
| CUR-007 Originality/licensing    | Partial                        | —                          | Pipeline metadata      | —                          | File provenance      | Validator only           | Provenance           | OQ-015; legal sampling                    |
| CUR-008 Review workflow          | Partial CLI                    | —                          | `content-pipeline.mjs` | —                          | File workflow        | Pipeline tests           | Ingestion pipeline   | IAM/CMS/OQ-015                            |
| CUR-009 AI draft boundary        | Implemented in pipeline policy | —                          | Pipeline gates         | —                          | Draft metadata       | Pipeline tests           | Authoring docs       | Authenticated CMS                         |
| CUR-010 Seed review truth        | Partial                        | Published content          | Baseline approval path | Catalog                    | Publication metadata | Repository tests         | README/audits        | OQ-015                                    |
| CUR-011 Quality validation       | Partial                        | —                          | Pipeline validator     | CLI                        | Schemas/files        | Pipeline/content tests   | Content docs         | Broken-link scheduling/human review       |
| CUR-012 Course-practice links    | Partial                        | Courses link ≥6 labs       | Seed/library           | Catalog/labs/projects APIs | Files                | V1 inventory test        | Cyber Range audit    | Objectives/scenarios/durable evidence     |

## Learner experience

| Requirement                        | Status                      | Frontend component               | Backend service               | API endpoint                    | Database model | Test coverage         | Documentation | Outstanding blocker                                  |
| ---------------------------------- | --------------------------- | -------------------------------- | ----------------------------- | ------------------------------- | -------------- | --------------------- | ------------- | ---------------------------------------------------- |
| LRN-001 Complete journey           | Partial                     | Core local learner pages         | Content/grading/labs/adaptive | Existing APIs                   | Local/memory   | Component/live tests  | V1 audit      | IAM, scenarios, instructor, credential               |
| LRN-002 Real dashboard             | Noncompliant for production | `Dashboard`, `AdaptivePanel`     | Recommendation only           | `/api/adaptive/recommendations` | Local          | App tests             | README        | Durable authorized data                              |
| LRN-003 Enrollment/progress        | Local only                  | Course/Lesson/Dashboard          | —                             | —                               | `localStorage` | Store/component tests | README        | Phase 1 persistence                                  |
| LRN-004 Course navigation          | Partial                     | State-based pages                | Content repo                  | Catalog                         | —              | App tests             | Project audit | Router/accessibility                                 |
| LRN-005 Failure/recovery           | Partial                     | Some loading/error text          | Generic 400/404               | Existing APIs                   | —              | Some tests            | Project audit | Typed errors/retries/offline                         |
| LRN-006 Credentials                | Missing                     | Local portfolio disclaimer       | —                             | —                               | —              | —                     | Audits        | Implement approved verified completion record        |
| LRN-007 Accessibility/localization | Partial                     | Semantic controls/responsive CSS | —                             | —                               | —              | DOM tests only        | Audits        | English/RTL-ready implementation; WCAG/browser audit |

## Assessment

| Requirement              | Status                        | Frontend component        | Backend service             | API endpoint        | Database model   | Test coverage         | Documentation       | Outstanding blocker      |
| ------------------------ | ----------------------------- | ------------------------- | --------------------------- | ------------------- | ---------------- | --------------------- | ------------------- | ------------------------ |
| ASM-001 Server bank      | Partial                       | Lesson check              | `gradeCheck` + publications | `/api/checks/grade` | File questions   | Core/repository tests | Artifact contracts  | Durable attempts/exams   |
| ASM-002 Assessment types | Missing except single choice  | LessonPage                | Single-choice only          | `/api/checks/grade` | —                | Single-choice tests   | Requirements        | Engine design            |
| ASM-003 Policies         | Missing                       | —                         | —                           | —                   | —                | —                     | Requirements        | Instructor/IAM/database  |
| ASM-004 No leakage       | Implemented for current route | Learner options only      | Safe projection/server key  | Grade/diagnostic    | Server files     | Privacy/live tests    | Threat model/audits | Reverify after new types |
| ASM-005 Durable evidence | Partial response only         | Updates local skill state | Evidence object response    | Grade/mastery       | DDL architecture | Core/adaptive tests   | Adaptive doc        | Database/IAM             |

## Adaptive learning

| Requirement                        | Status                  | Frontend component        | Backend service           | API endpoint            | Database model        | Test coverage            | Documentation         | Outstanding blocker                 |
| ---------------------------------- | ----------------------- | ------------------------- | ------------------------- | ----------------------- | --------------------- | ------------------------ | --------------------- | ----------------------------------- |
| ADP-001 Skill profile              | Partial                 | Dashboard recommendations | `adaptive.mjs`            | Mastery/recommendations | Skill DDL + local     | Adaptive/store tests     | Adaptive architecture | Durable trusted profile             |
| ADP-002 Evidence inputs            | Partial                 | Checks/labs/projects      | Mastery calculator        | `/api/adaptive/mastery` | Evidence DDL          | Adaptive tests           | Adaptive doc          | Scenarios/exams/rubrics/persistence |
| ADP-003 Recommendation behavior    | Partial                 | `AdaptivePanel`           | Recommendation rules      | Recommendations         | Recommendation DDL    | Adaptive tests           | Adaptive doc          | Durable review/variants             |
| ADP-004 Network/Linux profile      | Logic implemented       | Recommendation cards      | Rules                     | Recommendations         | —                     | Adaptive acceptance test | Adaptive doc          | End-to-end authenticated evidence   |
| ADP-005 Fixed curriculum           | Implemented locally     | Full catalog available    | Verified pool selection   | Catalog/recommendations | Files                 | Adaptive/content tests   | Adaptive doc          | Authenticated production            |
| ADP-006 Learner/instructor control | Partial learner dismiss | Dismiss button            | Instructor policy ignored | Recommendations         | Instructor policy DDL | Dismiss/rule tests       | Adaptive doc          | IAM/instructor UI                   |
| ADP-007 Decision logs              | Memory only             | —                         | Bounded decision log      | Recommendations         | Decision-log DDL      | Adaptive tests           | Adaptive doc          | Durable tenant storage              |
| ADP-008 Evaluation                 | Partial historical      | —                         | Rule profiles             | —                       | —                     | Adaptive tests           | Adaptive doc          | Real learner/pilot evaluation       |

## Sentinel and AI

| Requirement                    | Status                         | Frontend component    | Backend service           | API endpoint | Database model  | Test coverage            | Documentation       | Outstanding blocker                                 |
| ------------------------------ | ------------------------------ | --------------------- | ------------------------- | ------------ | --------------- | ------------------------ | ------------------- | --------------------------------------------------- |
| AI-001 Real AI boundary        | Current live AI missing        | `Mentor` labeled demo | Client deterministic code | —            | —               | Sentinel tests           | README/mentor doc   | OQ-007                                              |
| AI-002 Grounded retrieval      | Missing; lesson selection only | Mentor lesson context | —                         | —            | —               | Context tests            | Mentor doc          | OQ-007/OQ-008                                       |
| AI-003 Citation validity       | Partial stored citations       | Mentor links          | Publication references    | Catalog only | File references | Pipeline tests           | Content docs        | Retrieval/entailment evaluation                     |
| AI-004 Safe mentor             | Partial deterministic          | Mentor                | Regex rules client-side   | —            | —               | 54-case historical suite | Threat model        | Server policy/live model                            |
| AI-005 Prompt/data security    | Missing production boundary    | Client regex          | —                         | —            | —               | Deterministic tests      | Threat model        | Implement approved retention/consent policy and IAM |
| AI-006 Reliability controls    | Missing                        | —                     | —                         | —            | —               | —                        | Architecture target | OQ-007/OQ-012                                       |
| AI-007 Human content authority | Pipeline policy implemented    | —                     | Content gates             | —            | Files           | Pipeline tests           | Authoring docs      | Authenticated CMS                                   |
| AI-008 AI evaluation           | Partial deterministic only     | —                     | —                         | —            | —               | Sentinel eval tests      | Proposal/mentor doc | OQ-021/model adapter                                |

## Cyber Range

| Requirement                      | Status                             | Frontend component | Backend service             | API endpoint          | Database model | Test coverage                | Documentation      | Outstanding blocker                    |
| -------------------------------- | ---------------------------------- | ------------------ | --------------------------- | --------------------- | -------------- | ---------------------------- | ------------------ | -------------------------------------- |
| LAB-001 Discovery                | Partial                            | `Labs`             | Public lab projection       | `/api/labs`           | Files/local    | Component/inventory tests    | Cyber Range audit  | More filters/durable completion        |
| LAB-002 Minimum library          | Partial                            | 80 visible         | 80 publications             | `/api/labs`           | Files          | V1 inventory tests           | Cyber Range audit  | Isolated interactive definition/OQ-017 |
| LAB-003 Complete contract        | Implemented structurally           | Lab details        | Projection/private verifier | Labs APIs             | Files          | Schema/inventory tests       | Artifact contracts | Human review/persistence               |
| LAB-004 Lifecycle                | Memory only                        | Launch/actions     | `lab-runtime.mjs`           | Launch/session/action | Memory         | Runtime/live tests           | Cyber Range audit  | Durable worker/environment             |
| LAB-005 Verification/persistence | Partial                            | Submit/feedback    | `verifyLab`                 | `/api/labs/verify`    | Memory/local   | Core/runtime/component tests | Cyber Range audit  | Database/IAM                           |
| LAB-006 Isolation                | Missing executable runtime         | Simulation labels  | —                           | —                     | —              | Safety metadata tests        | Threat model       | OQ-017                                 |
| LAB-007 Authorized targets       | Implemented for current activities | No target input    | Fixed definitions           | Labs APIs             | Files          | Inventory/source review      | Cyber Range audit  | Reverify executable adapters           |
| LAB-008 Defensive completeness   | Partial/structural                 | Debrief/reflection | Published fields            | `/api/labs`           | Files          | Inventory validation         | Cyber Range audit  | Human SME review                       |
| LAB-009 Environment proof        | Missing                            | —                  | —                           | —                     | —              | —                            | Requirement only   | OQ-017/Docker capability               |
| LAB-010 Instructor/admin         | Missing                            | —                  | —                           | —                     | —              | —                            | Roadmap            | IAM/Phase 5                            |

## Evidence, scenarios, projects, and career

| Requirement                  | Status                     | Frontend component                  | Backend service      | API endpoint     | Database model | Test coverage             | Documentation      | Outstanding blocker                           |
| ---------------------------- | -------------------------- | ----------------------------------- | -------------------- | ---------------- | -------------- | ------------------------- | ------------------ | --------------------------------------------- |
| EVD-001 Workplace scenarios  | Missing runtime            | Some scenario text in projects/labs | —                    | —                | —              | —                         | Requirements       | Scenario engine/content review                |
| EVD-002 Complete projects    | Partial                    | `Portfolio`                         | Formative assessment | `/api/projects*` | Files/local    | Core/component tests      | V1 audit           | Files/instructor/durable submission           |
| EVD-003 Rubrics/human review | Partial published criteria | Rubric display                      | Returns rubric       | Projects APIs    | Files          | Inventory/core tests      | Artifact contracts | IAM/reviewer workflow                         |
| EVD-004 Portfolio evidence   | Local only                 | Portfolio/reflections               | —                    | —                | localStorage   | Store/component tests     | Audits             | IAM/database/completion record implementation |
| EVD-005 Career readiness     | Partial                    | Tracks/course/interview labs        | —                    | Labs only        | Local          | Inventory/component tests | Proposal           | Implement Junior SOC readiness evidence       |

## Institutional and audience editions

| Requirement             | Status                  | Frontend component | Backend service | API endpoint | Database model  | Test coverage   | Documentation     | Outstanding blocker                                  |
| ----------------------- | ----------------------- | ------------------ | --------------- | ------------ | --------------- | --------------- | ----------------- | ---------------------------------------------------- |
| ORG-001 University      | Missing                 | —                  | —               | —            | —               | —               | Roadmap           | Long-term target; tenant foundation only             |
| ORG-002 Enterprise      | Missing                 | —                  | —               | —            | —               | —               | Roadmap           | Long-term target; billing deferred                   |
| ORG-003 Instructor      | Missing                 | —                  | —               | —            | Policy DDL only | —               | Adaptive doc      | IAM/database                                         |
| ORG-004 Awareness       | Partial activities only | Awareness labs     | Lab catalog     | `/api/labs`  | Files/local     | Inventory tests | Cyber Range audit | Campaign/admin/consent                               |
| ORG-005 Student Academy | Missing as edition      | General learner UI | —               | —            | —               | —               | Requirements      | Scope decision                                       |
| ORG-006 Kids Academy    | Missing/deferred        | —                  | —               | —            | —               | —               | Requirement only  | Long-term target pending child-safety/legal approval |

## Identity, authorization, and privacy

| Requirement                         | Status                    | Frontend component           | Backend service       | API endpoint | Database model        | Test coverage            | Documentation         | Outstanding blocker                          |
| ----------------------------------- | ------------------------- | ---------------------------- | --------------------- | ------------ | --------------------- | ------------------------ | --------------------- | -------------------------------------------- |
| IAM-001 Account lifecycle           | Missing                   | —                            | —                     | —            | —                     | —                        | Requirements          | Implement approved first-party IAM; OQ-005   |
| IAM-002 Credential/session security | Missing                   | —                            | —                     | —            | —                     | —                        | Threat model          | Implement approved Argon2id/session controls |
| IAM-003 Roles                       | Missing                   | —                            | —                     | —            | —                     | —                        | Requirements          | Implement approved membership/RBAC model     |
| IAM-004 Server authorization        | Missing                   | Hidden controls not security | Guest check only      | Lab APIs     | —                     | Guest mismatch test      | Threat model          | IAM implementation                           |
| IAM-005 Tenant isolation            | Missing                   | —                            | —                     | —            | Adaptive columns only | —                        | Threat model          | Implement approved personal-tenant model     |
| IAM-006 Privacy rights              | Missing production        | Local privacy disclaimer     | —                     | —            | —                     | —                        | Threat model/proposal | Implement approved privacy/deletion controls |
| IAM-007 Development email           | Missing                   | —                            | —                     | —            | —                     | —                        | Requirements          | OQ-005                                       |
| IAM-008 Privilege testing           | Missing meaningful domain | —                            | Guest ownership check | Lab APIs     | —                     | One cross-owner lab test | Audit                 | IAM/tenancy                                  |

## Data and infrastructure

| Requirement              | Status                     | Frontend component  | Backend service | API endpoint            | Database model      | Test coverage        | Documentation        | Outstanding blocker          |
| ------------------------ | -------------------------- | ------------------- | --------------- | ----------------------- | ------------------- | -------------------- | -------------------- | ---------------------------- |
| DAT-001 Approved stack   | Architecture-only/conflict | —                   | Node current    | —                       | One SQL file        | DDL inspection only  | System/project audit | OQ-002                       |
| DAT-002 Durable model    | Missing                    | Browser local state | Memory/files    | Existing stateless APIs | Adaptive subset DDL | Store tests only     | Project audit        | OQ-002/OQ-004                |
| DAT-003 Migrations/seeds | Partial files only         | —                   | Seed script     | —                       | SQL + JSON seed     | Seed inventory tests | README               | Database runner/dev accounts |
| DAT-004 File storage     | Missing                    | —                   | —               | —                       | —                   | —                    | Requirement only     | OQ-010                       |
| DAT-005 Background jobs  | Missing                    | —                   | —               | —                       | —                   | —                    | Roadmap              | OQ-011                       |
| DAT-006 Backup/recovery  | Missing                    | —                   | —               | —                       | —                   | —                    | Runbook target       | OQ-006/OQ-010                |

## API, security, operations, and deployment

| Requirement                    | Status                      | Frontend component   | Backend service       | API endpoint          | Database model      | Test coverage                       | Documentation | Outstanding blocker              |
| ------------------------------ | --------------------------- | -------------------- | --------------------- | --------------------- | ------------------- | ----------------------------------- | ------------- | -------------------------------- |
| OPS-001 API design             | Partial                     | Direct fetch calls   | One HTTP handler      | 14 route behaviors    | —                   | Core/integration tests              | Project audit | Shared schemas/layers            |
| OPS-002 Headers/transport      | Partial local               | —                    | Security headers      | All responses         | —                   | Core/live tests                     | Threat model  | TLS/HSTS/CSP hardening           |
| OPS-003 Abuse controls         | Partial memory              | —                    | IP limiter/body limit | All requests          | —                   | Historical rate/body tests          | Audit         | Distributed/proxy-aware controls |
| OPS-004 Secrets                | Partial/no active secrets   | —                    | Env host/port only    | —                     | —                   | Source scan                         | Threat model  | Provider/secret manager          |
| OPS-005 Observability          | Partial stdout logs         | —                    | Request logs          | —                     | Memory decision log | Log inspection                      | Runbook       | OQ-012                           |
| OPS-006 Health/readiness       | Noncompliant readiness      | —                    | Always-ready handlers | `/healthz`, `/readyz` | —                   | Historical status checks            | Runbook       | Dependency checks                |
| OPS-007 Deployment             | Noncompliant Docker content | Frontend build       | Node runtime          | Port 8080             | —                   | Build historical; Docker unverified | Project audit | OQ-006; copy content             |
| OPS-008 Scalability            | Missing                     | —                    | Process-local state   | Unpaginated APIs      | —                   | —                                   | Project audit | Database/cache/queue/workers     |
| OPS-009 Performance            | Unmeasured/partial          | Full startup catalog | File cache            | Content APIs          | —                   | Build size only                     | Project audit | Budgets/load tests/pagination    |
| OPS-010 Commercial enforcement | Missing                     | —                    | —                     | —                     | —                   | —                                   | Roadmap       | OQ-013                           |

## UI and experience

| Requirement                         | Status               | Frontend component      | Backend service    | API endpoint  | Database model | Test coverage             | Documentation | Outstanding blocker           |
| ----------------------------------- | -------------------- | ----------------------- | ------------------ | ------------- | -------------- | ------------------------- | ------------- | ----------------------------- |
| UX-001 Professional/truthful design | Noncompliant metrics | Whole app               | —                  | —             | —              | Visual DOM only           | Project audit | Remove generated social proof |
| UX-002 Stable routing               | Missing              | State-based `Page`      | —                  | —             | —              | App navigation tests only | Project audit | Router/refactor               |
| UX-003 Responsive/accessibility     | Partial              | CSS/semantic controls   | —                  | —             | —              | DOM tests                 | Audits        | Real browser/WCAG target      |
| UX-004 Honest degraded states       | Partial              | Some errors/disclaimers | Generic API errors | Existing APIs | —              | Some component tests      | README        | Typed recovery/ready state    |
| UX-005 Themes/i18n                  | Missing              | —                       | —                  | —             | —              | —                         | Requirements  | OQ-022                        |

## Quality and release evidence

| Requirement               | Status             | Frontend component   | Backend service        | API endpoint    | Database model   | Test coverage                       | Documentation       | Outstanding blocker                   |
| ------------------------- | ------------------ | -------------------- | ---------------------- | --------------- | ---------------- | ----------------------------------- | ------------------- | ------------------------------------- |
| QA-001 Test layers        | Partial            | Component/unit tests | Unit/integration tests | Live verifier   | No DB/worker/E2E | 108 historical tests                | Audits              | Missing domains                       |
| QA-002 Real browser       | Missing            | —                    | —                      | —               | —                | No available browser in prior audit | Audits              | Browser environment                   |
| QA-003 Course/lab matrix  | Partial            | —                    | Inventory validator    | —               | Files            | V1 academy tests                    | Cyber Range audit   | 18/360/executable/persistence         |
| QA-004 Security tests     | Partial            | Sentinel/client      | Core/lab tests         | Existing APIs   | —                | Privacy/origin/rate/guest tests     | Threat model        | IAM/tenant/upload/lab escape          |
| QA-005 Static/build gates | Historical pass    | —                    | —                      | —               | —                | Format/lint/type/build/audit        | Audits/CI           | Rerun after implementation; SBOM      |
| QA-006 Runtime inspection | Partial historical | Web root             | API logs               | Existing routes | —                | Live verifier                       | Audits              | Worker/DB/browser/lab logs            |
| QA-007 Evidence report    | Partial            | —                    | —                      | —               | —                | Historical report                   | Audit docs          | Current full-stack evidence           |
| QA-008 Release threshold  | Not met            | —                    | —                      | —               | —                | —                                   | Current-state audit | Critical IAM/data/deployment blockers |

## Proposal and fellowship evaluation

| Requirement                          | Status                | Frontend component | Backend service  | API endpoint  | Database model | Test coverage       | Documentation           | Outstanding blocker         |
| ------------------------------------ | --------------------- | ------------------ | ---------------- | ------------- | -------------- | ------------------- | ----------------------- | --------------------------- |
| RES-001 Lebanon impact               | Proposal only         | General learner UI | —                | —             | —              | —                   | Approved proposal       | Pilot/recruitment           |
| RES-002 Responsible model scope      | Partial truthfulness  | Demo Mentor        | No model         | —             | —              | Deterministic tests | Proposal                | OQ-007/OQ-008               |
| RES-003 Public sources/data          | Partial               | References         | Content pipeline | Catalog       | Source files   | Pipeline tests      | Content docs/proposal   | Dataset use/evaluation plan |
| RES-004 Learning evaluation          | Missing               | —                  | —                | —             | —              | —                   | Proposal                | OQ-021/OQ-023               |
| RES-005 AI/recommendation evaluation | Partial deterministic | Adaptive cards     | Rule engine      | Adaptive APIs | Memory/local   | Rule/Sentinel tests | Proposal                | Live RAG/pilot              |
| RES-006 Ethics/documentation         | Partial documentation | —                  | —                | —             | —              | —                   | Proposal/open questions | OQ-009/OQ-014/OQ-021        |

## Coverage summary

| Status class                | Interpretation                                                                                                                                |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| Strongest current coverage  | Local seeded curriculum delivery, content validation, private single-choice grading, deterministic adaptation logic, safe bounded simulations |
| Partial but not production  | Learner progress, recommendations, lab lifecycle, projects, portfolio, Sentinel                                                               |
| Architecture-only           | Adaptive PostgreSQL subset, future commercial/system diagrams                                                                                 |
| Missing critical boundaries | Authentication, RBAC, tenancy, durable persistence, email, uploads, workers, observability, real RAG, executable isolation                    |
| Blocked by decisions        | Backend migration, providers, hosting, legal/privacy, reviewers, credentials, languages, pilot ethics                                         |

## 2026-07-30 Junior SOC learning milestone addendum

Only requirements changed by this milestone are superseded by this addendum; untouched historical rows above remain audit history.

| Requirement               | Current milestone evidence                                                                                                                                                                           | Status / limitation                                                                                                            |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| REL-003, LRN-003, DAT-002 | FastAPI enrollment, lesson progress, notes, bookmarks, activity attempts, assessment results, skill evidence, recommendations, and pathway completion; SQLAlchemy models and Alembic `20260730_0002` | Implemented for the Junior SOC pathway in the local trusted stack; production PostgreSQL restart verification remains required |
| REL-005, LRN-001, LRN-002 | `soc_pathway.py`; authenticated pathway/module/lesson/practice/assessment routes                                                                                                                     | Implemented as an eight-module private-beta sequence; external review pending                                                  |
| CUR-005, CUR-006          | Structured lesson fields and consistent authoritative source metadata                                                                                                                                | Implemented for the eight required pathway lessons; not a claim about the full academy target                                  |
| ASM-001 through ASM-004   | Server-private grading rules, deterministic and partial grading, retained/idempotent attempts, feedback, retakes, tenant filters                                                                     | Implemented for pathway practice and module assessments                                                                        |
| ADP-001 through ADP-004   | Existing skill graph reused; pathway evidence updates bounded mastery and triggers reasoned recommendations; repeated failure/increasing independence rules                                          | Implemented deterministically; learner-pilot evaluation pending                                                                |
| UX-002, UX-003, UX-004    | Stable Wouter deep links, loading/error/retry/empty states, semantic forms, existing responsive shell                                                                                                | Implemented for new pathway routes; final real-browser/mobile evidence pending                                                 |
| QA-001, QA-003, QA-005    | Focused backend pathway tests, extended 488-publication validation, TypeScript and strict Python checks                                                                                              | Current exact results recorded in `docs/competition/LEARNING_VERIFICATION.md` after final run                                  |

# Multi-organization portals milestone (2026-07-30)

| Requirement                           | Implemented evidence                                                                                     |
| ------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Explicit tenant roles and permissions | `ROLE_PERMISSIONS`, permission joins, `assert_permission`, role/tenant security tests                    |
| Organization switching and membership | Session active organization, protected activation, cache clearing, membership history                    |
| Secure invitations                    | Hashed token, expiry, intended email, role binding, accept/reject/cancel/resend, audit                   |
| Programmes and cohorts                | Tenant models/API, staff, enrolment, curriculum versions, archive behavior                               |
| Assignments and human review          | Version-pinned assignments, learner links, immutable revisions, review state/history                     |
| Instructor/university/company portals | Shared portal shell, role routes, real dashboards, cohorts, assignments, reviews, reports                |
| Learner-controlled recruiter sharing  | Hashed expiring/revocable shares, selected evidence, preview, public verification, access log            |
| Analytics and reports                 | Persisted aggregate calculations, definitions/limitations, permission-gated CSV, audit                   |
| Notifications and audit               | Tenant/user notifications and security/academic audit events                                             |
| Privacy and isolation                 | Server filters, inactive membership denial, foreign share/object denial, excluded private notes/Sentinel |
