import { useQuery } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link, useRoute } from "wouter";
import { apiFetch } from "../../lib/api-client";
import { CmsError, CmsPage } from "./CmsShared";

type TerminalResult = {
  command: string;
  cwd: string;
  exit_code: number;
  output: string;
  creates_evidence: false;
};

export function DraftLabWorkspace() {
  const [, params] = useRoute("/cms/preview/lab/:contentId/:versionId");
  const [cwd, setCwd] = useState("/home/analyst");
  const [history, setHistory] = useState<TerminalResult[]>([]);
  const [error, setError] = useState<unknown>();
  async function run(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const command = String(new FormData(form).get("command") || "");
    try {
      const result = await apiFetch<TerminalResult>(
        `/api/v1/cms/contents/${params?.contentId}/versions/${params?.versionId}/test-lab/command`,
        { method: "POST", body: JSON.stringify({ command, cwd }) },
      );
      setCwd(result.cwd);
      setHistory((current) => [...current, result]);
      form.reset();
    } catch (caught) {
      setError(caught);
    }
  }
  return (
    <CmsPage>
      <header className="cms-page-header">
        <div>
          <span className="cms-draft-ribbon">
            DRAFT LAB · NO LEARNER EVIDENCE
          </span>
          <h1>Protected lab workspace</h1>
        </div>
        <Link to={`/cms/builders/lab/${params?.contentId}`}>
          Return to builder
        </Link>
      </header>
      {Boolean(error) && <CmsError error={error} />}
      <section
        className="lab-terminal"
        aria-label="Deterministic draft lab terminal"
      >
        {history.length === 0 && (
          <p>
            Run an allowed command to test the configured virtual environment.
          </p>
        )}
        {history.map((item, index) => (
          <article key={`${item.command}-${index}`}>
            <strong>
              {item.cwd}$ {item.command}
            </strong>
            <pre>{item.output}</pre>
            <small>Exit {item.exit_code} · evidence creation disabled</small>
          </article>
        ))}
        <form onSubmit={(event) => void run(event)}>
          <label>
            Command
            <input name="command" required autoFocus autoComplete="off" />
          </label>
          <button className="primary">Run command</button>
        </form>
      </section>
    </CmsPage>
  );
}

type MissionPreview = {
  creates_evidence: false;
  mission: {
    title: string;
    description: string;
    metadata: {
      briefing?: string;
      stages?: Array<{
        id: string;
        title: string;
        goal: string;
        instructions?: string;
        evidence?: string[];
        actions?: string[];
        hints?: string[];
        completionCondition?: string;
      }>;
    };
  };
};
type MissionActionResult = {
  creates_evidence: false;
  outcome: string;
  feedback: string;
  resource_content: string | null;
  next_stage_index: number;
  mission_ready: boolean;
};

export function DraftMissionWorkspace() {
  const [, params] = useRoute("/cms/preview/mission/:contentId/:versionId");
  const [stageIndex, setStageIndex] = useState(0);
  const [actionResult, setActionResult] = useState<MissionActionResult | null>(
    null,
  );
  const [actionError, setActionError] = useState<unknown>();
  const query = useQuery({
    queryKey: ["cms-draft-mission", params?.versionId],
    queryFn: () =>
      apiFetch<MissionPreview>(
        `/api/v1/cms/contents/${params?.contentId}/versions/${params?.versionId}/test-mission`,
      ),
  });
  if (query.isLoading)
    return (
      <CmsPage>
        <p role="status">Launching draft mission workspace…</p>
      </CmsPage>
    );
  if (query.error)
    return (
      <CmsPage>
        <CmsError error={query.error} retry={() => void query.refetch()} />
      </CmsPage>
    );
  const mission = query.data!.mission;
  const stages = mission.metadata.stages || [];
  const stage = stages[stageIndex];
  async function act(
    actionType: "open_evidence" | "decision",
    identifier: string,
  ) {
    if (!stage) return;
    setActionError(undefined);
    try {
      const result = await apiFetch<MissionActionResult>(
        `/api/v1/cms/contents/${params?.contentId}/versions/${params?.versionId}/test-mission/action`,
        {
          method: "POST",
          body: JSON.stringify({
            stage_id: stage.id,
            action_type: actionType,
            resource_id: actionType === "open_evidence" ? identifier : null,
            decision_id: actionType === "decision" ? identifier : null,
          }),
        },
      );
      setActionResult(result);
      if (result.outcome === "correct" && !result.mission_ready)
        setStageIndex(result.next_stage_index);
    } catch (caught) {
      setActionError(caught);
    }
  }
  return (
    <CmsPage>
      <header className="cms-page-header">
        <div>
          <span className="cms-draft-ribbon">
            DRAFT MISSION · REAL ENGINE PLAYTEST · NO COMPLETION OR MASTERY
            EVIDENCE
          </span>
          <h1>{mission.title}</h1>
          <p>{mission.metadata.briefing || mission.description}</p>
        </div>
        <Link to={`/cms/builders/mission/${params?.contentId}`}>
          Return to builder
        </Link>
      </header>
      {Boolean(actionError) && <CmsError error={actionError} />}
      {actionResult && (
        <aside className="portal-state" role="status">
          <strong>{actionResult.outcome}</strong>
          <p>{actionResult.feedback}</p>
          {actionResult.resource_content && (
            <pre>{actionResult.resource_content}</pre>
          )}
          {actionResult.mission_ready && (
            <p>
              Draft mission playtest reached its submission-ready state. No
              record was created.
            </p>
          )}
        </aside>
      )}
      {stage ? (
        <section className="mission-preview-stage">
          <span>
            Stage {stageIndex + 1} of {stages.length}
          </span>
          <h2>{stage.title}</h2>
          <p>{stage.goal}</p>
          {stage.instructions && <p>{stage.instructions}</p>}
          <h3>Available evidence</h3>
          <ul>
            {stage.evidence?.map((item) => (
              <li key={item}>
                <button onClick={() => void act("open_evidence", item)}>
                  Open {item}
                </button>
              </li>
            ))}
          </ul>
          <h3>Available actions</h3>
          <ul>
            {stage.actions?.map((item) => (
              <li key={item}>
                <button onClick={() => void act("decision", item)}>
                  {item}
                </button>
              </li>
            ))}
          </ul>
          <details>
            <summary>Progressive hints</summary>
            <ol>
              {stage.hints?.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ol>
          </details>
        </section>
      ) : (
        <p>No configured stages are available.</p>
      )}
    </CmsPage>
  );
}
