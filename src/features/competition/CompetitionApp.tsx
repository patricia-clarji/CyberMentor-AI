import { useQuery } from "@tanstack/react-query";
import {
  BookOpenCheck,
  ClipboardCheck,
  LogOut,
  Map,
  Play,
  ShieldCheck,
} from "lucide-react";
import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { Link, Route, Switch, useLocation } from "wouter";
import { App } from "../../App";
import { apiFetch, ApiError } from "../../lib/api-client";
import { useAuth } from "../auth/auth-context";
import {
  SocAssessmentPage,
  SocLessonPage,
  SocModulePage,
  SocPathwayPage,
  SocPracticePage,
  SocSkillsPage,
} from "./SocLearningPages";
import { LabCatalogPage, LabWorkspacePage } from "./LabWorkspace";
import { ManagedContentPage } from "./ManagedContentPage";

type Dashboard = {
  profile: {
    experience_level: string | null;
    weekly_minutes: number | null;
    onboarding_completed_at: string | null;
  } | null;
  primary_goal: string | null;
  enrollments: { course_publication_id: string; status: string }[];
  lesson_progress: { status: string; percent_complete: number }[];
  skills: {
    skillId: string;
    name: string;
    mastery: number;
    confidence: number;
    reasoning: string;
  }[];
  recommendations: {
    activityId: string;
    activityType: string;
    reason: string;
    interventionType: string;
    required: boolean;
  }[];
};

function WorkflowShell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const [, navigate] = useLocation();
  async function signOut() {
    await logout();
    navigate("/login", { replace: true });
  }
  return (
    <div className="competition-shell">
      <a className="skip-link" href="#competition-main">
        Skip to main content
      </a>
      <header className="competition-header">
        <Link className="competition-brand" to="/academy">
          <ShieldCheck aria-hidden="true" />
          <span>
            CyberMentor
            <small>Junior SOC readiness beta</small>
          </span>
        </Link>
        <nav aria-label="Learner workflow">
          <Link to="/academy">Overview</Link>
          <Link to="/academy/diagnostic">Diagnostic</Link>
          <Link to="/academy/roadmap">Roadmap</Link>
          <Link to="/academy/pathway">SOC pathway</Link>
          <Link to="/academy/course">Course</Link>
          <Link to="/academy/skills">Skills</Link>
          <Link to="/academy/labs">Labs</Link>
          <Link to="/academy/mission">Mission</Link>
          <Link to="/academy/project">Project</Link>
          <Link to="/academy/sentinel">Sentinel</Link>
          <Link to="/organization/assignments">Assigned work</Link>
          <Link to="/portfolio/sharing">Share evidence</Link>
        </nav>
        <div className="learner-account">
          <span>{user?.display_name}</span>
          <button className="quiet-button" onClick={signOut}>
            <LogOut aria-hidden="true" /> Sign out
          </button>
        </div>
      </header>
      <main id="competition-main" className="competition-main">
        {children}
      </main>
    </div>
  );
}

function ErrorPanel({ error }: { error: unknown }) {
  const message =
    error instanceof ApiError
      ? error.message
      : "The request could not be completed.";
  return (
    <div className="workflow-error" role="alert">
      {message}
    </div>
  );
}

function DashboardPage() {
  const query = useQuery({
    queryKey: ["learner-dashboard"],
    queryFn: () => apiFetch<Dashboard>("/api/v1/learning/dashboard"),
  });
  if (query.isLoading)
    return <p role="status">Loading your evidence profile…</p>;
  if (query.error) return <ErrorPanel error={query.error} />;
  const data = query.data!;
  const demonstrated = data.skills.filter(
    (skill) => skill.confidence >= 0.4,
  ).length;
  return (
    <>
      <section className="workflow-hero">
        <span className="kicker">PRIVATE BETA · EVIDENCE FIRST</span>
        <h1>Build your Junior SOC analyst readiness.</h1>
        <p>
          Your roadmap changes from observed diagnostic and workplace evidence.
          Confidence is shown separately from estimated mastery.
        </p>
        {!data.profile?.onboarding_completed_at && (
          <Link className="primary-link" to="/academy/onboarding">
            Set your learning constraints
          </Link>
        )}
      </section>
      <section className="evidence-stats" aria-label="Recorded learner state">
        <article>
          <strong>{data.skills.length}</strong>
          <span>skills with recorded evidence</span>
        </article>
        <article>
          <strong>{demonstrated}</strong>
          <span>skills with practical confidence</span>
        </article>
        <article>
          <strong>{data.recommendations.length}</strong>
          <span>active roadmap actions</span>
        </article>
      </section>
      <section className="workflow-grid" aria-labelledby="next-actions">
        <div>
          <span className="eyebrow">01 · Establish a baseline</span>
          <h2 id="next-actions">Your verified workflow</h2>
          <p>
            Complete each step with your own reasoning. Diagnostic results are
            initial evidence, while mission performance raises practical
            confidence.
          </p>
        </div>
        <div className="workflow-cards">
          <WorkflowCard
            icon={<ClipboardCheck />}
            title="Diagnostic"
            text="Twelve server-graded decisions across networking, operating systems, evidence, and reporting."
            href="/academy/diagnostic"
          />
          <WorkflowCard
            icon={<Map />}
            title="Adaptive roadmap"
            text="Required prerequisites and bridge activities are based on your stored evidence."
            href="/academy/roadmap"
          />
          <WorkflowCard
            icon={<BookOpenCheck />}
            title="Junior SOC pathway"
            text="Study the ordered modules, complete server-graded practice, and build skill evidence."
            href="/academy/pathway"
          />
          <WorkflowCard
            icon={<Play />}
            title="Harbor Light mission"
            text="Investigate original synthetic evidence and produce a verifiable workplace result."
            href="/academy/mission"
          />
          <WorkflowCard
            icon={<BookOpenCheck />}
            title="Professional project"
            text="Submit a reproducible SOC escalation for an authorized human rubric review."
            href="/academy/project"
          />
        </div>
      </section>
    </>
  );
}

function WorkflowCard({
  icon,
  title,
  text,
  href,
}: {
  icon: ReactNode;
  title: string;
  text: string;
  href: string;
}) {
  return (
    <article className="workflow-card">
      <div aria-hidden="true">{icon}</div>
      <h3>{title}</h3>
      <p>{text}</p>
      <Link to={href}>Continue</Link>
    </article>
  );
}

function OnboardingPage() {
  const [, navigate] = useLocation();
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(undefined);
    const data = new FormData(event.currentTarget);
    try {
      await apiFetch("/api/v1/learning/onboarding", {
        method: "PUT",
        body: JSON.stringify({
          experience_level: data.get("experience"),
          career_objective: "Junior SOC Analyst",
          weekly_minutes: Number(data.get("weeklyMinutes")),
          networking_confidence: Number(data.get("networking")),
          linux_confidence: Number(data.get("linux")),
          investigation_confidence: Number(data.get("investigation")),
          learning_preferences: data.getAll("preference"),
          accessibility_needs: data.get("accessibility") || null,
        }),
      });
      navigate("/academy/diagnostic");
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="workflow-panel narrow">
      <span className="eyebrow">LEARNER CONSTRAINTS</span>
      <h1>Shape the starting plan.</h1>
      <p>Self-ratings guide support only. They are not skill evidence.</p>
      {error != null && <ErrorPanel error={error} />}
      <form className="workflow-form" onSubmit={submit}>
        <label>
          Current experience
          <select name="experience" defaultValue="beginner">
            <option value="beginner">Beginner</option>
            <option value="some-practice">Some practical experience</option>
            <option value="career-switcher">Career switcher</option>
          </select>
        </label>
        <label>
          Weekly learning time
          <select name="weeklyMinutes" defaultValue="360">
            <option value="180">3 hours</option>
            <option value="360">6 hours</option>
            <option value="600">10 hours</option>
          </select>
        </label>
        {[
          ["networking", "Networking confidence"],
          ["linux", "Linux confidence"],
          ["investigation", "Investigation confidence"],
        ].map(([name, label]) => (
          <label key={name}>
            {label}
            <input name={name} type="range" min="1" max="5" defaultValue="2" />
          </label>
        ))}
        <fieldset>
          <legend>Helpful learning modes</legend>
          {["worked-examples", "guided-practice", "visual-explanations"].map(
            (value) => (
              <label className="choice-row" key={value}>
                <input name="preference" type="checkbox" value={value} />
                {value.replace("-", " ")}
              </label>
            ),
          )}
        </fieldset>
        <label>
          Accessibility needs (optional)
          <textarea name="accessibility" rows={3} />
        </label>
        <button className="primary" disabled={busy}>
          {busy ? "Saving…" : "Save and begin diagnostic"}
        </button>
      </form>
    </section>
  );
}

type DiagnosticQuestion = {
  id: string;
  question_type: string;
  prompt: string;
  options: string[];
  skill_key: string;
  position: number;
  total: number;
};

function DiagnosticPage() {
  const [attemptId, setAttemptId] = useState("");
  const [question, setQuestion] = useState<DiagnosticQuestion>();
  const [feedback, setFeedback] = useState("");
  const [completed, setCompleted] = useState(false);
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  const [selfAssessment, setSelfAssessment] = useState("");
  async function start() {
    setBusy(true);
    setError(undefined);
    try {
      const result = await apiFetch<{
        attempt_id: string;
        question: DiagnosticQuestion;
      }>("/api/v1/diagnostic/start", {
        method: "POST",
        body: JSON.stringify({ self_assessment_text: selfAssessment }),
      });
      setAttemptId(result.attempt_id);
      setQuestion(result.question);
      setFeedback("");
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  }
  async function answer(response: Record<string, unknown>) {
    if (!question) return;
    setBusy(true);
    setError(undefined);
    try {
      const result = await apiFetch<{
        correct: boolean;
        explanation: string;
        confidence_notice: string;
        completed: boolean;
        next_question: DiagnosticQuestion | null;
      }>(`/api/v1/diagnostic/${attemptId}/responses/${question.id}`, {
        method: "POST",
        body: JSON.stringify({ response }),
      });
      setFeedback(
        `${result.correct ? "Supported." : "Revisit this."} ${result.explanation} ${result.confidence_notice}`,
      );
      setCompleted(result.completed);
      setQuestion(result.next_question ?? undefined);
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="workflow-panel narrow">
      <span className="eyebrow">SERVER-GRADED BASELINE</span>
      <h1>Junior SOC diagnostic</h1>
      <p>
        This is low-confidence initial evidence. Answer keys remain on the
        trusted server and are never included in the question response.
      </p>
      {error != null && <ErrorPanel error={error} />}
      {!attemptId && (
        <>
          <label>
            In your own words, what cybersecurity skill do you want to improve?
            <textarea
              rows={4}
              value={selfAssessment}
              onChange={(event) => setSelfAssessment(event.target.value)}
              placeholder="Example: I understand networking but need practice with Linux logs and SOC alerts."
            />
          </label>
          <p className="form-hint">
            This text gives the adaptive engine a low-confidence starting signal;
            the graded diagnostic remains the authoritative evidence.
          </p>
          <button className="primary" onClick={start} disabled={busy}>
            {busy ? "Preparing…" : "Start diagnostic"}
          </button>
        </>
      )}
      {feedback && (
        <div className="workflow-feedback" role="status">
          {feedback}
        </div>
      )}
      {question && (
        <DiagnosticQuestionForm
          key={question.id}
          question={question}
          busy={busy}
          onAnswer={answer}
        />
      )}
      {completed && (
        <div className="completion-panel">
          <h2>Baseline recorded</h2>
          <p>Your evidence-based roadmap is ready.</p>
          <Link className="primary-link" to="/academy/roadmap">
            Review roadmap
          </Link>
        </div>
      )}
    </section>
  );
}

function DiagnosticQuestionForm({
  question,
  busy,
  onAnswer,
}: {
  question: DiagnosticQuestion;
  busy: boolean;
  onAnswer: (response: Record<string, unknown>) => void;
}) {
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    if (question.question_type === "multiple_choice") {
      onAnswer({
        choices: data.getAll("choice").map((value) => Number(value)),
      });
      return;
    }
    if (question.question_type === "ordering") {
      const ranked = question.options
        .map((_, index) => ({
          index,
          rank: Number(data.get(`rank-${index}`)),
        }))
        .sort((left, right) => left.rank - right.rank)
        .map((item) => item.index);
      onAnswer({ order: ranked });
      return;
    }
    onAnswer({ choice: Number(data.get("choice")) });
  }
  return (
    <form className="diagnostic-card" onSubmit={submit}>
      <div className="question-progress">
        Question {question.position} of {question.total} ·{" "}
        {question.skill_key.replaceAll("-", " ")}
      </div>
      <h2>{question.prompt}</h2>
      {question.options.map((option, index) =>
        question.question_type === "ordering" ? (
          <label className="order-row" key={option}>
            <select name={`rank-${index}`} defaultValue={index + 1}>
              {question.options.map((_, rank) => (
                <option key={rank} value={rank + 1}>
                  {rank + 1}
                </option>
              ))}
            </select>
            {option}
          </label>
        ) : (
          <label className="choice-row" key={option}>
            <input
              name="choice"
              type={
                question.question_type === "multiple_choice"
                  ? "checkbox"
                  : "radio"
              }
              value={index}
              required={question.question_type !== "multiple_choice"}
            />
            {option}
          </label>
        ),
      )}
      <button className="primary" disabled={busy}>
        {busy ? "Evaluating…" : "Submit reasoning"}
      </button>
    </form>
  );
}

function RoadmapPage() {
  const query = useQuery({
    queryKey: ["learner-dashboard"],
    queryFn: () => apiFetch<Dashboard>("/api/v1/learning/dashboard"),
  });
  if (query.isLoading) return <p role="status">Building your roadmap…</p>;
  if (query.error) return <ErrorPanel error={query.error} />;
  return (
    <section className="workflow-panel">
      <span className="eyebrow">EVIDENCE-BASED SEQUENCE</span>
      <h1>Your Junior SOC roadmap</h1>
      <p>
        Required items close prerequisite gaps. Bridge activities connect
        strengths to weaker skills instead of repeating everything.
      </p>
      <div className="roadmap-list">
        {query.data!.recommendations.length ? (
          query.data!.recommendations.map((item, index) => (
            <article key={item.activityId}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <div>
                <small>
                  {item.required ? "REQUIRED" : "RECOMMENDED"} ·{" "}
                  {item.activityType.replaceAll("_", " ")}
                </small>
                <h2>{item.activityId.replaceAll("-", " ")}</h2>
                <p>{item.reason}</p>
              </div>
            </article>
          ))
        ) : (
          <div className="empty-state">
            Complete the diagnostic to generate a personalized roadmap.
          </div>
        )}
      </div>
    </section>
  );
}

type MissionStage = {
  key: string;
  position: number;
  total: number;
  title: string;
  objective: string;
  resources: {
    id: string;
    label: string;
    classification: string;
    opened: boolean;
  }[];
  actions: { id: string; label: string }[];
};

type MissionState = {
  session_id: string;
  title?: string;
  fictional_organization?: string;
  business_context?: string;
  briefing?: string;
  safety_notice?: string;
  status: string;
  stage: MissionStage;
};

function MissionPage() {
  const [mission, setMission] = useState<MissionState>();
  const [evidence, setEvidence] = useState("");
  const [feedback, setFeedback] = useState("");
  const [hint, setHint] = useState("");
  const [result, setResult] = useState<{
    passed: boolean;
    scores: Record<string, number>;
    strengths: string[];
    improvements: string[];
    completion_verification_id: string | null;
    scope_notice: string;
  }>();
  const [replay, setReplay] = useState<{
    timeline: Record<string, unknown>[];
    turning_points: Record<string, unknown>[];
    missed_evidence: string[];
  }>();
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  async function run<T>(operation: () => Promise<T>) {
    setBusy(true);
    setError(undefined);
    try {
      return await operation();
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  }
  async function start() {
    const value = await run(() =>
      apiFetch<MissionState>("/api/v1/missions/flagship/start", {
        method: "POST",
      }),
    );
    if (value) setMission(value);
  }
  async function action(
    action_type: "open_evidence" | "decision",
    value: string,
  ) {
    if (!mission) return;
    const response = await run(() =>
      apiFetch<
        Omit<MissionState, "session_id"> & {
          outcome: string;
          feedback: string;
          resource_content: string | null;
        }
      >(`/api/v1/missions/sessions/${mission.session_id}/actions`, {
        method: "POST",
        body: JSON.stringify(
          action_type === "open_evidence"
            ? { action_type, resource_id: value }
            : { action_type, decision_id: value },
        ),
      }),
    );
    if (response) {
      const advanced = response.stage.key !== mission.stage.key;
      setMission({
        ...mission,
        status: response.status,
        stage: response.stage,
      });
      setFeedback(response.feedback);
      if (advanced) {
        setEvidence("");
        setHint("");
      } else if (response.resource_content) {
        setEvidence(response.resource_content);
      }
    }
  }
  async function requestHint() {
    if (!mission) return;
    const response = await run(() =>
      apiFetch<{ level: number; hint: string; independence_notice: string }>(
        `/api/v1/missions/sessions/${mission.session_id}/hint`,
        { method: "POST" },
      ),
    );
    if (response)
      setHint(
        `Hint ${response.level}: ${response.hint} ${response.independence_notice}`,
      );
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!mission) return;
    const data = new FormData(event.currentTarget);
    const response = await run(() =>
      apiFetch<typeof result>(
        `/api/v1/missions/sessions/${mission.session_id}/submit`,
        {
          method: "POST",
          body: JSON.stringify({
            classification: data.get("classification"),
            rationale: data.get("rationale"),
            uncertainty: data.get("uncertainty"),
            recommendation: data.get("recommendation"),
            next_steps: [data.get("nextStep1"), data.get("nextStep2")],
            reflection: data.get("reflection"),
          }),
        },
      ),
    );
    if (response) setResult(response);
  }
  async function loadReplay() {
    if (!mission) return;
    const response = await run(() =>
      apiFetch<typeof replay>(
        `/api/v1/missions/sessions/${mission.session_id}/replay`,
      ),
    );
    if (response) setReplay(response);
  }
  if (!mission)
    return (
      <section className="workflow-panel narrow">
        <span className="eyebrow">FLAGSHIP WORKPLACE MISSION</span>
        <h1>Harbor Light</h1>
        <p>
          Investigate a fictional phishing-to-endpoint case using only supplied
          synthetic evidence. Actions, mistakes, hints, and decisions are
          recorded.
        </p>
        {error != null && <ErrorPanel error={error} />}
        <button className="primary" onClick={start} disabled={busy}>
          {busy ? "Preparing workspace…" : "Launch mission"}
        </button>
      </section>
    );
  if (result)
    return (
      <section className="workflow-panel">
        <span className="eyebrow">VERIFIED EVALUATION</span>
        <h1>{result.passed ? "Mission passed" : "Mission not yet passed"}</h1>
        <p>{result.scope_notice}</p>
        <div className="score-grid">
          {Object.entries(result.scores).map(([label, value]) => (
            <article key={label}>
              <strong>{Math.round(value * 100)}%</strong>
              <span>{label}</span>
            </article>
          ))}
        </div>
        <h2>Strengths</h2>
        <ul>
          {result.strengths.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        {result.improvements.length > 0 && (
          <>
            <h2>Next improvements</h2>
            <ul>
              {result.improvements.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </>
        )}
        {result.completion_verification_id && (
          <a
            href={`/api/v1/missions/verify/${result.completion_verification_id}`}
            target="_blank"
            rel="noreferrer"
          >
            Open scoped completion record
          </a>
        )}
        <button className="secondary" onClick={loadReplay} disabled={busy}>
          Load investigation replay
        </button>
        {replay && (
          <div className="replay-panel">
            <h2>Investigation replay</h2>
            <p>{replay.timeline.length} recorded actions</p>
            <ol>
              {replay.turning_points.map((point, index) => (
                <li key={index}>{String(point.observation)}</li>
              ))}
            </ol>
            <p>
              Missed evidence:{" "}
              {replay.missed_evidence.length
                ? replay.missed_evidence.join(", ")
                : "none"}
            </p>
          </div>
        )}
      </section>
    );
  return (
    <section className="workflow-panel mission-workspace">
      <span className="eyebrow">
        {mission.fictional_organization} · STAGE {mission.stage.position}/
        {mission.stage.total}
      </span>
      <h1>{mission.stage.title}</h1>
      <p>{mission.stage.objective}</p>
      {mission.safety_notice && (
        <div className="safety-notice">{mission.safety_notice}</div>
      )}
      {error != null && <ErrorPanel error={error} />}
      {feedback && (
        <div className="workflow-feedback" role="status">
          {feedback}
        </div>
      )}
      {hint && (
        <div className="hint-panel" role="status">
          {hint}
        </div>
      )}
      {mission.status === "active" ? (
        <div className="mission-columns">
          <section>
            <h2>Evidence desk</h2>
            {mission.stage.resources.map((resource) => (
              <button
                className="resource-button"
                key={resource.id}
                onClick={() => action("open_evidence", resource.id)}
                disabled={busy}
              >
                <span>{resource.label}</span>
                <small>{resource.classification}</small>
              </button>
            ))}
            <pre className="evidence-viewer" tabIndex={0}>
              {evidence || "Open an evidence source to inspect it."}
            </pre>
          </section>
          <section>
            <h2>Analyst decision</h2>
            <div className="decision-list">
              {mission.stage.actions.map((choice) => (
                <button
                  key={choice.id}
                  onClick={() => action("decision", choice.id)}
                  disabled={busy}
                >
                  {choice.label}
                </button>
              ))}
            </div>
            <button
              className="quiet-button"
              onClick={requestHint}
              disabled={busy}
            >
              Request progressive hint
            </button>
          </section>
        </div>
      ) : (
        <MissionReportForm busy={busy} onSubmit={submit} />
      )}
    </section>
  );
}

function MissionReportForm({
  busy,
  onSubmit,
}: {
  busy: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <form className="workflow-form mission-report" onSubmit={onSubmit}>
      <h2>Submit your escalation</h2>
      <label>
        Classification
        <select name="classification" defaultValue="inconclusive">
          <option value="inconclusive">Inconclusive</option>
          <option value="suspected_endpoint_compromise">
            Suspected endpoint compromise
          </option>
          <option value="confirmed_enterprise_breach">
            Confirmed enterprise breach
          </option>
          <option value="false_positive">False positive</option>
        </select>
      </label>
      <label>
        Evidence-based rationale
        <textarea name="rationale" minLength={120} rows={6} required />
      </label>
      <label>
        Remaining uncertainty
        <textarea name="uncertainty" minLength={20} rows={3} required />
      </label>
      <label>
        Recommended action
        <select name="recommendation" defaultValue="no_action">
          <option value="no_action">No action</option>
          <option value="isolate_fin_14_with_approval">
            Request approved isolation of FIN-14
          </option>
          <option value="reset_all_accounts">Reset all accounts</option>
          <option value="retaliate_against_source">
            Retaliate against source
          </option>
        </select>
      </label>
      <label>
        Next step 1
        <input name="nextStep1" minLength={10} required />
      </label>
      <label>
        Next step 2
        <input name="nextStep2" minLength={10} required />
      </label>
      <label>
        Reflection
        <textarea name="reflection" minLength={40} rows={4} required />
      </label>
      <button className="primary" disabled={busy}>
        {busy ? "Evaluating…" : "Submit for server evaluation"}
      </button>
    </form>
  );
}

type MentorReply = {
  message_id: string;
  answer: string;
  mode: string;
  mentor_mode: string;
  intervention: string;
  blocked: boolean;
  provider_generated: boolean;
  citations: {
    publication_id: string;
    title: string;
    publisher: string;
    url: string;
  }[];
  reasoning_summary: string;
  related_skills: string[];
  recommended_next_action: {
    type: string;
    id: string;
    reason: string;
  } | null;
  detected_misconceptions: string[];
  limitation_notice: string;
  provider: string;
  model: string;
  latency_ms: number;
};

type ProfessionalProject = {
  title: string;
  description: string;
  version: string;
  milestones: { position: number; title: string; requirement: string }[];
  rubric_version: string;
  rubric: {
    key: string;
    description: string;
    weight: number;
    pass_standard: string;
  }[];
  review_notice: string;
};

function ProjectPage() {
  const query = useQuery({
    queryKey: ["flagship-project"],
    queryFn: () => apiFetch<ProfessionalProject>("/api/v1/projects/flagship"),
  });
  const submissions = useQuery({
    queryKey: ["flagship-project-submissions"],
    queryFn: () =>
      apiFetch<
        {
          id: string;
          status: string;
          submitted_at: string;
          review_notice: string;
        }[]
      >("/api/v1/projects/flagship/submissions"),
  });
  const [receipt, setReceipt] = useState<{
    id: string;
    status: string;
    review_notice: string;
  }>();
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setBusy(true);
    setError(undefined);
    try {
      const response = await apiFetch<{
        id: string;
        status: string;
        review_notice: string;
      }>("/api/v1/projects/flagship/submissions", {
        method: "POST",
        body: JSON.stringify({
          body: data.get("body"),
          reflection: data.get("reflection"),
        }),
      });
      setReceipt(response);
      await submissions.refetch();
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  }
  if (query.isLoading) return <p role="status">Loading published project…</p>;
  if (query.error) return <ErrorPanel error={query.error} />;
  const project = query.data!;
  return (
    <section className="workflow-panel">
      <span className="eyebrow">HUMAN-REVIEWED EVIDENCE</span>
      <h1>{project.title}</h1>
      <p>{project.description}</p>
      <div className="safety-notice">{project.review_notice}</div>
      <div className="project-layout">
        <section>
          <h2>Required milestones</h2>
          <ol className="project-milestones">
            {project.milestones.map((milestone) => (
              <li key={milestone.position}>
                <strong>{milestone.title}</strong>
                <p>{milestone.requirement}</p>
              </li>
            ))}
          </ol>
        </section>
        <section>
          <h2>Published rubric · {project.rubric_version}</h2>
          <div className="rubric-list">
            {project.rubric.map((criterion) => (
              <article key={criterion.key}>
                <strong>{criterion.description}</strong>
                <span>{Math.round(criterion.weight * 100)}% weight</span>
                <p>{criterion.pass_standard}</p>
              </article>
            ))}
          </div>
        </section>
      </div>
      {error != null && <ErrorPanel error={error} />}
      {receipt ? (
        <div className="completion-panel" role="status">
          <h2>Submission saved · {receipt.status.replaceAll("_", " ")}</h2>
          <p>{receipt.review_notice}</p>
          <small>Submission ID: {receipt.id}</small>
        </div>
      ) : (
        <form className="workflow-form project-form" onSubmit={submit}>
          <h2>Submit your report</h2>
          <label>
            Professional incident escalation
            <textarea
              name="body"
              minLength={500}
              maxLength={30000}
              rows={14}
              aria-describedby="project-report-help"
              required
            />
          </label>
          <small id="project-report-help">
            At least 500 characters. Include scope, evidence, alternatives,
            uncertainty, action, verification, and reproducibility.
          </small>
          <label>
            Project reflection
            <textarea
              name="reflection"
              minLength={120}
              maxLength={5000}
              rows={6}
              required
            />
          </label>
          <button className="primary" disabled={busy}>
            {busy ? "Saving submission…" : "Submit for human review"}
          </button>
        </form>
      )}
      {submissions.data && submissions.data.length > 0 && (
        <section className="submission-history">
          <h2>Your submission history</h2>
          <ul>
            {submissions.data.map((item) => (
              <li key={item.id}>
                <strong>{item.status.replaceAll("_", " ")}</strong>
                <span>{new Date(item.submitted_at).toLocaleString()}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </section>
  );
}

const mentorContexts = {
  course: "course-4",
  lesson: "soc-01-l1",
  lab: "soc-lab-linux-auth-triage",
  mission: "harbor-light-phishing-investigation",
  project: "junior-soc-incident-escalation-project",
  assessment: "course-4",
  general: "",
} as const;

type MentorContext = keyof typeof mentorContexts;

function SentinelPage() {
  const [contextType, setContextType] = useState<MentorContext>("course");
  const [threadId, setThreadId] = useState("");
  const [messages, setMessages] = useState<
    {
      id?: string;
      role: "learner" | "sentinel";
      text: string;
      reply?: MentorReply;
      streaming?: boolean;
      feedback?: string;
    }[]
  >([]);
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  const [lastQuestion, setLastQuestion] = useState("");
  useEffect(() => {
    let active = true;
    apiFetch<{ id: string }>("/api/v1/mentor/threads", {
      method: "POST",
      body: JSON.stringify({
        context_type: contextType,
        context_id: mentorContexts[contextType] || null,
      }),
    })
      .then(async (value) => {
        if (!active) return;
        setThreadId(value.id);
        const history = await apiFetch<{
          messages: {
            id: string;
            role: "user" | "assistant";
            body: string;
            delivery_mode: string;
            mentor_mode: string;
            provider_generated: boolean;
            reasoning_summary: string | null;
            related_skills: string[];
            recommended_action: {
              type: string;
              id: string;
              reason: string;
            } | null;
          }[];
        }>(`/api/v1/mentor/threads/${value.id}`);
        if (!active) return;
        setMessages(
          history.messages.map((message) => ({
            id: message.id,
            role: message.role === "user" ? "learner" : "sentinel",
            text: message.body,
            reply:
              message.role === "assistant"
                ? {
                    message_id: message.id,
                    answer: message.body,
                    mode: message.delivery_mode,
                    mentor_mode: message.mentor_mode,
                    intervention: "recorded_intervention",
                    blocked: message.delivery_mode === "policy_refusal",
                    provider_generated: message.provider_generated,
                    citations: [],
                    reasoning_summary: message.reasoning_summary || "",
                    related_skills: message.related_skills,
                    recommended_next_action: message.recommended_action,
                    detected_misconceptions: [],
                    limitation_notice:
                      "Historical sources remain recorded server-side.",
                    provider: message.provider_generated
                      ? "configured provider"
                      : "deterministic",
                    model: "historical",
                    latency_ms: 0,
                  }
                : undefined,
          })),
        );
      })
      .catch((caught) => {
        if (active) setError(caught);
      });
    return () => {
      active = false;
    };
  }, [contextType]);
  function switchContext(nextContext: MentorContext) {
    setThreadId("");
    setMessages([]);
    setError(undefined);
    setContextType(nextContext);
  }
  async function sendQuestion(question: string) {
    if (!threadId) return;
    if (!question) return;
    setLastQuestion(question);
    setMessages((items) => [...items, { role: "learner", text: question }]);
    setBusy(true);
    setError(undefined);
    try {
      const reply = await apiFetch<MentorReply>(
        `/api/v1/mentor/threads/${threadId}/messages`,
        { method: "POST", body: JSON.stringify({ question }) },
      );
      const words = reply.answer.split(/\s+/);
      const placeholder = `stream-${reply.message_id}`;
      setMessages((items) => [
        ...items,
        {
          id: placeholder,
          role: "sentinel",
          text: "",
          reply,
          streaming: true,
        },
      ]);
      for (let index = 0; index < words.length; index += 8) {
        const text = words.slice(0, index + 8).join(" ");
        setMessages((items) =>
          items.map((item) =>
            item.id === placeholder ? { ...item, text } : item,
          ),
        );
        await new Promise((resolve) => window.setTimeout(resolve, 8));
      }
      setMessages((items) =>
        items.map((item) =>
          item.id === placeholder
            ? {
                ...item,
                id: reply.message_id,
                text: reply.answer,
                streaming: false,
              }
            : item,
        ),
      );
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const question = String(new FormData(form).get("question") || "").trim();
    if (!question) return;
    form.reset();
    await sendQuestion(question);
  }
  async function feedback(messageId: string, rating: string) {
    await apiFetch(
      `/api/v1/mentor/threads/${threadId}/messages/${messageId}/feedback`,
      {
        method: "POST",
        body: JSON.stringify({ rating, issue_tags: [] }),
      },
    );
    setMessages((items) =>
      items.map((item) =>
        item.id === messageId ? { ...item, feedback: rating } : item,
      ),
    );
  }
  async function copy(text: string) {
    await navigator.clipboard?.writeText(text);
  }
  return (
    <section className="workflow-panel mentor-page">
      <span className="eyebrow">GROUNDED LEARNING SUPPORT</span>
      <h1>Sentinel Mentor</h1>
      <p>
        Sentinel explains reviewed learner-visible content. It cannot grade,
        publish curriculum, issue credentials, reveal answers, or control labs.
        Its adaptation engine—not the configured model—chooses how to mentor.
      </p>
      <label className="mentor-context">
        Mentoring context
        <select
          value={contextType}
          disabled={busy}
          onChange={(event) =>
            switchContext(event.currentTarget.value as MentorContext)
          }
        >
          <option value="course">SOC course</option>
          <option value="lesson">Current lesson</option>
          <option value="lab">Linux authentication lab</option>
          <option value="mission">Harbor Light mission</option>
          <option value="project">Incident escalation project</option>
          <option value="assessment">Assessment support</option>
          <option value="general">General mentoring</option>
        </select>
        <small>
          Switching context resumes its private conversation and learner state.
        </small>
      </label>
      {error != null && <ErrorPanel error={error} />}
      <div className="mentor-log" aria-live="polite">
        {messages.length === 0 && (
          <div className="empty-state">
            Ask about alert triage, evidence quality, SOC decisions, or
            reporting.
          </div>
        )}
        {messages.map((message, index) => (
          <article
            className={`mentor-message ${message.role}`}
            key={message.id || index}
          >
            <strong>{message.role === "learner" ? "You" : "Sentinel"}</strong>
            <p>{message.text}</p>
            {message.streaming && (
              <small role="status">
                Sentinel is composing a grounded response…
              </small>
            )}
            {message.reply && (
              <>
                <div className="mentor-response-meta">
                  <span>{message.reply.mentor_mode.replaceAll("_", " ")}</span>
                  <small>
                    Delivery: {message.reply.mode.replaceAll("_", " ")} ·{" "}
                    {message.reply.provider_generated
                      ? "approved provider response"
                      : "no external model used"}
                  </small>
                </div>
                {message.reply.reasoning_summary && (
                  <details>
                    <summary>Why Sentinel chose this approach</summary>
                    <p>{message.reply.reasoning_summary}</p>
                  </details>
                )}
                {message.reply.related_skills.length > 0 && (
                  <div className="mentor-skill-tags">
                    {message.reply.related_skills.map((skill) => (
                      <span key={skill}>{skill.replaceAll("-", " ")}</span>
                    ))}
                  </div>
                )}
                {message.reply.citations.length > 0 && (
                  <ul aria-label="Reviewed sources">
                    {message.reply.citations.map((citation) => (
                      <li key={`${citation.publication_id}-${citation.url}`}>
                        <a href={citation.url} target="_blank" rel="noreferrer">
                          {citation.title} — {citation.publisher}
                        </a>
                      </li>
                    ))}
                  </ul>
                )}
                {message.reply.recommended_next_action && (
                  <div className="mentor-next-action">
                    <strong>Recommended next action</strong>
                    <p>{message.reply.recommended_next_action.reason}</p>
                    <small>
                      {message.reply.recommended_next_action.type.replaceAll(
                        "_",
                        " ",
                      )}{" "}
                      · {message.reply.recommended_next_action.id}
                    </small>
                  </div>
                )}
                <p className="limitation">{message.reply.limitation_notice}</p>
                {!message.streaming && message.id && (
                  <div className="mentor-message-actions">
                    <button
                      className="quiet-button"
                      onClick={() => void copy(message.text)}
                    >
                      Copy
                    </button>
                    <button
                      className="quiet-button"
                      disabled={Boolean(message.feedback)}
                      onClick={() => void feedback(message.id!, "helpful")}
                    >
                      Helpful
                    </button>
                    <button
                      className="quiet-button"
                      disabled={Boolean(message.feedback)}
                      onClick={() => void feedback(message.id!, "not_helpful")}
                    >
                      Needs improvement
                    </button>
                    {message.feedback && <small>Feedback saved</small>}
                  </div>
                )}
              </>
            )}
          </article>
        ))}
      </div>
      <form className="mentor-compose" onSubmit={submit}>
        <label htmlFor="mentor-question">Your question</label>
        <textarea
          id="mentor-question"
          name="question"
          maxLength={4000}
          rows={4}
          required
        />
        <button className="primary" disabled={busy || !threadId}>
          {busy ? "Reviewing sources…" : "Ask Sentinel"}
        </button>
        {error != null && lastQuestion && (
          <button
            className="secondary"
            type="button"
            disabled={busy}
            onClick={() => void sendQuestion(lastQuestion)}
          >
            Retry last question
          </button>
        )}
      </form>
    </section>
  );
}

export function CompetitionApp() {
  return (
    <WorkflowShell>
      <Switch>
        <Route path="/academy/managed/:contentType/:slug" component={ManagedContentPage} />
        <Route path="/academy" component={DashboardPage} />
        <Route path="/academy/onboarding" component={OnboardingPage} />
        <Route path="/academy/diagnostic" component={DiagnosticPage} />
        <Route path="/academy/roadmap" component={RoadmapPage} />
        <Route path="/academy/pathway" component={SocPathwayPage} />
        <Route
          path="/academy/pathway/modules/:moduleId"
          component={SocModulePage}
        />
        <Route
          path="/academy/pathway/lessons/:lessonId"
          component={SocLessonPage}
        />
        <Route
          path="/academy/pathway/practice/:activityId"
          component={SocPracticePage}
        />
        <Route
          path="/academy/pathway/assessments/:assessmentId"
          component={SocAssessmentPage}
        />
        <Route path="/academy/skills" component={SocSkillsPage} />
        <Route path="/academy/labs/:labId" component={LabWorkspacePage} />
        <Route path="/academy/labs" component={LabCatalogPage} />
        <Route path="/academy/mission" component={MissionPage} />
        <Route path="/academy/project" component={ProjectPage} />
        <Route path="/academy/sentinel" component={SentinelPage} />
        <Route path="/academy/course">
          <App />
        </Route>
        <Route>
          <DashboardPage />
        </Route>
      </Switch>
    </WorkflowShell>
  );
}
