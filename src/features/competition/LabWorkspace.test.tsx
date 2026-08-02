import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Route } from "wouter";
import { LabCatalogPage, LabWorkspacePage } from "./LabWorkspace";

function response(body: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  } as Response);
}

function renderPage(page: React.ReactNode) {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: { queries: { retry: false } },
        })
      }
    >
      {page}
    </QueryClientProvider>,
  );
}

const lab = {
  id: "soc-lab-linux-auth-triage",
  version: "1.0.0",
  title: "Triage repeated SSH authentication failures",
  labType: "guided",
  category: "Linux and authentication",
  difficulty: "foundation",
  estimatedMinutes: 35,
  prerequisites: ["linux-navigation"],
  linkedSkills: ["linux-navigation", "linux-logs"],
  objectives: [
    {
      id: "locate-log",
      title: "Locate the authentication log",
      required: true,
      stage: 1,
    },
  ],
  scenario: "A fictional Linux jump host generated an SSH alert.",
  learnerInstructions: ["Use only the simulated terminal."],
  availableTools: ["pwd", "ls", "cat", "grep"],
  reflectionQuestions: ["What evidence would change confidence?"],
  completionCriteria: {
    minimumRequiredObjectives: 1,
    minimumOverallBand: "developing",
    reportRequired: true,
  },
  generatedEvidence: {
    artifactType: "incident-report",
    title: "SSH authentication triage report",
  },
  portfolioEligibility: true,
  safetyNotice: "Authorized defensive training only. Everything is synthetic.",
};

function session(actions: unknown[] = [], hintsUsed = 0) {
  return {
    sessionId: "session-1",
    lab,
    status: "active",
    currentStage: 1,
    cwd: "/home/analyst",
    objectiveState: {
      requiredCompleted: actions.length ? 1 : 0,
      requiredTotal: 1,
      activeBranch: actions.length ? "primary" : "unresolved",
      objectives: {
        "locate-log": {
          title: "Locate the authentication log",
          required: true,
          bonus: false,
          stage: 1,
          completed: actions.length > 0,
        },
      },
    },
    scoreComponents: {},
    notes: "",
    hintsUsed,
    commandCount: actions.length,
    incorrectCommandCount: 0,
    outcome: null,
    version: actions.length + hintsUsed + 2,
    actions,
  };
}

describe("practical lab workspace", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    window.history.pushState({}, "", "/");
  });

  it("presents the seven supported lab types", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        response({
          labTypes: [
            "guided",
            "independent",
            "investigation",
            "incident-response",
            "detection",
            "secure-configuration",
            "threat-hunting",
          ],
          labs: [lab],
        }),
      ),
    );
    renderPage(<LabCatalogPage />);
    expect(
      await screen.findByRole("heading", {
        name: "Practical cybersecurity labs",
      }),
    ).toBeVisible();
    expect(screen.getByText("secure configuration")).toBeVisible();
    expect(screen.getByRole("link", { name: /open lab/i })).toBeVisible();
  });

  it("starts a durable workspace, records a wrong command, and reveals a hint", async () => {
    window.history.pushState({}, "", `/academy/labs/${lab.id}`);
    let actions: {
      sequence: number;
      type: string;
      input: string;
      output: string;
      successful: boolean;
      mistake: boolean;
      elapsedSeconds: number;
      metadata: { exitCode: number };
    }[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn((request: RequestInfo | URL, init?: RequestInit) => {
        const url = String(request);
        if (url.endsWith(`/labs/${lab.id}`) && !init?.method)
          return response(lab);
        if (url.endsWith(`/labs/${lab.id}/start`))
          return response({ resumed: false, session: session(actions) }, 201);
        if (url.endsWith("/mentor/threads"))
          return response({ id: "mentor-thread-1" }, 201);
        if (url.endsWith("/commands")) {
          const command = String(JSON.parse(String(init?.body)).command);
          actions = [
            ...actions,
            {
              sequence: actions.length + 1,
              type: "command",
              input: command,
              output: `${command}: command is not available in this simulation`,
              successful: false,
              mistake: true,
              elapsedSeconds: 2,
              metadata: { exitCode: 127 },
            },
          ];
          return response({ session: session(actions) });
        }
        if (url.endsWith("/hints"))
          return response({
            hint: {
              level: 1,
              kind: "orientation",
              text: "Start by identifying your current directory.",
            },
            session: session(actions, 1),
          });
        return response({}, 404);
      }),
    );
    renderPage(
      <Route path="/academy/labs/:labId" component={LabWorkspacePage} />,
    );
    expect(
      await screen.findByRole("heading", { name: lab.title }),
    ).toBeVisible();
    fireEvent.click(
      screen.getByRole("button", { name: /start or resume lab/i }),
    );
    expect(
      await screen.findByRole("region", { name: "Simulated terminal" }),
    ).toBeVisible();
    fireEvent.change(screen.getByPlaceholderText("Try pwd or ls"), {
      target: { value: "whoami" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Run" }));
    expect(
      await screen.findByText(
        "whoami: command is not available in this simulation",
      ),
    ).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Get hint 1 of 5" }));
    expect(
      await screen.findByText("Start by identifying your current directory."),
    ).toBeVisible();
    await waitFor(() =>
      expect(screen.getByText("1/1 objectives")).toBeVisible(),
    );
    expect(
      screen.getByRole("heading", { name: "Investigation notes" }),
    ).toBeVisible();
    expect(screen.getByRole("heading", { name: "Sentinel" })).toBeVisible();
  });
});
