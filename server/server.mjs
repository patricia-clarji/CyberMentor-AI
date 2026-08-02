import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import { extname, join, normalize, resolve } from "node:path";
import { randomUUID } from "node:crypto";
import {
  allowedOrigin,
  assessProjectSubmission,
  gradeCheck,
  securityHeaders,
  verifyLab,
} from "./core.mjs";
import {
  loadPublishedContent,
  publicLab,
  publicLesson,
  publicProject,
} from "./content-repository.mjs";
import {
  decisionLog,
  recommendActivities,
  selectDiagnosticQuestion,
  updateMastery,
} from "./adaptive.mjs";
import {
  authorizeLabVerification,
  getLabSession,
  launchLab,
  recordLabVerification,
  revealLabHint,
  transitionLab,
} from "./lab-runtime.mjs";
const apiOnly = process.argv.includes("--api-only");
const port = Number(
  process.env.CYBERMENTOR_LEGACY_API_PORT ||
    process.env.PORT ||
    (apiOnly ? 8787 : 8080),
);
const host =
  process.env.CYBERMENTOR_LOCAL_HOST || process.env.HOST || "127.0.0.1";
const trustedApiOrigin = process.env.TRUSTED_API_ORIGIN || "";
const distRoot = resolve("dist");
const limits = new Map();
const adaptiveDecisionLogs = [];
const types = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".ico": "image/x-icon",
  ".json": "application/json; charset=utf-8",
};
function json(res, status, body, headers = {}) {
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
    ...headers,
  });
  res.end(JSON.stringify(body));
}
async function body(req) {
  let raw = "";
  for await (const chunk of req) {
    raw += chunk;
    if (raw.length > 16384) throw new Error("BODY_TOO_LARGE");
  }
  try {
    return JSON.parse(raw || "{}");
  } catch {
    throw new Error("INVALID_JSON");
  }
}
function rateLimited(ip) {
  const now = Date.now();
  const current = limits.get(ip);
  if (!current || current.reset < now) {
    limits.set(ip, { count: 1, reset: now + 60000 });
    return false;
  }
  current.count++;
  return current.count > 60;
}
async function proxyTrustedApi(req, res, url) {
  if (!trustedApiOrigin) {
    json(res, 503, {
      error: "Trusted API is not configured for this runtime.",
    });
    return 503;
  }
  const chunks = [];
  let size = 0;
  for await (const chunk of req) {
    size += chunk.length;
    if (size > 16384) throw new Error("BODY_TOO_LARGE");
    chunks.push(chunk);
  }
  const headers = {
    accept: req.headers.accept || "application/json",
    "content-type": req.headers["content-type"] || "application/json",
    "x-request-id": req.headers["x-request-id"] || randomUUID(),
  };
  if (req.headers.cookie) headers.cookie = req.headers.cookie;
  if (req.headers["x-csrf-token"])
    headers["x-csrf-token"] = req.headers["x-csrf-token"];
  const upstream = await fetch(
    new URL(`${url.pathname}${url.search}`, trustedApiOrigin),
    {
      method: req.method,
      headers,
      body: chunks.length ? Buffer.concat(chunks) : undefined,
      redirect: "manual",
    },
  );
  const responseHeaders = {
    "Content-Type":
      upstream.headers.get("content-type") || "application/json; charset=utf-8",
    "Cache-Control": "no-store",
  };
  const setCookies = upstream.headers.getSetCookie?.() || [];
  if (setCookies.length) responseHeaders["Set-Cookie"] = setCookies;
  const upstreamRequestId = upstream.headers.get("x-request-id");
  if (upstreamRequestId) responseHeaders["X-Upstream-Request-ID"] = upstreamRequestId;
  res.writeHead(upstream.status, responseHeaders);
  res.end(Buffer.from(await upstream.arrayBuffer()));
  return upstream.status;
}
async function handler(req, res) {
  const started = Date.now();
  const requestId = randomUUID();
  let requestPath = "/";
  const headers = securityHeaders(requestId);
  Object.entries(headers).forEach(([k, v]) => res.setHeader(k, v));
  let status = 500;
  try {
    const origin = req.headers.origin;
    if (!allowedOrigin(origin, req.headers.host)) {
      status = 403;
      return json(res, status, { error: "Origin not allowed." });
    }
    if (rateLimited(req.socket.remoteAddress || "unknown")) {
      status = 429;
      res.setHeader("Retry-After", "60");
      return json(res, status, { error: "Too many requests." });
    }
    const url = new URL(
      req.url || "/",
      `http://${req.headers.host || "localhost"}`,
    );
    requestPath = url.pathname;
    if (url.pathname.startsWith("/api/v1/")) {
      status = await proxyTrustedApi(req, res, url);
      return;
    }
    if (url.pathname === "/healthz" || url.pathname === "/api/health") {
      status = 200;
      return json(res, status, { status: "ok", mode: "local-content-service" });
    }
    if (url.pathname === "/readyz") {
      try {
        const [lessons, labs, projects] = await Promise.all([
          loadPublishedContent({ artifactType: "lesson" }),
          loadPublishedContent({ artifactType: "lab" }),
          loadPublishedContent({ artifactType: "project" }),
        ]);
        const ready =
          lessons.length === 144 &&
          labs.length === 80 &&
          projects.length === 12;
        status = ready ? 200 : 503;
        return json(res, status, {
          status: ready ? "ready" : "not_ready",
          publications: {
            lessons: lessons.length,
            labs: labs.length,
            projects: projects.length,
          },
        });
      } catch {
        status = 503;
        return json(res, status, {
          status: "not_ready",
          publications: "unavailable",
        });
      }
    }
    if (url.pathname === "/api/content/catalog" && req.method === "GET") {
      const lessons = await loadPublishedContent({ artifactType: "lesson" });
      status = 200;
      return json(res, status, {
        publications: lessons.map(publicLesson),
        sourceOfTruth: "version-controlled-published-content",
      });
    }
    if (url.pathname === "/api/labs" && req.method === "GET") {
      const labs = await loadPublishedContent({ artifactType: "lab" });
      status = 200;
      return json(res, status, {
        labs: labs.map(publicLab),
      });
    }
    if (url.pathname === "/api/labs/launch" && req.method === "POST") {
      const payload = await body(req);
      const labBank = await loadPublishedContent({ artifactType: "lab" });
      const result = launchLab(payload.ownerId, payload.labId, labBank);
      status = result.status;
      return json(res, status, result.body);
    }
    if (url.pathname === "/api/labs/session" && req.method === "GET") {
      const result = getLabSession(
        url.searchParams.get("sessionId"),
        url.searchParams.get("ownerId"),
      );
      status = result.status;
      return json(res, status, result.body);
    }
    if (url.pathname === "/api/labs/action" && req.method === "POST") {
      const payload = await body(req);
      const result = transitionLab(
        payload.sessionId,
        payload.ownerId,
        payload.action,
      );
      status = result.status;
      return json(res, status, result.body);
    }
    if (url.pathname === "/api/labs/hint" && req.method === "POST") {
      const payload = await body(req);
      const labBank = await loadPublishedContent({ artifactType: "lab" });
      const result = revealLabHint(
        payload.sessionId,
        payload.ownerId,
        payload.level,
        labBank,
      );
      status = result.status;
      return json(res, status, result.body);
    }
    if (url.pathname === "/api/projects" && req.method === "GET") {
      const projects = await loadPublishedContent({ artifactType: "project" });
      status = 200;
      return json(res, status, { projects: projects.map(publicProject) });
    }
    if (url.pathname === "/api/projects/submit" && req.method === "POST") {
      const payload = await body(req);
      const projectBank = await loadPublishedContent({
        artifactType: "project",
      });
      const result = assessProjectSubmission(
        payload.projectId,
        payload.evidence,
        payload.completedDeliverables,
        projectBank,
      );
      status = result.status;
      return json(res, status, result.body);
    }
    if (url.pathname === "/api/checks/grade" && req.method === "POST") {
      const payload = await body(req);
      const questionBank = await loadPublishedContent({
        artifactType: "question",
      });
      const result = gradeCheck(
        payload.questionId,
        payload.choice,
        questionBank,
      );
      status = result.status;
      return json(res, status, result.body);
    }
    if (url.pathname === "/api/labs/verify" && req.method === "POST") {
      const payload = await body(req);
      const labBank = await loadPublishedContent({ artifactType: "lab" });
      const authorization = authorizeLabVerification(
        payload.sessionId,
        payload.ownerId,
        payload.labId,
      );
      if (authorization.status !== 200) {
        status = authorization.status;
        return json(res, status, authorization.body);
      }
      const result = verifyLab(payload.labId, payload.evidence, labBank);
      if (result.status === 200)
        result.body.instance = recordLabVerification(
          authorization.session,
          result.body.correct,
        );
      status = result.status;
      return json(res, status, result.body);
    }
    if (url.pathname === "/api/adaptive/mastery" && req.method === "POST") {
      const payload = await body(req);
      if (
        !payload.previous ||
        !Array.isArray(payload.evidence) ||
        payload.evidence.length > 100
      ) {
        status = 400;
        return json(res, status, { error: "Invalid mastery evidence." });
      }
      status = 200;
      return json(res, status, {
        skillState: updateMastery(payload.previous, payload.evidence),
        model: "transparent-rules-1.0.0",
        credentialEvidence: false,
      });
    }
    if (
      url.pathname === "/api/adaptive/recommendations" &&
      req.method === "POST"
    ) {
      const payload = await body(req);
      if (!payload.skills || typeof payload.skills !== "object") {
        status = 400;
        return json(res, status, { error: "A skill-state map is required." });
      }
      const publications = await loadPublishedContent({
        artifactType: "practice-activity",
      });
      const input = {
        skills: payload.skills,
        activities: publications.map((publication) => ({
          ...publication.artifact,
          id: publication.id,
          publicationStatus: publication.publicationStatus,
          verificationStatus: publication.verificationStatus,
        })),
        goals: Array.isArray(payload.goals) ? payload.goals : [],
        roleTrack:
          typeof payload.roleTrack === "string" ? payload.roleTrack : undefined,
        timeAvailable: Number(payload.timeAvailable) || 60,
        recentMistakes: Array.isArray(payload.recentMistakes)
          ? payload.recentMistakes
          : [],
        failureCounts:
          payload.failureCounts && typeof payload.failureCounts === "object"
            ? payload.failureCounts
            : {},
        instructorPolicy: {},
      };
      const recommendations = recommendActivities(input);
      const log = {
        id: randomUUID(),
        ...decisionLog(input, recommendations),
      };
      adaptiveDecisionLogs.push(log);
      if (adaptiveDecisionLogs.length > 500) adaptiveDecisionLogs.shift();
      status = 200;
      return json(res, status, {
        recommendations,
        decisionId: log.id,
        model: log.engineVersion,
        notice: recommendations.length
          ? "Recommendations are optional and use published activities only."
          : "No suitable published activity is currently available.",
      });
    }
    if (
      url.pathname === "/api/adaptive/diagnostic/next" &&
      req.method === "POST"
    ) {
      const payload = await body(req);
      if (
        typeof payload.skillId !== "string" ||
        !Array.isArray(payload.recentResults)
      ) {
        status = 400;
        return json(res, status, { error: "Invalid diagnostic state." });
      }
      const publications = await loadPublishedContent({
        artifactType: "question",
      });
      const question = selectDiagnosticQuestion({
        questions: publications.map((publication) => ({
          ...publication.artifact,
          id: publication.id,
          version: publication.contentVersion,
          publicationStatus: publication.publicationStatus,
          verificationStatus: publication.verificationStatus,
        })),
        skillId: payload.skillId,
        recentResults: payload.recentResults,
      });
      status = 200;
      return json(res, status, {
        question: question
          ? {
              id: question.id,
              version: question.version,
              prompt: question.prompt,
              options: question.options,
              skillTags: question.skillTags,
              difficulty: question.difficulty,
            }
          : null,
        estimateNotice:
          "Diagnostic results are estimates and become more reliable with independent evidence.",
      });
    }
    if (url.pathname.startsWith("/api/")) {
      status = 404;
      return json(res, status, { error: "API route not found." });
    }
    if (apiOnly) {
      status = 404;
      return json(res, status, { error: "Not found." });
    }
    let relative = normalize(decodeURIComponent(url.pathname))
      .replace(/^(\.\.[/\\])+/, "")
      .replace(/^[/\\]+/, "");
    if (!relative) relative = "index.html";
    let file = join(distRoot, relative);
    if (!file.startsWith(distRoot)) throw new Error("INVALID_PATH");
    try {
      if (!(await stat(file)).isFile()) throw new Error();
    } catch {
      file = join(distRoot, "index.html");
    }
    const data = await readFile(file);
    status = 200;
    res.writeHead(status, {
      "Content-Type": types[extname(file)] || "application/octet-stream",
      "Cache-Control": file.endsWith("index.html")
        ? "no-cache"
        : "public, max-age=31536000, immutable",
    });
    res.end(data);
  } catch (error) {
    status = error?.message === "BODY_TOO_LARGE" ? 413 : 400;
    json(res, status, {
      error: status === 413 ? "Request body too large." : "Invalid request.",
    });
  } finally {
    console.log(
      JSON.stringify({
        level: "info",
        event: "http_request",
        requestId,
        method: req.method,
        path: requestPath,
        status,
        durationMs: Date.now() - started,
      }),
    );
  }
}
createServer(handler).listen(port, host, () =>
  console.log(
    JSON.stringify({
      level: "info",
      event: "server_ready",
      host,
      port,
      apiOnly,
    }),
  ),
);
