import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { Link } from "wouter";
import { ApiError, apiFetch } from "../../lib/api-client";
import { CMS_TYPES } from "./cms-types";

export function CmsNav() {
  const capabilities = useQuery({
    queryKey: ["cms-capabilities"],
    queryFn: () =>
      apiFetch<{ permissions: string[] }>("/api/v1/cms/capabilities"),
  });
  const permissions = new Set(capabilities.data?.permissions || []);
  return (
    <nav className="cms-nav" aria-label="Content management">
      <Link to="/cms">Dashboard</Link>
      <Link to="/cms/library">Library</Link>
      {permissions.has("content.create") &&
        CMS_TYPES.map((type) => (
          <Link key={type} to={`/cms/builders/${type}`}>
            {type.replaceAll("_", " ")}
          </Link>
        ))}
      {permissions.has("content.review") && (
        <Link to="/cms/reviews">Reviews</Link>
      )}
      {permissions.has("content.media.view") && (
        <Link to="/cms/media">Media</Link>
      )}
      {permissions.has("platform.flags.view") && (
        <Link to="/cms/flags">Flags</Link>
      )}
      {permissions.has("audit_logs.view") && <Link to="/cms/audit">Audit</Link>}
      {permissions.has("platform.jobs.view") && (
        <Link to="/cms/jobs">Jobs</Link>
      )}
    </nav>
  );
}

export function CmsPage({ children }: { children: ReactNode }) {
  return (
    <section className="portal-page cms-page">
      <CmsNav />
      {children}
    </section>
  );
}

export function CmsError({
  error,
  retry,
}: {
  error: unknown;
  retry?: () => void;
}) {
  return (
    <div className="portal-state error" role="alert">
      <p>
        {error instanceof ApiError
          ? error.message
          : error instanceof Error
            ? error.message
            : "The CMS request could not be completed."}
      </p>
      {retry && <button onClick={retry}>Retry</button>}
    </div>
  );
}

export function CmsEmpty({ children }: { children: ReactNode }) {
  return <div className="portal-state">{children}</div>;
}

export function StatusBadge({ value }: { value: string }) {
  return (
    <span className={`cms-status cms-status-${value}`}>
      {value.replaceAll("_", " ")}
    </span>
  );
}
