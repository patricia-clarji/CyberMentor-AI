# CyberMentor AI

**Learn. Defend. Investigate. Break Safely. Become Job-Ready.**

CyberMentor AI Version 1 ships as an immediately usable, local-first cybersecurity academy. A normal install seeds 12 published courses with 48 modules, 144 substantial lessons, 144 server-graded questions, 80 usable Cyber Range activities, 12 workplace projects, 12 rubrics, 12 completion rules, and 24 adaptive practice activities.

## Quick start

```bash
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. The API is at `http://127.0.0.1:8787`; health is `/api/health`. No API key or manual publication step is required. Both `postinstall` and `predev` run the idempotent Version 1 seed.

To verify a running development instance:

```bash
npm run verify:live
```

## AI/ML submission artifacts

The final fellowship materials are [the 4-page project report](docs/SUBMISSION_REPORT.md), [the proposal](docs/SUBMISSION_PROPOSAL.md), [dataset documentation](docs/DATASETS.md), and the [NLP/model pipeline](docs/ai/NLP_AND_MODEL_PIPELINE.md). A reproducible dependency-free logistic-regression learner-skill baseline is under `ml/`:

```bash
npm run ml:train
python ml/infer.py "I need help with Linux permissions and chmod"
npm run ml:test
```

The model uses clearly labeled synthetic demo data; its saved holdout metrics are not claims about Lebanese learners.

The live gate checks the web/API, all 144 lesson publications, grading-key privacy, 80 labs, 12 projects, server-side quiz grading, range launch, cross-owner denial, progressive hints, wrong-answer rejection, reset, correct verification, project submission, and cold-start adaptive recommendations.

## Included academy

- Cybersecurity Foundations
- Networking for Cybersecurity
- Linux for Cybersecurity Professionals
- Introduction to Security Operations and SOC Analysis
- Incident Response Foundations
- Digital Forensics Foundations
- Ethical Hacking and Penetration Testing Foundations
- Web Application Security Foundations
- Python for Cybersecurity
- Cloud Security Foundations
- AI and LLM Security Foundations
- Cybersecurity Career and Interview Preparation

Each course contains four modules and twelve lessons, at least six linked range activities, a workplace project, a published rubric, and completion criteria. Dual-use material is restricted to bundled fictional evidence or explicitly authorized local practice and pairs offensive concepts with detection, remediation, verification, and cleanup.

## Cyber Range

The seeded range contains exactly 80 original, launchable activities: 40 interactive browser, awareness, or career simulations; 20 artifact-analysis investigations; and 20 secure-configuration exercises. Ten are dedicated awareness simulations and ten are dedicated interview/career simulations. Search and filters cover category, difficulty, environment, and skills. Learners can bookmark, launch or resume a server-owned session, pause, reveal progressive hints, submit server-verified evidence, reset, complete a defensive debrief, and save a local portfolio reflection.

These activities are deliberately labeled simulations or bounded artifact workspaces. The repository currently ships zero executable Docker or microVM labs and does not claim otherwise. No activity accepts public targets, arbitrary addresses, arbitrary commands, unrestricted outbound traffic, privileged containers, or host mounts.

## Automated checks

```bash
npm run format
npm run lint
npm run typecheck
npm test -- --run
npm run content:validate
npm run build
npm audit --audit-level=moderate
```

## Content trust and updates

The immutable Version 1 publications use the narrowly scoped `v1-release-baseline` approval recorded under the product owner's release directive. It applies only to the initial academy. Future course changes, new lessons, instructor or community contributions, and AI-assisted drafts must use the normal source-ingestion and independent human-review workflow before publication.

The seed reads the 12 reviewed course specifications and writes versioned publications under `content/published/` plus a normalized data seed at `db/seeds/001_v1_academy.seed.json`. The pipeline keeps references, source snapshots, semantic versions, review dates, content hashes, and publication status. AI-assisted drafts cannot auto-publish.

Content maintainers can run:

```bash
npm run seed:v1
npm run content:refresh -- --source nist-csf-2
npm run content:validate
npm run content:status
```

See [content authoring](docs/content/content-authoring.md), [ingestion and publication](docs/content/ingestion-pipeline.md), and [provenance](docs/content/provenance.md).

## Architecture and honest limitations

React, TypeScript, Vite, Vitest, and a dependency-free Node HTTP API provide the verified local experience. Learner progress, notes, bookmarks, enrollment, and formative portfolio state are browser-local. Quiz keys and lab verification evidence remain server-side. Sentinel is a deterministic, citation-bound demo mentor and works without an LLM key.

Version 1 does not yet provide production identity, email flows, durable authenticated sessions, tenant isolation, an applied relational database, queues, uploads, payments, instructor/admin CMS workflows, live LLM/RAG, or hardened container orchestration for hostile labs. Cyber Range instances are bounded in-memory development sessions keyed to a local guest identifier; they are not a multi-tenant authorization boundary. The generated normalized seed is ready for a future persistence adapter, but the current runtime is file-backed and local-first. Browser-local progress has no identity assurance and is not credential evidence.

Docker can be started with `docker compose up --build`, then opened at `http://127.0.0.1:8080`. This path was not executed in the current Windows audit environment and must not be treated as an isolation boundary for hostile exercises.

See the [Version 1 release verification](docs/audit/2026-07-19-v1-release.md), [system architecture](docs/architecture/system.md), [adaptive architecture](docs/architecture/adaptive-learning.md), [threat model](docs/security/threat-model.md), and [roadmap](docs/product/roadmap.md).

Troubleshooting: stop the existing CyberMentor process if ports 5173 or 8787 are already occupied; clear `cm-progress` in local storage to reset learner state; use current Node LTS or newer.
