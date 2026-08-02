# Adaptive learning architecture

## Separation of responsibilities

- The verified curriculum defines required lessons, official assessments, completion rules, rubrics, labs, scenarios, and certification mappings.
- The versioned skill graph defines stable skill IDs, hierarchy, prerequisites, domain, description, and difficulty. Its current `draft-taxonomy` status is explicit; human review is still required.
- The deterministic adaptive engine calculates advisory mastery and chooses from verified published practice pools.
- Sentinel explains approved material and supplies bounded support. It does not define the official sequence, invent required exercises, or make grading decisions.

Learners can always open the complete published curriculum. Recommendations appear as optional dashboard cards with a plain-language reason and a dismiss control; they do not replace or hide official lessons.

## Mastery model

For each accepted evidence item, the engine calculates:

`item weight = source weight × independence × attempt penalty × hint penalty × evidence-quality weight`

Source weights are lesson check `0.20`, quiz `0.45`, exam `0.65`, lab `0.80`, scenario `0.70`, project `0.90`, retention check `0.75`, and command recall `0.12`. Unsupported events such as opening a lesson are ignored. The weighted observed score is blended with the prior estimate in proportion to prior confidence. Confidence grows with total evidence weight, number of items, and diversity of evidence types, is capped at `0.98`, and remains below `0.20` after one perfect quiz response from a new learner.

Recency applies a gradual exponential factor with a 365-day time constant and a floor of `0.72`. Returning learners therefore retain progress and receive short retention checks rather than being reset.

## Recommendation model

The engine filters out every activity that is not both `verified` and `published`, then considers prerequisite readiness, mastery gaps, confidence, difficulty fit, available time, learner goals, role track, recent mistakes, evidence pattern, inactivity, repeated failure, and authenticated instructor policy. It can prefer practical work for strong theory/weak practice, conceptual explanations for command memorization, bridge activities across strong and weak domains, expert challenges for advanced learners, and prerequisite interventions after repeated failures.

Every recommendation includes a reason, priority, difficulty, activity type, hint start level, engine version, and repeated-failure instructor flag. Progressive hints are stored with the reviewed activity; the engine selects a starting level and never generates a hidden solution.

Diagnostics branch from a standard question toward easier or harder approved questions. Three uniformly correct or incorrect recent results stop the short diagnostic. Question keys remain server-side.

Decision logs record selected IDs, bounded feature summaries, reasons, and engine version. They explicitly exclude chain-of-thought. The local server keeps at most 500 logs in memory; production requires tenant-keyed durable storage and retention controls.

## Instructor authority

The migration models fixed, adaptive-practice, and adaptive-low-stakes modes; mandatory activities; forced prerequisites; mastery thresholds; accommodations; and an override note. The unauthenticated demo API intentionally ignores client-supplied instructor policy so a learner cannot spoof it. An authenticated instructor UI/API, audit trail, and organization authorization are not implemented.

## Acceptance coverage

Automated tests cover all required profiles:

- strong networking and weak Linux;
- strong theory and weak practical work;
- weak theory and strong tool memorization;
- advanced learner;
- learner returning after two inactive months;
- repeated prerequisite failure with targeted intervention and instructor flag.

They also cover one-answer confidence limits, stronger weighting for independent lab evidence, diagnostic branching, stored hints, review expiry, unpublished-activity exclusion, and dual-use safety approval.

## Known limitations

The published activity and question pools are empty because no accountable humans are enrolled to review them. Mastery state is browser-local and client-supplied, so it is advisory only. There is no durable event store, authenticated instructor policy, cohort analytics, certification engine, adaptive lab orchestration, or production experiment framework. Those boundaries prevent the current implementation from being represented as a production personalization system.
