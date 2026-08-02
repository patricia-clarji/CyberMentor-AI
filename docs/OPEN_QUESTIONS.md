# CyberMentor AI Open Questions

**Created:** 2026-07-28  
**Purpose:** Record resolved decisions and capture remaining details that must not be replaced with fabricated values.

## How to answer

The disposition table is authoritative over the original question wording retained below for history. Answer only items marked **Open**. “Deferred” means the capability remains an approved later target but is not a competition blocker.

## Decision disposition

| ID     | Status            | Approved disposition                                                                                                                                                                                   |
| ------ | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| OQ-001 | Resolved          | B — private single-organization beta with tenant-aware foundations                                                                                                                                     |
| OQ-002 | Resolved          | C — incremental FastAPI/SQLAlchemy 2/Alembic migration behind stable contracts; retain Node until parity and tests exist                                                                               |
| OQ-003 | Resolved          | A — first-party Argon2id account system, secure HTTP-only cookie sessions, rotation/revocation, verification/reset, Mailpit locally, later OIDC support                                                |
| OQ-004 | Resolved          | B — many-to-many memberships, active organization context, and an automatic private personal tenant                                                                                                    |
| OQ-005 | Open              | Production email provider, sending domain, DNS owner, and budget remain required                                                                                                                       |
| OQ-006 | Open              | Exact managed container/PostgreSQL host, region, domain, DNS owner, environments, and budget remain required                                                                                           |
| OQ-007 | Open              | Live LLM provider, model, account/region, API credential, privacy terms, and monthly budget remain required                                                                                            |
| OQ-008 | Open              | English is the competition language and RTL readiness is required; the initial English embedding provider/model, hosting, dimensions, and budget remain required                                       |
| OQ-009 | Resolved          | Minimal necessary retention; no provider training; separate structured learner state; deletion controls; redacted evaluation logs; explicit research consent; no biometric/emotional surveillance      |
| OQ-010 | Open              | MinIO local and private S3-compatible abstraction are approved; production object store and malware-scanning service/worker remain required                                                            |
| OQ-011 | Resolved          | Celery plus Redis for email, indexing, report generation, upload scanning, lab cleanup, and notifications                                                                                              |
| OQ-012 | Open              | Structured logs and OpenTelemetry-ready instrumentation are approved; error/telemetry accounts, alert destinations, and beta alert owner confirmation remain required                                  |
| OQ-013 | Resolved/deferred | No billing in the competition beta; retain entitlement architecture without checkout/subscription UI                                                                                                   |
| OQ-014 | Resolved/deferred | Kids Academy is excluded until child privacy, guardian consent, age bands, jurisdiction, and legal review exist                                                                                        |
| OQ-015 | Open              | Accountable technical cybersecurity, instructional, and accessibility reviewers and publication authority remain required                                                                              |
| OQ-016 | Resolved          | Issue only a CyberMentor Verified Completion Record; never call it an industry certification                                                                                                           |
| OQ-017 | Open              | Browser simulations are preferred and a very small number of local Docker labs may be used; production executable worker, concurrency, quotas, and budget remain required before executable deployment |
| OQ-018 | Resolved          | 18 courses/360 lessons remain the full-academy target; the competition gate is one reviewed SOC Analyst path; current 12 courses remain baseline/draft until review proves otherwise                   |
| OQ-019 | Resolved          | Generated local-only accounts require an explicit development seed flag, may print only locally, and must be rejected by production guards/tests                                                       |
| OQ-020 | Resolved          | First-party, tenant-scoped privacy-conscious events only; no advertising or third-party behavioral tracking                                                                                            |
| OQ-021 | Open              | Teaching-team/ethics approval, recruitment, consent, sample, incentives, and data handling remain required for the approximately 5–15-person Lebanese pilot                                            |
| OQ-022 | Resolved          | English competition release; RTL-ready architecture; Arabic next pilot; French deferred                                                                                                                |
| OQ-023 | Resolved          | First readiness profile is Junior SOC Analyst, using explicit evidence, independence, recency, and limited hint-dependency criteria; no employment guarantee                                           |
| OQ-024 | Resolved/deferred | Defer the intelligence feed; later use CISA KEV, NVD/CVE, and official advisories with original summaries and links                                                                                    |
| OQ-025 | Open              | Authoritative Git remote/branch or permission and destination for a new protected repository remain required                                                                                           |

## Exact remaining questions

1. **OQ-005:** Which production email provider and sending domain will be used, who controls DNS, and what delivery budget/retention policy is approved?
2. **OQ-006:** Which managed container and PostgreSQL provider, region, beta domain, DNS owner, environment set, and monthly infrastructure budget are approved?
3. **OQ-007:** Which live LLM provider/model/account/region will Sentinel use, who owns the server-side credential, what privacy terms apply, and what monthly AI budget/usage ceiling is approved?
4. **OQ-008:** Which initial English embedding provider/model and hosting mode are approved, and what dimensions, re-index policy, and cost ceiling should be used?
5. **OQ-010:** Which production S3-compatible object store and malware-scanning service or worker are approved, including credentials, limits, retention, and region?
6. **OQ-012:** Which error/telemetry services and accounts are approved, where should alerts go, and who owns beta incident response?
7. **OQ-015:** Who are the accountable technical cybersecurity, instructional, and accessibility reviewers, may any roles overlap with disclosure, and who alone has publication authority?
8. **OQ-017:** Will the competition deployment include executable labs; if yes, what dedicated worker design, host OS, concurrency, quotas, isolation controls, and budget are approved?
9. **OQ-021:** Has the teaching team approved the pilot, how will approximately 5–15 Lebanese participants be recruited, and what consent, incentive, and data-handling process is approved?
10. **OQ-025:** What is the authoritative Git remote and branch, or may a new protected repository be initialized and connected—and at which remote?

## Priority 0 — required before implementation foundation

### OQ-001 — First approved release scope

**Missing:** The first release boundary is not explicit: fellowship demonstration, private single-organization beta, multi-tenant commercial beta, or public production.

**Why required:** Security, tenancy, infrastructure, support, legal, and definition-of-done requirements differ materially.

**Options:**

A. Fellowship-only local demonstration  
B. Private single-organization beta  
C. Private multi-tenant beta  
D. Public commercial production

**Recommendation:** B, built with tenant-aware foundations, followed by C after isolation/security evidence.

**Question:** Which release scope should the next implementation phase target?

### OQ-002 — Backend and database migration strategy

**Missing:** The approved target mandates SQLAlchemy 2/Alembic, while the current API is Node.js.

**Why required:** This determines language, directory structure, ORM, migrations, testing, deployment, and the fate of current API code.

**Options:**

A. Retain Node and use a TypeScript ORM; formally amend DAT-001  
B. Replace the Node API with Python/FastAPI + SQLAlchemy/Alembic  
C. Incrementally introduce FastAPI and migrate route groups behind stable contracts

**Recommendation:** C. Preserve working content/grading behavior while moving trusted domains to the approved stack.

**Question:** Do you approve incremental migration to FastAPI/SQLAlchemy/Alembic, or do you want the Node stack retained?

### OQ-003 — Authentication ownership

**Missing:** No identity provider or first-party auth decision exists.

**Why required:** Registration, password security, sessions, MFA, invitations, account recovery, and production credentials depend on it.

**Options:**

A. First-party email/password sessions using Argon2id  
B. Self-hosted identity provider such as Keycloak  
C. Managed provider such as Auth0/Clerk  
D. Enterprise SSO only

**Recommendation:** A for the controlled beta, with provider abstraction and later OIDC support. It directly satisfies the approved Argon2id/Mailpit flow.

**Credentials/accounts:** A needs only local Mailpit initially; B/C/D require provider configuration, and C requires an external account.

**Question:** Which authentication option is approved?

### OQ-004 — Organization and tenancy semantics

**Missing:** It is unknown whether one user can belong to multiple organizations, whether personal learners have a personal tenant, and who owns portfolio evidence.

**Why required:** Every query, object key, role, invitation, AI retrieval, lab session, billing record, and deletion policy depends on ownership.

**Options:**

A. One user belongs to one organization  
B. Many-to-many memberships with an active organization context  
C. Separate personal and institutional accounts

**Recommendation:** B, with personal learners assigned to a private personal organization.

**Question:** Can users belong to multiple organizations, and should personal learners receive a personal tenant?

### OQ-005 — Production email provider and domain

**Missing:** Mailpit covers local development only. No production provider, sending domain, sender name, DNS access, or retention policy is defined.

**Why required:** Verification, reset, invitation, notification, bounce, abuse, and delivery monitoring require it.

**Options:** AWS SES, Postmark, Resend, another approved provider.

**Recommendation:** Postmark for a small beta or SES for AWS-aligned scale; keep a provider interface and Mailpit adapter.

**Credentials/accounts:** Provider account, verified domain, DNS records, API/SMTP credentials.

**Question:** Which provider and domain should be used, and who controls DNS?

### OQ-006 — Hosting, domain, DNS, TLS, and environments

**Missing:** No deployment host, production domain, region, DNS owner, TLS strategy, environment count, or budget exists.

**Why required:** Container topology, secrets, networking, storage, backups, monitoring, data residency, and release verification depend on it.

**Options:**

A. Managed container platform + managed PostgreSQL  
B. AWS ECS/RDS/ElastiCache/S3  
C. Kubernetes  
D. Single VM for private beta

**Recommendation:** A for the first private beta; avoid Kubernetes until operational need is proven.

**Question:** What host, region, domain, DNS owner, environments, and monthly infrastructure budget are approved?

## Priority 1 — required before AI, data, and operations

### OQ-007 — LLM provider and model

**Missing:** Provider, model, account, region, privacy terms, token limits, cost budget, and fallback policy.

**Why required:** A live AI claim cannot be implemented or evaluated without these.

**Options:** OpenAI/Azure OpenAI, Anthropic, Google, a local open-weight model, or provider-agnostic multi-provider support.

**Recommendation:** Provider abstraction with one approved hosted model for evaluation and deterministic no-key fallback. Select the model only after privacy/cost constraints are known.

**Credentials/accounts:** Provider account and server-side API credential for hosted models; compute environment for local models.

**Question:** Which provider/account/region and monthly AI budget are approved?

### OQ-008 — Embedding and retrieval model

**Missing:** Language scope, embedding model, dimensions, hosting, version, and re-index policy.

**Why required:** pgvector schema, retrieval latency, multilingual quality, cost, and migration depend on it.

**Options:**

A. Hosted embedding API  
B. Local English embedding model  
C. Local multilingual embedding model

**Recommendation:** C if Arabic/French remain in launch scope; otherwise benchmark A and B against the reviewed corpus.

**Question:** Which launch languages and embedding deployment model should retrieval support?

### OQ-009 — AI data retention and consent

**Missing:** Whether prompts, responses, retrieved chunks, feedback, and learner profiles may be stored or sent to providers.

**Why required:** Privacy, provider configuration, deletion, audit, evaluation, and model-training policy depend on it.

**Recommendation:** No provider training, minimum prompt retention, explicit feedback consent, tenant-scoped threads, configurable deletion, and redacted evaluation logs.

**Question:** Approve this policy or specify different retention/training rules and jurisdictions.

### OQ-010 — Object storage and malware scanning

**Missing:** Production object-store provider, file limits, allowed formats, scanning service, encryption, retention, and evidence access rules.

**Why required:** Project/lab evidence uploads cannot be safely implemented without it.

**Options:** S3-compatible provider, AWS S3, Azure Blob, Google Cloud Storage; MinIO locally.

**Recommendation:** S3-compatible abstraction with MinIO locally, production provider selected by hosting choice, and an asynchronous antivirus/content-disarm pipeline.

**Credentials/accounts:** Storage account/bucket credentials; scanning infrastructure/provider.

**Question:** Which production object store and scanning approach are approved?

### OQ-011 — Redis and worker framework

**Missing:** Job framework, broker, worker ownership, priority, retries, and operational responsibility.

**Why required:** Email, indexing, content refresh, uploads, AI, analytics, and lab cleanup require durable work.

**Options:** Celery + Redis, Dramatiq + Redis, RQ + Redis, managed queue.

**Recommendation:** Celery + Redis if FastAPI/SQLAlchemy is approved; a managed queue may replace Redis for production later.

**Question:** Which worker/broker approach is approved?

### OQ-012 — Observability providers

**Missing:** Error tracking, metrics, traces, log aggregation, alert routing, and on-call owner.

**Why required:** The definition of done requires production errors and failed jobs to be visible.

**Options:** OpenTelemetry plus a managed backend; Sentry for errors; Prometheus/Grafana; cloud-native stack.

**Recommendation:** OpenTelemetry instrumentation, Sentry for application errors, and the hosting platform’s initial logs/metrics.

**Credentials/accounts:** Provider projects, ingestion keys, alert destinations.

**Question:** Which providers and alert owner are approved?

## Priority 2 — product, content, legal, and commercial decisions

### OQ-013 — Billing and commercial model

**Missing:** Customer type, plans, prices, currencies, trials, taxes, refunds, seat model, quotas, and billing provider.

**Why required:** Billing and entitlements cannot be implemented safely from a generic “Stripe” assumption.

**Options:** No billing for beta; Stripe subscriptions; invoice/contract enterprise sales; hybrid.

**Recommendation:** No billing in the first private beta. Define entitlements independently, then integrate Stripe only after commercial/legal decisions.

**Question:** Is billing in the next release, and if so what plans, currencies, tax/refund rules, and provider are approved?

### OQ-014 — Legal, privacy, and child-safety jurisdiction

**Missing:** Legal entity, launch countries, privacy laws, age threshold, guardian consent, terms, privacy notice, data-processing agreements, moderation, and incident contacts.

**Why required:** Kids Academy, learner analytics, AI, uploads, and public launch cannot proceed safely without it.

**Recommendation:** Exclude Kids Academy from launch until counsel approves an age-specific design and consent/data policy.

**Question:** What legal entity, launch jurisdictions, minimum age, and legal reviewer apply?

### OQ-015 — Accountable content reviewers

**Missing:** Named technical, instructional, accessibility, licensing, safety, and publisher authorities.

**Why required:** The reviewer registry is empty, and seeded metadata is not accountable commercial review.

**Recommendation:** Enroll distinct named reviewers under protected repository/SSO identity and define conflict-of-interest rules.

**Question:** Who will fill each review role, and who has publication authority?

### OQ-016 — Credential authority

**Missing:** Credential name, issuer, completion criteria, validity, revocation, public verification, and external recognition.

**Why required:** A certificate cannot be represented as professional evidence without defined authority.

**Recommendation:** Start with “CyberMentor course completion record,” not certification, and verify it cryptographically only after criteria are approved.

**Question:** What credentials may CyberMentor issue and what claims may they make?

### OQ-017 — Executable lab isolation target

**Missing:** Local Docker availability, production worker/control-plane design, microVM requirement, host OS, concurrency, quotas, and budget.

**Why required:** Safe executable labs cannot be implemented or claimed without an isolation target.

**Options:**

A. Local Docker only for controlled development  
B. Dedicated single-tenant lab workers  
C. Firecracker/microVM service  
D. Hardened Kubernetes namespaces

**Recommendation:** A for development plus B for the first private beta; evaluate C before public multi-tenant hostile workloads.

**Question:** Which local and production isolation options, concurrency target, and budget are approved?

### OQ-018 — Final curriculum scope and review bar

**Missing:** Confirmation that the later 18-course/360-lesson override remains the fellowship release target, and whether existing seeded content may be used before accountable review.

**Why required:** Scope changes staffing, schedule, review capacity, and release definition.

**Recommendation:** Keep 18/360 as the final product target, but gate the first implementation release on one fully reviewed vertical course before scaling.

**Question:** Confirm the 18-course/360-lesson target and the required human-review bar for the next release.

### OQ-019 — Development accounts

**Missing:** Approved development emails, role fixtures, password-delivery method, and environment guard.

**Why required:** Test journeys require accounts, while production cannot ship demo credentials.

**Recommendation:** Generate environment-scoped fixtures during explicit development seed, display credentials only in local logs/docs excluded from production, and test the production guard.

**Question:** Approve generated local-only accounts or provide approved test identities.

### OQ-020 — Analytics and consent

**Missing:** Product metrics, event taxonomy, provider, consent basis, retention, organization access, and learner opt-out.

**Why required:** “Real analytics” and adaptive evaluation cannot be implemented from invented events.

**Recommendation:** First-party tenant-scoped events in PostgreSQL/warehouse export; no third-party tracking until privacy review.

**Question:** Which metrics and consent/retention policy are approved?

### OQ-021 — Fellowship pilot ethics and recruitment

**Missing:** Teaching-team approval, participant recruitment, consent form, sample target, incentives, and data handling.

**Why required:** The proposal’s learning/usability evaluation depends on real participants.

**Recommendation:** Seek written teaching-team approval and use a small consented pilot; use synthetic data until approved.

**Question:** Is ethics/teaching-team approval required, and can the program help recruit participants?

### OQ-022 — Language and RTL launch scope

**Missing:** Whether English, Arabic, and French are launch requirements and who validates translations.

**Why required:** UI layout, content review, embeddings, evaluation, accessibility, and cost differ.

**Recommendation:** English first with RTL-ready architecture, then Arabic pilot with accountable reviewers; add French based on demand.

**Question:** Which languages are required for the next release?

### OQ-023 — Definition of professional readiness

**Missing:** Role-specific skills, minimum evidence, rubric thresholds, independence criteria, recency, reviewer authority, and allowed claim language.

**Why required:** The core promise cannot be measured without it.

**Recommendation:** Define role profiles with required verified skills, at least one reviewed workplace project, practical evidence, reflection, and recency; avoid employment guarantees.

**Question:** What exact evidence constitutes readiness for each initial role?

### OQ-024 — Cyber news and vulnerability intelligence

**Missing:** Sources, licenses, update frequency, editorial policy, archival policy, severity normalization, and notification rules.

**Why required:** Live intelligence can become stale, misleading, or legally problematic.

**Recommendation:** Start with CISA KEV, NVD/CVE, vendor advisories, and manual editorial rules; do not republish third-party articles.

**Question:** Which sources, refresh SLA, and notification scope are approved?

### OQ-025 — Version-control source of truth

**Missing:** The current `.git` directory is not a functioning repository. Remote, branch, history, protection rules, and release tag are unavailable.

**Why required:** Auditability, CI provenance, reviewer protection, rollback, and change ownership depend on version control.

**Recommendation:** Reconnect the workspace to the authoritative remote or create a new protected repository before implementation.

**Question:** What is the authoritative Git remote and branch, and may this workspace be reconnected to it?

## Answer record

Once answered, each item should be updated with:

- selected option;
- approver;
- decision date;
- affected requirement IDs;
- credentials/account owner;
- implementation phase;
- follow-up actions.
