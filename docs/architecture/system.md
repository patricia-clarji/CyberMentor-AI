# System architecture

## Verified local foundation

The running system is a React client plus a dependency-free Node HTTP API. Its learner-content path is deliberately narrow:

`reviewed version files → content/published/latest.json → server repository → sanitized API payload → course player`

The server rejects drafts, unverified records, expired reviews, missing required review roles, missing dual-use safety approval, and malformed publications. Legacy records in `src/data/courses.ts` provide planning shells only and cannot enter that path. Question keys and lab verification rules remain in server-only publication artifacts; learner lesson, diagnostic, and lab payloads omit them.

The browser keeps demo enrollment, notes, bookmarks, progress, recommendation dismissal, and advisory skill estimates in local storage. These records have no identity assurance and cannot create credential evidence. The API adds request IDs, structured JSON logs, same-origin enforcement, IP rate limiting, request-body limits, and security headers.

The deterministic Sentinel does bounded retrieval from verified lesson context when available and otherwise uses a clearly labeled no-key fallback. It refuses real-target offensive help and graded-answer requests. It is an enhancement, never the source of required curriculum.

The adaptive engine is a separate rules module. It updates skill estimates only from explicit evidence types, applies confidence and recency controls, and selects only verified published activities. Its reasons and inputs are auditable without storing hidden model reasoning. See [adaptive learning](adaptive-learning.md).

## Implemented repository boundaries, not deployed services

`db/migrations/001_adaptive_learning.sql` specifies tenant-keyed PostgreSQL tables for skills, objectives, learner state, evidence, practice activities, recommendations, decision logs, and instructor policy. No PostgreSQL service, migration runner, seed, authenticated instructor policy API, or durable event store is present in this checkout. The migration is architecture-only and has not been applied.

## Target commercial context

Browser → edge/web application → authenticated stateless API → PostgreSQL and object storage. The API publishes idempotent jobs to workers for email, indexing, AI, analytics, and lab lifecycle actions. An isolated lab control plane communicates with dedicated sandbox workers; untrusted workloads never share application nodes.

Organization ownership belongs in every tenant row and query policy. Server authorization remains mandatory when the client hides a control. Answers, validation rules, secrets, private evidence, and instructor policies remain server-side; object downloads use short-lived signed URLs.

A future live AI adapter may accept server-side OpenAI-compatible configuration. Retrieval chunks must preserve course, module, lesson, difficulty, source, content type, safety class, version, and date. Citation validation rejects ungrounded citations, and deterministic demo mode remains the fallback.

Production entities additionally include users, sessions, organizations, memberships, cohorts, course versions, enrollments, progress events, attempts, projects, rubrics, labs, evidence, mentor threads, entitlements, audits, and consent records.
