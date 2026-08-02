# Trusted Learning Engine

## Boundaries

The FastAPI service owns enrollment, progress, notes, bookmarks, pathway practices, module assessments, attempt history, grading, skill evidence, mastery updates, and roadmap rebuilding. Authenticated progress is not derived from `localStorage`.

The existing Node service remains the delivery and validation service for the wider published catalogue. The new Junior SOC sequence uses the trusted backend so graded learner evidence does not depend on the legacy stateless grading endpoint.

## Learner-safe contracts

Learner responses include prompts, options, objectives, feedback policy, version, skills, and review state. `private_answer` never enters pathway, lesson, practice, or assessment payloads.

Supported pathway activity renderers and trusted evaluators are:

- instructional lesson;
- single-choice/scenario decision;
- multiple-choice;
- ordering;
- command interpretation;
- log interpretation;
- email-header analysis;
- matching represented as a deterministic evidence choice;
- guided investigation;
- short written response using a deterministic keyword/length rubric;
- module assessment.

Multiple-choice and ordering responses support deterministic partial credit. Written responses use a bounded rubric. Sentinel is not a grading authority.

## Persistence and concurrency

- `Enrollment` stores pathway enrollment and completion.
- `LessonProgress` stores status, last position, content version, and an optimistic concurrency version.
- `LearnerNote` is server-owned and saves are upserts by owner and lesson.
- `Bookmark` is unique by owner, resource type, and resource ID.
- `LearningActivityAttempt` stores response, score, pass state, hints, evaluator, feedback, version, submission time, and idempotency key.
- `SkillEvidence` stores the tenant/user, skill, source, source version, score, independence, hints, attempt sequence, timestamp, and provenance hash.

An idempotency key can replay the same response and receive the same attempt. Reusing it for a different activity or response returns a conflict. Tenant and user filters are applied to every learner record lookup.

## Mastery and adaptation

One learning activity creates low-confidence evidence and cannot create high mastery. Later evidence updates the estimate with bounded weighting, confidence, evidence strength, independence, a reason summary, and a next-review date.

The roadmap is rebuilt after trusted learning evidence. It can:

- preserve the required SOC course and mission;
- target weak prerequisites;
- retain advanced network work for demonstrated networking strength;
- bridge strong network reasoning into weak Linux investigation;
- raise remediation and guidance after repeated unsuccessful evidence;
- reduce guidance and increase independent reassessment after successful hint-free evidence.

Every stored recommendation includes a learner-visible reason. The deterministic rules select approved activities; no LLM rewrites required curriculum.

