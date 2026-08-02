import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent, type ReactNode } from "react";
import { Link, Route, Switch, useLocation, useRoute } from "wouter";
import { apiFetch, ApiError } from "../../lib/api-client";
import { useAuth } from "../auth/auth-context";

type DashboardData = {
  portal: string;
  metrics: Record<string, number | null>;
  definitions: Record<string, string>;
  time_range: string;
  data_source: string;
  last_updated: string;
  limitations: string;
};

type Cohort = {
  id: string;
  stable_key: string;
  name: string;
  description: string;
  cohort_type: string;
  status: string;
  start_date: string;
  end_date: string | null;
  active_learners: number;
};

type Assignment = {
  id: string;
  title: string;
  assignment_type: string;
  content_id: string;
  content_version: string;
  due_at: string | null;
  overdue: boolean;
  review_required: boolean;
  status: string;
};

function ErrorState({ error }: { error: unknown }) {
  return (
    <div className="portal-state error" role="alert">
      {error instanceof ApiError
        ? error.message
        : "The requested organization data could not be loaded."}
    </div>
  );
}

function EmptyState({ children }: { children: ReactNode }) {
  return <div className="portal-state">{children}</div>;
}

function useActiveRoles() {
  const { user } = useAuth();
  return (
    user?.organizations.find(
      (organization) => organization.id === user.active_organization_id,
    )?.roles ?? []
  );
}

function canManage(roles: string[]) {
  return roles.some((role) =>
    [
      "organization_owner",
      "organization_admin",
      "cohort_manager",
      "company_manager",
    ].includes(role),
  );
}

function PortalShell({ children }: { children: ReactNode }) {
  const { user, activateOrganization, logout } = useAuth();
  const [, navigate] = useLocation();
  const roles = useActiveRoles();
  async function switchOrganization(organizationId: string) {
    await activateOrganization(organizationId);
    navigate("/organization", { replace: true });
  }
  return (
    <div className="competition-shell portal-shell">
      <a className="skip-link" href="#portal-main">
        Skip to main content
      </a>
      <header className="competition-header">
        <Link className="competition-brand" to="/organization">
          <span>
            CyberMentor
            <small>Organization workspace</small>
          </span>
        </Link>
        <nav aria-label="Organization portals">
          <Link to="/instructor">Instructor</Link>
          <Link to="/university">University</Link>
          <Link to="/company">Company</Link>
          <Link to="/recruiter">Recruiter</Link>
          <Link to="/organization">Organization</Link>
          <Link to="/academy">Learner</Link>
        </nav>
        <div className="portal-account">
          <label>
            Active organization
            <select
              value={user?.active_organization_id}
              onChange={(event) =>
                void switchOrganization(event.currentTarget.value)
              }
            >
              {user?.organizations.map((organization) => (
                <option value={organization.id} key={organization.id}>
                  {organization.name}
                </option>
              ))}
            </select>
          </label>
          <small>{roles.join(", ") || "No active role"}</small>
          <button
            className="quiet-button"
            onClick={() => void logout().then(() => navigate("/login"))}
          >
            Sign out
          </button>
        </div>
      </header>
      <main id="portal-main" className="competition-main">
        {children}
      </main>
    </div>
  );
}

function PortalDashboard({ portal }: { portal: string }) {
  const query = useQuery({
    queryKey: ["portal-dashboard", portal],
    queryFn: () =>
      apiFetch<DashboardData>(`/api/v1/operations/dashboard?portal=${portal}`),
  });
  if (query.isLoading)
    return <p role="status">Loading organization metrics…</p>;
  if (query.error) return <ErrorState error={query.error} />;
  const data = query.data!;
  return (
    <section className="portal-page">
      <span className="eyebrow">REAL ORGANIZATION EVIDENCE</span>
      <h1>{portal.replaceAll("_", " ")} dashboard</h1>
      <p>
        Metrics are calculated from persisted events in the active organization.
        No sample trend data is inserted.
      </p>
      <div className="portal-metrics">
        {Object.entries(data.metrics).map(([key, value]) => (
          <article key={key}>
            <strong>
              {value == null
                ? "Insufficient data"
                : key.endsWith("_rate")
                  ? `${Math.round(value * 100)}%`
                  : value}
            </strong>
            <span>{key.replaceAll("_", " ")}</span>
          </article>
        ))}
      </div>
      <section className="portal-definition">
        <h2>Metric definitions</h2>
        {Object.entries(data.definitions).map(([key, definition]) => (
          <p key={key}>
            <strong>{key.replaceAll("_", " ")}:</strong> {definition}
          </p>
        ))}
        <small>
          Source: {data.data_source} · Range: {data.time_range} · Updated{" "}
          {new Date(data.last_updated).toLocaleString()}
        </small>
        <p>{data.limitations}</p>
      </section>
    </section>
  );
}

function CohortsPage() {
  const queryClient = useQueryClient();
  const roles = useActiveRoles();
  const query = useQuery({
    queryKey: ["organization-cohorts"],
    queryFn: () => apiFetch<Cohort[]>("/api/v1/operations/cohorts"),
  });
  const [error, setError] = useState<unknown>();
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    try {
      await apiFetch("/api/v1/operations/cohorts", {
        method: "POST",
        body: JSON.stringify({
          stable_key: data.get("stable_key"),
          name: data.get("name"),
          description: data.get("description"),
          cohort_type: data.get("cohort_type"),
          start_date: data.get("start_date"),
        }),
      });
      form.reset();
      await queryClient.invalidateQueries({
        queryKey: ["organization-cohorts"],
      });
    } catch (caught) {
      setError(caught);
    }
  }
  return (
    <section className="portal-page">
      <h1>Cohorts</h1>
      <p>
        Learners leaving a cohort are archived from the roster; their historical
        evidence remains intact.
      </p>
      {query.isLoading && <p role="status">Loading cohorts…</p>}
      {query.error && <ErrorState error={query.error} />}
      {query.data?.length === 0 && (
        <EmptyState>No cohorts exist in this organization yet.</EmptyState>
      )}
      <div className="portal-list">
        {query.data?.map((cohort) => (
          <article key={cohort.id}>
            <div>
              <h2>{cohort.name}</h2>
              <p>{cohort.description || "No description provided."}</p>
              <small>
                {cohort.cohort_type.replaceAll("_", " ")} · {cohort.status} ·{" "}
                {cohort.active_learners} active learners
              </small>
            </div>
            <Link to={`/instructor/cohorts/${cohort.id}`}>Open cohort</Link>
          </article>
        ))}
      </div>
      {canManage(roles) && (
        <form className="portal-form" onSubmit={create}>
          <h2>Create cohort</h2>
          {error != null && <ErrorState error={error} />}
          <label>
            Stable key
            <input
              name="stable_key"
              pattern="[a-z0-9]+(?:-[a-z0-9]+)*"
              required
            />
          </label>
          <label>
            Name
            <input name="name" minLength={2} required />
          </label>
          <label>
            Description
            <textarea name="description" />
          </label>
          <label>
            Cohort type
            <select name="cohort_type">
              <option value="academic_course">Academic course</option>
              <option value="bootcamp">Bootcamp</option>
              <option value="employee_training">Employee training</option>
              <option value="certification_preparation">
                Certification preparation
              </option>
              <option value="private_group">Private group</option>
            </select>
          </label>
          <label>
            Start date
            <input name="start_date" type="date" required />
          </label>
          <button className="primary">Create cohort</button>
        </form>
      )}
    </section>
  );
}

function CohortPage() {
  const [, params] = useRoute("/instructor/cohorts/:cohortId");
  const cohortId = params?.cohortId ?? "";
  const query = useQuery({
    queryKey: ["organization-cohort", cohortId],
    queryFn: () =>
      apiFetch<{
        name: string;
        status: string;
        cohort_type: string;
        learners: { user_id: string; display_name: string; status: string }[];
        curriculum: {
          type: string;
          id: string;
          version: string;
          due_at: string | null;
        }[];
      }>(`/api/v1/operations/cohorts/${cohortId}`),
    enabled: Boolean(cohortId),
  });
  if (query.isLoading) return <p role="status">Loading cohort roster…</p>;
  if (query.error) return <ErrorState error={query.error} />;
  const cohort = query.data!;
  return (
    <section className="portal-page">
      <h1>{cohort.name}</h1>
      <p>
        {cohort.cohort_type.replaceAll("_", " ")} · {cohort.status}
      </p>
      <h2>Learner roster</h2>
      {cohort.learners.length === 0 ? (
        <EmptyState>No learners are enrolled.</EmptyState>
      ) : (
        <div className="portal-list">
          {cohort.learners.map((learner) => (
            <article key={learner.user_id}>
              <strong>{learner.display_name}</strong>
              <span>{learner.status}</span>
              <Link to={`/instructor/learners/${learner.user_id}`}>
                Authorized progress
              </Link>
            </article>
          ))}
        </div>
      )}
      <h2>Version-pinned curriculum</h2>
      {cohort.curriculum.length === 0 ? (
        <EmptyState>No curriculum has been assigned.</EmptyState>
      ) : (
        <ul>
          {cohort.curriculum.map((item) => (
            <li key={`${item.type}-${item.id}-${item.version}`}>
              {item.type}: {item.id} · version {item.version}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function AssignmentsPage() {
  const queryClient = useQueryClient();
  const roles = useActiveRoles();
  const query = useQuery({
    queryKey: ["organization-assignments"],
    queryFn: () => apiFetch<Assignment[]>("/api/v1/operations/assignments"),
  });
  const [message, setMessage] = useState("");
  async function submitAssignment(
    assignmentId: string,
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const result = await apiFetch<{ revision: number; status: string }>(
      `/api/v1/operations/assignments/${assignmentId}/submissions`,
      {
        method: "POST",
        body: JSON.stringify({ body: data.get("body"), evidence_items: [] }),
      },
    );
    setMessage(
      `Revision ${result.revision} submitted with ${result.status.replaceAll("_", " ")} status.`,
    );
    form.reset();
  }
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const created = await apiFetch<{ id: string }>(
      "/api/v1/operations/assignments",
      {
        method: "POST",
        body: JSON.stringify({
          title: data.get("title"),
          instructions: data.get("instructions"),
          assignment_type: data.get("assignment_type"),
          content_id: data.get("content_id"),
          content_version: data.get("content_version"),
          review_required: data.get("review_required") === "on",
        }),
      },
    );
    setMessage(`Draft ${created.id} created.`);
    form.reset();
    await queryClient.invalidateQueries({
      queryKey: ["organization-assignments"],
    });
  }
  return (
    <section className="portal-page">
      <h1>Assignments</h1>
      {query.isLoading && <p role="status">Loading assignments…</p>}
      {query.error && <ErrorState error={query.error} />}
      {query.data?.length === 0 && (
        <EmptyState>No assigned work exists yet.</EmptyState>
      )}
      <div className="portal-list">
        {query.data?.map((assignment) => (
          <article key={assignment.id}>
            <h2>{assignment.title}</h2>
            <p>
              {assignment.assignment_type} · {assignment.content_id} · version{" "}
              {assignment.content_version}
            </p>
            <small>
              {assignment.status}
              {assignment.overdue ? " · overdue" : ""}
              {assignment.review_required ? " · human review required" : ""}
            </small>
            {!canManage(roles) && assignment.status === "active" && (
              <form
                className="portal-inline-form"
                onSubmit={(event) =>
                  void submitAssignment(assignment.id, event)
                }
              >
                <label>
                  Your response
                  <textarea name="body" minLength={1} required />
                </label>
                <button>Submit assignment</button>
              </form>
            )}
          </article>
        ))}
      </div>
      {canManage(roles) && (
        <form className="portal-form" onSubmit={(event) => void create(event)}>
          <h2>Create version-pinned assignment</h2>
          {message && <p role="status">{message}</p>}
          <label>
            Title
            <input name="title" required />
          </label>
          <label>
            Instructions
            <textarea name="instructions" required />
          </label>
          <label>
            Type
            <select name="assignment_type">
              <option value="pathway">Pathway</option>
              <option value="lesson">Lesson</option>
              <option value="lab">Lab</option>
              <option value="mission">Mission</option>
              <option value="project">Project</option>
              <option value="reflection">Reflection</option>
            </select>
          </label>
          <label>
            Content ID
            <input name="content_id" required />
          </label>
          <label>
            Content version
            <input name="content_version" required />
          </label>
          <label className="check-row">
            <input name="review_required" type="checkbox" />
            Human review required
          </label>
          <button className="primary">Save draft</button>
        </form>
      )}
    </section>
  );
}

function ReviewsPage() {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["organization-reviews"],
    queryFn: () =>
      apiFetch<
        {
          id: string;
          assignment_title: string;
          learner_user_id: string;
          state: string;
          revision_count: number;
          content_version: string;
          feedback: string | null;
        }[]
      >("/api/v1/operations/reviews"),
  });
  async function decide(
    reviewId: string,
    decision: "approved" | "revision_requested" | "rejected",
  ) {
    await apiFetch(`/api/v1/operations/reviews/${reviewId}/decision`, {
      method: "POST",
      body: JSON.stringify({
        decision,
        feedback:
          decision === "approved"
            ? "Evidence meets the recorded completion criteria."
            : "Revise the evidence using the published criteria.",
        rubric_scores: [],
      }),
    });
    await queryClient.invalidateQueries({ queryKey: ["organization-reviews"] });
  }
  return (
    <section className="portal-page">
      <h1>Human review queue</h1>
      <p>AI suggestions never become final review decisions.</p>
      {query.isLoading && <p role="status">Loading review queue…</p>}
      {query.error && <ErrorState error={query.error} />}
      {query.data?.length === 0 && (
        <EmptyState>No review requests are waiting.</EmptyState>
      )}
      <div className="portal-list">
        {query.data?.map((review) => (
          <article key={review.id}>
            <h2>{review.assignment_title}</h2>
            <p>
              State: {review.state.replaceAll("_", " ")} · revision{" "}
              {review.revision_count} · content {review.content_version}
            </p>
            {["pending", "in_review", "resubmitted"].includes(review.state) && (
              <div className="portal-actions">
                <button onClick={() => void decide(review.id, "approved")}>
                  Approve
                </button>
                <button
                  onClick={() => void decide(review.id, "revision_requested")}
                >
                  Request revision
                </button>
                <button onClick={() => void decide(review.id, "rejected")}>
                  Reject with reason
                </button>
              </div>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}

function LearnerDetailPage() {
  const [, params] = useRoute("/instructor/learners/:learnerId");
  const learnerId = params?.learnerId ?? "";
  const query = useQuery({
    queryKey: ["authorized-learner-detail", learnerId],
    queryFn: () =>
      apiFetch<{
        display_name: string;
        skills: {
          skill_id: string;
          mastery: number;
          confidence: number;
        }[];
        completion_records: {
          scope_type: string;
          scope_id: string;
          issued_at: string;
          revoked: boolean;
        }[];
        privacy_notice: string;
      }>(`/api/v1/operations/learners/${learnerId}`),
    enabled: Boolean(learnerId),
  });
  if (query.isLoading)
    return <p role="status">Loading authorized learner evidence…</p>;
  if (query.error) return <ErrorState error={query.error} />;
  const learner = query.data!;
  return (
    <section className="portal-page">
      <h1>{learner.display_name}</h1>
      <p className="limitation">{learner.privacy_notice}</p>
      <h2>Evidence-backed skills</h2>
      {learner.skills.length === 0 ? (
        <EmptyState>
          No organization-scoped skill evidence is available.
        </EmptyState>
      ) : (
        <div className="portal-list">
          {learner.skills.map((skill) => (
            <article key={skill.skill_id}>
              <strong>{skill.skill_id}</strong>
              <span>
                mastery estimate {Math.round(skill.mastery * 100)}% · confidence{" "}
                {Math.round(skill.confidence * 100)}%
              </span>
            </article>
          ))}
        </div>
      )}
      <h2>Completion records</h2>
      {learner.completion_records.map((record) => (
        <article key={`${record.scope_type}-${record.scope_id}`}>
          {record.scope_type}: {record.scope_id} ·{" "}
          {record.revoked ? "revoked" : "current"}
        </article>
      ))}
    </section>
  );
}

function ProgrammesPage() {
  const query = useQuery({
    queryKey: ["organization-programmes"],
    queryFn: () =>
      apiFetch<
        {
          id: string;
          stable_key: string;
          name: string;
          academic_period: string | null;
          qualification_label: string | null;
          required_pathways: string[];
          required_projects: string[];
          status: string;
        }[]
      >("/api/v1/operations/programmes"),
  });
  return (
    <section className="portal-page">
      <h1>Programmes</h1>
      <p>
        Programme labels are internal unless verified accreditation metadata is
        explicitly recorded.
      </p>
      {query.isLoading && <p role="status">Loading programmes…</p>}
      {query.error && <ErrorState error={query.error} />}
      {query.data?.length === 0 && (
        <EmptyState>No programmes have been created.</EmptyState>
      )}
      <div className="portal-list">
        {query.data?.map((programme) => (
          <article key={programme.id}>
            <div>
              <h2>{programme.name}</h2>
              <p>
                {programme.academic_period || "No academic period assigned"}
              </p>
              <small>
                {programme.status} · {programme.required_pathways.length}{" "}
                required pathways · {programme.required_projects.length}{" "}
                required projects
              </small>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function MembersPage() {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["organization-members"],
    queryFn: () =>
      apiFetch<
        {
          membership_id: string;
          display_name: string;
          email: string;
          active: boolean;
          roles: string[];
          joined_at: string;
        }[]
      >("/api/v1/organizations/members"),
  });
  async function setActive(membershipId: string, active: boolean) {
    await apiFetch(`/api/v1/organizations/members/${membershipId}`, {
      method: "PATCH",
      body: JSON.stringify({ active }),
    });
    await queryClient.invalidateQueries({ queryKey: ["organization-members"] });
  }
  return (
    <section className="portal-page">
      <h1>Organization members</h1>
      <nav className="portal-subnav" aria-label="Organization management">
        <Link to="/organization">Profile</Link>
        <Link to="/organization/invitations">Invitations</Link>
        <Link to="/organization/audit">Audit</Link>
      </nav>
      {query.isLoading && <p role="status">Loading members…</p>}
      {query.error && <ErrorState error={query.error} />}
      <div className="portal-list">
        {query.data?.map((member) => (
          <article key={member.membership_id}>
            <div>
              <strong>{member.display_name || member.email}</strong>
              <p>{member.email}</p>
              <small>
                {member.roles.join(", ")} ·{" "}
                {member.active ? "active" : "inactive"}
              </small>
            </div>
            <button
              onClick={() =>
                void setActive(member.membership_id, !member.active)
              }
            >
              {member.active ? "Deactivate" : "Reactivate"}
            </button>
          </article>
        ))}
      </div>
    </section>
  );
}

function InvitationsPage() {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["organization-invitations"],
    queryFn: () =>
      apiFetch<
        {
          id: string;
          email: string;
          role: string;
          status: string;
          expires_at: string;
        }[]
      >("/api/v1/organizations/invitations"),
  });
  const [message, setMessage] = useState("");
  async function send(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    await apiFetch("/api/v1/organizations/invitations", {
      method: "POST",
      body: JSON.stringify({
        email: data.get("email"),
        role: data.get("role"),
      }),
    });
    setMessage("Invitation sent.");
    form.reset();
    await queryClient.invalidateQueries({
      queryKey: ["organization-invitations"],
    });
  }
  return (
    <section className="portal-page">
      <h1>Organization invitations</h1>
      {query.isLoading && <p role="status">Loading invitations…</p>}
      {query.error && <ErrorState error={query.error} />}
      <div className="portal-list">
        {query.data?.map((item) => (
          <article key={item.id}>
            <strong>{item.email}</strong>
            <span>
              {item.role.replaceAll("_", " ")} · {item.status} · expires{" "}
              {new Date(item.expires_at).toLocaleDateString()}
            </span>
          </article>
        ))}
      </div>
      <form className="portal-form" onSubmit={(event) => void send(event)}>
        <h2>Invite member</h2>
        {message && <p role="status">{message}</p>}
        <label>
          Intended email
          <input name="email" type="email" required />
        </label>
        <label>
          Assigned role
          <select name="role">
            <option value="learner">Learner</option>
            <option value="instructor">Instructor</option>
            <option value="reviewer">Reviewer</option>
            <option value="cohort_manager">Cohort manager</option>
            <option value="company_manager">Company manager</option>
            <option value="recruiter">Recruiter</option>
            <option value="organization_admin">Organization admin</option>
          </select>
        </label>
        <button className="primary">Send invitation</button>
      </form>
    </section>
  );
}

function OrganizationPage({ section = "profile" }: { section?: string }) {
  const query = useQuery({
    queryKey: ["active-organization", section],
    queryFn: () =>
      apiFetch<Record<string, unknown>>(
        section === "audit"
          ? "/api/v1/organizations/audit"
          : section === "members"
            ? "/api/v1/organizations/members"
            : section === "invitations"
              ? "/api/v1/organizations/invitations"
              : "/api/v1/organizations/current",
      ),
  });
  return (
    <section className="portal-page">
      <h1>Organization {section}</h1>
      <nav className="portal-subnav" aria-label="Organization management">
        <Link to="/organization">Profile</Link>
        <Link to="/organization/members">Members</Link>
        <Link to="/organization/invitations">Invitations</Link>
        <Link to="/organization/settings">Settings</Link>
        <Link to="/organization/audit">Audit</Link>
      </nav>
      {query.isLoading && <p role="status">Loading {section}…</p>}
      {query.error && <ErrorState error={query.error} />}
      {query.data && (
        <pre className="portal-data">{JSON.stringify(query.data, null, 2)}</pre>
      )}
    </section>
  );
}

function SharingPage() {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["learner-shares"],
    queryFn: () =>
      apiFetch<
        {
          id: string;
          display_name: string;
          expires_at: string;
          status: string;
        }[]
      >("/api/v1/operations/shares"),
  });
  const evidence = useQuery({
    queryKey: ["shareable-evidence"],
    queryFn: () =>
      apiFetch<{
        artifacts: {
          id: string;
          title: string;
          type: string;
          verification_state: string;
        }[];
        completion_records: {
          id: string;
          scope_type: string;
          scope_id: string;
          criteria_version: string;
        }[];
      }>("/api/v1/operations/shareable-evidence"),
  });
  const [token, setToken] = useState("");
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const result = await apiFetch<{ share_token: string }>(
      "/api/v1/operations/shares",
      {
        method: "POST",
        body: JSON.stringify({
          display_name: data.get("display_name"),
          include_email: data.get("include_email") === "on",
          expires_in_days: Number(data.get("expires_in_days")),
          artifact_ids: data.getAll("artifact_ids"),
          completion_ids: data.getAll("completion_ids"),
        }),
      },
    );
    setToken(result.share_token);
    await queryClient.invalidateQueries({ queryKey: ["learner-shares"] });
  }
  return (
    <section className="portal-page">
      <h1>Recruiter evidence sharing</h1>
      <p>
        Shares are private by default, expire automatically, and contain only
        evidence you explicitly select.
      </p>
      {query.error && <ErrorState error={query.error} />}
      <div className="portal-list">
        {query.data?.map((share) => (
          <article key={share.id}>
            <strong>{share.display_name}</strong>
            <span>
              {share.status} · expires{" "}
              {new Date(share.expires_at).toLocaleDateString()}
            </span>
            <Link to={`/portfolio/preview/${share.id}`}>Preview</Link>
          </article>
        ))}
      </div>
      <form className="portal-form" onSubmit={(event) => void create(event)}>
        <h2>Create controlled share</h2>
        <label>
          Recruiter display name
          <input name="display_name" minLength={2} required />
        </label>
        <label>
          Expires in days
          <input
            name="expires_in_days"
            type="number"
            min={1}
            max={180}
            defaultValue={30}
          />
        </label>
        <label className="check-row">
          <input name="include_email" type="checkbox" /> Include account email
        </label>
        <fieldset>
          <legend>Select evidence to share</legend>
          {evidence.isLoading && <p role="status">Loading your evidence…</p>}
          {evidence.data?.artifacts.map((artifact) => (
            <label className="check-row" key={artifact.id}>
              <input name="artifact_ids" type="checkbox" value={artifact.id} />
              {artifact.title} · {artifact.verification_state}
            </label>
          ))}
          {evidence.data?.completion_records.map((record) => (
            <label className="check-row" key={record.id}>
              <input name="completion_ids" type="checkbox" value={record.id} />
              {record.scope_type}: {record.scope_id} · criteria{" "}
              {record.criteria_version}
            </label>
          ))}
          {evidence.data &&
            evidence.data.artifacts.length === 0 &&
            evidence.data.completion_records.length === 0 && (
              <p>
                No eligible evidence is available. You can still create an empty
                share.
              </p>
            )}
        </fieldset>
        <button className="primary">Create share</button>
      </form>
      {token && (
        <div className="completion-panel" role="status">
          <strong>Share created</strong>
          <p>
            Copy this one-time link now:{" "}
            <Link to={`/verify/${token}`}>Open recruiter preview</Link>
          </p>
        </div>
      )}
    </section>
  );
}

export function RecruiterVerifyPage({ token }: { token?: string }) {
  const [, params] = useRoute("/verify/:shareToken");
  const shareToken = token ?? params?.shareToken ?? "";
  const query = useQuery({
    queryKey: ["public-shared-profile", shareToken],
    queryFn: () =>
      apiFetch<{
        display_name: string;
        email: string | null;
        expires_at: string;
        artifacts: {
          id: string;
          title: string;
          type: string;
          verification_state: string;
        }[];
        completion_records: {
          id: string;
          scope_type: string;
          scope_id: string;
          criteria_version: string;
        }[];
        dimensions: Record<string, number | string | null>;
        limitations: string;
      }>(`/api/v1/verify/${shareToken}`),
    enabled: Boolean(shareToken),
    retry: false,
  });
  if (query.isLoading)
    return (
      <main className="public-verification" role="status">
        Verifying learner-approved evidence…
      </main>
    );
  if (query.error)
    return (
      <main className="public-verification">
        <ErrorState error={query.error} />
      </main>
    );
  const profile = query.data!;
  return (
    <main className="public-verification">
      <span className="eyebrow">LEARNER-APPROVED EVIDENCE</span>
      <h1>{profile.display_name}</h1>
      {profile.email && <p>{profile.email}</p>}
      <p>Share expires {new Date(profile.expires_at).toLocaleString()}.</p>
      <h2>Transparent evidence dimensions</h2>
      <dl>
        {Object.entries(profile.dimensions).map(([key, value]) => (
          <div key={key}>
            <dt>{key.replaceAll("_", " ")}</dt>
            <dd>{value ?? "Insufficient data"}</dd>
          </div>
        ))}
      </dl>
      <h2>Approved artifacts</h2>
      {profile.artifacts.length === 0 ? (
        <EmptyState>No artifacts were selected for this share.</EmptyState>
      ) : (
        profile.artifacts.map((artifact) => (
          <article key={artifact.id}>
            <strong>{artifact.title}</strong>
            <span>{artifact.verification_state}</span>
          </article>
        ))
      )}
      <h2>Completion records</h2>
      {profile.completion_records.map((record) => (
        <article key={record.id}>
          {record.scope_type}: {record.scope_id} · criteria{" "}
          {record.criteria_version}
        </article>
      ))}
      <p className="limitation">{profile.limitations}</p>
    </main>
  );
}

function ReportsPage() {
  return (
    <section className="portal-page">
      <h1>Reports</h1>
      <p>
        Exports include definitions, generation time, organization scope, and
        limitations.
      </p>
      <div className="portal-list">
        {[
          "cohort-progress",
          "assignment-completion",
          "employee-training",
          "project-review",
          "audit",
        ].map((type) => (
          <a key={type} href={`/api/v1/operations/reports/${type}.csv`}>
            Export {type.replaceAll("-", " ")} CSV
          </a>
        ))}
      </div>
    </section>
  );
}

function PermissionDenied() {
  return (
    <section className="portal-page">
      <div className="portal-state error" role="alert">
        This organization role does not permit access to the requested portal.
      </div>
    </section>
  );
}

export function PortalApp() {
  const roles = useActiveRoles();
  const instructor = roles.some((role) =>
    [
      "organization_owner",
      "organization_admin",
      "instructor",
      "reviewer",
      "cohort_manager",
    ].includes(role),
  );
  const university = canManage(roles);
  const company = roles.some((role) =>
    ["organization_owner", "organization_admin", "company_manager"].includes(
      role,
    ),
  );
  const recruiter = roles.some((role) =>
    ["organization_owner", "organization_admin", "recruiter"].includes(role),
  );
  return (
    <PortalShell>
      <Switch>
        <Route path="/instructor/cohorts/:cohortId" component={CohortPage} />
        <Route path="/instructor/learners/:learnerId">
          {instructor ? <LearnerDetailPage /> : <PermissionDenied />}
        </Route>
        <Route path="/instructor/assignments/:assignmentId">
          {instructor ? <AssignmentsPage /> : <PermissionDenied />}
        </Route>
        <Route path="/instructor/reviews/:reviewId">
          {instructor ? <ReviewsPage /> : <PermissionDenied />}
        </Route>
        <Route path="/instructor/cohorts">
          {instructor ? <CohortsPage /> : <PermissionDenied />}
        </Route>
        <Route path="/instructor/assignments">
          {instructor ? <AssignmentsPage /> : <PermissionDenied />}
        </Route>
        <Route path="/instructor/reviews">
          {instructor ? <ReviewsPage /> : <PermissionDenied />}
        </Route>
        <Route path="/instructor/reports">
          {instructor ? <ReportsPage /> : <PermissionDenied />}
        </Route>
        <Route path="/instructor">
          {instructor ? (
            <PortalDashboard portal="instructor" />
          ) : (
            <PermissionDenied />
          )}
        </Route>
        <Route path="/university/programmes">
          {university ? <ProgrammesPage /> : <PermissionDenied />}
        </Route>
        <Route path="/university/programmes/:programmeId">
          {university ? <ProgrammesPage /> : <PermissionDenied />}
        </Route>
        <Route path="/university/analytics">
          {university ? (
            <PortalDashboard portal="university" />
          ) : (
            <PermissionDenied />
          )}
        </Route>
        <Route path="/university">
          {university ? (
            <PortalDashboard portal="university" />
          ) : (
            <PermissionDenied />
          )}
        </Route>
        <Route path="/company/cohorts">
          {company ? <CohortsPage /> : <PermissionDenied />}
        </Route>
        <Route path="/company/training">
          {company ? <AssignmentsPage /> : <PermissionDenied />}
        </Route>
        <Route path="/company/skills">
          {company ? (
            <PortalDashboard portal="company" />
          ) : (
            <PermissionDenied />
          )}
        </Route>
        <Route path="/company/reports">
          {company ? <ReportsPage /> : <PermissionDenied />}
        </Route>
        <Route path="/company">
          {company ? (
            <PortalDashboard portal="company" />
          ) : (
            <PermissionDenied />
          )}
        </Route>
        <Route path="/recruiter">
          {recruiter ? (
            <PortalDashboard portal="recruiter" />
          ) : (
            <PermissionDenied />
          )}
        </Route>
        <Route path="/organization/members">
          <MembersPage />
        </Route>
        <Route path="/organization/invitations">
          <InvitationsPage />
        </Route>
        <Route path="/organization/settings">
          <OrganizationPage section="settings" />
        </Route>
        <Route path="/organization/audit">
          <OrganizationPage section="audit" />
        </Route>
        <Route path="/organization/assignments">
          <AssignmentsPage />
        </Route>
        <Route path="/organization">
          <OrganizationPage />
        </Route>
        <Route path="/portfolio/preview/:shareId" component={SharingPage} />
        <Route path="/portfolio/sharing/:shareId" component={SharingPage} />
        <Route path="/portfolio/sharing" component={SharingPage} />
        <Route>
          <PortalDashboard portal="instructor" />
        </Route>
      </Switch>
    </PortalShell>
  );
}
