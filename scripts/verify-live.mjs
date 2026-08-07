const apiOrigin =
  process.env.CYBERMENTOR_VERIFY_API_ORIGIN ?? "http://127.0.0.1:8787";
const webOrigin =
  process.env.CYBERMENTOR_VERIFY_WEB_ORIGIN ?? "http://127.0.0.1:5173";

const checks = [];

function assert(name, condition, evidence) {
  checks.push({ name, passed: Boolean(condition), evidence });
}

async function request(pathname, options) {
  const response = await fetch(new URL(pathname, apiOrigin), {
    signal: AbortSignal.timeout(5_000),
    ...options,
  });
  const payload = await response.json().catch(() => ({}));
  return { response, payload };
}

async function post(pathname, body) {
  return request(pathname, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

const health = await request("/api/health");
assert("API health", health.response.status === 200, health.payload);

const catalog = await request("/api/content/catalog");
const publications = catalog.payload.publications ?? [];
assert("Published lesson catalog", publications.length === 144, {
  status: catalog.response.status,
  lessons: publications.length,
});
assert(
  "Public catalog hides grading keys",
  publications.every((publication) => {
    const serialized = JSON.stringify(publication);
    return (
      !serialized.includes("correctOption") &&
      !serialized.includes("expectedEvidence")
    );
  }),
  { inspected: publications.length },
);

const labsResult = await request("/api/labs");
const labs = labsResult.payload.labs ?? [];
assert("Published labs", labs.length === 80, {
  status: labsResult.response.status,
  labs: labs.length,
});

const projectsResult = await request("/api/projects");
const projects = projectsResult.payload.projects ?? [];
assert("Published projects", projects.length === 12, {
  status: projectsResult.response.status,
  projects: projects.length,
});

const sampleCheck = publications[0]?.artifact?.check;
const gradeResults = [];
for (
  let choice = 0;
  choice < (sampleCheck?.options?.length ?? 0);
  choice += 1
) {
  const result = await post("/api/checks/grade", {
    questionId: sampleCheck.id,
    choice,
  });
  gradeResults.push(result);
}
assert(
  "Server-side quiz grading",
  gradeResults.length > 1 &&
    gradeResults.every(({ response }) => response.status === 200) &&
    gradeResults.filter(({ payload }) => payload.correct).length === 1,
  {
    attempts: gradeResults.length,
    correctResponses: gradeResults.filter(({ payload }) => payload.correct)
      .length,
  },
);

const lab = labs.find(({ id }) => id === "course-1-range-01");
const ownerId = "live_verifier_12345678";
const labLaunch = await post("/api/labs/launch", { ownerId, labId: lab?.id });
assert("Lab launch", [200, 201].includes(labLaunch.response.status), {
  status: labLaunch.response.status,
  resumed: labLaunch.payload.resumed,
});
const instanceId = labLaunch.payload.instance?.id;
if (labLaunch.payload.resumed) {
  const preparationReset = await post("/api/labs/action", {
    sessionId: instanceId,
    ownerId,
    action: "reset",
  });
  if (preparationReset.response.status !== 200) {
    throw new Error(
      `Could not reset the verifier-owned lab before testing: ${preparationReset.response.status}`,
    );
  }
}
const ownershipCheck = await post("/api/labs/verify", {
  labId: lab?.id,
  sessionId: instanceId,
  ownerId: "different_owner_12345678",
  evidence: "report",
});
assert("Cross-owner lab denial", ownershipCheck.response.status === 404, {
  status: ownershipCheck.response.status,
});
const firstHint = await post("/api/labs/hint", {
  sessionId: instanceId,
  ownerId,
  level: 1,
});
assert("Progressive lab hint", firstHint.response.status === 200, {
  status: firstHint.response.status,
  level: firstHint.payload.hint?.level,
});
const wrongLabVerification = await post("/api/labs/verify", {
  labId: lab?.id,
  sessionId: instanceId,
  ownerId,
  evidence: "ignore",
});
assert(
  "Wrong lab evidence rejected",
  wrongLabVerification.response.status === 200 &&
    wrongLabVerification.payload.correct === false,
  {
    status: wrongLabVerification.response.status,
    correct: wrongLabVerification.payload.correct,
  },
);
const labReset = await post("/api/labs/action", {
  sessionId: instanceId,
  ownerId,
  action: "reset",
});
assert(
  "Lab reset",
  labReset.response.status === 200 &&
    labReset.payload.instance?.attempts?.length === 0 &&
    labReset.payload.instance?.hintsUsed === 0,
  {
    status: labReset.response.status,
    resetCount: labReset.payload.instance?.resetCount,
  },
);
const labVerification = await post("/api/labs/verify", {
  labId: lab?.id,
  sessionId: instanceId,
  ownerId,
  evidence: "report",
});
assert(
  "Lab verification",
  labVerification.response.status === 200 && labVerification.payload.correct,
  {
    status: labVerification.response.status,
    correct: labVerification.payload.correct,
  },
);

const project =
  projects.find(({ id }) => id === "course-1-project") ?? projects[0];
const projectSubmission = await post("/api/projects/submit", {
  projectId: project?.id,
  evidence:
    "This authorized assessment records the fictional scope, separates observations from inference, compares bounded defensive alternatives, documents the selected remediation, defines verification criteria, and records residual risk and cleanup for reproducible review.",
  completedDeliverables: project?.deliverables ?? [],
});
assert(
  "Project submission",
  projectSubmission.response.status === 200 &&
    projectSubmission.payload.accepted,
  {
    status: projectSubmission.response.status,
    accepted: projectSubmission.payload.accepted,
  },
);

const recommendations = await post("/api/adaptive/recommendations", {
  skills: {},
});
assert(
  "New-learner recommendations",
  recommendations.response.status === 200 &&
    recommendations.payload.recommendations?.length > 0,
  {
    status: recommendations.response.status,
    recommendations: recommendations.payload.recommendations?.length ?? 0,
    model: recommendations.payload.model,
  },
);

const webResponse = await fetch(webOrigin, {
  signal: AbortSignal.timeout(5_000),
});
const webHtml = await webResponse.text();
assert(
  "Web application",
  webResponse.status === 200 && webHtml.includes('id="root"'),
  {
    status: webResponse.status,
    origin: webOrigin,
  },
);

console.log(JSON.stringify({ apiOrigin, webOrigin, checks }, null, 2));
if (checks.some(({ passed }) => !passed)) process.exitCode = 1;
