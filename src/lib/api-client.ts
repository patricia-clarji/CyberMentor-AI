export type ApiErrorBody = {
  error?: {
    code?: string;
    message?: string;
    requestId?: string;
  };
};

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string,
    readonly requestId?: string,
  ) {
    super(message);
  }
}

function cookie(name: string) {
  return document.cookie
    .split("; ")
    .find((value) => value.startsWith(`${name}=`))
    ?.slice(name.length + 1);
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const method = (init.method || "GET").toUpperCase();
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (
    init.body &&
    !(init.body instanceof FormData) &&
    !headers.has("Content-Type")
  ) {
    headers.set("Content-Type", "application/json");
  }
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const csrf = cookie("cm_csrf");
    if (csrf) headers.set("X-CSRF-Token", decodeURIComponent(csrf));
  }
  const response = await fetch(path, {
    ...init,
    headers,
    credentials: "include",
  });
  const body = (await response.json().catch(() => ({}))) as T & ApiErrorBody;
  if (!response.ok) {
    throw new ApiError(
      body.error?.message || "The request could not be completed.",
      response.status,
      body.error?.code || "request_failed",
      body.error?.requestId,
    );
  }
  return body;
}
