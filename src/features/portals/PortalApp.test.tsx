import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthContext, type CurrentUser } from "../auth/auth-context";
import { PortalApp, RecruiterVerifyPage } from "./PortalApp";

function response(body: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

function userWithRole(role: string): CurrentUser {
  return {
    id: "user-1",
    email: "person@example.com",
    display_name: "Portal User",
    email_verified: true,
    active_organization_id: "org-1",
    organizations: [
      {
        id: "org-1",
        name: "Northbridge",
        slug: "northbridge",
        kind: "university",
        roles: [role],
      },
      {
        id: "org-2",
        name: "Acme",
        slug: "acme",
        kind: "company",
        roles: ["learner"],
      },
    ],
  };
}

function renderPortal(path: string, role = "organization_owner") {
  window.history.pushState({}, "", path);
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthContext.Provider
        value={{
          user: userWithRole(role),
          loading: false,
          refresh: vi.fn(),
          logout: vi.fn(),
          activateOrganization: vi.fn(),
        }}
      >
        <PortalApp />
      </AuthContext.Provider>
    </QueryClientProvider>,
  );
}

describe("organization portals", () => {
  beforeEach(() => vi.restoreAllMocks());
  afterEach(() => {
    vi.unstubAllGlobals();
    window.history.pushState({}, "", "/");
  });

  it("renders traceable instructor metrics and their limitations", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        response({
          portal: "instructor",
          metrics: {
            active_cohorts: 2,
            active_learners: 14,
            pending_reviews: 3,
            assignment_completion_rate: 0.5,
          },
          definitions: {
            assignment_completion_rate:
              "Completed learner assignments divided by all learner assignments.",
          },
          time_range: "all persisted organization events",
          data_source: "tenant-scoped records",
          last_updated: "2026-07-30T12:00:00Z",
          limitations: "Readiness is not guaranteed.",
        }),
      ),
    );
    renderPortal("/instructor");
    expect(
      await screen.findByRole("heading", { name: "instructor dashboard" }),
    ).toBeVisible();
    expect(screen.getByText("14")).toBeVisible();
    expect(screen.getByText("50%")).toBeVisible();
    expect(screen.getByText("Readiness is not guaranteed.")).toBeVisible();
  });

  it("hides instructor portal data from a learner role", () => {
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);
    renderPortal("/instructor", "learner");
    expect(screen.getByRole("alert")).toHaveTextContent(
      "does not permit access",
    );
    expect(fetch).not.toHaveBeenCalled();
  });

  it("shows an honest cohort empty state with accessible organization switching", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => response([])),
    );
    renderPortal("/instructor/cohorts", "instructor");
    expect(
      await screen.findByText("No cohorts exist in this organization yet."),
    ).toBeVisible();
    expect(screen.getByLabelText("Active organization")).toHaveValue("org-1");
    expect(
      screen.queryByRole("button", { name: "Create cohort" }),
    ).not.toBeInTheDocument();
  });

  it("renders only learner-approved recruiter evidence", async () => {
    window.history.pushState({}, "", "/verify/token-1");
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        response({
          display_name: "SOC Candidate",
          email: null,
          expires_at: "2026-08-30T12:00:00Z",
          artifacts: [
            {
              id: "artifact-1",
              title: "Incident escalation",
              type: "human_reviewed_project",
              verification_state: "verified",
            },
          ],
          completion_records: [],
          dimensions: {
            demonstrated_skills: 3,
            evidence_depth: 1,
            independence: "insufficient data",
          },
          limitations: "This is not a hire score or employment guarantee.",
        }),
      ),
    );
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={queryClient}>
        <RecruiterVerifyPage token="token-1" />
      </QueryClientProvider>,
    );
    expect(
      await screen.findByRole("heading", { name: "SOC Candidate" }),
    ).toBeVisible();
    expect(screen.getByText("Incident escalation")).toBeVisible();
    expect(screen.queryByText("person@example.com")).not.toBeInTheDocument();
    expect(screen.queryByText(/Sentinel/i)).not.toBeInTheDocument();
    expect(
      screen.getByText("This is not a hire score or employment guarantee."),
    ).toBeVisible();
  });
});
