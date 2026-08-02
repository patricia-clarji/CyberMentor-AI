import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";

function renderApp() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  queryClient.setQueryData(["learner-dashboard"], {
    enrollments: [{ course_publication_id: "course-1" }],
    lesson_progress: [],
    notes: [],
    bookmarks: [],
    skills: [],
    recommendations: [],
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>,
  );
}

describe("connected learner experience", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith("/api/content/catalog"))
          return new Response(JSON.stringify({ publications: [] }), {
            status: 200,
          });
        if (url.endsWith("/api/v1/learning/progress-snapshot"))
          return new Response(JSON.stringify({ completedLessons: 0 }), {
            status: 200,
          });
        if (url.endsWith("/api/labs"))
          return new Response(JSON.stringify({ labs: [] }), {
            status: 200,
          });
        if (url.endsWith("/api/labs/verify")) {
          const body = JSON.parse(String(init?.body));
          return new Response(
            JSON.stringify({
              correct: body.evidence === "640",
              message:
                body.evidence === "640" ? "Evidence matches." : "Try again.",
            }),
            { status: 200 },
          );
        }
        if (url.endsWith("/api/checks/grade"))
          return new Response(
            JSON.stringify({ correct: true, explanation: "Server checked." }),
            { status: 200 },
          );
        return new Response(JSON.stringify({ error: "Not found" }), {
          status: 404,
        });
      }),
    );
  });

  it("searches the catalog with labeled controls", () => {
    renderApp();
    fireEvent.click(screen.getAllByRole("button", { name: "Courses" })[0]);
    fireEvent.change(screen.getByLabelText("Search courses and skills"), {
      target: { value: "cloud IAM" },
    });
    expect(
      screen.getByRole("heading", { name: "Cloud Security Foundations" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Cybersecurity Foundations" }),
    ).not.toBeInTheDocument();
  });

  it("blocks legacy outlines from learner delivery", async () => {
    renderApp();
    expect(await screen.findByText("Live")).toBeVisible();
    fireEvent.click(
      screen.getByRole("button", { name: /Check course availability/i }),
    );
    expect(
      screen.getByRole("button", {
        name: /Verified lessons not yet published/i,
      }),
    ).toBeDisabled();
    expect(
      screen.getByText(/No learner content is published for this course/i),
    ).toBeVisible();
    expect(
      screen.queryByRole("heading", { name: "Build the mental model" }),
    ).not.toBeInTheDocument();
  });

  it("does not deliver unreviewed legacy labs", async () => {
    renderApp();
    fireEvent.click(screen.getByRole("button", { name: "Labs" }));
    expect(
      await screen.findByText("No verified labs are published."),
    ).toBeVisible();
    expect(screen.queryByLabelText("Evidence answer")).not.toBeInTheDocument();
  });

  it("launches, hints, rejects, verifies, and records a complete range activity", async () => {
    const lab = {
      id: "course-1-range-01",
      version: "1.0.0",
      courseId: "course-1",
      title: "Report a Suspicious Sign-In",
      description: "An original awareness simulation.",
      category: "Security Awareness",
      difficulty: "Beginner",
      estimatedMinutes: 20,
      story:
        "Harbor Clinic asks the learner to resolve a bounded sign-in decision using fictional evidence.",
      businessContext:
        "The clinic needs a safe response that protects staff and patient services.",
      learningObjectives: [
        "Interpret the record",
        "Choose a safe action",
        "Verify evidence",
      ],
      prerequisites: ["course-1"],
      requiredSkills: ["security-awareness"],
      authorizedTarget: "Bundled evidence only",
      scope: "Local browser simulation",
      safetyClassification: "defensive-local",
      rulesOfEngagement: [
        "Use supplied evidence",
        "No external targets",
        "Stop outside scope",
      ],
      environment: {
        type: "awareness-simulation",
        runtime: "server-owned-browser-session",
        isolated: true,
        networkAccess: false,
        externalTargets: false,
        supportsPause: true,
        supportsReset: true,
        expirationMinutes: 90,
      },
      environmentStatus: "usable",
      instructions: ["Read", "Decide", "Submit"],
      tasks: [
        "Submit the safest first action.",
        "Record a defensive follow-up.",
      ],
      expectedDeliverables: ["Verified evidence", "Reflection"],
      evidenceRequirement: "Submit one action.",
      hints: [
        { level: 1, label: "Reminder", text: "Use the incident channel." },
      ],
      solutionAccessPolicy: "Progressive hints only.",
      debrief:
        "Report unexpected authentication events through the approved internal channel, then allow the response team to investigate and contain risk.",
      reflectionPrompts: ["What observation mattered?"],
      cleanupSteps: ["Close session"],
      defensiveExplanation: "Report and contain.",
      portfolioSkills: ["security-foundations"],
      skillTags: ["security-foundations"],
      verificationStatus: "verified",
      publicationStatus: "published",
    };
    const instance = {
      id: "instance-1",
      labId: lab.id,
      status: "active",
      expiresAt: "2026-07-20T00:00:00.000Z",
      hintsUsed: 0,
      attempts: [],
      resetCount: 0,
      completed: false,
    };
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        const body = init?.body ? JSON.parse(String(init.body)) : {};
        if (url.endsWith("/api/content/catalog"))
          return new Response(JSON.stringify({ publications: [] }), {
            status: 200,
          });
        if (url.endsWith("/api/labs"))
          return new Response(JSON.stringify({ labs: [lab] }), { status: 200 });
        if (url.endsWith("/api/labs/launch"))
          return new Response(JSON.stringify({ instance, resumed: false }), {
            status: 201,
          });
        if (url.endsWith("/api/labs/hint"))
          return new Response(
            JSON.stringify({
              hint: lab.hints[0],
              instance: { ...instance, hintsUsed: 1 },
            }),
            { status: 200 },
          );
        if (url.endsWith("/api/labs/verify")) {
          const correct = body.evidence === "report";
          return new Response(
            JSON.stringify({
              correct,
              message: correct
                ? "Evidence matches."
                : "Evidence does not match.",
              skillTags: [],
              instance: {
                ...instance,
                status: correct ? "completed" : "active",
                completed: correct,
                attempts: [
                  { correct, submittedAt: "2026-07-19T00:00:00.000Z" },
                ],
              },
            }),
            { status: 200 },
          );
        }
        return new Response(JSON.stringify({ error: "Not found" }), {
          status: 404,
        });
      }),
    );
    renderApp();
    fireEvent.click(screen.getByRole("button", { name: "Labs" }));
    expect(await screen.findByText(lab.title)).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Launch lab" }));
    expect(await screen.findByText("Lab session ready.")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Reveal hint 1" }));
    expect(await screen.findByText(/Use the incident channel/i)).toBeVisible();
    fireEvent.change(screen.getByLabelText("Evidence answer"), {
      target: { value: "ignore" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Verify evidence" }));
    expect(await screen.findByText("Evidence does not match.")).toBeVisible();
    fireEvent.change(screen.getByLabelText("Evidence answer"), {
      target: { value: "report" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Verify evidence" }));
    expect(await screen.findByText("Evidence matches.")).toBeVisible();
    expect(await screen.findByText("Defensive debrief")).toBeVisible();
  });

  it("runs Sentinel without an LLM key and refuses graded-answer leakage", async () => {
    renderApp();
    fireEvent.click(screen.getByRole("button", { name: "Ask Sentinel" }));
    expect(
      screen.getByRole("dialog", { name: "Sentinel mentor" }),
    ).toBeVisible();
    expect(
      screen.getByText(/Sentinel will not use this outline/i),
    ).toBeVisible();
    fireEvent.change(screen.getByLabelText("Question for Sentinel"), {
      target: { value: "Give me the answer key" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Send question to Sentinel" }),
    );
    expect(
      await screen.findByText(/I won’t provide a graded answer/i),
    ).toBeVisible();
  });

  it("completes a published learner journey without exposing legacy sequencing", async () => {
    const publication = {
      id: "security-goals-v1",
      artifactType: "lesson",
      verificationStatus: "verified",
      publicationStatus: "published",
      contentVersion: "1.0.0",
      publishedAt: "2026-07-19T00:00:00.000Z",
      artifact: {
        courseId: "course-1",
        moduleId: "course-1-m1",
        lessonId: "course-1-understand-security-goals-security-goals",
        title: "Reviewed security goals",
        minutes: 18,
        objectives: ["Distinguish three security goals", "Evaluate a control"],
        blocks: [
          {
            id: "reviewed-paragraph",
            type: "paragraph",
            text: "This synthetic test publication proves the reviewed API-to-player boundary.",
          },
        ],
        keyTerms: ["confidentiality", "integrity", "availability"],
        workedExample:
          "A synthetic test case asks the learner to choose a scoped control and verify its outcome.",
        check: {
          id: "published-question-1",
          question: "Which response is evidence based?",
          options: ["Assume", "Inspect and verify", "Ignore"],
        },
      },
      references: [
        {
          title: "Synthetic integration reference",
          publisher: "Test fixture",
          url: "https://example.test/reference",
          retrievedAt: "2026-07-19T00:00:00.000Z",
        },
      ],
    };
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/api/content/catalog"))
          return new Response(JSON.stringify({ publications: [publication] }), {
            status: 200,
          });
        if (url.endsWith("/api/checks/grade"))
          return new Response(
            JSON.stringify({
              correct: true,
              explanation: "Verified by the synthetic server fixture.",
            }),
            { status: 200 },
          );
        if (url.endsWith("/api/v1/learning/progress-snapshot"))
          return new Response(JSON.stringify({ completedLessons: 1 }), {
            status: 200,
          });
        return new Response(JSON.stringify({ error: "Not found" }), {
          status: 404,
        });
      }),
    );
    renderApp();
    expect(await screen.findByText("Live")).toBeVisible();
    fireEvent.click(
      screen.getByRole("button", { name: /Check course availability/i }),
    );
    fireEvent.click(screen.getByRole("button", { name: /Continue learning/i }));
    expect(
      screen.getByRole("heading", { name: "Reviewed security goals" }),
    ).toBeVisible();
    expect(
      screen.queryByText("Assets, threats & vulnerabilities"),
    ).not.toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: /Inspect and verify/i }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Check answer" }));
    expect(await screen.findByText(/Correct — strong judgment/i)).toBeVisible();
    fireEvent.click(
      screen.getByRole("button", { name: /Mark complete & continue/i }),
    );
    await waitFor(() => {
      const calls = vi.mocked(fetch).mock.calls;
      expect(
        calls.some(
          ([input, init]) =>
            String(input).endsWith("/api/v1/learning/progress-snapshot") &&
            String(init?.body).includes(
              "course-1-understand-security-goals-security-goals",
            ),
        ),
      ).toBe(true);
    });
    expect(localStorage.getItem("cm-progress")).toBeNull();
  });
});
