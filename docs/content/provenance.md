# Content provenance record

Audit date: 2026-07-19.

The curriculum in `src/data/courses.ts` was authored for this repository from an original topic specification and a shared instructional template. No third-party course export, proprietary assessment bank, certification question set, video transcript, or scraped lesson corpus is present in the repository. A web search for a distinctive sentence from the lesson template returned no matching source during this audit; that is evidence of no obvious verbatim web reuse, not a mathematical proof of originality.

The eight unique reference targets are public primary sources from NIST, CISA, MITRE, OWASP, the Python Software Foundation, and the Linux Kernel Organization. The audit opened or searched each target. CISA references were updated to stable official pages or the official Cloud Security Technical Reference Architecture PDF. Each legacy lesson stores one source title, publisher, URL, and access date. Those links were not mapped claim by claim, so the application marks all 144 records `legacy-unverified`; they are blocked from learner delivery, grading, lab APIs, adaptive pools, Sentinel grounding, and any “Verified References” label.

Important quality limitation: the 144 lesson records use the same three-paragraph instructional template with topic substitution. They satisfy the structural schema and exceed 100 words, but they do **not** constitute 144 independently researched, substantial lessons. Module quizzes also reuse one generic question pattern. The 12 project entries are one-sentence briefs; scenario packs, full rubrics, model expectations, and downloadable evidence are absent. These limitations are production blockers for a paid academy and are recorded in the audit and roadmap.

No executable technical commands are included in the lesson corpus, so there were no commands to validate. Offensive-security topics contain repeated authorization, isolation, defensive visibility, remediation, verification, reporting, and cleanup language. The ten implemented practice exercises use fixed fictional evidence and never initiate network scans, exploit processes, or external requests.

New material must use the source registry, digest snapshots, claim-level evidence, semantic versions, and independent approvals described in [the ingestion pipeline](ingestion-pipeline.md). No verified learner lesson has been published through that pipeline yet; the included human-authored fixture exists only to exercise validation.
