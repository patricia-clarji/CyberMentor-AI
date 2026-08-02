# Authoritative content ingestion and publication

CyberMentor does not bulk-generate lessons with an LLM. Learner content moves through a source-backed, versioned workflow and remains unpublished until independent human review is recorded against the exact content hash.

## Trust and storage boundaries

- `content/sources.json` is the allowlisted source registry. Sources must use HTTPS, identify their publisher and authority class, and document the reproduction policy.
- Retrieval follows at most three redirects, permits only allowlisted hosts, times out after 20 seconds, and rejects responses larger than 5 MB.
- The pipeline stores retrieval metadata, a SHA-256 digest, and evidence-match results. It deliberately does not retain or republish raw source pages.
- Short evidence excerpts are limited to 25 words. Published records retain source URL, publisher, publication date when known, retrieval time, source version, digest, and claim linkage.
- Digest-named snapshots preserve history. Published semantic versions are immutable; changed content requires a new version. `content/published/manifest.json` is the synchronized learner-delivery index, while version files remain the rollback source.

## Authoring state machine

`draft → in-review → approved → published`

`rejected` returns work to the authoring cycle. Editing claim content changes its SHA-256 content hash and invalidates earlier approvals. Workflow status and timestamps do not change that hash.

Every draft—course, module, lesson, question, lab, scenario, project, rubric, glossary entry, certification mapping, completion rule, explanation variant, or practice activity—must declare:

- a stable kebab-case ID and semantic content version;
- human/AI provenance and an accountable author;
- atomic factual claims, each with a registered source, locator, and short evidence excerpt;
- command verification for executable instructions;
- domain, difficulty, audience, prerequisites, skill tags, licensing notes, dates, review interval, and change log;
- technical, instructional, accessibility, and licensing review requirements; dual-use content also requires independent safety review.

A publishable lesson uses supported structured blocks, includes at least two measurable objectives, key terms, a substantial worked example, and a server-graded check reference. Block `claimIds` connect authored prose to cited factual claims. The validator rejects answer-key fields, shallow lessons under 300 instructional words, external media, unmapped claims, and incomplete dual-use safety metadata. Typed checks also reject incomplete question banks, labs, scenarios, projects, rubrics, mappings, completion rules, explanation variants, and adaptive activities. `src/data/verified-content.ts` consumes the learner-safe server API; it never imports draft files or answer banks.

AI assistance, when used for editing or ideation, must be disclosed with the exact label `DRAFT — AI-ASSISTED — NOT REVIEWED`. It never counts as a source or reviewer and cannot publish content.

See [artifact contracts](artifact-contracts.md) for the type-specific authoring and learner-delivery boundaries.

## Commands

Retrieve one source and verify cited evidence:

```bash
npm run content:refresh -- --source nist-csf-2
npm run content:validate
npm run content:import
npm run content:status
```

Before reviewing, enroll real reviewers in `content/reviewers.json` through a protected repository change. A reviewer must be active, enrolled for the requested role, and different from the author.

```bash
npm run content:review -- --draft lesson-id --reviewer reviewer-id --role cybersecurity-subject-matter-expert --decision approve --comment "Evidence and technical accuracy checked."
npm run content:review -- --draft lesson-id --reviewer reviewer-id --role instructional-reviewer --decision approve --comment "Objectives, scaffolding, and assessment alignment checked."
npm run content:review -- --draft lesson-id --reviewer reviewer-id --role accessibility-reviewer --decision approve --comment "Keyboard, screen-reader, media, and language accessibility checked."
npm run content:review -- --draft lesson-id --reviewer reviewer-id --role licensing-reviewer --decision approve --comment "Licensing, excerpt length, and originality evidence checked."
npm run content:publish -- --draft lesson-id --publisher publisher-id
npm run content:sync
```

Publication fails if the draft is not approved, any source is stale, evidence does not match its retrieved source, a required review is missing, unauthorized, non-independent, or not performed by a distinct reviewer, the publisher lacks the `content-publisher` role, the publisher is the author, or the content changed after review. Current published records are revalidated for exact review roles, publisher enrollment, review expiry, skill IDs, immutable-version linkage, and references before synchronization.

An authorized publisher can reactivate an existing immutable version; the action is recorded under `content/operations/`:

```bash
npm run content:rollback -- --artifact lesson-id --version 1.2.0 --publisher publisher-id --reason "Rollback after verified regression"
```

Equivalent convenience targets are available in the root `Makefile`: `content-validate`, `content-import`, `content-publish`, `content-check-references`, and `content-rollback`.

## Automated checks

`npm run validate-content` checks the application inventory, skill graph, pipeline behavior, source safety, content-hash invalidation, evidence support, duplicate claims and sources, stale or missing snapshots, deprecated terminology, command verification, provenance, typed artifacts, review expiry, immutable publications, and publication gating.

The scheduled workflow refreshes sources every Monday, validates evidence, and opens a pull request containing metadata and reports. A refresh failure fails the job; it is never converted to a passing result. The automation cannot publish learner content.

## Deliberate limitations

The repository currently has no authenticated CMS. Reviewer identity is therefore bounded by protected repository access and branch-review policy; production publication needs SSO-backed reviewer identity and an append-only audit store. The reviewer registry is empty by default, so a fresh checkout cannot publish content accidentally. No artifact is currently published, which means the fail-closed learner UI has no deliverable curriculum until accountable humans complete the workflow.
