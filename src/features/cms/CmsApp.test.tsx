import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CmsApp } from "./CmsApp";

function response(body: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

function renderCms(path: string) {
  window.history.pushState({}, "", path);
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <CmsApp />
    </QueryClientProvider>,
  );
}

describe("operational CMS", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
    vi.stubGlobal(
      "fetch",
      vi.fn(() => response({ items: [], total: 0, page: 1, page_size: 100 })),
    );
  });
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    window.history.pushState({}, "", "/");
    localStorage.clear();
  });

  it("renders every dedicated builder route with its domain fields", async () => {
    const cases = [
      ["course", "Short summary"],
      ["module", "Purpose"],
      ["lesson", "Target audience"],
      ["question", "Question type"],
      ["assessment", "Passing score (0–1)"],
      ["lab", "Scenario"],
      ["mission", "Mission briefing"],
      ["learning_path", "Target role"],
      ["skill", "Stable skill ID"],
      ["reference", "Publisher"],
    ];
    for (const [type, field] of cases) {
      renderCms(`/cms/builders/${type}`);
      expect(
        await screen.findByRole("heading", {
          name: `Create ${type.replaceAll("_", " ")}`,
        }),
      ).toBeVisible();
      expect(screen.getByLabelText(field)).toBeVisible();
      cleanup();
    }
  });

  it("adds, duplicates, collapses, previews, and keyboard-reorders lesson blocks", async () => {
    renderCms("/cms/builders/lesson");
    await screen.findByRole("heading", { name: "Create lesson" });
    fireEvent.click(screen.getByRole("button", { name: "Add block" }));
    fireEvent.change(screen.getByLabelText("Block type"), {
      target: { value: "heading" },
    });
    fireEvent.change(screen.getAllByLabelText("Title")[1], {
      target: { value: "Evidence first" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Duplicate" }));
    expect(
      screen.getByRole("button", { name: "Move block 2 up" }),
    ).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "Move block 2 up" }));
    fireEvent.click(
      screen.getAllByRole("button", { name: "Preview block" })[0],
    );
    expect(screen.getByText("BLOCK PREVIEW")).toBeVisible();
    fireEvent.click(screen.getAllByRole("button", { name: "Collapse" })[0]);
    expect(
      screen.getAllByRole("button", { name: "Expand" })[0],
    ).toHaveAttribute("aria-expanded", "false");
  });

  it("uses the real protected lab command endpoint from the builder", async () => {
    const version = {
      id: "content-1",
      version_id: "version-1",
      content_type: "lab",
      title: "Draft lab",
      public_slug: "draft-lab",
      description: "Test",
      version: "1.0.0",
      revision: 1,
      lock_version: 1,
      version_status: "draft",
      review_state: "draft",
      metadata: { allowedCommands: ["ls"], virtualFiles: [] },
      sections: [],
      objectives: [],
      relationships: [],
      reviews: [],
      comments: [],
      review_history: [],
      validation: [],
    };
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("test-lab/command"))
          return response({
            preview: true,
            creates_evidence: false,
            command: "ls",
            cwd: "/home/analyst",
            exit_code: 0,
            output: "evidence.txt",
          });
        if (url.endsWith("/api/v1/cms/contents/content-1"))
          return response({
            ...version,
            versions: [
              {
                id: "version-1",
                revision: 1,
                version: "1.0.0",
                status: "draft",
                review_state: "draft",
                change_summary: "Initial",
                created_at: new Date().toISOString(),
                published_at: null,
              },
            ],
          });
        if (url.includes("/versions/version-1")) return response(version);
        return response({ items: [], total: 0, page: 1, page_size: 100 });
      }),
    );
    renderCms("/cms/builders/lab/content-1");
    expect(
      await screen.findByRole("heading", {
        name: "Protected real lab terminal · preview mode",
      }),
    ).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Run draft command" }));
    await waitFor(() => expect(screen.getByText("evidence.txt")).toBeVisible());
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("test-lab/command"),
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("renders visual and accessible skill graph relationships", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/api/v1/cms/capabilities"))
          return response({ permissions: ["content.create"] });
        return response({
          items: [
            {
              id: "skill-target",
              content_type: "skill",
              title: "Evidence analysis",
              public_slug: "evidence-analysis",
              description: "Target skill",
              lifecycle_status: "published",
            },
          ],
          total: 1,
          page: 1,
          page_size: 100,
        });
      }),
    );
    renderCms("/cms/builders/skill");
    await screen.findByRole("heading", { name: "Create skill" });
    fireEvent.change(screen.getByLabelText("Relationship"), {
      target: { value: "prerequisite" },
    });
    fireEvent.change(screen.getByLabelText("Content"), {
      target: { value: "skill-target" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Attach" }));
    expect(
      screen.getByText("Accessible relationship graph alternative"),
    ).toBeVisible();
    expect(screen.getAllByText("Evidence analysis").length).toBeGreaterThan(0);
  });

  it("recovers safely stored unsaved builder work", async () => {
    renderCms("/cms/builders/lesson");
    await screen.findByRole("heading", { name: "Create lesson" });
    fireEvent.change(screen.getByLabelText("Title"), {
      target: { value: "Recovered evidence lesson" },
    });
    await waitFor(
      () =>
        expect(
          localStorage.getItem("cybermentor:cms:draft:lesson:new"),
        ).toContain("Recovered evidence lesson"),
      { timeout: 1500 },
    );
    cleanup();
    renderCms("/cms/builders/lesson");
    fireEvent.click(
      await screen.findByRole("button", { name: "Restore unsaved work" }),
    );
    expect(screen.getByLabelText("Title")).toHaveValue(
      "Recovered evidence lesson",
    );
  });

  it("playtests draft mission decisions through the shared mission evaluator", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.includes("test-mission/action") && init?.method === "POST")
          return response({
            preview: true,
            creates_evidence: false,
            outcome: "correct",
            feedback:
              "Decision recorded. The evidence supports moving forward.",
            resource_content: null,
            next_stage_index: 0,
            mission_ready: true,
          });
        if (url.includes("test-mission"))
          return response({
            creates_evidence: false,
            mission: {
              title: "Draft mission",
              description: "Synthetic mission",
              metadata: {
                briefing: "Investigate safely.",
                stages: [
                  {
                    id: "stage-1",
                    title: "Triage",
                    goal: "Select the supported action.",
                    evidence: ["auth.log"],
                    actions: ["inspect log"],
                    hints: ["Read timestamps"],
                  },
                ],
              },
            },
          });
        return response({ permissions: ["content.edit_draft"] });
      }),
    );
    renderCms("/cms/preview/mission/content-1/version-1");
    fireEvent.click(await screen.findByRole("button", { name: "inspect log" }));
    expect(
      await screen.findByText(
        "Decision recorded. The evidence supports moving forward.",
      ),
    ).toBeVisible();
    expect(screen.getByText(/No record was created/)).toBeVisible();
  });
});
