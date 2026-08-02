import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthContext, type CurrentUser } from "../auth/auth-context";
import { CompetitionApp } from "./CompetitionApp";

const user: CurrentUser = {
  id: "user-1",
  email: "learner@example.com",
  display_name: "Evidence Learner",
  email_verified: true,
  active_organization_id: "org-1",
  organizations: [
    {
      id: "org-1",
      name: "Evidence Learner workspace",
      slug: "evidence-learner",
      kind: "personal",
      roles: ["learner"],
    },
  ],
};

function response(body: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  } as Response);
}

function renderApp(path: string) {
  window.history.pushState({}, "", path);
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthContext.Provider
        value={{
          user,
          loading: false,
          refresh: vi.fn(),
          logout: vi.fn(),
          activateOrganization: vi.fn(),
        }}
      >
        <CompetitionApp />
      </AuthContext.Provider>
    </QueryClientProvider>,
  );
}

describe("competition learner workflow", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    window.history.pushState({}, "", "/");
  });

  it("renders camel-case adaptive recommendations without crashing", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        response({
          profile: null,
          primary_goal: "Junior SOC Analyst",
          enrollments: [],
          lesson_progress: [],
          skills: [],
          recommendations: [
            {
              id: "rec-1",
              activityType: "guided_practice",
              activityId: "linux-investigation-refresh",
              reason: "Practical Linux evidence needs guided reinforcement.",
              interventionType: "guided_learning_mode",
              required: true,
            },
          ],
        }),
      ),
    );
    renderApp("/academy/roadmap");
    expect(
      await screen.findByRole("heading", { name: "Your Junior SOC roadmap" }),
    ).toBeVisible();
    expect(
      screen.getByRole("heading", { name: "linux investigation refresh" }),
    ).toBeVisible();
    expect(screen.getByText("REQUIRED · guided practice")).toBeVisible();
  });

  it("shows the human-review boundary on the professional project", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((request: RequestInfo | URL) => {
        const url = String(request);
        if (url.endsWith("/submissions")) return response([]);
        return response({
          title: "Professional SOC Incident Escalation",
          description: "Produce a reproducible incident escalation.",
          version: "soc-report-1.0.0",
          milestones: [
            {
              position: 1,
              title: "Problem and scope",
              requirement: "State the authorized scope and business context.",
            },
          ],
          rubric_version: "soc-report-1.0.0",
          rubric: [
            {
              key: "problem-definition",
              description: "Define the scoped problem.",
              weight: 0.2,
              pass_standard: "Scope and impact are explicit.",
            },
          ],
          review_notice:
            "Submission does not pass automatically. An authorized human reviewer is required.",
        });
      }),
    );
    renderApp("/academy/project");
    expect(
      await screen.findByRole("heading", {
        name: "Professional SOC Incident Escalation",
      }),
    ).toBeVisible();
    expect(
      screen.getByText(
        "Submission does not pass automatically. An authorized human reviewer is required.",
      ),
    ).toBeVisible();
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Submit for human review" }),
      ).toBeEnabled(),
    );
  });

  it("renders the ordered SOC pathway with explicit completion rules", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        response({
          id: "junior-soc-analyst-pathway",
          version: "1.0.0",
          title: "Junior SOC Analyst Pathway",
          purpose: "Prepare for a bounded workplace investigation.",
          review_state: "internally-checked-pending-external-review",
          estimated_minutes: 655,
          enrolled: true,
          modules: [
            {
              id: "soc-01-foundations",
              position: 1,
              title: "SOC foundations and evidence reasoning",
              purpose: "Make defensible decisions.",
              prerequisite_skills: [],
              objectives: ["Separate observations.", "Preserve uncertainty."],
              linked_skills: ["alert-triage"],
              estimated_minutes: 70,
              review_state: "internally-checked-pending-external-review",
              required_lessons: ["soc-01-l1"],
              required_practices: ["soc-01-practice"],
              required_assessment: "soc-01-foundations-assessment",
              completion_rules: {
                all_required_lessons_completed: true,
                all_required_practices_passed: true,
                assessment_minimum_score: 0.7,
              },
              lessons: [
                {
                  id: "soc-01-l1",
                  title: "From events to decisions",
                  minutes: 35,
                  linked_skills: ["alert-triage"],
                  review_state: "internally-checked-pending-external-review",
                },
              ],
              practice: {
                id: "soc-01-practice",
                type: "scenario_decision",
                title: "Classify the signal",
                scenario: "Synthetic evidence.",
                objective: "Choose the supported conclusion.",
                prompt: "Which conclusion?",
                options: ["Unsupported", "Supported"],
                feedback: "Preserve uncertainty.",
                linked_skills: ["alert-triage"],
              },
              assessment: {
                id: "soc-01-foundations-assessment",
                title: "Foundations assessment",
                version: "1.0.0",
                retake_policy: "Attempts are retained.",
              },
            },
          ],
          module_statuses: [
            {
              module_id: "soc-01-foundations",
              unlocked: true,
              completed: false,
              required_lessons_completed: false,
              required_practices_completed: false,
              assessment_passed: false,
            },
          ],
        }),
      ),
    );
    renderApp("/academy/pathway");
    expect(
      await screen.findByRole("heading", {
        name: "Junior SOC Analyst Pathway",
      }),
    ).toBeVisible();
    expect(
      screen.getByRole("heading", {
        name: "SOC foundations and evidence reasoning",
      }),
    ).toBeVisible();
    expect(
      screen.getByText(/required lesson, practice, and a 70%/i),
    ).toBeVisible();
  });

  it("submits a module assessment and displays deterministic feedback", async () => {
    vi.stubGlobal("crypto", {
      randomUUID: () => "assessment-browser-test-0001",
    });
    vi.stubGlobal(
      "fetch",
      vi.fn((request: RequestInfo | URL, init?: RequestInit) => {
        if (init?.method === "POST")
          return response({
            score: 1,
            passed: true,
            feedback: "The evidence-based response is supported.",
          });
        return response({
          id: "soc-01-foundations-assessment",
          version: "1.0.0",
          title: "SOC foundations assessment",
          retake_policy: "Every attempt is retained.",
          questions: [
            {
              id: "soc-01-foundations-q1",
              type: "scenario_decision",
              prompt: "Which statement preserves uncertainty?",
              options: ["Confirmed breach", "Suspicious; correlate next"],
              explanation: "Correlate.",
              feedback: "Correlate.",
              linked_skills: ["alert-triage"],
              skill: "alert-triage",
              weight: 1,
            },
          ],
          attempts: [],
        });
      }),
    );
    renderApp("/academy/pathway/assessments/soc-01-foundations-assessment");
    expect(
      await screen.findByRole("heading", {
        name: "SOC foundations assessment",
      }),
    ).toBeVisible();
    fireEvent.click(screen.getByLabelText("Suspicious; correlate next"));
    fireEvent.click(
      screen.getByRole("button", { name: "Submit module assessment" }),
    );
    expect(
      await screen.findByRole("heading", { name: "Assessment passed" }),
    ).toBeVisible();
    expect(screen.getByText("Score: 100%")).toBeVisible();
  });

  it("restores Sentinel history and shows adaptive mentoring evidence", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((request: RequestInfo | URL, init?: RequestInit) => {
        const url = String(request);
        if (url.endsWith("/mentor/threads") && init?.method === "POST")
          return response({
            id: "thread-1",
            context_type: "course",
            context_id: "course-4",
            status: "active",
          });
        if (url.endsWith("/mentor/threads/thread-1") && !init?.method)
          return response({
            thread: {
              id: "thread-1",
              context_type: "course",
              context_id: "course-4",
              status: "active",
            },
            messages: [
              {
                id: "history-1",
                role: "assistant",
                body: "Previously, we separated observations from conclusions.",
                delivery_mode: "deterministic_fallback",
                mentor_mode: "review",
                provider_generated: false,
                reasoning_summary: "Prior learning required review.",
                related_skills: ["alert-triage"],
                recommended_action: null,
                created_at: "2026-07-30T12:00:00Z",
              },
            ],
          });
        if (url.endsWith("/messages") && init?.method === "POST")
          return response({
            thread_id: "thread-1",
            message_id: "answer-1",
            answer:
              "Which event is directly observed, and what evidence would test your inference?",
            mode: "deterministic_fallback",
            mentor_mode: "socratic",
            intervention: "ask_question",
            provider_generated: false,
            blocked: false,
            citations: [
              {
                publication_id: "lesson-1",
                publication_version: "1.0.0",
                chunk_id: "evidence",
                title: "Evidence reasoning",
                publisher: "NIST",
                url: "https://csrc.nist.gov/example",
                verification_status: "verified",
              },
            ],
            reasoning_summary:
              "Selected socratic mode because the learner should test an assumption.",
            related_skills: ["alert-triage", "evidence-preservation"],
            recommended_next_action: {
              type: "lesson",
              id: "alert-triage",
              reason: "Review evidence boundaries before reassessment.",
            },
            detected_misconceptions: ["premature-conclusion"],
            limitation_notice: "Sentinel does not reveal assessed answers.",
            prompt_version: "sentinel-mentor-2.0.0",
            retrieval_version: "soc-reviewed-hybrid-2.0.0",
            provider: "deterministic",
            model: "fallback-2.0.0",
            latency_ms: 0,
          });
        if (url.endsWith("/feedback") && init?.method === "POST")
          return response({
            message_id: "answer-1",
            rating: "helpful",
            saved: true,
          });
        return response({}, 404);
      }),
    );
    renderApp("/academy/sentinel");
    expect(
      await screen.findByText(
        "Previously, we separated observations from conclusions.",
      ),
    ).toBeVisible();
    fireEvent.change(screen.getByLabelText("Your question"), {
      target: { value: "I think this alert proves compromise." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Ask Sentinel" }));
    await waitFor(() =>
      expect(
        screen.getByText(
          "Which event is directly observed, and what evidence would test your inference?",
        ),
      ).toBeVisible(),
    );
    expect(screen.getByText("socratic")).toBeVisible();
    expect(screen.getByText("Evidence reasoning — NIST")).toBeVisible();
    expect(
      screen.getByText("Review evidence boundaries before reassessment."),
    ).toBeVisible();
    fireEvent.click(screen.getAllByRole("button", { name: "Helpful" }).at(-1)!);
    expect(await screen.findByText("Feedback saved")).toBeVisible();
  });
});
