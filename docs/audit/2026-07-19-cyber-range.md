# CyberMentor AI Cyber Range completion report — 2026-07-19

## Verified inventory

The current seed produces 488 published artifacts, including exactly 80 usable Cyber Range activities. Counts are derived from the generated manifest, normalized seed, content validator, and automated inventory test.

| Classification                 | Verified count | Meaning                                                                                      |
| ------------------------------ | -------------: | -------------------------------------------------------------------------------------------- |
| Interactive simulations        |             40 | Server-owned browser, awareness, or career sessions using bundled fictional evidence         |
| Artifact-analysis labs         |             20 | Bounded investigation of supplied synthetic records                                          |
| Secure-configuration labs      |             20 | Server-verified configuration or remediation decisions                                       |
| Awareness simulations          |             10 | Included in the interactive count                                                            |
| Career/interview simulations   |             10 | Included in the interactive count                                                            |
| Executable Docker/microVM labs |              0 | No executable environment is shipped or claimed                                              |
| Total usable labs              |             80 | Every listed activity has tasks, hints, verification, debrief, reset, and UI/API integration |

The expandable taxonomy contains 59 categories. Every one of the 12 currently published courses links to at least six usable activities.

## Implemented learner flow

The Cyber Range page now supports:

- search across titles, descriptions, categories, and skills;
- category, difficulty, and environment filters;
- guided and independent support modes;
- bookmarks and completion counts;
- explicit simulation/artifact/configuration labels;
- server-owned launch and resume;
- pause, resume, reset, close, and expiration state;
- five progressive hint levels;
- server-side bounded evidence verification;
- wrong-attempt and hint-dependency tracking;
- defensive debrief and reflection;
- local portfolio skill evidence and adaptive mastery evidence.

## Safety boundary

All 80 activities are non-executable, bounded simulations. Their published definitions require no network access, no external targets, no arbitrary commands, and no public target input. Offensive concepts remain restricted to supplied fictional evidence and include authorization, defensive monitoring, remediation, retesting, and cleanup.

The runtime rejects cross-owner instance access with the same 404 response used for an unknown instance. This prevents identifier-based disclosure inside the development runtime, but the owner identifier is a browser-local guest identifier, not authenticated identity. Consequently this is not a production multi-tenant authorization boundary.

## Executed evidence

- `npm run seed:v1`: 488 publications; 80 labs.
- `npm run content:validate`: 488 checked; zero errors and zero warnings.
- `npm run format`: passed after all changes.
- `npm run lint`: passed after all changes.
- `npm test -- --run`: all 12 discovered files and all 108 tests passed; none were disabled.
- `npm run build`: passed after all changes, including `tsc -b`; JS 260.00 kB (80.11 kB gzip), CSS 26.76 kB (6.36 kB gzip).
- Live HTTP gate on isolated audit API port 8791: passed all 15 current checks, including launch, cross-owner denial, progressive hint, wrong evidence, reset, correct completion, grading privacy, projects, recommendations, and web availability.
- In-app browser discovery returned no browser sessions; Playwright, browser console, screenshots, and responsive visual checks were not executed.

## Cyber Range audit table

| Area                            | Check performed                                                                                                                                                        | Result                               | Evidence                                                                      | Defect found                                             | Fix applied                                                                  | Remaining risk                                                                                   |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------ | ----------------------------------------------------------------------------- | -------------------------------------------------------- | ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| Catalog and taxonomy            | Seeded, validated, and counted all published activities and categories                                                                                                 | Pass                                 | 80 usable activities; 59 categories; every course links at least six          | Only 12 shallow evidence exercises existed               | Added the structured 80-activity original library and generated publications | The attached global override still requires six more courses                                     |
| Activity completeness           | Validated story, context, objectives, skills, duration, tasks, evidence, hints, verifier, debrief, reflection, references, safety, version, author, review, and status | Pass                                 | Schema validation: 488/488 publications, zero errors/warnings                 | Prior lab cards lacked a complete workplace flow         | Added complete definitions and learner-safe public projections               | Automated structure cannot replace external SME field evaluation                                 |
| Discovery and dashboard         | Component-tested search, filters, bookmarks, counts, recommendations, weak-skill/mastery evidence, and responsive layout rules                                         | Pass in DOM tests                    | Full component group: 8/8                                                     | Cyber Range was a simple lab list                        | Added a data-driven dashboard and catalog                                    | Real-browser accessibility, console, and mobile visual QA not executed                           |
| Lifecycle                       | Exercised launch, resume, pause, reset, close, expiration, and attempt history                                                                                         | Pass for local runtime               | Runtime unit tests plus live API gate                                         | Start action did not create a controlled instance        | Added server-owned bounded session lifecycle                                 | Sessions and attempts are in memory and disappear on restart                                     |
| Hints and adaptive support      | Tested sequential five-level hints and guided/independent modes                                                                                                        | Pass                                 | Unit/component/live tests                                                     | No progressive hint dependency tracking                  | Enforced ordered reveal and recorded hint use                                | Support adapts locally; there is no durable learner model                                        |
| Verification and answer secrecy | Submitted wrong and correct evidence; inspected public projections                                                                                                     | Pass                                 | Wrong rejected, correct accepted, private verifier absent from public catalog | Lab completion could be trusted without an instance      | Required an authorized active session and server-side verifier               | Current verifiers check bounded text/structured evidence, not hostile VMs                        |
| IDOR boundary                   | Requested a valid instance using another local owner identifier                                                                                                        | Pass for development boundary        | Same 404 as an unknown instance                                               | Instance ownership was not modeled                       | Bound every action to owner and session                                      | Guest browser IDs are forgeable and are not production authentication or tenancy                 |
| Isolation and safety            | Inspected all definitions and enforced environment declarations                                                                                                        | Pass for non-executable simulations  | 80/80 specify no external targets, arbitrary commands, or network access      | Product language risked implying a real executable range | Truthfully classified all activities and added authorization/defense/cleanup | Zero Docker/microVM labs are shipped; hostile-code isolation is unimplemented                    |
| Portfolio evidence              | Completed a lab and recorded skills, attempts, hint use, completion, reflection, and date                                                                              | Partial                              | Store and component tests                                                     | No practical evidence flow                               | Added local formative portfolio evidence                                     | No identity assurance, signature, instructor validation, or durable storage                      |
| Originality and provenance      | Reviewed generated definitions for source references, bounded fictional organizations, and proprietary-platform copying                                                | Pass for declared repository content | Unique definitions, official-source registry, content validator               | Starter range did not meet the requested breadth         | Added original scenarios rather than copied walkthroughs                     | Automated inspection cannot prove universal non-infringement; legal/SME sampling remains prudent |

## Remaining final-integration gaps

- The attached global final override requires 18 courses with 20 lessons each; the current verified academy still contains 12 courses and 144 lessons.
- PostgreSQL, Redis, MinIO, Mailpit, durable authentication, role accounts, RBAC, tenancy, instructor review, and platform analytics are not implemented.
- Cyber Range instances and attempts are in memory; learner reflections and bookmarks are browser-local.
- No Docker image or microVM environment is included, built, or lifecycle-tested.
- No real-browser session was available for the required Playwright audit.

These gaps are not represented as completed features.
