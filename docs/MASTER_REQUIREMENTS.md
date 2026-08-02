# CyberMentor AI Master Requirements

**Status:** Governing requirement registry  
**Created:** 2026-07-28  
**Implementation authorization:** None. Audit and planning only.

## 1. Purpose

This document normalizes the approved CyberMentor AI proposal, product directives, safety rules, prior requirement attachments, current takeover instructions, and verified repository constraints into stable requirement IDs.

The IDs in this document are the canonical keys used by:

- [CURRENT_STATE_AUDIT.md](CURRENT_STATE_AUDIT.md)
- [IMPLEMENTATION_ROADMAP.md](IMPLEMENTATION_ROADMAP.md)
- [DECISION_LOG.md](DECISION_LOG.md)
- [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)
- [TRACEABILITY_MATRIX.md](TRACEABILITY_MATRIX.md)

Requirements are grouped when several source bullets describe one inseparable vertical capability. A grouped requirement is satisfied only when all behavior stated in that requirement is satisfied.

## 2. Authority and precedence

When sources disagree, use this order:

1. explicit instructions in the latest user message;
2. explicit later overrides in the final integration and content/lab directives;
3. the approved CyberMentor AI proposal;
4. earlier approved product requirements;
5. current executable repository evidence for implementation status;
6. latest verified audits;
7. older audits and architecture documents as historical evidence only.

Implementation evidence cannot cancel an approved requirement. It can only show that the requirement is unimplemented, partial, or contradicted.

Historical statements such as “zero publications” are superseded by the current 488-record manifest. Conversely, a seeded publication status does not prove independent human review, production persistence, or professional credential validity.

## 3. Release profiles

Requirement approval and release gating are separate. A requirement may remain an approved product target without blocking the competition release.

### 3.1 Competition/private-beta release

The competition release is a **private single-organization beta built on tenant-aware foundations**. It proves one complete, production-oriented Junior SOC Analyst learner vertical slice. It is not a public commercial release and must not be represented as one.

| ID      | Competition release requirement                                                                                                                                                                                                                                               |
| ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| REL-001 | Operate as a controlled private single-organization beta while implementing tenant-aware data and authorization boundaries that do not require a later tenancy rewrite.                                                                                                       |
| REL-002 | Provide authenticated learner registration, verified email identity, secure first-party Argon2id credentials, secure server-side sessions, and account recovery.                                                                                                              |
| REL-003 | Persist learner identity, enrollment, progress, attempts, evidence, recommendations, mentor state, and completion data durably in PostgreSQL.                                                                                                                                 |
| REL-004 | Give every learner a personal tenant and enforce active-organization membership and role permissions server-side using a many-to-many membership model.                                                                                                                       |
| REL-005 | Deliver one coherent Junior SOC Analyst Readiness path with explicit prerequisite, skill, independence, recency, and evidence criteria.                                                                                                                                       |
| REL-006 | Include one diagnostic that produces a personalized roadmap grounded in the approved SOC readiness profile.                                                                                                                                                                   |
| REL-007 | Include one deeply reviewed foundational course whose content, references, commands, assessments, practice, accessibility, licensing, and safety have accountable review.                                                                                                     |
| REL-008 | Connect the course to several meaningful guided and independent practice activities rather than isolated cards or decorative completion.                                                                                                                                      |
| REL-009 | Include one flagship original workplace SOC mission with business context, realistic evidence, decision points, verification, debrief, and portfolio outcomes.                                                                                                                |
| REL-010 | Capture authorized learner actions, mistakes, retries, hints, and relevant decisions as trusted evidence without biometric or emotional surveillance.                                                                                                                         |
| REL-011 | Adapt prerequisite remediation, scaffolding, hint depth, and learning mode using trusted evidence while leaving official curriculum unchanged.                                                                                                                                |
| REL-012 | Operate a server-side, grounded, safety-controlled, evaluated Sentinel Mentor through an approved live model and provide a truthful deterministic fallback for missing keys, timeouts, outages, or budget limits.                                                             |
| REL-013 | Produce an evidence-based learner skill profile that distinguishes observed performance from inference and records confidence, recency, independence, and provenance.                                                                                                         |
| REL-014 | Provide an investigation replay that lets the learner and authorized reviewer inspect the mission timeline, decisions, mistakes, evidence, feedback, and remediation.                                                                                                         |
| REL-015 | Include one reviewed professional SOC project with a versioned rubric, submission, feedback, reflection, and evidence outcome.                                                                                                                                                |
| REL-016 | Issue one publicly verifiable, revocable **CyberMentor Verified Completion Record** containing the completed course or mission, evidence and skill areas evaluated, issue date, verification ID, and criteria version. It must not be described as an industry certification. |
| REL-017 | Provide a polished responsive interface with complete loading/error states, keyboard operation, accessible names, focus behavior, contrast, reduced-motion support, and no launch-critical dead interactions.                                                                 |
| REL-018 | Execute and document safety, authorization, prompt-injection, leakage, retrieval/citation, fallback, accessibility, security, and AI quality evaluations for the release slice.                                                                                               |
| REL-019 | Conduct a small, explicitly consented Lebanese learner pilot only after teaching-team/ethics approval, with minimal data collection and truthful limitations.                                                                                                                 |
| REL-020 | Provide reproducible local, test/CI, and private-beta deployment documentation, migrations, seeds, health checks, backup/restore procedures, and evidence for the exact released revision.                                                                                    |

### 3.2 Full academy target

The full academy remains an approved target, but it is not a competition release gate. It includes the 18-course catalog, at least 360 reviewed lessons, the complete course contracts, at least 80 reviewed practical activities, broader assessments, full authoring/review workflows, and role pathways beyond Junior SOC Analyst. Existing seeded content may be retained as baseline or draft material, but it must not be represented as independently reviewed commercial content until the review record proves that claim.

### 3.3 Long-term company target

University, enterprise, security-awareness, Kids Academy, commercial billing, public recruiter discovery, multilingual publication, a public hostile-workload cyber range, and comprehensive cyber-intelligence/news remain approved long-term targets. They are not competition release blockers. Each becomes a release gate only when promoted into an explicitly approved later release profile.

### 3.4 Scope interpretation

- “Required,” “must,” and numeric catalog targets remain normative for their assigned release profile.
- Deferral from the competition release is not rejection or removal.
- Competition claims must describe only the verified private-beta slice.
- Shared foundations must avoid knowingly blocking the approved full-academy and company targets.

## 4. Status vocabulary

| Status              | Meaning                                                                                                                                                            |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Implemented         | Current frontend, backend, persistence, authorization, validation, tests, documentation, production configuration, and manual verification satisfy the requirement |
| Partial             | Some required behavior exists, but the definition of done is not met                                                                                               |
| Architecture-only   | A schema or document exists without an operating vertical feature                                                                                                  |
| Missing             | No meaningful implementation exists                                                                                                                                |
| Blocked             | Implementation requires an unresolved product, provider, legal, security, or deployment decision                                                                   |
| Noncompliant        | Current behavior contradicts the approved requirement                                                                                                              |
| Historical evidence | Previously executed evidence; not reverified in this audit                                                                                                         |

## 5. Definition of done

### GOV-001 — Vertical feature completion

A feature is complete only when frontend behavior, backend behavior, durable persistence, server-side authorization, validation, loading and error states, accessibility, critical tests, documentation, production configuration, and manual verification all exist without unresolved console or server errors.

### GOV-002 — No false completion

Metadata, documentation, cards, routes, mocked tests, client-only state, or architecture diagrams do not constitute completion. No test may be disabled, acceptance threshold lowered, or error hidden to create a passing result.

### GOV-003 — Truthful claims

“AI-powered,” “adaptive,” “verified,” “production-ready,” “job-ready,” “professional readiness,” “credential,” and similar claims require implementation evidence. Simulations, local modes, seeded review metadata, and deterministic rules must be labeled accurately.

### GOV-004 — No fake product data

The product must not display invented learners, ratings, progress, partners, employers, testimonials, certifications, success rates, or operational metrics as real data.

### GOV-005 — No dead launch-critical interactions

Launch-critical pages must contain no placeholder behavior, nonfunctional buttons, “coming soon” substitutes, empty destination pages, or silent failures.

### GOV-006 — Question and blocker rule

Before implementation, inspect whether required product, security, infrastructure, data, content, provider, legal, and deployment details are available. Stop only the affected work, document the missing decision and options, recommend one option, and ask a precise question.

### GOV-007 — External dependency disclosure

Every external service must identify credentials/accounts, production provider, local adapter, data flow, privacy boundary, cost, failure mode, and configuration. A local adapter must not be represented as a production integration.

### GOV-008 — Evidence-only reporting

Commands, URLs, counts, accounts, migrations, tests, builds, browser checks, provider integrations, and deployment status may be reported as verified only when evidence exists for the current relevant version.

### GOV-009 — Safe development accounts

Development accounts may exist only for non-production environments, must be clearly labeled, and must be impossible to enable automatically in production. Production must not ship demo credentials.

### GOV-010 — Controlled implementation process

Every phase must audit, classify retained/refactored/removed/rebuilt work, plan, identify blockers, receive required answers, implement, run checks, manually verify, self-audit, update documentation, and report changes. This takeover stops after documentation until explicit approval.

## 6. Product definition

### PRD-001 — Professional-development outcome

CyberMentor AI must close the gap between understanding theory, selecting an appropriate action, completing practical work independently, and producing credible professional evidence.

### PRD-002 — Practice-first learning model

The learning flow must connect theory, worked examples, mini-practice, guided labs, knowledge checks, scenarios, independent labs, capstones, reflection, and portfolio evidence. Learners should spend more time practicing than passively reading.

### PRD-003 — Verified curriculum subsystem

Official curriculum must remain a stored, versioned, reviewed, cited, and published subsystem separate from AI, adaptation, and lab runtime behavior.

### PRD-004 — Adaptive subsystem

Skill modeling, prerequisite intervention, difficulty selection, hint timing, review scheduling, and recommendations must operate in the background and must not rewrite official curriculum.

### PRD-005 — Sentinel subsystem

Sentinel must be a grounded cybersecurity mentor separate from official curriculum, assessment authority, and lab control. It may explain, guide, retrieve, cite, review safe artifacts, and recommend approved learning.

### PRD-006 — Cyber Range subsystem

The Cyber Range must be a first-class practical platform with safe, authorized, isolated or accurately labeled simulated activities, server-side verification, evidence, attempts, and lifecycle controls.

### PRD-007 — Professional evidence subsystem

Projects, scenarios, labs, rubrics, reflections, feedback, and verified completion records must build a credible learner portfolio without overstating identity assurance or employer recognition.

### PRD-008 — Career development

The product must support role roadmaps, skill-gap analysis, interview practice, resume/project evidence, report feedback, and career readiness.

### PRD-009 — Cyber intelligence

The target product includes cited cybersecurity news, vulnerability intelligence, remediation context, source freshness, and safe links to authoritative records.

### PRD-010 — Institutional editions

The target product includes university, instructor/cohort, enterprise employee-training, security-awareness, student, and age-appropriate Kids Cyber Safety experiences with appropriate privacy and authorization boundaries.

### PRD-011 — Authoring and administration

The target product includes authenticated content authoring/review, organization administration, platform administration, audit history, and safe publication controls.

### PRD-012 — Commercial foundation

Subscriptions, billing, plans, quotas, entitlements, organization ownership, and production operations must be real and server-enforced before commercialization.

## 7. Curriculum and content

### CUR-001 — Non-empty seeded academy

A normal install and seed must provide a usable published academy without manual publication.

### CUR-002 — Required 18-course catalog

The final approved catalog contains:

1. Cybersecurity Foundations
2. Networking for Cybersecurity
3. Linux for Cybersecurity Professionals
4. Windows Security Foundations
5. Python for Cybersecurity
6. SOC Analyst Foundations
7. SIEM and Log Analysis
8. Incident Response Foundations
9. Digital Forensics Foundations
10. Ethical Hacking and Penetration Testing Foundations
11. Web Application Security
12. API Security Foundations
13. Active Directory Security Foundations
14. Cloud Security Foundations
15. DevSecOps and Container Security
16. Threat Intelligence and Threat Hunting
17. AI and LLM Security
18. Cybersecurity Career and Interview Preparation

### CUR-003 — Required depth

The approved final override requires 18 complete courses with at least 20 meaningful lessons per course, producing at least 360 non-duplicative lessons. Each course requires substantial major learning paths rather than title-swapped templates.

### CUR-004 — Complete course contract

Each course must include overview, audience, prerequisites, outcomes, difficulty, duration, modules, substantial lessons, structured visuals, examples, checks, module quizzes, practical exercises, labs, scenarios, a course project, rubric, references, final assessment, and completion criteria.

### CUR-005 — Structured content rendering

Lessons must render from structured content supporting objectives, headings, definitions, diagrams, images with alternative text, examples, code, terminal output, packets, logs, warnings, misconceptions, glossary, checks, practice, labs, projects, references, and summaries.

### CUR-006 — Authoritative evidence

Published technical content must identify authoritative sources, publisher, URL, retrieval date, source version when known, verification date, review state, content version, and freshness interval. Unsupported details must be omitted or labeled unverified.

### CUR-007 — Originality and licensing

Content must be original synthesis, must not copy proprietary commercial courses or certification questions, must use short compliant excerpts, and must receive licensing/provenance review.

### CUR-008 — Content workflow

Future content must move through draft, technical review, instructional review, accessibility review, licensing review, conditional safety review, approval, and authorized publication with version history, diff, preview, validation, and rollback.

### CUR-009 — AI-assisted draft boundary

AI may assist bounded editing or ideation only with explicit disclosure. It cannot act as source, reviewer, or publisher, and cannot autonomously publish cybersecurity content.

### CUR-010 — Seeded Version 1 review truth

Seeded Version 1 content may use explicit initial-release metadata and be visible locally, but must not claim external expert certification. Accountable human SME review remains required before commercial release.

### CUR-011 — Quality validation

Automated content gates must cover schema, required metadata, references, broken links, freshness, terminology, commands, safety, originality/licensing evidence, review approvals, duplicate boilerplate, routes, and publication integrity.

### CUR-012 — Course-to-practice integration

Every major course must link its objectives and skills to relevant checks, labs, scenarios, projects, rubrics, completion rules, and portfolio evidence.

## 8. Learner experience

### LRN-001 — Complete learner journey

The target journey is registration, email verification, goals, diagnostic, skill profile, career track, enrollment, lessons, practice, quizzes, labs, adaptive support, scenarios, projects, evaluation, skill evidence, credential, and portfolio.

### LRN-002 — Real learner dashboard

Dashboard data must come from authorized durable backend records and include track, courses, goals, recommendations, weak/strong skills, confidence, assignments, labs, projects, credentials, history, time, and recommendation reasons.

### LRN-003 — Enrollment and progress

Enrollment, lesson completion, attempts, time, notes, bookmarks, recommendations, and completion state must persist durably for authenticated learners.

### LRN-004 — Course-player navigation

The player must provide stable routes, module/lesson navigation, previous/next actions, progress, bookmarks, notes, references, practice and lab launches, project milestones, Ask Sentinel, responsive behavior, and keyboard accessibility.

### LRN-005 — Loading, failure, and recovery

Every learner workflow must expose accurate loading, empty, error, retry, expiration, offline/degraded, and recovery states without silently falling back to misleading content.

### LRN-006 — Credentials and certificates

Completion credentials must derive from server-enforced completion criteria and identity-bound evidence. Verification, revocation, versioning, and public/private portfolio controls are required.

### LRN-007 — Accessibility and localization

The product must meet an approved WCAG target, support keyboard/screen-reader/mobile use, and be architected for English, Arabic/RTL, and French if those languages remain in scope.

## 9. Assessment

### ASM-001 — Server-owned assessment bank

Question definitions, versions, keys, scoring logic, explanations, attempts, and audit history must remain server-side and be associated with objectives, skills, difficulty, and content versions.

### ASM-002 — Assessment types

The engine must support single choice, multiple choice, true/false, matching, ordering, short answer, fill-in, command interpretation, log/packet analysis, code review, scenario decisions, and file evidence.

### ASM-003 — Assessment policies

The engine must support randomized selection, adaptive low-stakes practice, standardized exams, attempt limits, timing, partial credit, explanations, instructor override, and immutable attempt history.

### ASM-004 — No answer leakage

Keys, private explanations, expected evidence, and evaluator-only examples must never be included in learner bundles or unauthorized API responses.

### ASM-005 — Evidence-based grading

Assessment results must produce durable, versioned mastery evidence with independence, hints, attempts, timing, and source provenance.

## 10. Adaptive learning

### ADP-001 — Skill graph and learner profile

Maintain stable skill IDs, hierarchy, prerequisites, difficulty, evidence, mastery estimate, confidence, recency, and review schedule.

### ADP-002 — Evidence inputs

Use diagnostics, checks, quizzes, exams, labs, hint use, independence, scenarios, project rubrics, and retention checks. Passive page views must not create mastery.

### ADP-003 — Recommendation behavior

Detect gaps and strengths, select only approved activities, adjust challenge and hint timing, schedule review, reduce repetition, offer explanation variants, and explain every recommendation.

### ADP-004 — Strong-networking/weak-Linux acceptance profile

Deprioritize basic networking, retain advanced networking, recommend guided Linux refreshers and practice, use networking knowledge to explain Linux networking, reveal Linux hints earlier, and reduce support as mastery improves.

### ADP-005 — Fixed curriculum

Official lesson order and content remain available and unchanged. Personalization selects reviewed variants and activities rather than generating replacement curriculum.

### ADP-006 — Learner and instructor control

Learners may dismiss or override optional recommendations where appropriate. Authorized instructors may set fixed/adaptive modes, prerequisites, mandatory activities, accommodations, and documented overrides.

### ADP-007 — Transparent decisions

Store bounded input features, selected activity, reason, engine version, and timestamp without hidden chain-of-thought. Production decisions must be tenant-keyed and durable.

### ADP-008 — Evaluation

Test cold start, low evidence confidence, recency, strong theory/weak practice, weak theory/tool memorization, advanced learners, returning learners, repeated prerequisite failure, and instructor intervention.

## 11. Sentinel and AI

### AI-001 — Real AI claim boundary

The product may claim live AI only when a server-side model adapter is configured and evaluated. Deterministic fallback must be labeled as such.

### AI-002 — Grounded retrieval

Sentinel must retrieve from current lesson/module/course, prerequisites, approved knowledge, lab state, approved hints, projects, learner-visible rubrics, cyber intelligence, and authorized learner skill state.

### AI-003 — Citation validity

Answers must cite retrieved authoritative evidence. The system must validate citation source, version, access permission, and support for material claims.

### AI-004 — Safe mentor behavior

Sentinel must answer ordinary questions and greetings, explain concepts, use Socratic guidance, explain mistakes, recommend approved learning, and refuse graded answers, secrets, unsafe real-target assistance, and unauthorized tool actions.

### AI-005 — Prompt and data security

Treat user, retrieved, instructor, and tool content as untrusted; enforce prompt/tool policy server-side; protect cross-user data; redact secrets; constrain tools; validate output; and record safe audit metadata.

### AI-006 — Reliability controls

Support timeouts, retries, provider circuit breakers, budgets, rate limits, streaming cancellation, deterministic fallback, model/prompt versions, latency/cost metrics, and provider outage behavior.

### AI-007 — Human content authority

Sentinel can assist learning and authoring but cannot define official curriculum, publish content, expose evaluator material, or issue credentials.

### AI-008 — AI evaluation

Maintain reviewed tests for grounding, Recall@k, citation precision, unsupported claims, prompt injection, answer leakage, cross-user leakage, safe refusal, helpfulness, latency, cost, and multilingual behavior.

## 12. Cyber Range

### LAB-001 — Discoverable range

Provide catalog, categories, search, filters, difficulty, duration, skills, prerequisites, course/track links, environment type, completion, favorites, recommendations, attempts, and truthful availability.

### LAB-002 — Minimum usable library

Version 1 requires at least 80 fully usable activities, including at least 25 executable or interactive isolated activities, 20 artifact investigations, 15 secure coding/configuration/remediation activities, 10 awareness simulations, and 10 career/interview simulations.

### LAB-003 — Complete lab contract

Every available lab requires stable ID, title, category, difficulty, duration, original scenario, business context, objectives, prerequisites, skills, environment, safety scope, rules, instructions, tasks, evidence, hints, private verification, solution policy, debrief, defense/remediation, reflection, portfolio mapping, references, version, author, review, and publication status.

### LAB-004 — Lifecycle

Available labs must launch, become healthy, pause/resume where supported, expire, reset, clean up, recover from failure, record attempts, and never route to an empty page.

### LAB-005 — Verification and persistence

Wrong evidence must fail, correct evidence must pass, verification must be server-side, and attempts, hints, completion, evidence, reset, ownership, and audit events must persist.

### LAB-006 — Isolation

Executable labs require per-user isolation, isolated networks, outbound deny by default, resource limits, timeouts, safe mounts, no Docker socket, no sensitive host paths, no unjustified privilege, and automatic teardown.

### LAB-007 — Authorized targets only

No arbitrary public target, address, domain, scanning, brute force, exploit, payload, or phishing target input is permitted. Activities use local vulnerable systems, simulations, synthetic evidence, mock clouds, or explicitly authorized targets.

### LAB-008 — Defensive completeness

Offensive concepts must include authorization, scope, defender visibility, detection, remediation, reporting, retesting, and cleanup.

### LAB-009 — Environment proof

Every executable environment must include its build/runtime definition, fixtures, health check, limits, reset, expiration, cleanup, ownership, verification, logs, and executed lifecycle evidence.

### LAB-010 — Instructor and administration

Authorized instructors and administrators require review, feedback, lab publication, lifecycle monitoring, evidence access, and safe management tools.

## 13. Scenarios, projects, portfolio, and career

### EVD-001 — Workplace scenarios

Implement realistic decision-based scenarios for major specializations, including SOC, incident response, forensics, penetration testing, web, cloud, application security, threat hunting, and AI security.

### EVD-002 — Complete course projects

Every course requires organization context, business problem, scope, milestones, deliverables, evidence files, rubric, evaluation, submission, feedback, Sentinel boundaries, reflection, and portfolio output.

### EVD-003 — Rubrics and human review

Rubrics require versioned criteria, performance levels, passing rule, private evaluator guidance, authorized reviewer decisions, feedback, and audit history.

### EVD-004 — Portfolio evidence

Store demonstrated skills, difficulty, objectives, reflection, feedback, files, completion date, verifier, verification state, visibility, and revocation state.

### EVD-005 — Career readiness

Provide role mapping, interview simulations, professional writing/report feedback, project storytelling, skill-gap plans, and evidence-based readiness without promising employment.

## 14. Institutional and audience editions

### ORG-001 — University edition

Support institutions, programs, courses, sections, instructors, students, assignments, due dates, grading, cohorts, outcomes, exports, and authorized academic administration.

### ORG-002 — Enterprise edition

Support organizations, managers, employee groups, assignments, awareness campaigns, deadlines, completion, reporting, entitlements, and private organizational data.

### ORG-003 — Instructor experience

Instructors require authorized learner/cohort views, assignment controls, adaptive overrides, submission review, feedback, grading, accommodations, and auditable actions.

### ORG-004 — Security-awareness academy

Provide role-appropriate, measurable awareness training and simulations without real phishing or deceptive external delivery unless separately authorized and legally approved.

### ORG-005 — Student Academy

Provide age-appropriate foundational and career exploration experiences with truthful progress and safeguarding.

### ORG-006 — Kids Cyber Safety Academy

Requires defined age bands, parental/guardian consent, child-privacy compliance, safe content, no unsafe chat, no collection beyond necessity, and age-appropriate moderation.

## 15. Identity, authorization, and privacy

### IAM-001 — Account lifecycle

Implement registration, email verification, login, logout, forgot/reset password, password change, profile, session management/revocation, account deletion, data export, and organization invitations.

### IAM-002 — Credential and session security

Use Argon2id where passwords are owned, secure HTTP-only cookies, rotation, expiry, CSRF controls, secure token storage, generic recovery responses, brute-force controls, and revocation.

### IAM-003 — Required roles

Guest, Learner, Instructor, Content Author, Technical Reviewer, Instructional Reviewer, Organization Manager, University Administrator, Enterprise Administrator, and Platform Administrator.

### IAM-004 — Server authorization

Enforce role, permission, organization, ownership, and resource policies server-side for every protected action.

### IAM-005 — Tenant isolation

Every tenant-owned row, object, job, cache key, AI retrieval, lab instance, log, and query must be organization-scoped and covered by cross-tenant tests.

### IAM-006 — Privacy rights

Implement consent, minimization, retention, deletion, export, private-by-default portfolios, AI data controls, and jurisdiction-appropriate privacy notices.

### IAM-007 — Development email

Local development uses Mailpit or an equivalent clearly labeled adapter. Production requires a selected email provider, verified domain, DNS, delivery security, and monitoring.

### IAM-008 — Privilege testing

Test horizontal and vertical escalation, IDOR, cross-organization access, answer keys, reviewer permissions, private learner data, admin settings, and session abuse.

## 16. Data and infrastructure

### DAT-001 — Approved data stack

The approved target specifies PostgreSQL, SQLAlchemy 2, Alembic, pgvector, Redis where justified, object-storage abstraction, MinIO locally, and a background worker.

### DAT-002 — Durable domain model

Persist users, sessions, organizations, memberships, roles, permissions, curriculum/versioning, enrollments, progress, notes, bookmarks, skills, evidence, assessment attempts, labs, projects, scenarios, AI conversations/citations, feedback, audit logs, subscriptions, entitlements, and notifications.

### DAT-003 — Migrations and seeds

Provide repeatable upgrade/downgrade migrations, transaction-safe seeds, deterministic Version 1 content import, development accounts, environment guards, and migration/seed verification.

### DAT-004 — File storage

Use private object storage, malware scanning, content-type/size validation, signed access, tenant prefixes, encryption, retention, deletion, and audit records.

### DAT-005 — Background jobs

Use idempotent jobs, retries, backoff, dead-letter handling, job ownership, observability, and safe workers for email, indexing, AI, analytics, content refresh, uploads, and lab cleanup.

### DAT-006 — Backup and recovery

Define backup, restore, retention, disaster recovery, recovery objectives, and tested restore drills for databases, object storage, content versions, and critical configuration.

## 17. API, security, operations, and deployment

### OPS-001 — API design

Use versioned, typed contracts; consistent validation/errors; pagination; idempotency where needed; authorization middleware; audit context; and frontend-action-to-service-to-model traceability.

### OPS-002 — Security headers and transport

Use TLS, HSTS, CSP without avoidable unsafe directives, content sniffing protection, framing protection, referrer and permissions policies, secure cookies, and production proxy configuration.

### OPS-003 — Abuse controls

Use distributed rate limiting, account lockout safeguards, bot/abuse monitoring, request limits, upload limits, AI quotas, lab quotas, and safe proxy-aware client identification.

### OPS-004 — Secret management

Keep secrets server-side in an approved secret store, rotate them, redact logs, separate environments, and prevent local/development credentials from entering production.

### OPS-005 — Observability

Provide structured logs, metrics, traces, request/job/model/lab IDs, dashboards, SLOs, alerts, error tracking, audit logs, privacy filters, and on-call procedures.

### OPS-006 — Health and readiness

Liveness checks process health; readiness verifies required database, content, queue, storage, and configured service dependencies without exposing secrets.

### OPS-007 — Deployment

Provide reproducible production images, minimal build context, non-root/read-only operation where possible, runtime content, migrations, worker, frontend/API, rollback, TLS, domain/DNS, and environment validation.

### OPS-008 — Scalability

Support stateless API replicas, shared persistence/cache, pagination, durable jobs, object storage, isolated lab workers, quotas, connection pooling, caching, and measured load limits.

### OPS-009 — Performance

Define and measure page, API, retrieval, grading, lab-launch, and AI latency budgets; avoid loading the full academy at startup; use caching and code/data splitting without stale authorization.

### OPS-010 — Commercial enforcement

Billing, subscription, quota, and entitlement state must be server-owned, auditable, tenant-scoped, and resilient to provider webhook retries.

## 18. UI and experience quality

### UX-001 — Professional product design

The product must communicate a serious professional platform, not a generated dashboard, while avoiding unsupported social proof or decorative data.

### UX-002 — Stable routing

Courses, modules, lessons, labs, scenarios, projects, portfolios, and administration require stable URLs, deep links, browser history, authorization-aware route guards, and useful not-found states.

### UX-003 — Responsive and accessible interaction

Support keyboard navigation, focus management, screen readers, contrast, zoom, reduced motion, touch/mobile layouts, accessible forms, error summaries, and appropriate WCAG testing.

### UX-004 — Honest degraded states

Unavailable providers, empty content, expired labs, lost sessions, stale references, and failed jobs must produce truthful recovery guidance rather than fake data or silent fallback.

### UX-005 — Themes and internationalization

Dark/light themes and multilingual/RTL support must be implemented and browser-tested if retained in launch scope.

## 19. Quality, testing, and release evidence

### QA-001 — Automated test layers

Maintain unit, integration, API, database, component, E2E, content, AI, adaptive, security, tenancy, RBAC, lab-lifecycle, worker, migration, and deployment tests.

### QA-002 — Real-browser verification

Use Playwright or an approved real-browser runner for learner, instructor, reviewer, university, enterprise, administrator, responsive, theme, console, and network journeys.

### QA-003 — Course and lab matrix

Automatically verify required course counts/depth/references/routes/quizzes/labs/scenarios/projects/rubrics and lab counts/types/content/environments/verification/persistence/reset/cleanup.

### QA-004 — Security testing

Test authentication, CSRF, rate limits, IDOR, RBAC, tenancy, answer leakage, prompt injection, cross-user AI leakage, uploads, lab ownership/isolation, secrets, headers, and dependency risk.

### QA-005 — Build and static gates

Run formatting, linting, frontend/backend type checks, schema checks, production builds, dependency audits, and license/SBOM checks without suppressing valid failures.

### QA-006 — Runtime inspection

Inspect frontend console, network failures, API logs, worker failures, database errors, failed jobs, lab logs, AI failures, and health/readiness behavior.

### QA-007 — Evidence report

Final reports must derive exact counts and results from repository/database/runtime evidence and list startup commands, URLs, accounts, migrations, seeds, images, tests, builds, limitations, and blockers.

### QA-008 — Release threshold

No reproducible critical or high-severity defect may remain for the claimed release scope. Medium risks require explicit acceptance, owner, and remediation date.

## 20. Approved proposal and fellowship evaluation

### RES-001 — Lebanon impact

Prioritize accessible practical cybersecurity development for Lebanese university students, graduates, career switchers, instructors, and early-career professionals.

### RES-002 — Responsible model scope

Do not claim to train a foundation model. Evaluate an existing instruction-following model and retrieval system against transparent deterministic and lexical baselines.

### RES-003 — Public data and sources

Use authoritative public sources and appropriately licensed datasets such as NIST, CISA KEV, MITRE ATT&CK, and a documented subset of CIC-IDS2017, with provenance and limitations.

### RES-004 — Learning evaluation

Measure pre/post learning, task completion, repeated-error reduction, lab completion, and qualitative understanding with consented participants when approval and recruitment exist.

### RES-005 — AI and recommendation evaluation

Measure retrieval Recall@5, citation precision, unsupported claims, leakage, recommendation quality versus a baseline, cold-start coverage, latency, and cost.

### RES-006 — Ethics and documentation

Obtain required consent/ethics approval, minimize/anonymize participant data, document decisions and unsuccessful experiments, maintain an implementation/evaluation log, and include a final reflection.

## 21. Requirement change control

New requirements must:

1. receive a stable ID or explicitly amend an existing ID;
2. identify the approving source and date;
3. record impact in the decision log;
4. update the traceability matrix;
5. identify dependencies and blockers;
6. avoid silently weakening safety, security, content, or evidence rules.
