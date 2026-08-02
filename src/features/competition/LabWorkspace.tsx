import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bot,
  CheckCircle2,
  ChevronRight,
  FileSearch,
  Lightbulb,
  Play,
  RotateCcw,
  TerminalSquare,
} from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useParams } from "wouter";
import { apiFetch, ApiError } from "../../lib/api-client";

type LabSummary = {
  id: string;
  version: string;
  title: string;
  labType: string;
  category: string;
  difficulty: string;
  estimatedMinutes: number;
  prerequisites: string[];
  linkedSkills: string[];
  availableTools: string[];
  portfolioEligibility: boolean;
  safetyNotice: string;
};

type LabDetail = LabSummary & {
  scenario: string;
  learnerInstructions: string[];
  objectives: {
    id: string;
    title: string;
    required: boolean;
    bonus?: boolean;
    stage: number;
  }[];
  reflectionQuestions: string[];
  completionCriteria: {
    minimumRequiredObjectives: number;
    minimumOverallBand: string;
    reportRequired: boolean;
  };
  generatedEvidence: { artifactType: string; title: string };
};

type LabAction = {
  sequence: number;
  type: string;
  input: string | null;
  output: string | null;
  successful: boolean;
  mistake: boolean;
  elapsedSeconds: number;
  metadata: { exitCode?: number; checkpoint?: string; level?: number };
};

type LabSession = {
  sessionId: string;
  lab: LabDetail;
  status: string;
  currentStage: number;
  cwd: string;
  objectiveState: {
    requiredCompleted: number;
    requiredTotal: number;
    activeBranch: string;
    objectives: Record<
      string,
      {
        title: string;
        required: boolean;
        bonus: boolean;
        stage: number;
        completed: boolean;
      }
    >;
  };
  scoreComponents: Record<string, { band: string }>;
  notes: string;
  hintsUsed: number;
  commandCount: number;
  incorrectCommandCount: number;
  outcome: string | null;
  version: number;
  actions: LabAction[];
};

type SubmissionResult = {
  passed: boolean;
  overallBand: string;
  components: Record<string, string>;
  feedback: string[];
  portfolioArtifactId: string | null;
  completionVerificationId: string | null;
  canRetry: boolean;
  session: LabSession;
};

type MentorReply = {
  message_id: string;
  answer: string;
  mentor_mode: string;
  reasoning_summary: string;
  related_skills: string[];
  recommended_next_action: {
    type: string;
    id: string;
    reason: string;
  } | null;
  citations: {
    publication_id: string;
    title: string;
    publisher: string;
    url: string;
  }[];
  limitation_notice: string;
};

function errorMessage(error: unknown) {
  return error instanceof ApiError
    ? error.message
    : "The practical lab request could not be completed.";
}

function label(value: string) {
  return value
    .replaceAll("-", " ")
    .replaceAll(/([A-Z])/g, " $1")
    .trim();
}

export function LabCatalogPage() {
  const query = useQuery({
    queryKey: ["practical-labs"],
    queryFn: () =>
      apiFetch<{ labTypes: string[]; labs: LabSummary[] }>("/api/v1/labs"),
  });
  if (query.isLoading) return <p role="status">Loading practical labs…</p>;
  if (query.error)
    return <div className="workflow-error">{errorMessage(query.error)}</div>;
  return (
    <section className="workflow-panel lab-catalog">
      <span className="eyebrow">AUTHORIZED SYNTHETIC PRACTICE</span>
      <h1>Practical cybersecurity labs</h1>
      <p>
        Investigate scenario-specific files, logs, processes, and network
        records in a deterministic workspace. Commands never execute on the
        host.
      </p>
      <div className="lab-type-strip" aria-label="Supported lab types">
        {query.data!.labTypes.map((type) => (
          <span key={type}>{label(type)}</span>
        ))}
      </div>
      <div className="lab-card-grid">
        {query.data!.labs.map((lab) => (
          <article className="lab-card" key={lab.id}>
            <div>
              <span className="lab-type">{label(lab.labType)}</span>
              <span>{lab.difficulty}</span>
            </div>
            <h2>{lab.title}</h2>
            <p>
              {lab.category} · {lab.estimatedMinutes} minutes
            </p>
            <ul>
              {lab.linkedSkills.slice(0, 4).map((skill) => (
                <li key={skill}>{label(skill)}</li>
              ))}
            </ul>
            <Link className="primary-link" to={`/academy/labs/${lab.id}`}>
              Open lab <ChevronRight aria-hidden="true" />
            </Link>
          </article>
        ))}
      </div>
    </section>
  );
}

export function LabWorkspacePage() {
  const { labId } = useParams<{ labId: string }>();
  const queryClient = useQueryClient();
  const detail = useQuery({
    queryKey: ["practical-lab", labId],
    queryFn: () => apiFetch<LabDetail>(`/api/v1/labs/${labId}`),
  });
  const [session, setSession] = useState<LabSession>();
  const [busy, setBusy] = useState("");
  const [error, setError] = useState<unknown>();
  const [hint, setHint] = useState<{
    level: number;
    kind: string;
    text: string;
  }>();
  const [notes, setNotes] = useState("");
  const [submission, setSubmission] = useState<SubmissionResult>();
  const [replay, setReplay] = useState<{
    mistakes: LabAction[];
    corrections: { sequence: number; action: string }[];
    expertSolution: string[] | null;
    timeSpentSeconds: number;
  }>();
  const logEnd = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logEnd.current?.scrollIntoView?.({ block: "nearest" });
  }, [session?.actions.length]);

  async function start() {
    setBusy("start");
    setError(undefined);
    try {
      const result = await apiFetch<{ resumed: boolean; session: LabSession }>(
        `/api/v1/labs/${labId}/start`,
        { method: "POST" },
      );
      setSession(result.session);
      setNotes(result.session.notes);
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy("");
    }
  }

  async function command(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session) return;
    const form = event.currentTarget;
    const data = new FormData(form);
    const value = String(data.get("command") || "").trim();
    if (!value) return;
    form.reset();
    setBusy("command");
    setError(undefined);
    try {
      const result = await apiFetch<{ session: LabSession }>(
        `/api/v1/labs/sessions/${session.sessionId}/commands`,
        { method: "POST", body: JSON.stringify({ command: value }) },
      );
      setSession(result.session);
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy("");
    }
  }

  async function askHint() {
    if (!session) return;
    setBusy("hint");
    setError(undefined);
    try {
      const result = await apiFetch<{
        hint: { level: number; kind: string; text: string };
        session: LabSession;
      }>(`/api/v1/labs/sessions/${session.sessionId}/hints`, {
        method: "POST",
      });
      setHint(result.hint);
      setSession(result.session);
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy("");
    }
  }

  async function saveNotes() {
    if (!session) return;
    setBusy("notes");
    setError(undefined);
    try {
      const result = await apiFetch<{ session: LabSession }>(
        `/api/v1/labs/sessions/${session.sessionId}/notes`,
        {
          method: "PATCH",
          body: JSON.stringify({
            notes,
            expected_version: session.version,
          }),
        },
      );
      setSession(result.session);
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy("");
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session) return;
    const data = new FormData(event.currentTarget);
    setBusy("submit");
    setError(undefined);
    try {
      const result = await apiFetch<SubmissionResult>(
        `/api/v1/labs/sessions/${session.sessionId}/submit`,
        {
          method: "POST",
          body: JSON.stringify({
            indicator: data.get("indicator"),
            classification: data.get("classification"),
            recommendation: data.get("recommendation"),
            report: data.get("report"),
            reflection: data.get("reflection"),
            idempotency_key: crypto.randomUUID(),
          }),
        },
      );
      setSubmission(result);
      setSession(result.session);
      if (result.passed) {
        setReplay(
          await apiFetch(`/api/v1/labs/sessions/${session.sessionId}/replay`),
        );
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: ["learner-dashboard"] }),
          queryClient.invalidateQueries({ queryKey: ["soc-skills"] }),
        ]);
      }
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy("");
    }
  }

  if (detail.isLoading) return <p role="status">Loading lab definition…</p>;
  if (detail.error)
    return <div className="workflow-error">{errorMessage(detail.error)}</div>;
  const lab = detail.data!;
  if (!session) {
    return (
      <section className="workflow-panel lab-briefing">
        <Link to="/academy/labs">← All practical labs</Link>
        <span className="eyebrow">{label(lab.labType)}</span>
        <h1>{lab.title}</h1>
        <p className="lab-scenario">{lab.scenario}</p>
        <div className="safety-notice">{lab.safetyNotice}</div>
        <div className="lab-briefing-grid">
          <section>
            <h2>Objectives</h2>
            <ol>
              {lab.objectives.map((objective) => (
                <li key={objective.id}>
                  {objective.title}
                  {objective.bonus && <small> optional bonus</small>}
                </li>
              ))}
            </ol>
          </section>
          <section>
            <h2>Workspace contract</h2>
            <p>
              {lab.estimatedMinutes} minutes · {lab.difficulty} · version{" "}
              {lab.version}
            </p>
            <p>Tools: {lab.availableTools.join(", ")}</p>
            <p>Generated evidence: {lab.generatedEvidence.title}</p>
          </section>
        </div>
        {error != null && (
          <div className="workflow-error">{errorMessage(error)}</div>
        )}
        <button className="primary" disabled={busy === "start"} onClick={start}>
          <Play aria-hidden="true" />
          {busy === "start" ? "Opening workspace…" : "Start or resume lab"}
        </button>
      </section>
    );
  }

  const evidence = session.actions.filter(
    (action) => action.type === "command" && action.successful && action.output,
  );
  return (
    <section className="lab-workspace">
      <header className="lab-workspace-header">
        <div>
          <span className="eyebrow">
            {label(lab.labType)} · stage {session.currentStage}
          </span>
          <h1>{lab.title}</h1>
        </div>
        <div className="lab-status">
          <strong>{label(session.outcome || session.status)}</strong>
          <span>
            {session.objectiveState.requiredCompleted}/
            {session.objectiveState.requiredTotal} objectives
          </span>
          <small>{label(session.objectiveState.activeBranch)} path</small>
        </div>
      </header>
      {error != null && (
        <div className="workflow-error" role="alert">
          {errorMessage(error)}
        </div>
      )}
      <div className="lab-workspace-grid">
        <aside
          className="lab-objectives"
          aria-label="Lab objectives and progress"
        >
          <h2>Objectives</h2>
          <ol>
            {Object.entries(session.objectiveState.objectives).map(
              ([id, objective]) => (
                <li className={objective.completed ? "complete" : ""} key={id}>
                  <CheckCircle2 aria-hidden="true" />
                  <span>
                    {objective.title}
                    {objective.bonus && <small> bonus</small>}
                  </span>
                </li>
              ),
            )}
          </ol>
          <h2>Evidence</h2>
          <div className="lab-evidence-list">
            {evidence.length === 0 ? (
              <p>No evidence viewed yet.</p>
            ) : (
              evidence.slice(-5).map((item) => (
                <article key={item.sequence}>
                  <FileSearch aria-hidden="true" />
                  <span>
                    <strong>{item.input}</strong>
                    <small>{item.output?.split("\n")[0]}</small>
                  </span>
                </article>
              ))
            )}
          </div>
        </aside>
        <div className="lab-center">
          <section className="lab-terminal" aria-label="Simulated terminal">
            <div className="terminal-title">
              <TerminalSquare aria-hidden="true" />
              Synthetic terminal
              <span>{session.cwd}</span>
            </div>
            <div className="terminal-log" aria-live="polite">
              <p className="terminal-notice">
                Commands are interpreted inside this scenario only. Host
                execution, pipes, redirection, and expansion are disabled.
              </p>
              {session.actions
                .filter((action) => action.type === "command")
                .map((action) => (
                  <div className="terminal-entry" key={action.sequence}>
                    <div>
                      <span className="terminal-prompt">$</span> {action.input}
                    </div>
                    {action.output && (
                      <pre className={action.mistake ? "terminal-error" : ""}>
                        {action.output}
                      </pre>
                    )}
                    {action.metadata.checkpoint && (
                      <small>{action.metadata.checkpoint}</small>
                    )}
                  </div>
                ))}
              <div ref={logEnd} />
            </div>
            <form className="terminal-compose" onSubmit={command}>
              <label className="sr-only" htmlFor="lab-command">
                Terminal command
              </label>
              <span aria-hidden="true">$</span>
              <input
                id="lab-command"
                name="command"
                autoComplete="off"
                spellCheck={false}
                disabled={session.status !== "active" || busy === "command"}
                placeholder="Try pwd or ls"
              />
              <button
                disabled={session.status !== "active" || busy === "command"}
              >
                Run
              </button>
            </form>
          </section>
          <section className="lab-notes">
            <div>
              <h2>Investigation notes</h2>
              <small>Saved to this durable session</small>
            </div>
            <textarea
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              rows={5}
              maxLength={12000}
              disabled={session.status !== "active"}
            />
            <button
              className="quiet-button"
              disabled={session.status !== "active" || busy === "notes"}
              onClick={saveNotes}
            >
              {busy === "notes" ? "Saving…" : "Save notes"}
            </button>
          </section>
          {session.status === "active" && (
            <form className="lab-submission workflow-form" onSubmit={submit}>
              <h2>Submit evidence and report</h2>
              <div className="lab-form-pair">
                <label>
                  Strongest indicator
                  <input name="indicator" maxLength={1000} required />
                </label>
                <label>
                  Classification
                  <input name="classification" maxLength={1000} required />
                </label>
              </div>
              <label>
                Recommended action
                <textarea
                  name="recommendation"
                  minLength={20}
                  rows={3}
                  required
                />
              </label>
              <label>
                Evidence-grounded report
                <textarea name="report" minLength={80} rows={8} required />
              </label>
              <label>
                Reflection
                <textarea name="reflection" minLength={20} rows={4} required />
              </label>
              <button className="primary" disabled={busy === "submit"}>
                {busy === "submit"
                  ? "Validating evidence…"
                  : "Submit for validation"}
              </button>
            </form>
          )}
          {submission && (
            <section className="lab-report" role="status">
              <h2>
                Assessment: {label(submission.overallBand)}
                {submission.passed ? " · completed" : " · recovery available"}
              </h2>
              <div className="component-bands">
                {Object.entries(submission.components).map(([name, band]) => (
                  <span key={name}>
                    <small>{label(name)}</small>
                    <strong>{label(band)}</strong>
                  </span>
                ))}
              </div>
              <ul>
                {submission.feedback.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              {submission.portfolioArtifactId && (
                <p>
                  Portfolio artifact generated:{" "}
                  <code>{submission.portfolioArtifactId}</code>
                </p>
              )}
            </section>
          )}
          {replay && (
            <section className="lab-replay">
              <h2>
                <RotateCcw aria-hidden="true" /> Investigation replay
              </h2>
              <p>
                {replay.mistakes.length} mistake(s), {replay.corrections.length}{" "}
                correction(s), {Math.ceil(replay.timeSpentSeconds / 60)}{" "}
                minute(s).
              </p>
              {replay.expertSolution && (
                <>
                  <h3>Expert solution</h3>
                  <ol>
                    {replay.expertSolution.map((step) => (
                      <li key={step}>{step}</li>
                    ))}
                  </ol>
                </>
              )}
            </section>
          )}
        </div>
        <aside className="lab-support">
          <section>
            <h2>
              <Lightbulb aria-hidden="true" /> Adaptive hint
            </h2>
            <p>
              Hints progress through five levels and are recorded as
              independence evidence.
            </p>
            {hint && (
              <div className="hint-card" role="status">
                <small>
                  Level {hint.level} · {label(hint.kind)}
                </small>
                <p>{hint.text}</p>
              </div>
            )}
            <button
              className="secondary"
              disabled={session.status !== "active" || busy === "hint"}
              onClick={askHint}
            >
              Get hint {Math.min(5, session.hintsUsed + 1)} of 5
            </button>
          </section>
          <LabSentinel labId={lab.id} />
        </aside>
      </div>
    </section>
  );
}

function LabSentinel({ labId }: { labId: string }) {
  const [threadId, setThreadId] = useState("");
  const [reply, setReply] = useState<MentorReply>();
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let active = true;
    apiFetch<{ id: string }>("/api/v1/mentor/threads", {
      method: "POST",
      body: JSON.stringify({ context_type: "lab", context_id: labId }),
    })
      .then((value) => {
        if (active) setThreadId(value.id);
      })
      .catch((caught) => {
        if (active) setError(caught);
      });
    return () => {
      active = false;
    };
  }, [labId]);
  async function ask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!threadId) return;
    const form = event.currentTarget;
    const question = String(new FormData(form).get("question") || "").trim();
    if (!question) return;
    setBusy(true);
    setError(undefined);
    try {
      setReply(
        await apiFetch(`/api/v1/mentor/threads/${threadId}/messages`, {
          method: "POST",
          body: JSON.stringify({ question }),
        }),
      );
      form.reset();
    } catch (caught) {
      setError(caught);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="lab-sentinel">
      <h2>
        <Bot aria-hidden="true" /> Sentinel
      </h2>
      <p>
        Ask for conceptual help. Sentinel cannot run commands or reveal answers.
      </p>
      {reply && (
        <div className="mentor-message sentinel" aria-live="polite">
          <div className="mentor-response-meta">
            <span>{label(reply.mentor_mode)}</span>
          </div>
          <p>{reply.answer}</p>
          <details>
            <summary>Why this approach</summary>
            <p>{reply.reasoning_summary}</p>
          </details>
          {reply.related_skills.length > 0 && (
            <div className="mentor-skill-tags">
              {reply.related_skills.map((skill) => (
                <span key={skill}>{label(skill)}</span>
              ))}
            </div>
          )}
          {reply.citations.length > 0 && (
            <ul aria-label="Reviewed sources">
              {reply.citations.map((citation) => (
                <li key={`${citation.publication_id}-${citation.url}`}>
                  <a href={citation.url} target="_blank" rel="noreferrer">
                    {citation.title} — {citation.publisher}
                  </a>
                </li>
              ))}
            </ul>
          )}
          {reply.recommended_next_action && (
            <div className="mentor-next-action">
              <strong>Recommended next action</strong>
              <p>{reply.recommended_next_action.reason}</p>
            </div>
          )}
          <small>{reply.limitation_notice}</small>
        </div>
      )}
      {error != null && (
        <small className="terminal-error">{errorMessage(error)}</small>
      )}
      <form onSubmit={ask}>
        <label className="sr-only" htmlFor="lab-sentinel-question">
          Ask Sentinel
        </label>
        <textarea
          id="lab-sentinel-question"
          name="question"
          rows={3}
          maxLength={4000}
          required
        />
        <button className="quiet-button" disabled={!threadId || busy}>
          {busy ? "Reviewing…" : "Ask Sentinel"}
        </button>
      </form>
    </section>
  );
}
