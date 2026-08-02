import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link, useLocation, useParams } from "wouter";
import { apiFetch, ApiError } from "../../lib/api-client";

type ModuleStatus = {
  module_id: string;
  unlocked: boolean;
  completed: boolean;
  required_lessons_completed: boolean;
  required_practices_completed: boolean;
  assessment_passed: boolean;
};

type Activity = {
  id: string;
  type: string;
  title: string;
  scenario: string;
  objective: string;
  prompt: string;
  options?: string[];
  feedback: string;
  linked_skills: string[];
};

type PathwayModule = {
  id: string;
  position: number;
  title: string;
  purpose: string;
  prerequisite_skills: string[];
  objectives: string[];
  linked_skills: string[];
  estimated_minutes: number;
  review_state: string;
  required_lessons: string[];
  required_practices: string[];
  required_assessment: string;
  completion_rules: {
    all_required_lessons_completed: boolean;
    all_required_practices_passed: boolean;
    assessment_minimum_score: number;
  };
  lessons: {
    id: string;
    title: string;
    minutes: number;
    linked_skills: string[];
    review_state: string;
  }[];
  practice: Activity;
  assessment: {
    id: string;
    title: string;
    version: string;
    retake_policy: string;
  };
};

type Pathway = {
  id: string;
  version: string;
  title: string;
  purpose: string;
  review_state: string;
  estimated_minutes: number;
  enrolled: boolean;
  modules: PathwayModule[];
  module_statuses: ModuleStatus[];
};

function message(error: unknown) {
  return error instanceof ApiError
    ? error.message
    : "The learning request could not be completed.";
}

function LoadingOrError({
  loading,
  error,
  retry,
}: {
  loading: boolean;
  error: unknown;
  retry: () => void;
}) {
  if (loading) return <p role="status">Loading your saved learning state…</p>;
  if (!error) return null;
  return (
    <div className="workflow-error" role="alert">
      <p>{message(error)}</p>
      <button className="quiet-button" onClick={retry}>
        Retry
      </button>
    </div>
  );
}

function usePathway() {
  return useQuery({
    queryKey: ["soc-pathway"],
    queryFn: () =>
      apiFetch<Pathway>("/api/v1/learning/pathways/junior-soc-analyst"),
  });
}

export function SocPathwayPage() {
  const query = usePathway();
  const queryClient = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  if (query.isLoading || query.error)
    return (
      <LoadingOrError
        loading={query.isLoading}
        error={query.error}
        retry={() => void query.refetch()}
      />
    );
  const pathway = query.data!;
  async function enroll() {
    setBusy(true);
    setError(undefined);
    try {
      await apiFetch("/api/v1/learning/enrollments", {
        method: "POST",
        body: JSON.stringify({ course_publication_id: pathway.id }),
      });
      await Promise.all([
        query.refetch(),
        queryClient.invalidateQueries({ queryKey: ["learner-dashboard"] }),
      ]);
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="workflow-panel">
      <span className="eyebrow">ORDERED · SERVER-OWNED PROGRESS</span>
      <h1>{pathway.title}</h1>
      <p>{pathway.purpose}</p>
      <div className="safety-notice">
        Content review: {pathway.review_state.replaceAll("-", " ")} · Version{" "}
        {pathway.version}
      </div>
      {error != null && <div className="workflow-error">{message(error)}</div>}
      {!pathway.enrolled && (
        <button className="primary" disabled={busy} onClick={enroll}>
          {busy ? "Enrolling…" : "Enrol in this pathway"}
        </button>
      )}
      <div className="roadmap-list">
        {pathway.modules.map((module) => {
          const status = pathway.module_statuses.find(
            (item) => item.module_id === module.id,
          );
          return (
            <article key={module.id}>
              <span>{String(module.position).padStart(2, "0")}</span>
              <div>
                <small>
                  {status?.completed
                    ? "COMPLETE"
                    : status?.unlocked
                      ? "AVAILABLE"
                      : "PREREQUISITE REQUIRED"}{" "}
                  · {module.estimated_minutes} MIN
                </small>
                <h2>{module.title}</h2>
                <p>{module.purpose}</p>
                <p>
                  Completion: required lesson, practice, and a 70% module
                  assessment score.
                </p>
                <Link to={`/academy/pathway/modules/${module.id}`}>
                  {status?.completed ? "Review module" : "Open module"}
                </Link>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

export function SocModulePage() {
  const { moduleId } = useParams<{ moduleId: string }>();
  const query = usePathway();
  if (query.isLoading || query.error)
    return (
      <LoadingOrError
        loading={query.isLoading}
        error={query.error}
        retry={() => void query.refetch()}
      />
    );
  const module = query.data!.modules.find((item) => item.id === moduleId);
  const status = query.data!.module_statuses.find(
    (item) => item.module_id === moduleId,
  );
  if (!module)
    return <div className="workflow-error">The requested module was not found.</div>;
  return (
    <section className="workflow-panel">
      <Link to="/academy/pathway">← Pathway</Link>
      <span className="eyebrow">MODULE {module.position}</span>
      <h1>{module.title}</h1>
      <p>{module.purpose}</p>
      <h2>Learning objectives</h2>
      <ul>
        {module.objectives.map((objective) => (
          <li key={objective}>{objective}</li>
        ))}
      </ul>
      {!status?.unlocked && (
        <div className="safety-notice">
          Earlier required modules are incomplete. You may preview this module,
          but the roadmap still recommends completing prerequisites first.
        </div>
      )}
      <div className="workflow-cards">
        {module.lessons.map((lesson) => (
          <article className="workflow-card" key={lesson.id}>
            <small>
              INSTRUCTIONAL LESSON · {lesson.minutes} MIN ·{" "}
              {status?.required_lessons_completed ? "COMPLETE" : "REQUIRED"}
            </small>
            <h3>{lesson.title}</h3>
            <p>{lesson.linked_skills.join(" · ")}</p>
            <Link to={`/academy/pathway/lessons/${lesson.id}`}>Study lesson</Link>
          </article>
        ))}
        <article className="workflow-card">
          <small>
            PRACTICE · {status?.required_practices_completed ? "PASSED" : "REQUIRED"}
          </small>
          <h3>{module.practice.title}</h3>
          <p>{module.practice.objective}</p>
          <Link to={`/academy/pathway/practice/${module.practice.id}`}>
            Open practice
          </Link>
        </article>
        <article className="workflow-card">
          <small>
            ASSESSMENT · {status?.assessment_passed ? "PASSED" : "70% REQUIRED"}
          </small>
          <h3>{module.assessment.title}</h3>
          <p>{module.assessment.retake_policy}</p>
          <Link to={`/academy/pathway/assessments/${module.assessment.id}`}>
            Open assessment
          </Link>
        </article>
      </div>
    </section>
  );
}

type Lesson = {
  id: string;
  version: string;
  title: string;
  minutes: number;
  review_state: string;
  why_it_matters: string;
  prerequisites: string[];
  objectives: string[];
  concept: string;
  worked_example: string;
  evidence_artifact: string;
  terminology: { term: string; definition: string }[];
  common_misconception: string;
  guided_practice: string;
  reflection_question: string;
  practical_relevance: string;
  linked_skills: string[];
  references: {
    publisher: string;
    title: string;
    url: string;
    retrieved_at: string;
    source_date: string;
  }[];
  progress: { status: string; version: number } | null;
};

export function SocLessonPage() {
  const { lessonId } = useParams<{ lessonId: string }>();
  const queryClient = useQueryClient();
  const [, navigate] = useLocation();
  const query = useQuery({
    queryKey: ["soc-lesson", lessonId],
    queryFn: () =>
      apiFetch<Lesson>(
        `/api/v1/learning/pathways/junior-soc-analyst/lessons/${lessonId}`,
      ),
  });
  const [note, setNote] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState<unknown>();
  if (query.isLoading || query.error)
    return (
      <LoadingOrError
        loading={query.isLoading}
        error={query.error}
        retry={() => void query.refetch()}
      />
    );
  const item = query.data!;
  async function complete() {
    setError(undefined);
    try {
      await apiFetch(`/api/v1/learning/lessons/${item.id}/progress`, {
        method: "PUT",
        body: JSON.stringify({
          lesson_version: item.version,
          status: "completed",
          percent_complete: 100,
          last_position: "reflection",
          expected_version: item.progress?.version,
        }),
      });
      if (note.trim()) {
        await apiFetch("/api/v1/learning/notes", {
          method: "POST",
          body: JSON.stringify({
            lesson_publication_id: item.id,
            body: note.trim(),
          }),
        });
      }
      await Promise.all([
        query.refetch(),
        queryClient.invalidateQueries({ queryKey: ["soc-pathway"] }),
        queryClient.invalidateQueries({ queryKey: ["learner-dashboard"] }),
      ]);
      setNotice("Lesson completion and private note are saved on the server.");
    } catch (caught) {
      setError(caught);
    }
  }
  async function bookmark() {
    setError(undefined);
    try {
      await apiFetch("/api/v1/learning/bookmarks", {
        method: "POST",
        body: JSON.stringify({ resource_type: "lesson", resource_id: item.id }),
      });
      setNotice("Bookmark saved on the server.");
      await queryClient.invalidateQueries({ queryKey: ["learner-dashboard"] });
    } catch (caught) {
      setError(caught);
    }
  }
  return (
    <article className="workflow-panel narrow lesson">
      <button className="quiet-button" onClick={() => navigate("/academy/pathway")}>
        ← Pathway
      </button>
      <span className="eyebrow">
        {item.minutes} MIN · {item.review_state.replaceAll("-", " ")}
      </span>
      <h1>{item.title}</h1>
      {error != null && <div className="workflow-error">{message(error)}</div>}
      {notice && <div className="workflow-feedback">{notice}</div>}
      <h2>Why this matters in SOC work</h2>
      <p>{item.why_it_matters}</p>
      <h2>Objectives</h2>
      <ul>{item.objectives.map((value) => <li key={value}>{value}</li>)}</ul>
      <h2>Concept</h2>
      <p>{item.concept}</p>
      <h2>Synthetic investigation evidence</h2>
      <pre className="evidence-view">{item.evidence_artifact}</pre>
      <h2>Worked example</h2>
      <p>{item.worked_example}</p>
      <h2>Terminology</h2>
      <dl>
        {item.terminology.map((term) => (
          <div key={term.term}>
            <dt>{term.term}</dt>
            <dd>{term.definition}</dd>
          </div>
        ))}
      </dl>
      <h2>Common misconception</h2>
      <p>{item.common_misconception}</p>
      <h2>Guided practice</h2>
      <p>{item.guided_practice}</p>
      <h2>Reflection</h2>
      <p>{item.reflection_question}</p>
      <label>
        Private lesson note
        <textarea
          aria-label="Private lesson note"
          rows={4}
          value={note}
          onChange={(event) => setNote(event.target.value)}
        />
      </label>
      <div className="lesson-actions">
        <button className="quiet-button" onClick={bookmark}>
          Add bookmark
        </button>
        <button className="primary" onClick={complete}>
          {item.progress?.status === "completed"
            ? "Save note and keep complete"
            : "Save and complete lesson"}
        </button>
      </div>
      <h2>Approved references</h2>
      <ul>
        {item.references.map((reference) => (
          <li key={reference.url}>
            <a href={reference.url} target="_blank" rel="noreferrer">
              {reference.publisher}: {reference.title}
            </a>{" "}
            (source {reference.source_date}; retrieved {reference.retrieved_at})
          </li>
        ))}
      </ul>
    </article>
  );
}

function responseFromForm(
  activity: { type: string; options?: string[] },
  data: FormData,
  prefix = "",
) {
  if (activity.type === "multiple_choice" || activity.type === "email_header_analysis")
    return { choices: data.getAll(`${prefix}choice`).map(Number) };
  if (activity.type === "ordering")
    return {
      order: (activity.options || [])
        .map((_, index) => ({
          index,
          rank: Number(data.get(`${prefix}rank-${index}`)),
        }))
        .sort((left, right) => left.rank - right.rank)
        .map((item) => item.index),
    };
  if (activity.type === "short_written_response")
    return { answer: String(data.get(`${prefix}answer`) || "") };
  return { choice: Number(data.get(`${prefix}choice`)) };
}

function ActivityFields({
  activity,
  prefix = "",
}: {
  activity: Activity;
  prefix?: string;
}) {
  if (activity.type === "short_written_response")
    return (
      <label>
        Your evidence-based response
        <textarea name={`${prefix}answer`} minLength={80} rows={6} required />
      </label>
    );
  return (
    <>
      {(activity.options || []).map((option, index) =>
        activity.type === "ordering" ? (
          <label className="order-row" key={option}>
            <select name={`${prefix}rank-${index}`} defaultValue={index + 1}>
              {(activity.options || []).map((_, rank) => (
                <option key={rank} value={rank + 1}>{rank + 1}</option>
              ))}
            </select>
            {option}
          </label>
        ) : (
          <label className="choice-row" key={option}>
            <input
              name={`${prefix}choice`}
              type={
                activity.type === "multiple_choice" ||
                activity.type === "email_header_analysis"
                  ? "checkbox"
                  : "radio"
              }
              value={index}
              required={
                activity.type !== "multiple_choice" &&
                activity.type !== "email_header_analysis"
              }
            />
            {option}
          </label>
        ),
      )}
    </>
  );
}

export function SocPracticePage() {
  const { activityId } = useParams<{ activityId: string }>();
  const query = usePathway();
  const queryClient = useQueryClient();
  const [result, setResult] = useState<{ score: number; passed: boolean; feedback: string }>();
  const [error, setError] = useState<unknown>();
  if (query.isLoading || query.error)
    return (
      <LoadingOrError loading={query.isLoading} error={query.error} retry={() => void query.refetch()} />
    );
  const activity = query.data!.modules
    .map((module) => module.practice)
    .find((item) => item.id === activityId);
  if (!activity) return <div className="workflow-error">Practice not found.</div>;
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(undefined);
    try {
      const value = await apiFetch<typeof result>(
        `/api/v1/learning/pathways/junior-soc-analyst/activities/${activity!.id}/submit`,
        {
          method: "POST",
          body: JSON.stringify({
            response: responseFromForm(
              activity!,
              new FormData(event.currentTarget),
            ),
            idempotency_key: crypto.randomUUID(),
            hints_used: 0,
          }),
        },
      );
      setResult(value);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["soc-pathway"] }),
        queryClient.invalidateQueries({ queryKey: ["learner-dashboard"] }),
      ]);
    } catch (caught) {
      setError(caught);
    }
  }
  return (
    <section className="workflow-panel narrow">
      <Link to="/academy/pathway">← Pathway</Link>
      <span className="eyebrow">{activity.type.replaceAll("_", " ")}</span>
      <h1>{activity.title}</h1>
      <p>{activity.scenario}</p>
      <p><strong>Objective:</strong> {activity.objective}</p>
      {error != null && <div className="workflow-error">{message(error)}</div>}
      {result ? (
        <div className="completion-panel" role="status">
          <h2>{result.passed ? "Practice passed" : "More evidence needed"}</h2>
          <p>Score: {Math.round(result.score * 100)}%</p>
          <p>{result.feedback}</p>
        </div>
      ) : (
        <form className="diagnostic-card" onSubmit={submit}>
          <h2>{activity.prompt}</h2>
          <ActivityFields activity={activity} />
          <button className="primary">Submit for server validation</button>
        </form>
      )}
    </section>
  );
}

type Assessment = {
  id: string;
  version: string;
  title: string;
  retake_policy: string;
  questions: (Activity & { weight: number; skill: string })[];
  attempts: { id: string; score: number; passed: boolean; submitted_at: string }[];
};

export function SocAssessmentPage() {
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["soc-assessment", assessmentId],
    queryFn: () =>
      apiFetch<Assessment>(
        `/api/v1/learning/pathways/junior-soc-analyst/assessments/${assessmentId}`,
      ),
  });
  const [result, setResult] = useState<{ score: number; passed: boolean; feedback: string }>();
  const [error, setError] = useState<unknown>();
  if (query.isLoading || query.error)
    return (
      <LoadingOrError loading={query.isLoading} error={query.error} retry={() => void query.refetch()} />
    );
  const assessment = query.data!;
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const responses = Object.fromEntries(
      assessment.questions.map((question) => [
        question.id,
        responseFromForm(question, data, `${question.id}-`),
      ]),
    );
    setError(undefined);
    try {
      const value = await apiFetch<typeof result>(
        `/api/v1/learning/pathways/junior-soc-analyst/assessments/${assessment.id}/submit`,
        {
          method: "POST",
          body: JSON.stringify({
            responses,
            idempotency_key: crypto.randomUUID(),
            hints_used: 0,
          }),
        },
      );
      setResult(value);
      await Promise.all([
        query.refetch(),
        queryClient.invalidateQueries({ queryKey: ["soc-pathway"] }),
        queryClient.invalidateQueries({ queryKey: ["learner-dashboard"] }),
      ]);
    } catch (caught) {
      setError(caught);
    }
  }
  return (
    <section className="workflow-panel narrow">
      <Link to="/academy/pathway">← Pathway</Link>
      <span className="eyebrow">SERVER-GRADED · VERSION {assessment.version}</span>
      <h1>{assessment.title}</h1>
      <p>{assessment.retake_policy}</p>
      {error != null && <div className="workflow-error">{message(error)}</div>}
      {result && (
        <div className="completion-panel" role="status">
          <h2>{result.passed ? "Assessment passed" : "Reassessment recommended"}</h2>
          <p>Score: {Math.round(result.score * 100)}%</p>
          <p>{result.feedback}</p>
        </div>
      )}
      <form className="workflow-form" onSubmit={submit}>
        {assessment.questions.map((question, index) => (
          <fieldset data-question={question.id} key={question.id}>
            <legend>{index + 1}. {question.prompt}</legend>
            <ActivityFields activity={question} prefix={`${question.id}-`} />
          </fieldset>
        ))}
        <button className="primary">Submit module assessment</button>
      </form>
      {assessment.attempts.length > 0 && (
        <>
          <h2>Attempt history</h2>
          <ul>
            {assessment.attempts.map((attempt) => (
              <li key={attempt.id}>
                {Math.round(attempt.score * 100)}% · {attempt.passed ? "passed" : "not passed"} ·{" "}
                {new Date(attempt.submitted_at).toLocaleString()}
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

type SkillEvidenceResponse = {
  skills: {
    skill_id: string;
    skill_name: string;
    current_estimate: number;
    confidence: number;
    independence: number;
    supporting_evidence_count: number;
    weak_area: boolean;
    recent_evidence: string | null;
    next_review: string | null;
    why_changed: string;
  }[];
  evidence: {
    id: string;
    skill_id: string;
    skill_name: string;
    source_activity: string;
    evidence_type: string;
    result: number;
    independence: number;
    hint_usage: number;
    timestamp: string;
    evaluator: string;
    valid: boolean;
  }[];
};

export function SocSkillsPage() {
  const evidence = useQuery({
    queryKey: ["skill-evidence"],
    queryFn: () => apiFetch<SkillEvidenceResponse>("/api/v1/learning/skills/evidence"),
  });
  if (evidence.isLoading || evidence.error)
    return (
      <LoadingOrError
        loading={evidence.isLoading}
        error={evidence.error}
        retry={() => void evidence.refetch()}
      />
    );
  return (
    <section className="workflow-panel">
      <span className="eyebrow">OBSERVED EVIDENCE</span>
      <h1>Your SOC skill evidence</h1>
      <p>
        Estimates require multiple evidence items. A single correct response does
        not establish mastery.
      </p>
      {evidence.data!.skills.length > 0 && (
        <div className="workflow-cards">
          {evidence.data!.skills.map((skill) => (
            <article className="workflow-card" key={skill.skill_id}>
              <small>{skill.weak_area ? "DEVELOPING AREA" : "SUPPORTED AREA"}</small>
              <h2>{skill.skill_name}</h2>
              <p>
                Estimate {Math.round(skill.current_estimate * 100)}% · confidence{" "}
                {Math.round(skill.confidence * 100)}% · independence{" "}
                {Math.round(skill.independence * 100)}%
              </p>
              <p>{skill.why_changed}</p>
              <small>
                {skill.supporting_evidence_count} supporting item(s) · next review{" "}
                {skill.next_review
                  ? new Date(skill.next_review).toLocaleDateString()
                  : "not scheduled"}
              </small>
            </article>
          ))}
        </div>
      )}
      <h2>Recent evidence</h2>
      {evidence.data!.evidence.length === 0 ? (
        <div className="empty-state">
          No learning evidence yet. Complete a pathway practice or assessment.
        </div>
      ) : (
        <div className="workflow-cards">
          {evidence.data!.evidence.map((item) => (
            <article className="workflow-card" key={item.id}>
              <small>{item.evidence_type.replaceAll("_", " ")} · {item.evaluator}</small>
              <h2>{item.skill_name}</h2>
              <p>Result {Math.round(item.result * 100)}% · independence{" "}
                {Math.round(item.independence * 100)}% · hints {item.hint_usage}</p>
              <p>Source: {item.source_activity}</p>
              <small>{new Date(item.timestamp).toLocaleString()}</small>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
