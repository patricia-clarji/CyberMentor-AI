import { useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { Link } from "wouter";
import { apiFetch } from "../../lib/api-client";
import { CmsEmpty, CmsError, CmsPage, StatusBadge } from "./CmsShared";
import type { CmsContentSummary } from "./cms-types";
import { CMS_TYPES } from "./cms-types";

export function CmsDashboard() {
  const query = useQuery({
    queryKey: ["cms-dashboard"],
    queryFn: () =>
      apiFetch<{
        counts: Record<string, number>;
        pending_reviews: number;
        validation_failures: number;
        failed_jobs: number;
        worker_status: string;
        queue_size: number | null;
        database_status: string;
        migration_version: string;
        media_assets: number;
        recent_content: CmsContentSummary[];
      }>("/api/v1/cms/dashboard"),
  });
  const capabilities = useQuery({
    queryKey: ["cms-capabilities"],
    queryFn: () =>
      apiFetch<{ permissions: string[] }>("/api/v1/cms/capabilities"),
  });
  return (
    <CmsPage>
      <header className="cms-page-header">
        <div>
          <span className="eyebrow">Operational CMS</span>
          <h1>Content administration</h1>
        </div>
        {capabilities.data?.permissions.includes("content.create") && (
          <Link className="primary" to="/cms/builders/course">
            Create a course
          </Link>
        )}
      </header>
      {query.isLoading && <p role="status">Loading CMS metrics…</p>}
      {query.error && (
        <CmsError error={query.error} retry={() => void query.refetch()} />
      )}
      {query.data && (
        <>
          <div className="cms-metric-grid">
            {Object.entries(query.data.counts).map(([key, value]) => (
              <article key={key}>
                <strong>{value}</strong>
                <span>{key.replaceAll("_", " ")}</span>
              </article>
            ))}
            <article>
              <strong>{query.data.pending_reviews}</strong>
              <span>pending reviews</span>
            </article>
            <article>
              <strong>{query.data.validation_failures}</strong>
              <span>validation failures</span>
            </article>
            <article>
              <strong>{query.data.failed_jobs}</strong>
              <span>failed jobs</span>
            </article>
          </div>
          <section>
            <h2>System status</h2>
            <dl className="cms-definition-list">
              <div>
                <dt>Database</dt>
                <dd>
                  {query.data.database_status} · migration{" "}
                  {query.data.migration_version}
                </dd>
              </div>
              <div>
                <dt>Worker</dt>
                <dd>{query.data.worker_status}</dd>
              </div>
              <div>
                <dt>Queue</dt>
                <dd>
                  {query.data.queue_size ??
                    "Unknown — no continuous worker telemetry configured"}
                </dd>
              </div>
              <div>
                <dt>Media assets</dt>
                <dd>{query.data.media_assets}</dd>
              </div>
            </dl>
          </section>
          <section>
            <h2>Recently edited</h2>
            <div className="portal-list">
              {query.data.recent_content.map((item) => (
                <article key={item.id}>
                  <strong>{item.title}</strong>
                  <span>
                    {item.content_type} · {item.lifecycle_status}
                  </span>
                  <Link to={`/cms/content/${item.id}`}>Open workspace</Link>
                </article>
              ))}
            </div>
            {query.data.recent_content.length === 0 && (
              <CmsEmpty>No managed content exists yet.</CmsEmpty>
            )}
          </section>
        </>
      )}
    </CmsPage>
  );
}

export function ContentLibrary() {
  const [queryText, setQueryText] = useState("");
  const [type, setType] = useState("");
  const [status, setStatus] = useState("");
  const [reviewState, setReviewState] = useState("");
  const [tag, setTag] = useState("");
  const [skill, setSkill] = useState("");
  const [author, setAuthor] = useState("");
  const [reviewer, setReviewer] = useState("");
  const [updatedAfter, setUpdatedAfter] = useState("");
  const [sort, setSort] = useState("updated_desc");
  const [page, setPage] = useState(1);
  const capabilities = useQuery({
    queryKey: ["cms-capabilities"],
    queryFn: () =>
      apiFetch<{ permissions: string[] }>("/api/v1/cms/capabilities"),
  });
  const query = useQuery({
    queryKey: [
      "cms-library",
      queryText,
      type,
      status,
      reviewState,
      tag,
      skill,
      author,
      reviewer,
      updatedAfter,
      sort,
      page,
    ],
    queryFn: () => {
      const params = new URLSearchParams({
        q: queryText,
        page: String(page),
        page_size: "20",
        sort,
      });
      if (type) params.set("content_type", type);
      if (status) params.set("status", status);
      if (reviewState) params.set("review_state", reviewState);
      if (tag) params.set("tag", tag);
      if (skill) params.set("skill", skill);
      if (author) params.set("author", author);
      if (reviewer) params.set("reviewer", reviewer);
      if (updatedAfter)
        params.set("updated_after", new Date(updatedAfter).toISOString());
      return apiFetch<{
        items: CmsContentSummary[];
        total: number;
        page_size: number;
      }>(`/api/v1/cms/contents?${params}`);
    },
  });
  return (
    <CmsPage>
      <header className="cms-page-header">
        <div>
          <span className="eyebrow">CMS search</span>
          <h1>Content library</h1>
        </div>
      </header>
      <form
        className="cms-filter-grid"
        onSubmit={(event) => event.preventDefault()}
      >
        <label>
          Full-text search
          <input
            value={queryText}
            onChange={(event) => {
              setQueryText(event.currentTarget.value);
              setPage(1);
            }}
          />
        </label>
        <label>
          Content type
          <select
            value={type}
            onChange={(event) => {
              setType(event.currentTarget.value);
              setPage(1);
            }}
          >
            <option value="">All types</option>
            {CMS_TYPES.map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </label>
        <label>
          Lifecycle status
          <select
            value={status}
            onChange={(event) => {
              setStatus(event.currentTarget.value);
              setPage(1);
            }}
          >
            <option value="">All statuses</option>
            {[
              "draft",
              "in_review",
              "revision_requested",
              "approved",
              "scheduled",
              "published",
              "archived",
            ].map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </label>
        <label>
          Review state
          <input
            value={reviewState}
            onChange={(event) => {
              setReviewState(event.currentTarget.value);
              setPage(1);
            }}
          />
        </label>
        <label>
          Tag
          <input
            value={tag}
            onChange={(event) => {
              setTag(event.currentTarget.value);
              setPage(1);
            }}
          />
        </label>
        <label>
          Skill ID
          <input
            value={skill}
            onChange={(event) => {
              setSkill(event.currentTarget.value);
              setPage(1);
            }}
          />
        </label>
        <label>
          Author email
          <input
            value={author}
            onChange={(event) => {
              setAuthor(event.currentTarget.value);
              setPage(1);
            }}
          />
        </label>
        <label>
          Reviewer email
          <input
            value={reviewer}
            onChange={(event) => {
              setReviewer(event.currentTarget.value);
              setPage(1);
            }}
          />
        </label>
        <label>
          Updated after
          <input
            type="date"
            value={updatedAfter}
            onChange={(event) => {
              setUpdatedAfter(event.currentTarget.value);
              setPage(1);
            }}
          />
        </label>
        <label>
          Sort
          <select
            value={sort}
            onChange={(event) => setSort(event.currentTarget.value)}
          >
            <option value="updated_desc">Recently updated</option>
            <option value="updated_asc">Oldest updated</option>
            <option value="title_asc">Title A–Z</option>
            <option value="title_desc">Title Z–A</option>
          </select>
        </label>
      </form>
      {query.isLoading && <p role="status">Searching managed content…</p>}
      {query.error && (
        <CmsError error={query.error} retry={() => void query.refetch()} />
      )}
      <div className="portal-list">
        {query.data?.items.map((item) => (
          <article key={item.id}>
            <div>
              <strong>{item.title}</strong>
              <p>{item.description}</p>
              <span>
                {item.content_type} ·{" "}
                <StatusBadge value={item.lifecycle_status} /> ·{" "}
                {item.review_state}
              </span>
            </div>
            <div>
              {capabilities.data?.permissions.includes(
                "content.edit_draft",
              ) && (
                <Link to={`/cms/builders/${item.content_type}/${item.id}`}>
                  Edit
                </Link>
              )}
              <Link to={`/cms/content/${item.id}`}>Workflow</Link>
            </div>
          </article>
        ))}
      </div>
      {query.data?.items.length === 0 && (
        <CmsEmpty>No content matches these filters.</CmsEmpty>
      )}
      {query.data && (
        <nav className="cms-pagination" aria-label="Content pages">
          <button
            disabled={page === 1}
            onClick={() => setPage((value) => value - 1)}
          >
            Previous
          </button>
          <span>
            Page {page} of{" "}
            {Math.max(1, Math.ceil(query.data.total / query.data.page_size))}
          </span>
          <button
            disabled={page * query.data.page_size >= query.data.total}
            onClick={() => setPage((value) => value + 1)}
          >
            Next
          </button>
        </nav>
      )}
    </CmsPage>
  );
}

export function ReviewQueue() {
  const query = useQuery({
    queryKey: ["cms-review-queue"],
    queryFn: () =>
      apiFetch<
        Array<{
          assignment_id: string;
          content_id: string;
          version_id: string;
          title: string;
          reviewer_type: string;
          status: string;
          due_at: string | null;
        }>
      >("/api/v1/cms/reviews"),
  });
  return (
    <CmsPage>
      <h1>Assigned review queue</h1>
      {query.isLoading && <p role="status">Loading assigned reviews…</p>}
      {query.error && (
        <CmsError error={query.error} retry={() => void query.refetch()} />
      )}
      <div className="portal-list">
        {query.data?.map((item) => (
          <article key={item.assignment_id}>
            <strong>{item.title}</strong>
            <span>
              {item.reviewer_type.replaceAll("_", " ")} · {item.status}
              {item.due_at
                ? ` · due ${new Date(item.due_at).toLocaleString()}`
                : ""}
            </span>
            <Link to={`/cms/content/${item.content_id}`}>Open review</Link>
          </article>
        ))}
      </div>
      {query.data?.length === 0 && (
        <CmsEmpty>No active reviews are assigned to this account.</CmsEmpty>
      )}
    </CmsPage>
  );
}

type MediaAsset = {
  id: string;
  filename: string;
  title: string;
  description: string;
  mime_type: string;
  file_size: number;
  checksum: string;
  review_state: string;
  accessibility_text: string | null;
  scan_status: string;
  version: number;
  usage_count: number;
  usages: Array<{ version_id: string; location_key: string }>;
};

export function MediaLibrary() {
  const client = useQueryClient();
  const [error, setError] = useState<unknown>();
  const [message, setMessage] = useState("");
  const [usageDrafts, setUsageDrafts] = useState<
    Record<string, { versionId: string; location: string }>
  >({});
  const query = useQuery({
    queryKey: ["cms-media"],
    queryFn: () => apiFetch<MediaAsset[]>("/api/v1/cms/media"),
  });
  const mediaCapabilities = useQuery({
    queryKey: ["cms-capabilities"],
    queryFn: () =>
      apiFetch<{ permissions: string[] }>("/api/v1/cms/capabilities"),
  });
  const canManage =
    mediaCapabilities.data?.permissions.includes("content.media.manage") ??
    false;
  const canAttach =
    mediaCapabilities.data?.permissions.includes("content.edit_draft") ?? false;
  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(undefined);
    const data = new FormData(event.currentTarget);
    try {
      const result = await apiFetch<MediaAsset>("/api/v1/cms/media", {
        method: "POST",
        body: data,
      });
      setMessage(
        `Uploaded ${result.title}. Malware scanning is unconfigured; dangerous file types remain disabled.`,
      );
      event.currentTarget.reset();
      await client.invalidateQueries({ queryKey: ["cms-media"] });
    } catch (caught) {
      setError(caught);
    }
  }
  async function remove(asset: MediaAsset) {
    if (
      !window.confirm(
        `Delete ${asset.title}? Published dependencies will block this action.`,
      )
    )
      return;
    try {
      await apiFetch(`/api/v1/cms/media/${asset.id}`, { method: "DELETE" });
      await client.invalidateQueries({ queryKey: ["cms-media"] });
    } catch (caught) {
      setError(caught);
    }
  }
  async function attach(asset: MediaAsset) {
    const draft = usageDrafts[asset.id];
    if (!draft?.versionId || !draft.location) return;
    try {
      const parameters = new URLSearchParams({
        version_id: draft.versionId,
        location_key: draft.location,
      });
      await apiFetch(`/api/v1/cms/media/${asset.id}/attach?${parameters}`, {
        method: "POST",
      });
      setMessage(`${asset.title} is now tracked at ${draft.location}.`);
      await client.invalidateQueries({ queryKey: ["cms-media"] });
    } catch (caught) {
      setError(caught);
    }
  }
  return (
    <CmsPage>
      <h1>Private media library</h1>
      <p>
        Approved formats: PNG, JPEG, WebP, sanitized SVG, PDF, JSON, and CSV.
        Malware scanning is not configured; executable and dangerous formats are
        rejected.
      </p>
      {message && (
        <p role="status" className="completion-panel">
          {message}
        </p>
      )}
      {Boolean(error) && <CmsError error={error} />}
      {canManage && (
        <form className="portal-form" onSubmit={(event) => void upload(event)}>
          <h2>Upload media</h2>
          <label>
            Title
            <input name="title" required minLength={2} />
          </label>
          <label>
            Description
            <textarea name="description" />
          </label>
          <label>
            Alternative text for images
            <input name="accessibility_text" />
          </label>
          <label>
            Language
            <input name="language" defaultValue="en" />
          </label>
          <label>
            Replace an existing asset
            <select name="replacement_of_media_id">
              <option value="">New asset</option>
              {query.data?.map((asset) => (
                <option key={asset.id} value={asset.id}>
                  {asset.title} · v{asset.version}
                </option>
              ))}
            </select>
          </label>
          <label>
            File
            <input
              name="file"
              type="file"
              required
              accept=".png,.jpg,.jpeg,.webp,.svg,.pdf,.json,.csv"
            />
          </label>
          <button className="primary">Upload privately</button>
        </form>
      )}
      {query.isLoading && <p role="status">Loading media…</p>}
      {query.error && (
        <CmsError error={query.error} retry={() => void query.refetch()} />
      )}
      <div className="portal-list">
        {query.data?.map((asset) => {
          const usage = usageDrafts[asset.id] || {
            versionId: "",
            location: "",
          };
          return (
            <article key={asset.id}>
              <div>
                <strong>{asset.title}</strong>
                <p>{asset.description || asset.filename}</p>
                <span>
                  {asset.mime_type} · {(asset.file_size / 1024).toFixed(1)} KiB
                  · v{asset.version} · {asset.scan_status} scan ·{" "}
                  {asset.usage_count} usage(s)
                </span>
                <small>SHA-256 {asset.checksum}</small>
                {asset.usages.map((item) => (
                  <small key={`${item.version_id}-${item.location_key}`}>
                    {item.location_key} in version {item.version_id}
                  </small>
                ))}
                {canAttach && (
                  <fieldset>
                    <legend>Track usage in managed content</legend>
                    <label>
                      Content version ID
                      <input
                        value={usage.versionId}
                        onChange={(event) =>
                          setUsageDrafts((current) => ({
                            ...current,
                            [asset.id]: {
                              ...usage,
                              versionId: event.currentTarget.value,
                            },
                          }))
                        }
                      />
                    </label>
                    <label>
                      Block or field location
                      <input
                        value={usage.location}
                        placeholder="sections.block-id.image"
                        onChange={(event) =>
                          setUsageDrafts((current) => ({
                            ...current,
                            [asset.id]: {
                              ...usage,
                              location: event.currentTarget.value,
                            },
                          }))
                        }
                      />
                    </label>
                    <button
                      type="button"
                      disabled={!usage.versionId || !usage.location}
                      onClick={() => void attach(asset)}
                    >
                      Attach and track usage
                    </button>
                  </fieldset>
                )}
              </div>
              <div>
                <a href={`/api/v1/cms/media/${asset.id}/content`}>
                  Authorized download
                </a>
                {canManage && (
                  <button onClick={() => void remove(asset)}>Delete</button>
                )}
              </div>
            </article>
          );
        })}
      </div>
      {query.data?.length === 0 && (
        <CmsEmpty>No media assets uploaded.</CmsEmpty>
      )}
    </CmsPage>
  );
}

type Flag = {
  id: string;
  name: string;
  description: string;
  environment: string;
  default_state: boolean;
  current_state: boolean;
  effective_state: boolean;
  starts_at: string | null;
  expires_at: string | null;
  expired: boolean;
};
export function FeatureFlags() {
  const client = useQueryClient();
  const [error, setError] = useState<unknown>();
  const query = useQuery({
    queryKey: ["cms-flags"],
    queryFn: () => apiFetch<Flag[]>("/api/v1/cms/feature-flags"),
  });
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    try {
      await apiFetch("/api/v1/cms/feature-flags", {
        method: "POST",
        body: JSON.stringify({
          name: data.get("name"),
          description: data.get("description"),
          environment: data.get("environment"),
          default_state: false,
          current_state: data.get("active") === "on",
          starts_at: data.get("starts_at")
            ? new Date(String(data.get("starts_at"))).toISOString()
            : null,
          expires_at: data.get("expires_at")
            ? new Date(String(data.get("expires_at"))).toISOString()
            : null,
        }),
      });
      form.reset();
      await client.invalidateQueries({ queryKey: ["cms-flags"] });
    } catch (caught) {
      setError(caught);
    }
  }
  async function toggle(flag: Flag) {
    try {
      await apiFetch(`/api/v1/cms/feature-flags/${flag.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          current_state: !flag.current_state,
          description: flag.description,
          starts_at: flag.starts_at,
          expires_at: flag.expires_at,
        }),
      });
      await client.invalidateQueries({ queryKey: ["cms-flags"] });
    } catch (caught) {
      setError(caught);
    }
  }
  return (
    <CmsPage>
      <h1>Feature flags</h1>
      {Boolean(error) && <CmsError error={error} />}
      <form
        className="cms-inline-form"
        onSubmit={(event) => void create(event)}
      >
        <label>
          Name
          <input name="name" required pattern="[a-z][a-z0-9_.-]+" />
        </label>
        <label>
          Description
          <input name="description" required minLength={3} />
        </label>
        <label>
          Environment
          <select name="environment">
            <option>development</option>
            <option>test</option>
            <option>production</option>
          </select>
        </label>
        <label>
          Starts
          <input name="starts_at" type="datetime-local" />
        </label>
        <label>
          Expiry
          <input name="expires_at" type="datetime-local" />
        </label>
        <label className="check-row">
          <input name="active" type="checkbox" />
          Active
        </label>
        <button>Create flag</button>
      </form>
      {query.isLoading && <p role="status">Loading flags…</p>}
      {query.error && (
        <CmsError error={query.error} retry={() => void query.refetch()} />
      )}
      <div className="portal-list">
        {query.data?.map((flag) => (
          <article key={flag.id}>
            <strong>{flag.name}</strong>
            <p>{flag.description}</p>
            <span>
              {flag.environment} · configured{" "}
              {flag.current_state ? "on" : "off"} · effective{" "}
              {flag.effective_state ? "on" : "off"}
              {flag.expired ? " · expired" : ""}
              {flag.starts_at
                ? ` · starts ${new Date(flag.starts_at).toLocaleString()}`
                : ""}
              {flag.expires_at
                ? ` · expires ${new Date(flag.expires_at).toLocaleString()}`
                : ""}
            </span>
            <button onClick={() => void toggle(flag)}>
              {flag.current_state ? "Disable" : "Enable"}
            </button>
          </article>
        ))}
      </div>
    </CmsPage>
  );
}

export function AuditLog() {
  const query = useQuery({
    queryKey: ["cms-audit"],
    queryFn: () =>
      apiFetch<
        Array<{
          id: string;
          actor_user_id: string | null;
          action: string;
          outcome: string;
          target_type: string | null;
          target_id: string | null;
          request_id: string | null;
          detail: string | null;
          created_at: string;
        }>
      >("/api/v1/cms/audit?limit=200"),
  });
  return (
    <CmsPage>
      <h1>Immutable CMS audit log</h1>
      {query.isLoading && <p role="status">Loading audit events…</p>}
      {query.error && (
        <CmsError error={query.error} retry={() => void query.refetch()} />
      )}
      <div className="cms-table-wrap">
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Actor</th>
              <th>Action</th>
              <th>Target</th>
              <th>Result</th>
              <th>Request</th>
            </tr>
          </thead>
          <tbody>
            {query.data?.map((item) => (
              <tr key={item.id}>
                <td>{new Date(item.created_at).toLocaleString()}</td>
                <td>{item.actor_user_id || "system"}</td>
                <td>{item.action}</td>
                <td>
                  {item.target_type}: {item.target_id}
                </td>
                <td>{item.outcome}</td>
                <td>{item.request_id || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {query.data?.length === 0 && (
        <CmsEmpty>No CMS audit events recorded.</CmsEmpty>
      )}
    </CmsPage>
  );
}

type Job = {
  id: string;
  job_type: string;
  status: string;
  progress: number;
  error_detail: string | null;
  created_at: string;
  completed_at: string | null;
  retry_count: number;
};
export function JobControl() {
  const client = useQueryClient();
  const [error, setError] = useState<unknown>();
  const query = useQuery({
    queryKey: ["cms-jobs"],
    queryFn: () => apiFetch<Job[]>("/api/v1/cms/jobs"),
  });
  const capabilities = useQuery({
    queryKey: ["cms-capabilities"],
    queryFn: () =>
      apiFetch<{ permissions: string[] }>("/api/v1/cms/capabilities"),
  });
  const canManage =
    capabilities.data?.permissions.includes("platform.jobs.manage") ?? false;
  async function action(job: Job, operation: "retry" | "cancel") {
    try {
      await apiFetch(`/api/v1/cms/jobs/${job.id}/${operation}`, {
        method: "POST",
        body: JSON.stringify({
          reason: `Authorized ${operation} from CMS job control`,
        }),
      });
      await client.invalidateQueries({ queryKey: ["cms-jobs"] });
    } catch (caught) {
      setError(caught);
    }
  }
  async function runDue() {
    try {
      await apiFetch("/api/v1/cms/jobs/run-due", { method: "POST" });
      await client.invalidateQueries({ queryKey: ["cms-jobs"] });
    } catch (caught) {
      setError(caught);
    }
  }
  return (
    <CmsPage>
      <header className="cms-page-header">
        <div>
          <h1>Background jobs</h1>
          <p>Only real persisted job state is displayed.</p>
        </div>
        {canManage && (
          <button onClick={() => void runDue()}>Run due publications</button>
        )}
      </header>
      {Boolean(error) && <CmsError error={error} />}
      {query.isLoading && <p role="status">Loading jobs…</p>}
      {query.error && (
        <CmsError error={query.error} retry={() => void query.refetch()} />
      )}
      <div className="portal-list">
        {query.data?.map((job) => (
          <article key={job.id}>
            <strong>{job.job_type}</strong>
            <span>
              {job.status} · {job.progress}% · retries {job.retry_count}
            </span>
            {job.error_detail && <p>{job.error_detail}</p>}
            {canManage && (
              <div>
                {["failed", "cancelled"].includes(job.status) && (
                  <button onClick={() => void action(job, "retry")}>
                    Retry
                  </button>
                )}
                {["queued", "retrying"].includes(job.status) && (
                  <button onClick={() => void action(job, "cancel")}>
                    Cancel
                  </button>
                )}
              </div>
            )}
          </article>
        ))}
      </div>
      {query.data?.length === 0 && (
        <CmsEmpty>No persisted background jobs.</CmsEmpty>
      )}
    </CmsPage>
  );
}
