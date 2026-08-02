import { useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useEffect, useState } from "react";
import { Link, useRoute } from "wouter";
import { apiFetch } from "../../lib/api-client";
import { useAuth } from "../auth/auth-context";
import { CmsEmpty, CmsError, CmsPage, StatusBadge } from "./CmsShared";
import type { CmsComment, CmsContentSummary, CmsVersion } from "./cms-types";

export function ContentWorkspace() {
  const [, params] = useRoute("/cms/content/:contentId");
  const contentId = params?.contentId || "";
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [selectedVersionId, setSelectedVersionId] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState<unknown>();
  const [compare, setCompare] = useState<Record<string, unknown> | null>(null);
  const capabilities = useQuery({
    queryKey: ["cms-capabilities"],
    queryFn: () =>
      apiFetch<{ permissions: string[] }>("/api/v1/cms/capabilities"),
  });
  const content = useQuery({
    queryKey: ["cms-workspace", contentId],
    queryFn: () =>
      apiFetch<CmsContentSummary>(`/api/v1/cms/contents/${contentId}`),
    enabled: Boolean(contentId),
  });
  useEffect(() => {
    if (!selectedVersionId && content.data?.versions?.length)
      // The persisted latest version becomes the explicit user selection.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setSelectedVersionId(content.data.versions[0].id);
  }, [content.data, selectedVersionId]);
  const version = useQuery({
    queryKey: ["cms-workspace-version", contentId, selectedVersionId],
    queryFn: () =>
      apiFetch<CmsVersion>(
        `/api/v1/cms/contents/${contentId}/versions/${selectedVersionId}`,
      ),
    enabled: Boolean(contentId && selectedVersionId),
  });
  async function refresh() {
    await Promise.all([content.refetch(), version.refetch()]);
    await queryClient.invalidateQueries({ queryKey: ["cms-dashboard"] });
  }
  async function action(
    path: string,
    body?: Record<string, unknown>,
    method = "POST",
  ) {
    setError(undefined);
    try {
      await apiFetch(path, {
        method,
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      setMessage("CMS workflow updated.");
      await refresh();
    } catch (caught) {
      setError(caught);
    }
  }
  async function compareVersions(fromRevision: number, toRevision: number) {
    try {
      setCompare(
        await apiFetch<Record<string, unknown>>(
          `/api/v1/cms/contents/${contentId}/compare?from_revision=${fromRevision}&to_revision=${toRevision}`,
        ),
      );
    } catch (caught) {
      setError(caught);
    }
  }
  if (content.isLoading)
    return (
      <CmsPage>
        <p role="status">Loading version history…</p>
      </CmsPage>
    );
  if (content.error)
    return (
      <CmsPage>
        <CmsError error={content.error} retry={() => void content.refetch()} />
      </CmsPage>
    );
  const current = version.data;
  const permissions = new Set(capabilities.data?.permissions || []);
  return (
    <CmsPage>
      <header className="cms-page-header">
        <div>
          <span className="eyebrow">Content workspace</span>
          <h1>{content.data?.title}</h1>
        </div>
        {current && (
          <div>
            <StatusBadge value={current.version_status} /> v{current.version}{" "}
            {current.content_type === "skill" &&
              permissions.has("content.skills.manage") &&
              permissions.has("content.archive") && (
                <button
                  onClick={() => {
                    const targetSkillId = window.prompt(
                      "Target managed skill UUID",
                    );
                    const reason =
                      targetSkillId && window.prompt("Merge reason");
                    if (
                      targetSkillId &&
                      reason &&
                      window.confirm(
                        "Merge this skill? Draft relationships will migrate while published history and learner evidence remain pinned.",
                      )
                    )
                      void action(
                        `/api/v1/cms/contents/${contentId}/merge-skill`,
                        { target_skill_id: targetSkillId, reason },
                      );
                  }}
                >
                  Merge skill
                </button>
              )}{" "}
            {permissions.has("content.archive") && (
              <button
                onClick={() => {
                  const reason = window.prompt("Archive reason");
                  if (
                    reason &&
                    window.confirm(
                      "Archive this content? Published history and learner evidence will be preserved.",
                    )
                  )
                    void action(`/api/v1/cms/contents/${contentId}/archive`, {
                      reason,
                    });
                }}
              >
                Archive
              </button>
            )}
          </div>
        )}
      </header>
      {message && (
        <p role="status" className="completion-panel">
          {message}
        </p>
      )}
      {Boolean(error) && <CmsError error={error} />}
      <div className="cms-workspace-grid">
        <aside>
          <h2>Version history</h2>
          <label>
            Selected version
            <select
              value={selectedVersionId}
              onChange={(event) =>
                setSelectedVersionId(event.currentTarget.value)
              }
            >
              {content.data?.versions?.map((item) => (
                <option value={item.id} key={item.id}>
                  r{item.revision} · v{item.version} · {item.status}
                </option>
              ))}
            </select>
          </label>
          {content.data?.versions?.length ? (
            <div className="portal-list">
              {content.data.versions.map((item) => (
                <article key={item.id}>
                  <strong>Revision {item.revision}</strong>
                  <span>{item.change_summary}</span>
                  <StatusBadge value={item.status} />
                </article>
              ))}
            </div>
          ) : (
            <CmsEmpty>No versions exist.</CmsEmpty>
          )}
        </aside>
        <main>
          {version.isLoading && <p role="status">Loading selected version…</p>}
          {version.error && (
            <CmsError
              error={version.error}
              retry={() => void version.refetch()}
            />
          )}
          {current && (
            <>
              <nav className="cms-action-bar" aria-label="Version actions">
                {permissions.has("content.edit_draft") && (
                  <Link
                    to={`/cms/builders/${current.content_type}/${contentId}`}
                  >
                    Open builder
                  </Link>
                )}
                {permissions.has("content.validate") && (
                  <button
                    onClick={() =>
                      void action(
                        `/api/v1/cms/contents/${contentId}/versions/${current.version_id}/validate`,
                      )
                    }
                  >
                    Validate
                  </button>
                )}
                {permissions.has("content.submit_review") && (
                  <button
                    onClick={() =>
                      void action(
                        `/api/v1/cms/contents/${contentId}/versions/${current.version_id}/submit-review`,
                      )
                    }
                  >
                    Submit or resubmit
                  </button>
                )}
              </nav>
              <ReviewPanel
                contentId={contentId}
                version={current}
                currentUserId={user?.id || ""}
                canAssign={permissions.has("content.assign_reviewer")}
                onChange={refresh}
                setError={setError}
              />
              <PublicationPanel
                contentId={contentId}
                version={current}
                onAction={action}
                onCompare={compareVersions}
                versions={content.data?.versions || []}
                permissions={permissions}
              />
              <h2>Validation results</h2>
              {current.validation.length ? (
                current.validation.map((item) => (
                  <article
                    key={item.rule_id}
                    className={`cms-validation-${item.state}`}
                  >
                    <strong>{item.explanation}</strong>
                    <p>{item.field_location || "Content"}</p>
                  </article>
                ))
              ) : (
                <CmsEmpty>Run validation to produce current results.</CmsEmpty>
              )}
            </>
          )}
        </main>
      </div>
      {compare && (
        <ComparisonView value={compare} close={() => setCompare(null)} />
      )}
    </CmsPage>
  );
}

function ReviewPanel({
  contentId,
  version,
  currentUserId,
  canAssign,
  onChange,
  setError,
}: {
  contentId: string;
  version: CmsVersion;
  currentUserId: string;
  canAssign: boolean;
  onChange: () => Promise<void>;
  setError: (error: unknown) => void;
}) {
  const [replyTo, setReplyTo] = useState<string | null>(null);
  const [decisionNotes, setDecisionNotes] = useState("");
  async function submit(
    path: string,
    body: Record<string, unknown>,
    method = "POST",
  ) {
    try {
      await apiFetch(path, { method, body: JSON.stringify(body) });
      await onChange();
    } catch (caught) {
      setError(caught);
    }
  }
  async function assign(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    await submit(
      `/api/v1/cms/contents/${contentId}/versions/${version.version_id}/reviewers`,
      {
        reviewer_email: data.get("email"),
        reviewer_type: data.get("reviewer_type"),
        due_at: data.get("due_at") || null,
      },
    );
    form.reset();
  }
  async function comment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    await submit(
      `/api/v1/cms/contents/${contentId}/versions/${version.version_id}/comments`,
      {
        body: data.get("body"),
        parent_comment_id: replyTo,
        location_type: data.get("location_type"),
        location_key: data.get("location_key") || null,
        severity: data.get("severity"),
      },
    );
    setReplyTo(null);
    form.reset();
  }
  async function decision(decision: string) {
    const notes = decisionNotes.trim();
    if (!notes) {
      setError(new Error("Review decision notes are required."));
      return;
    }
    await submit(
      `/api/v1/cms/contents/${contentId}/versions/${version.version_id}/decision`,
      {
        decision,
        notes,
        checklist: [
          {
            key: "validation",
            required: true,
            passed: !version.validation.some(
              (item) => item.state === "failure",
            ),
          },
        ],
      },
    );
    setDecisionNotes("");
  }
  const roots = version.comments.filter((item) => !item.parent_comment_id);
  return (
    <section className="cms-review-panel">
      <h2>Review workflow</h2>
      <p>
        Mandatory independent reviews:{" "}
        {version.required_reviewer_types
          .map((role) => {
            const assignment = version.reviews.find(
              (review) => review.reviewer_type === role,
            );
            return `${role.replaceAll("_", " ")} (${assignment?.status || "unassigned"})`;
          })
          .join(" · ")}
      </p>
      {canAssign && (
        <form
          className="cms-inline-form"
          onSubmit={(event) => void assign(event)}
        >
          <label>
            Reviewer email
            <input name="email" type="email" required />
          </label>
          <label>
            Reviewer role
            <select name="reviewer_type">
              <option value="technical_reviewer">Technical reviewer</option>
              <option value="instructional_reviewer">
                Instructional reviewer
              </option>
              <option value="accessibility_reviewer">
                Accessibility reviewer
              </option>
              <option value="content_administrator">
                Content administrator
              </option>
            </select>
          </label>
          <label>
            Due date
            <input name="due_at" type="datetime-local" />
          </label>
          <button>Assign or reassign</button>
        </form>
      )}
      <div className="portal-list">
        {version.reviews.map((review) => (
          <article key={review.id}>
            <strong>{review.reviewer_type.replaceAll("_", " ")}</strong>
            <span>
              {review.status} · reviewer {review.reviewer_user_id}
            </span>
            {review.reviewer_user_id === currentUserId &&
              review.status === "assigned" && (
                <button
                  onClick={() =>
                    void submit(`/api/v1/cms/reviewers/${review.id}/start`, {})
                  }
                >
                  Start review
                </button>
              )}
            {canAssign && review.status !== "approved" && (
              <button
                onClick={() =>
                  void submit(
                    `/api/v1/cms/contents/${contentId}/versions/${version.version_id}/reviewers/${review.id}`,
                    {},
                    "DELETE",
                  )
                }
              >
                Remove
              </button>
            )}
          </article>
        ))}
      </div>
      {!version.reviews.length && <CmsEmpty>No reviewers assigned.</CmsEmpty>}
      <form className="portal-form" onSubmit={(event) => void comment(event)}>
        <h3>{replyTo ? "Reply to review comment" : "Add review comment"}</h3>
        <label>
          Comment
          <textarea name="body" required minLength={2} />
        </label>
        <div className="cms-inline-fields">
          <label>
            Location
            <select name="location_type">
              <option value="version">Whole version</option>
              <option value="section">Lesson block</option>
              <option value="objective">Objective</option>
              <option value="metadata">Metadata field</option>
            </select>
          </label>
          <label>
            Location ID
            <input name="location_key" placeholder="Block UUID or field" />
          </label>
          <label>
            Severity
            <select name="severity">
              <option>suggestion</option>
              <option>warning</option>
              <option>blocking</option>
            </select>
          </label>
        </div>
        <button>Post comment</button>
        {replyTo && (
          <button type="button" onClick={() => setReplyTo(null)}>
            Cancel reply
          </button>
        )}
      </form>
      <div className="cms-comments">
        {roots.map((comment) => (
          <CommentThread
            key={comment.id}
            comment={comment}
            all={version.comments}
            currentUserId={currentUserId}
            reply={setReplyTo}
            edit={(item) => {
              const body = window.prompt("Edit comment", item.body);
              if (body)
                void submit(
                  `/api/v1/cms/comments/${item.id}`,
                  { body, suggested_change: null },
                  "PUT",
                );
            }}
            toggle={(item) =>
              void submit(
                `/api/v1/cms/comments/${item.id}`,
                { resolved: item.status === "open" },
                "PATCH",
              )
            }
          />
        ))}
      </div>
      {!roots.length && <CmsEmpty>No review comments.</CmsEmpty>}
      {version.reviews.some(
        (review) =>
          review.reviewer_user_id === currentUserId &&
          ["assigned", "in_review", "changes_requested"].includes(
            review.status,
          ),
      ) && (
        <div>
          <label>
            Review decision notes
            <textarea
              value={decisionNotes}
              onChange={(event) => setDecisionNotes(event.currentTarget.value)}
              required
            />
          </label>
          <div className="cms-action-bar">
            <button onClick={() => void decision("request_changes")}>
              Request changes
            </button>
            <button onClick={() => void decision("reject")}>Reject</button>
            <button
              className="primary"
              onClick={() => void decision("approve")}
            >
              Approve assigned review
            </button>
          </div>
        </div>
      )}
      {version.review_history.length > 0 && (
        <details>
          <summary>Review decision history</summary>
          {version.review_history.map((item) => (
            <article key={item.id}>
              <strong>{item.decision}</strong> by {item.reviewer_type} ·{" "}
              {new Date(item.decided_at).toLocaleString()}
              <p>{item.notes}</p>
            </article>
          ))}
        </details>
      )}
    </section>
  );
}

function CommentThread({
  comment,
  all,
  currentUserId,
  reply,
  edit,
  toggle,
}: {
  comment: CmsComment;
  all: CmsComment[];
  currentUserId: string;
  reply: (id: string) => void;
  edit: (comment: CmsComment) => void;
  toggle: (comment: CmsComment) => void;
}) {
  const children = all.filter((item) => item.parent_comment_id === comment.id);
  return (
    <article className={`cms-comment cms-comment-${comment.status}`}>
      <header>
        <strong>
          {comment.severity} · {comment.reviewer_type.replaceAll("_", " ")}
        </strong>
        <span>
          {new Date(comment.created_at).toLocaleString()}
          {comment.updated_at !== comment.created_at ? " · edited" : ""}
        </span>
      </header>
      <p>{comment.body}</p>
      {comment.location_key && (
        <a href={`#block-${comment.location_key}`}>
          Go to referenced {comment.location_type}
        </a>
      )}
      {comment.resolved_at && (
        <small>
          Resolved {new Date(comment.resolved_at).toLocaleString()} by{" "}
          {comment.resolved_by_user_id}
        </small>
      )}
      <div>
        <button onClick={() => reply(comment.id)}>Reply</button>
        {comment.author_user_id === currentUserId &&
          comment.status === "open" && (
            <button onClick={() => edit(comment)}>Edit</button>
          )}
        <button onClick={() => toggle(comment)}>
          {comment.status === "open" ? "Resolve" : "Reopen"}
        </button>
      </div>
      {children.map((child) => (
        <CommentThread
          key={child.id}
          comment={child}
          all={all}
          currentUserId={currentUserId}
          reply={reply}
          edit={edit}
          toggle={toggle}
        />
      ))}
    </article>
  );
}

function PublicationPanel({
  contentId,
  version,
  versions,
  onAction,
  onCompare,
  permissions,
}: {
  contentId: string;
  version: CmsVersion;
  versions: CmsContentSummary["versions"];
  onAction: (
    path: string,
    body?: Record<string, unknown>,
    method?: string,
  ) => Promise<void>;
  onCompare: (from: number, to: number) => Promise<void>;
  permissions: Set<string>;
}) {
  const [rollbackImpact, setRollbackImpact] = useState<Record<
    string,
    unknown
  > | null>(null);
  async function newDraft(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    await onAction(
      `/api/v1/cms/contents/${contentId}/versions/${version.version_id}/draft`,
      { version: data.get("version"), change_summary: data.get("reason") },
    );
  }
  async function schedule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    await onAction(
      `/api/v1/cms/contents/${contentId}/versions/${version.version_id}/schedule`,
      {
        publish_at: new Date(String(data.get("publish_at"))).toISOString(),
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      },
    );
  }
  async function rollback(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    if (
      !window.confirm(
        "Rollback changes the current published revision but preserves all history. Continue?",
      )
    )
      return;
    await onAction(`/api/v1/cms/contents/${contentId}/rollback`, {
      target_revision: Number(data.get("revision")),
      reason: data.get("reason"),
    });
  }
  async function previewRollback(form: HTMLFormElement) {
    const data = new FormData(form);
    setRollbackImpact(
      await apiFetch<Record<string, unknown>>(
        `/api/v1/cms/contents/${contentId}/rollback-impact?target_revision=${Number(data.get("revision"))}`,
      ),
    );
  }
  const previous = versions?.find((item) => item.revision !== version.revision);
  return (
    <section className="cms-publication-panel">
      <h2>Publication and versioning</h2>
      {permissions.has("content.create_version") && (
        <form
          className="cms-inline-form"
          onSubmit={(event) => void newDraft(event)}
        >
          <label>
            New semantic version
            <input
              name="version"
              pattern="\d+\.\d+\.\d+"
              required
              placeholder="1.1.0"
            />
          </label>
          <label>
            Change summary
            <input name="reason" required minLength={3} />
          </label>
          <button>Create draft from selected version</button>
        </form>
      )}
      {(permissions.has("content.schedule") ||
        permissions.has("content.publish")) && (
        <form
          className="cms-inline-form"
          onSubmit={(event) => void schedule(event)}
        >
          <label>
            Publication time
            <input name="publish_at" type="datetime-local" required />
          </label>
          {permissions.has("content.schedule") && (
            <button>Schedule approved version</button>
          )}
          {permissions.has("content.schedule") &&
            version.version_status === "scheduled" && (
              <button
                type="button"
                onClick={() =>
                  void onAction(
                    `/api/v1/cms/contents/${contentId}/versions/${version.version_id}/schedule`,
                    undefined,
                    "DELETE",
                  )
                }
              >
                Cancel schedule
              </button>
            )}
          {permissions.has("content.publish") && (
            <button
              type="button"
              className="primary"
              onClick={() =>
                void onAction(
                  `/api/v1/cms/contents/${contentId}/versions/${version.version_id}/publish`,
                  { reason: "Authorized immediate publication" },
                )
              }
            >
              Publish now
            </button>
          )}
        </form>
      )}
      {previous && (
        <button
          onClick={() => void onCompare(previous.revision, version.revision)}
        >
          Compare revision {previous.revision} with {version.revision}
        </button>
      )}
      {permissions.has("content.rollback") && (
        <form
          className="cms-inline-form"
          onSubmit={(event) => void rollback(event)}
        >
          <label>
            Published revision
            <select name="revision">
              {versions
                ?.filter((item) => item.published_at)
                .map((item) => (
                  <option value={item.revision} key={item.id}>
                    Revision {item.revision} · v{item.version}
                  </option>
                ))}
            </select>
          </label>
          <label>
            Rollback reason
            <input name="reason" required minLength={5} />
          </label>
          <button
            type="button"
            onClick={(event) => {
              const form = event.currentTarget.closest("form");
              if (form) void previewRollback(form);
            }}
          >
            Preview rollback impact
          </button>
          <button>Rollback safely</button>
        </form>
      )}
      {permissions.has("content.rollback") && rollbackImpact && (
        <aside className="portal-state">
          <strong>Rollback impact</strong>
          <p>{String(rollbackImpact.warning)}</p>
          <p>
            {
              ((rollbackImpact.dependent_content || []) as Array<unknown>)
                .length
            }{" "}
            dependent content item(s). Historical versions preserved:{" "}
            {rollbackImpact.historical_versions_preserved ? "yes" : "no"}.
            Learner records remapped:{" "}
            {rollbackImpact.learner_records_remapped ? "yes" : "no"}.
          </p>
        </aside>
      )}
    </section>
  );
}

function ComparisonView({
  value,
  close,
}: {
  value: Record<string, unknown>;
  close: () => void;
}) {
  const metadata = Object.entries(
    (value.metadata_changes || {}) as Record<
      string,
      { from: unknown; to: unknown }
    >,
  );
  const added = (value.sections_added || []) as Array<Record<string, unknown>>;
  const removed = (value.sections_removed || []) as Array<
    Record<string, unknown>
  >;
  const modified = (value.sections_modified || []) as Array<{
    section_key: string;
    from: Record<string, unknown>;
    to: Record<string, unknown>;
  }>;
  const reordered = (value.sections_reordered || []) as Array<{
    section_key: string;
    title: string;
    from: number;
    to: number;
  }>;
  const objectivesAdded = (value.objectives_added || []) as Array<
    Record<string, unknown>
  >;
  const objectivesRemoved = (value.objectives_removed || []) as Array<
    Record<string, unknown>
  >;
  const objectivesModified = (value.objectives_modified || []) as Array<{
    objective_key: string;
    to: Record<string, unknown>;
  }>;
  const relationsAdded = (value.relationships_added || []) as Array<
    Record<string, unknown>
  >;
  const relationsRemoved = (value.relationships_removed || []) as Array<
    Record<string, unknown>
  >;
  const relationsModified = (value.relationships_modified || []) as Array<{
    relationship_key: string;
  }>;
  const publication = value.publication_state as
    { from?: string; to?: string } | undefined;
  function friendly(item: unknown): string {
    if (item == null || item === "") return "none";
    if (Array.isArray(item)) return item.map(friendly).join(", ") || "none";
    if (typeof item === "object")
      return Object.entries(item as Record<string, unknown>)
        .map(
          ([key, entry]) =>
            `${key.replaceAll(/([A-Z])/g, " $1")}: ${friendly(entry)}`,
        )
        .join("; ");
    return String(item);
  }
  return (
    <aside className="cms-preview" aria-label="Version comparison">
      <div>
        <h2>Version comparison</h2>
        <button onClick={close}>Close</button>
      </div>
      <h3>Metadata changes</h3>
      {metadata.length ? (
        metadata.map(([key, change]) => (
          <article key={key}>
            <strong>{key}</strong>
            <p>From: {friendly(change.from)}</p>
            <p>To: {friendly(change.to)}</p>
          </article>
        ))
      ) : (
        <CmsEmpty>No metadata changed.</CmsEmpty>
      )}
      <h3>Added blocks</h3>
      {added.map((item) => (
        <p key={String(item.key)}>
          {String(item.type)}: {String(item.title)}
        </p>
      ))}
      <h3>Removed blocks</h3>
      {removed.map((item) => (
        <p key={String(item.key)}>
          {String(item.type)}: {String(item.title)}
        </p>
      ))}
      <h3>Modified blocks</h3>
      {modified.map((item) => (
        <article key={item.section_key}>
          <strong>{String(item.to.title || item.to.type)}</strong>
          <p>
            {String(item.from.body)} → {String(item.to.body)}
          </p>
        </article>
      ))}
      <h3>Reordered blocks</h3>
      {reordered.map((item) => (
        <p key={item.section_key}>
          {item.title || item.section_key}: position {item.from + 1} →{" "}
          {item.to + 1}
        </p>
      ))}
      <h3>Objective changes</h3>
      {objectivesAdded.map((item) => (
        <p key={`oa-${String(item.key)}`}>Added: {String(item.title)}</p>
      ))}
      {objectivesRemoved.map((item) => (
        <p key={`or-${String(item.key)}`}>Removed: {String(item.title)}</p>
      ))}
      {objectivesModified.map((item) => (
        <p key={item.objective_key}>Modified: {String(item.to.title)}</p>
      ))}
      <h3>Relationship changes</h3>
      {relationsAdded.map((item) => (
        <p key={`ra-${String(item.type)}-${String(item.targetContentId)}`}>
          Added: {String(item.type)} → {String(item.targetContentId)}
        </p>
      ))}
      {relationsRemoved.map((item) => (
        <p key={`rr-${String(item.type)}-${String(item.targetContentId)}`}>
          Removed: {String(item.type)} → {String(item.targetContentId)}
        </p>
      ))}
      {relationsModified.map((item) => (
        <p key={item.relationship_key}>Modified: {item.relationship_key}</p>
      ))}
      <h3>Publication state</h3>
      <p>
        {publication?.from || "unknown"} → {publication?.to || "unknown"}
      </p>
      <details>
        <summary>Advanced comparison data</summary>
        <pre>{JSON.stringify(value, null, 2)}</pre>
      </details>
    </aside>
  );
}
