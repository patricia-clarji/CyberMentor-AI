import { randomUUID } from "node:crypto";

const sessions = new Map();
const MAX_SESSIONS = 2_000;

const now = () => Date.now();
const iso = (value) => new Date(value).toISOString();
const validOwner = (value) =>
  typeof value === "string" && /^[a-zA-Z0-9_-]{8,128}$/.test(value);
const published = (item) =>
  item?.publicationStatus === "published" &&
  item?.verificationStatus === "verified";

function prune() {
  const current = now();
  for (const [id, session] of sessions) {
    if (session.expiresAt <= current || session.status === "closed")
      sessions.delete(id);
  }
  while (sessions.size >= MAX_SESSIONS)
    sessions.delete(sessions.keys().next().value);
}

function view(session) {
  return {
    id: session.id,
    labId: session.labId,
    status: session.status,
    startedAt: iso(session.startedAt),
    updatedAt: iso(session.updatedAt),
    expiresAt: iso(session.expiresAt),
    hintsUsed: session.hintsUsed,
    attempts: session.attempts.map(({ correct, submittedAt }) => ({
      correct,
      submittedAt: iso(submittedAt),
    })),
    resetCount: session.resetCount,
    completed: session.completed,
  };
}

function owned(sessionId, ownerId) {
  const session = sessions.get(sessionId);
  if (!session || !validOwner(ownerId) || session.ownerId !== ownerId)
    return null;
  if (session.expiresAt <= now()) {
    sessions.delete(sessionId);
    return null;
  }
  return session;
}

export function launchLab(ownerId, labId, labBank = []) {
  prune();
  if (!validOwner(ownerId))
    return {
      status: 400,
      body: { error: "A valid local learner identity is required." },
    };
  const publication = labBank.find(
    (item) => item.id === labId && published(item),
  );
  if (!publication || publication.artifact?.environmentStatus !== "usable")
    return { status: 404, body: { error: "Usable lab is not published." } };
  const existing = [...sessions.values()].find(
    (session) =>
      session.ownerId === ownerId &&
      session.labId === labId &&
      session.status !== "closed" &&
      session.expiresAt > now(),
  );
  if (existing)
    return { status: 200, body: { instance: view(existing), resumed: true } };
  const startedAt = now();
  const session = {
    id: randomUUID(),
    ownerId,
    labId,
    status: "active",
    startedAt,
    updatedAt: startedAt,
    expiresAt:
      startedAt +
      (publication.artifact.environment.expirationMinutes || 90) * 60_000,
    hintsUsed: 0,
    attempts: [],
    resetCount: 0,
    completed: false,
  };
  sessions.set(session.id, session);
  return { status: 201, body: { instance: view(session), resumed: false } };
}

export function getLabSession(sessionId, ownerId) {
  const session = owned(sessionId, ownerId);
  return session
    ? { status: 200, body: { instance: view(session) } }
    : { status: 404, body: { error: "Lab instance not found." } };
}

export function transitionLab(sessionId, ownerId, action) {
  const session = owned(sessionId, ownerId);
  if (!session)
    return { status: 404, body: { error: "Lab instance not found." } };
  if (!["pause", "resume", "reset", "close"].includes(action))
    return { status: 400, body: { error: "Unsupported lab action." } };
  if (action === "pause" && session.status === "active")
    session.status = "paused";
  if (action === "resume" && session.status === "paused")
    session.status = "active";
  if (action === "reset") {
    session.status = "active";
    session.hintsUsed = 0;
    session.attempts = [];
    session.completed = false;
    session.resetCount += 1;
  }
  if (action === "close") session.status = "closed";
  session.updatedAt = now();
  const result = view(session);
  if (action === "close") sessions.delete(session.id);
  return { status: 200, body: { instance: result } };
}

export function revealLabHint(sessionId, ownerId, level, labBank = []) {
  const session = owned(sessionId, ownerId);
  if (!session)
    return { status: 404, body: { error: "Lab instance not found." } };
  if (session.status !== "active")
    return {
      status: 409,
      body: { error: "Resume the lab before requesting a hint." },
    };
  const publication = labBank.find(
    (item) => item.id === session.labId && published(item),
  );
  const hints = publication?.artifact?.hints || [];
  if (
    !Number.isInteger(level) ||
    level < 1 ||
    level > hints.length ||
    level > session.hintsUsed + 1
  )
    return {
      status: 400,
      body: { error: "Hints must be revealed progressively." },
    };
  session.hintsUsed = Math.max(session.hintsUsed, level);
  session.updatedAt = now();
  return {
    status: 200,
    body: { hint: hints[level - 1], instance: view(session) },
  };
}

export function authorizeLabVerification(sessionId, ownerId, labId) {
  const session = owned(sessionId, ownerId);
  if (!session || session.labId !== labId)
    return { status: 404, body: { error: "Lab instance not found." } };
  if (session.status !== "active")
    return {
      status: 409,
      body: { error: "Resume the lab before submitting evidence." },
    };
  return { status: 200, session };
}

export function recordLabVerification(session, correct) {
  session.attempts.push({ correct: Boolean(correct), submittedAt: now() });
  if (session.attempts.length > 50) session.attempts.shift();
  session.completed ||= Boolean(correct);
  if (correct) session.status = "completed";
  session.updatedAt = now();
  return view(session);
}

export function clearLabSessionsForTests() {
  sessions.clear();
}
