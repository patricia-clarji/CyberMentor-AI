import { createHash, randomUUID } from "node:crypto";
import { mkdir, readFile, readdir, rename, writeFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const root = resolve(import.meta.dirname, "..");
const contentRoot = join(root, "content");
const paths = {
  sources: join(contentRoot, "sources.json"),
  terminology: join(contentRoot, "terminology.json"),
  reviewers: join(contentRoot, "reviewers.json"),
  skillGraph: join(contentRoot, "adaptive", "skills.json"),
  labs: join(contentRoot, "labs", "soc-practical-labs.json"),
  drafts: join(contentRoot, "drafts"),
  snapshots: join(contentRoot, "snapshots"),
  reviews: join(contentRoot, "reviews"),
  published: join(contentRoot, "published"),
  operations: join(contentRoot, "operations"),
  reports: join(contentRoot, "reports"),
};

export const normalizeText = (value) =>
  String(value || "")
    .normalize("NFKC")
    .replace(/\s+/g, " ")
    .trim();
const hash = (value) => createHash("sha256").update(value).digest("hex");
const stable = (value) => {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === "object")
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((key) => [key, stable(value[key])]),
    );
  return value;
};
export function draftContentHash(draft) {
  const content = structuredClone(draft);
  delete content.status;
  delete content.updatedAt;
  return hash(JSON.stringify(stable(content)));
}
async function readJson(file) {
  return JSON.parse(await readFile(file, "utf8"));
}
async function atomicJson(file, value) {
  await mkdir(dirname(file), { recursive: true });
  const temporary = `${file}.${randomUUID()}.tmp`;
  await writeFile(temporary, `${JSON.stringify(value, null, 2)}\n`, "utf8");
  await rename(temporary, file);
}
async function jsonFiles(directory) {
  try {
    return (await readdir(directory))
      .filter((name) => name.endsWith(".json"))
      .sort()
      .map((name) => join(directory, name));
  } catch {
    return [];
  }
}
async function loadWorkspace() {
  const sourceDocument = await readJson(paths.sources);
  const terminology = await readJson(paths.terminology);
  const reviewerDocument = await readJson(paths.reviewers);
  const skillGraph = await readJson(paths.skillGraph);
  const labDocument = await readJson(paths.labs);
  const drafts = await Promise.all(
    (await jsonFiles(paths.drafts)).map(readJson),
  );
  const reviews = await Promise.all(
    (await jsonFiles(paths.reviews)).map(readJson),
  );
  return {
    sourceDocument,
    sources: sourceDocument.sources,
    terminology,
    reviewerDocument,
    skillGraph,
    labDocument,
    drafts,
    reviews,
  };
}

const labTypes = new Set([
  "guided",
  "independent",
  "investigation",
  "incident-response",
  "detection",
  "secure-configuration",
  "threat-hunting",
]);
const labTools = new Set([
  "pwd",
  "ls",
  "cd",
  "cat",
  "grep",
  "find",
  "ps",
  "netstat",
  "ss",
  "journalctl",
  "tail",
  "head",
  "chmod",
  "chown",
]);
const trustedLabSkills = new Set([
  "security-foundations",
  "tcp-ip-reasoning",
  "dns",
  "http",
  "linux-navigation",
  "linux-processes",
  "linux-permissions",
  "linux-logs",
  "windows-processes",
  "windows-events",
  "authentication-events",
  "email-analysis",
  "ioc-analysis",
  "siem-query-reasoning",
  "alert-triage",
  "incident-severity",
  "evidence-preservation",
  "escalation-writing",
  "incident-reporting",
]);

export function validateLabDefinitions(document, skillIds = new Set()) {
  const issues = [];
  if (document?.schemaVersion !== 1)
    issues.push(
      issue(
        "error",
        "INVALID_LAB_SCHEMA_VERSION",
        "Expected lab schema version 1",
      ),
    );
  if (!Array.isArray(document?.labs) || !document.labs.length) {
    issues.push(
      issue(
        "error",
        "EMPTY_LAB_CATALOG",
        "At least one lab definition is required",
      ),
    );
    return issues;
  }
  const ids = new Set();
  const required = [
    "id",
    "version",
    "title",
    "labType",
    "category",
    "difficulty",
    "estimatedMinutes",
    "prerequisites",
    "linkedSkills",
    "objectives",
    "scenario",
    "learnerInstructions",
    "availableTools",
    "virtualEnvironment",
    "validation",
    "hints",
    "reflectionQuestions",
    "completionCriteria",
    "generatedEvidence",
    "portfolioEligibility",
    "expertSolution",
  ];
  for (const lab of document.labs) {
    const context = { labId: lab?.id };
    for (const field of required)
      if (!(field in (lab || {})))
        issues.push(issue("error", "MISSING_LAB_FIELD", field, context));
    if (!/^soc-lab-[a-z0-9-]+$/.test(lab?.id || ""))
      issues.push(issue("error", "INVALID_LAB_ID", lab?.id, context));
    if (ids.has(lab?.id))
      issues.push(issue("error", "DUPLICATE_LAB_ID", lab.id, context));
    ids.add(lab?.id);
    if (!labTypes.has(lab?.labType))
      issues.push(issue("error", "INVALID_LAB_TYPE", lab?.labType, context));
    for (const tool of lab?.availableTools || [])
      if (!labTools.has(tool))
        issues.push(issue("error", "UNSAFE_LAB_TOOL", tool, context));
    const levels = (lab?.hints || []).map((hint) => hint.level);
    if (JSON.stringify(levels) !== JSON.stringify([1, 2, 3, 4, 5]))
      issues.push(
        issue(
          "error",
          "INVALID_LAB_HINT_LADDER",
          "Hints must contain progressive levels 1 through 5",
          context,
        ),
      );
    for (const skill of lab?.linkedSkills || [])
      if (skillIds.size && !skillIds.has(skill))
        issues.push(issue("error", "UNKNOWN_LAB_SKILL", skill, context));
    for (const file of lab?.virtualEnvironment?.files || [])
      if (!file.path?.startsWith("/"))
        issues.push(
          issue("error", "INVALID_VIRTUAL_FILE_PATH", file.path, context),
        );
  }
  return issues;
}
export function safeSource(source) {
  const errors = [];
  try {
    const url = new URL(source.url);
    if (url.protocol !== "https:") errors.push("source URL must use HTTPS");
    if (!source.allowedHosts?.includes(url.hostname))
      errors.push(`host ${url.hostname} is not allowlisted`);
  } catch {
    errors.push("source URL is invalid");
  }
  if (!source.id || !/^[a-z0-9-]+$/.test(source.id))
    errors.push("source ID must be lowercase kebab-case");
  if (!source.publisher) errors.push("publisher is required");
  if (!source.reproductionPolicy)
    errors.push("reproduction policy is required");
  return errors;
}
function htmlText(value) {
  return normalizeText(
    value
      .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, " ")
      .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, " ")
      .replace(/<[^>]+>/g, " ")
      .replace(/&nbsp;/gi, " ")
      .replace(/&amp;/gi, "&")
      .replace(/&lt;/gi, "<")
      .replace(/&gt;/gi, ">")
      .replace(/&quot;/gi, '"')
      .replace(/&#39;/gi, "'"),
  );
}
async function fetchBounded(source) {
  let current = source.url;
  for (let redirect = 0; redirect <= 3; redirect++) {
    const target = new URL(current);
    if (
      target.protocol !== "https:" ||
      !source.allowedHosts.includes(target.hostname)
    )
      throw new Error(`unsafe redirect target: ${target.origin}`);
    const response = await fetch(target, {
      redirect: "manual",
      signal: AbortSignal.timeout(20_000),
      headers: {
        Accept: "text/html,application/json,application/pdf;q=0.8",
        "User-Agent":
          "CyberMentor-ContentVerifier/0.1 (+local source verification)",
      },
    });
    if ([301, 302, 303, 307, 308].includes(response.status)) {
      const location = response.headers.get("location");
      if (!location) throw new Error("redirect missing Location header");
      current = new URL(location, target).href;
      continue;
    }
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const length = Number(response.headers.get("content-length") || 0);
    if (length > 5_000_000) throw new Error("source exceeds 5 MB limit");
    const bytes = new Uint8Array(await response.arrayBuffer());
    if (bytes.byteLength > 5_000_000)
      throw new Error("source exceeds 5 MB limit");
    return { response, bytes, finalUrl: target.href };
  }
  throw new Error("too many redirects");
}
function evidenceForSource(drafts, sourceId) {
  return drafts.flatMap((draft) =>
    (draft.claims || []).flatMap((claim) =>
      (claim.citations || [])
        .filter((citation) => citation.sourceId === sourceId)
        .map((citation) => ({
          draftId: draft.id,
          claimId: claim.id,
          evidence: citation.evidence,
          evidenceHash: hash(normalizeText(citation.evidence).toLowerCase()),
        })),
    ),
  );
}

export async function refreshSources({ sourceId } = {}) {
  const { sourceDocument, drafts } = await loadWorkspace();
  const selected = sourceDocument.sources.filter(
    (source) => source.enabled && (!sourceId || source.id === sourceId),
  );
  if (!selected.length)
    throw new Error("no enabled source matched the request");
  const results = [];
  for (const source of selected) {
    const safety = safeSource(source);
    if (safety.length) {
      results.push({ sourceId: source.id, status: "failed", errors: safety });
      continue;
    }
    try {
      const { response, bytes, finalUrl } = await fetchBounded(source);
      const contentType = response.headers.get("content-type") || "unknown";
      const digest = hash(bytes);
      const decoded = contentType.includes("html")
        ? htmlText(new TextDecoder().decode(bytes)).toLowerCase()
        : "";
      const evidenceMatches = evidenceForSource(drafts, source.id).map(
        ({ evidence, ...item }) => ({
          ...item,
          matched:
            Boolean(decoded) &&
            decoded.includes(normalizeText(evidence).toLowerCase()),
          requiresManualReview: !contentType.includes("html"),
        }),
      );
      const retrievedAt = new Date().toISOString();
      const snapshot = {
        schemaVersion: 1,
        sourceId: source.id,
        sourceTitle: source.title,
        publisher: source.publisher,
        requestedUrl: source.url,
        finalUrl,
        retrievedAt,
        publicationDate:
          source.publicationDate || response.headers.get("last-modified"),
        sourceVersion:
          response.headers.get("etag") ||
          response.headers.get("last-modified") ||
          digest.slice(0, 16),
        contentDigest: digest,
        contentType,
        byteLength: bytes.byteLength,
        httpStatus: response.status,
        evidenceMatches,
        rawContentStored: false,
      };
      await atomicJson(
        join(paths.snapshots, source.id, `${digest}.json`),
        snapshot,
      );
      await atomicJson(
        join(paths.snapshots, source.id, "latest.json"),
        snapshot,
      );
      results.push({
        sourceId: source.id,
        status: "retrieved",
        sourceVersion: snapshot.sourceVersion,
        contentDigest: digest,
        evidenceMatches,
      });
    } catch (error) {
      results.push({
        sourceId: source.id,
        status: "failed",
        errors: [error instanceof Error ? error.message : String(error)],
      });
    }
  }
  const report = {
    schemaVersion: 1,
    generatedAt: new Date().toISOString(),
    command: "refresh",
    results,
  };
  await atomicJson(join(paths.reports, "ingestion-latest.json"), report);
  return report;
}
async function latestSnapshot(sourceId) {
  try {
    return await readJson(join(paths.snapshots, sourceId, "latest.json"));
  } catch {
    return null;
  }
}
const issue = (severity, code, message, context = {}) => ({
  severity,
  code,
  message,
  ...context,
});

const publishableArtifactTypes = new Set([
  "course",
  "module",
  "lesson",
  "question",
  "lab",
  "scenario",
  "project",
  "rubric",
  "glossary-entry",
  "certification-mapping",
  "completion-rule",
  "explanation-variant",
  "practice-activity",
]);
const requiredReviewRoles = [
  "cybersecurity-subject-matter-expert",
  "instructional-reviewer",
  "accessibility-reviewer",
  "licensing-reviewer",
];
const blockTypes = new Set([
  "heading",
  "paragraph",
  "objective-list",
  "definition",
  "callout",
  "warning",
  "diagram",
  "image",
  "comparison-table",
  "code",
  "terminal",
  "packet-breakdown",
  "log-sample",
  "forensic-artifact",
  "worked-example",
  "misconception",
  "knowledge-check",
  "interactive-decision",
  "practice-launch",
  "lab-launch",
  "project-milestone",
  "reference-list",
  "summary",
]);

function artifactForDraft(draft) {
  const field =
    {
      "glossary-entry": "glossaryEntry",
      "certification-mapping": "certificationMapping",
      "completion-rule": "completionRule",
      "explanation-variant": "explanationVariant",
      "practice-activity": "practiceActivity",
    }[draft.artifactType] || draft.artifactType;
  return draft[field];
}

function validateRequiredMetadata(draft, issues, context) {
  if (draft.artifactType === "validation-fixture") return;
  const metadata = draft.metadata;
  if (
    !["defensive", "dual-use"].includes(draft.riskClassification) ||
    !metadata?.domain ||
    !metadata?.difficulty ||
    !Array.isArray(metadata?.audience) ||
    !Array.isArray(metadata?.prerequisites) ||
    !Array.isArray(metadata?.skillTags) ||
    !metadata?.skillTags.length ||
    !metadata?.licenseNotes ||
    !Number.isInteger(metadata?.reviewIntervalDays) ||
    metadata.reviewIntervalDays < 1 ||
    metadata.reviewIntervalDays > 365 ||
    !Array.isArray(metadata?.changeLog) ||
    !metadata.changeLog.length
  )
    issues.push(
      issue(
        "error",
        "MISSING_REQUIRED_METADATA",
        "Risk classification, domain, difficulty, audience, prerequisites, skills, license notes, review interval, and change log are required",
        context,
      ),
    );
  const requiredDates = {
    createdAt: draft.createdAt,
    updatedAt: draft.updatedAt,
    ...(["approved", "published"].includes(draft.status)
      ? {
          lastReviewedAt: draft.lastReviewedAt,
          nextReviewAt: draft.nextReviewAt,
        }
      : {}),
  };
  for (const [field, value] of Object.entries(requiredDates))
    if (!Number.isFinite(Date.parse(value || "")))
      issues.push(
        issue("error", "INVALID_REVIEW_DATE", `${field} is required`, context),
      );
  if (
    Number.isFinite(Date.parse(draft.nextReviewAt || "")) &&
    Date.parse(draft.nextReviewAt) <= Date.now()
  )
    issues.push(
      issue(
        "error",
        "REVIEW_DATE_NOT_FUTURE",
        "nextReviewAt must be in the future",
        context,
      ),
    );
}

function validateTypedArtifact(draft, issues, context) {
  if (draft.artifactType === "validation-fixture") return;
  if (!publishableArtifactTypes.has(draft.artifactType)) {
    issues.push(
      issue(
        "error",
        "INVALID_ARTIFACT_TYPE",
        "Artifact type is not supported by the publication pipeline",
        context,
      ),
    );
    return;
  }
  const artifact = artifactForDraft(draft);
  if (!artifact || typeof artifact !== "object") {
    issues.push(
      issue(
        "error",
        "MISSING_ARTIFACT_BODY",
        `Missing ${draft.artifactType} body`,
        context,
      ),
    );
    return;
  }
  const nonEmpty = (field) =>
    field !== undefined &&
    field !== null &&
    field !== "" &&
    (!Array.isArray(field) || field.length > 0);
  const requireFields = (fields, code, message) => {
    if (fields.some((field) => !nonEmpty(artifact[field])))
      issues.push(issue("error", code, message, context));
  };
  if (draft.artifactType === "course")
    requireFields(
      ["title", "summary", "learningOutcomes", "moduleIds", "completionRuleId"],
      "INCOMPLETE_COURSE_DEFINITION",
      "Courses require a summary, outcomes, ordered modules, and a completion rule",
    );
  if (draft.artifactType === "module")
    requireFields(
      ["title", "courseId", "learningObjectives", "lessonIds"],
      "INCOMPLETE_MODULE_DEFINITION",
      "Modules require a parent course, objectives, and ordered lessons",
    );
  if (draft.artifactType === "question") {
    if (
      !artifact.prompt ||
      !Array.isArray(artifact.options) ||
      artifact.options.length < 3 ||
      !Number.isInteger(artifact.correctOption) ||
      artifact.correctOption < 0 ||
      artifact.correctOption >= artifact.options.length ||
      !artifact.learningObjectiveId ||
      !Array.isArray(artifact.skillTags) ||
      !artifact.skillTags.length ||
      !artifact.explanation ||
      !artifact.distractorExplanations ||
      Object.keys(artifact.distractorExplanations).length <
        artifact.options.length - 1
    )
      issues.push(
        issue(
          "error",
          "INVALID_QUESTION_BANK_ENTRY",
          "Objective, skills, options, verified key, rationales, and explanation are required",
          context,
        ),
      );
  }
  if (draft.artifactType === "lab") {
    const fields = [
      "title",
      "learningObjectives",
      "authorizedTarget",
      "scope",
      "safetyClassification",
      "environment",
      "tasks",
      "expectedEvidence",
      "validationLogic",
      "hints",
      "cleanupSteps",
      "defensiveExplanation",
      "skillTags",
    ];
    requireFields(
      fields,
      "INCOMPLETE_LAB_DEFINITION",
      "Labs require objectives, authorization, scope, environment, tasks, evidence, bounded validation, hints, cleanup, defense, and skills",
    );
    if (artifact.validationLogic?.type !== "normalized-equals")
      issues.push(
        issue(
          "error",
          "UNSAFE_LAB_VALIDATOR",
          "Only the bounded normalized-equals verifier is supported",
          context,
        ),
      );
  }
  if (draft.artifactType === "scenario")
    requireFields(
      [
        "title",
        "learningObjectives",
        "briefing",
        "decisionPoints",
        "expectedEvidence",
        "verificationLogic",
        "hints",
        "debrief",
      ],
      "INCOMPLETE_SCENARIO_DEFINITION",
      "Scenarios require objectives, briefing, decisions, evidence, verification, hints, and debrief",
    );
  if (draft.artifactType === "project") {
    const fields = [
      "title",
      "scenario",
      "requirements",
      "deliverables",
      "milestones",
      "rubric",
      "expectedEvidence",
      "learnerConstraints",
      "mentorBoundaries",
    ];
    requireFields(
      fields,
      "INCOMPLETE_PROJECT_DEFINITION",
      "Projects require scenario, deliverables, milestones, rubric, evidence, constraints, and mentor boundaries",
    );
  }
  if (draft.artifactType === "rubric")
    requireFields(
      ["title", "criteria", "performanceLevels", "passingRule"],
      "INCOMPLETE_RUBRIC_DEFINITION",
      "Rubrics require criteria, performance levels, and an explicit passing rule",
    );
  if (draft.artifactType === "glossary-entry")
    requireFields(
      ["term", "definition", "relatedSkillIds"],
      "INCOMPLETE_GLOSSARY_ENTRY",
      "Glossary entries require a term, definition, and related skills",
    );
  if (draft.artifactType === "certification-mapping")
    requireFields(
      ["certification", "examVersion", "objectives", "skillMappings"],
      "INCOMPLETE_CERTIFICATION_MAPPING",
      "Certification mappings require an exam version, objectives, and skill mappings",
    );
  if (draft.artifactType === "completion-rule")
    requireFields(
      ["title", "requirements", "evidenceTypes"],
      "INCOMPLETE_COMPLETION_RULE",
      "Completion rules require requirements and accepted evidence types",
    );
  if (draft.artifactType === "explanation-variant")
    requireFields(
      ["skillId", "misconception", "explanation", "workedExample"],
      "INCOMPLETE_EXPLANATION_VARIANT",
      "Explanation variants require a skill, misconception, explanation, and worked example",
    );
  if (draft.artifactType === "practice-activity") {
    const fields = [
      "title",
      "skillTags",
      "prerequisites",
      "difficulty",
      "estimatedMinutes",
      "activityType",
      "hints",
      "verificationLogic",
      "explanation",
    ];
    requireFields(
      fields,
      "INCOMPLETE_PRACTICE_ACTIVITY",
      "Adaptive activities require skills, prerequisites, difficulty, duration, hints, verification, and explanation",
    );
  }
  if (
    draft.riskClassification === "dual-use" &&
    (!draft.safety?.authorizedLocalOnly ||
      !draft.safety?.defensiveCounterpart ||
      !draft.safety?.cleanupRequired)
  )
    issues.push(
      issue(
        "error",
        "INCOMPLETE_DUAL_USE_SAFETY",
        "Dual-use content requires local authorization, defense, and cleanup controls",
        context,
      ),
    );
}

function validateSkillGraph(skillGraph, issues) {
  const skills = new Map();
  for (const skill of skillGraph?.skills || []) {
    const context = { skillId: skill.id || "unknown" };
    if (!skill.id || skills.has(skill.id))
      issues.push(
        issue(
          "error",
          skills.has(skill.id) ? "DUPLICATE_SKILL" : "INVALID_SKILL_ID",
          skill.id || "Skill ID is required",
          context,
        ),
      );
    skills.set(skill.id, skill);
    if (
      !skill.name ||
      !skill.domain ||
      normalizeText(skill.description).length < 20 ||
      ![
        "foundation",
        "guided",
        "standard",
        "advanced",
        "expert-challenge",
      ].includes(skill.difficulty) ||
      !Array.isArray(skill.prerequisites)
    )
      issues.push(
        issue(
          "error",
          "INCOMPLETE_SKILL",
          "Skills require name, domain, description, difficulty, and prerequisites",
          context,
        ),
      );
  }
  for (const skill of skills.values()) {
    for (const linked of [skill.parentSkillId, ...(skill.prerequisites || [])])
      if (linked && (!skills.has(linked) || linked === skill.id))
        issues.push(
          issue(
            "error",
            "INVALID_SKILL_RELATIONSHIP",
            `${skill.id} references invalid skill ${linked}`,
            { skillId: skill.id },
          ),
        );
  }
  const visiting = new Set();
  const visited = new Set();
  const visit = (id) => {
    if (visiting.has(id)) {
      issues.push(
        issue("error", "CYCLIC_SKILL_GRAPH", `Cycle includes ${id}`, {
          skillId: id,
        }),
      );
      return;
    }
    if (visited.has(id)) return;
    visiting.add(id);
    const skill = skills.get(id);
    for (const linked of [
      skill?.parentSkillId,
      ...(skill?.prerequisites || []),
    ])
      if (linked && skills.has(linked)) visit(linked);
    visiting.delete(id);
    visited.add(id);
  };
  for (const id of skills.keys()) visit(id);
  return new Set(skills.keys());
}

function validatePublication(
  publication,
  reviewerDocument,
  skillIds,
  issues,
  context,
) {
  const baselineApproved =
    publication?.approvalBasis === "v1-release-baseline" &&
    publication?.releaseApproval?.authority === "product-owner" &&
    publication?.releaseApproval?.decision === "approved" &&
    publication?.releaseApproval?.scope === "initial-v1-academy" &&
    Number.isFinite(
      Date.parse(publication?.releaseApproval?.recordedAt || ""),
    ) &&
    (publication?.riskClassification !== "dual-use" ||
      publication?.releaseApproval?.includesSafetyReview === true);
  if (
    !publication?.id ||
    !/^\d+\.\d+\.\d+([+-][a-z0-9.-]+)?$/i.test(
      publication?.contentVersion || "",
    ) ||
    !publishableArtifactTypes.has(publication?.artifactType) ||
    !/^[a-f0-9]{64}$/.test(publication?.contentHash || "") ||
    publication?.verificationStatus !== "verified" ||
    publication?.publicationStatus !== "published" ||
    !publication?.artifact
  )
    issues.push(
      issue(
        "error",
        "MALFORMED_PUBLICATION",
        "Publication identity, version, hash, type, status, and artifact body must be valid",
        context,
      ),
    );
  for (const [field, value] of Object.entries({
    publishedAt: publication?.publishedAt,
    lastReviewedAt: publication?.lastReviewedAt,
    nextReviewAt: publication?.nextReviewAt,
  }))
    if (!Number.isFinite(Date.parse(value || "")))
      issues.push(
        issue(
          "error",
          "INVALID_PUBLICATION_DATE",
          `${field} is required`,
          context,
        ),
      );
  if (
    Number.isFinite(Date.parse(publication?.nextReviewAt || "")) &&
    Date.parse(publication.nextReviewAt) <= Date.now()
  )
    issues.push(
      issue(
        "error",
        "EXPIRED_PUBLICATION_REVIEW",
        "Published content is past its next review date",
        context,
      ),
    );
  if (!publication?.provenance?.author || !publication?.provenance?.publisher)
    issues.push(
      issue(
        "error",
        "MISSING_PUBLICATION_PROVENANCE",
        "Publication author and publisher are required",
        context,
      ),
    );
  if (!baselineApproved) {
    const publisher = reviewerDocument.reviewers.find(
      (reviewer) => reviewer.id === publication?.provenance?.publisher,
    );
    if (!publisher?.active || !publisher.roles?.includes("content-publisher"))
      issues.push(
        issue(
          "error",
          "UNAUTHORIZED_PUBLISHER",
          "Publication must identify an active enrolled content publisher",
          context,
        ),
      );
    const requiredRoles = [
      ...requiredReviewRoles,
      ...(publication?.riskClassification === "dual-use"
        ? ["safety-reviewer"]
        : []),
    ];
    const approvals = (publication?.provenance?.reviews || []).filter(
      (review) =>
        review?.decision === "approve" &&
        Number.isFinite(Date.parse(review?.reviewedAt || "")) &&
        review?.reviewer !== publication?.provenance?.author &&
        reviewerDocument.reviewers.some(
          (reviewer) =>
            reviewer.id === review.reviewer &&
            reviewer.active &&
            reviewer.roles.includes(review.role),
        ),
    );
    for (const role of requiredRoles)
      if (!approvals.some((review) => review.role === role))
        issues.push(
          issue(
            "error",
            "MISSING_PUBLICATION_APPROVAL",
            `Publication is missing an authorized ${role} approval`,
            context,
          ),
        );
    if (!hasDistinctRoleApprovals(approvals, requiredRoles))
      issues.push(
        issue(
          "error",
          "NON_DISTINCT_PUBLICATION_REVIEWERS",
          "Each publication review role needs a distinct accountable reviewer",
          context,
        ),
      );
  }
  if (!Array.isArray(publication?.references) || !publication.references.length)
    issues.push(
      issue(
        "error",
        "PUBLICATION_WITHOUT_REFERENCES",
        "Published content requires at least one source-backed reference",
        context,
      ),
    );
  for (const skillId of publication?.metadata?.skillTags || [])
    if (!skillIds.has(skillId))
      issues.push(
        issue(
          "error",
          "UNKNOWN_PUBLICATION_SKILL",
          `Publication references unknown skill ${skillId}`,
          context,
        ),
      );
  for (const reference of publication?.references || [])
    if (
      !reference?.publisher ||
      !reference?.title ||
      !/^https:\/\//.test(reference?.url || "") ||
      !Number.isFinite(Date.parse(reference?.retrievedAt || "")) ||
      !reference?.sourceVersion
    )
      issues.push(
        issue(
          "error",
          "BROKEN_SOURCE_METADATA",
          "Published references require publisher, title, HTTPS URL, retrieval date, and source version",
          context,
        ),
      );
  const forbiddenMetricKey = (value, path = "") => {
    if (!value || typeof value !== "object") return;
    for (const [key, child] of Object.entries(value)) {
      const childPath = path ? `${path}.${key}` : key;
      if (
        /^(rating|ratings|learnerCount|studentCount|testimonial|testimonials)$/i.test(
          key,
        )
      )
        issues.push(
          issue(
            "error",
            "FAKE_PRODUCT_METRIC",
            `Published learner content cannot contain unsupported metric ${childPath}`,
            context,
          ),
        );
      else forbiddenMetricKey(child, childPath);
    }
  };
  forbiddenMetricKey(publication?.artifact);
}

export function validatePublishedGraph(publications, issues = []) {
  const byId = new Map();
  for (const publication of publications) {
    if (byId.has(publication.id))
      issues.push(
        issue("error", "DUPLICATE_PUBLICATION_ID", publication.id, {
          publicationId: publication.id,
        }),
      );
    byId.set(publication.id, publication);
  }
  for (const publication of publications) {
    const artifact = publication.artifact || {};
    const context = { publicationId: publication.id };
    if (publication.artifactType === "course")
      for (const moduleId of artifact.moduleIds || [])
        if (byId.get(moduleId)?.artifactType !== "module")
          issues.push(
            issue(
              "error",
              "INVALID_MODULE_REFERENCE",
              `Course references missing module ${moduleId}`,
              context,
            ),
          );
    if (publication.artifactType === "module")
      for (const lessonId of artifact.lessonIds || [])
        if (byId.get(lessonId)?.artifactType !== "lesson")
          issues.push(
            issue(
              "error",
              "INVALID_LESSON_REFERENCE",
              `Module references missing lesson ${lessonId}`,
              context,
            ),
          );
  }
  return issues;
}

async function validatePublishedRepository(reviewerDocument, skillIds, issues) {
  let directories;
  try {
    directories = (await readdir(paths.published, { withFileTypes: true }))
      .filter((entry) => entry.isDirectory())
      .sort((a, b) => a.name.localeCompare(b.name));
  } catch {
    return 0;
  }
  const publications = [];
  for (let index = 0; index < directories.length; index += 32) {
    await Promise.all(
      directories.slice(index, index + 32).map(async (directory) => {
        const context = { publicationId: directory.name };
        try {
          const publication = await readJson(
            join(paths.published, directory.name, "latest.json"),
          );
          publications.push(publication);
          validatePublication(
            publication,
            reviewerDocument,
            skillIds,
            issues,
            context,
          );
          if (publication.id !== directory.name)
            issues.push(
              issue(
                "error",
                "PUBLICATION_PATH_MISMATCH",
                "Publication ID must match its directory name",
                context,
              ),
            );
          const immutableVersion = await readJson(
            join(
              paths.published,
              directory.name,
              `${publication.contentVersion}.json`,
            ),
          );
          if (
            immutableVersion.id !== publication.id ||
            immutableVersion.contentHash !== publication.contentHash
          )
            issues.push(
              issue(
                "error",
                "PUBLICATION_VERSION_MISMATCH",
                "latest.json must identify an existing immutable version with the same content hash",
                context,
              ),
            );
        } catch (error) {
          issues.push(
            issue(
              "error",
              "UNREADABLE_PUBLICATION",
              error instanceof Error ? error.message : String(error),
              context,
            ),
          );
        }
      }),
    );
  }
  validatePublishedGraph(publications, issues);
  const byId = new Map();
  for (const publication of publications) {
    if (byId.has(publication.id))
      issues.push(
        issue("error", "DUPLICATE_PUBLICATION_ID", publication.id, {
          publicationId: publication.id,
        }),
      );
    byId.set(publication.id, publication);
  }
  const referencedLessons = new Set();
  const referencedQuestions = new Set();
  for (const publication of publications) {
    const artifact = publication.artifact || {};
    const context = { publicationId: publication.id };
    if (publication.artifactType === "course") {
      if (
        !Array.isArray(artifact.moduleIds) ||
        new Set(artifact.moduleIds).size !== artifact.moduleIds.length
      )
        issues.push(
          issue(
            "error",
            "BROKEN_MODULE_ORDER",
            "A course requires a unique ordered module list",
            context,
          ),
        );
      for (const moduleId of artifact.moduleIds || [])
        if (byId.get(moduleId)?.artifactType !== "module")
          issues.push(
            issue(
              "error",
              "INVALID_MODULE_REFERENCE",
              `Course references missing module ${moduleId}`,
              context,
            ),
          );
      if (
        byId.get(artifact.completionRuleId)?.artifactType !== "completion-rule"
      )
        issues.push(
          issue(
            "error",
            "INVALID_COMPLETION_RULE",
            "Course completionRuleId must reference a published completion rule",
            context,
          ),
        );
    }
    if (publication.artifactType === "module") {
      if (byId.get(artifact.courseId)?.artifactType !== "course")
        issues.push(
          issue(
            "error",
            "INVALID_COURSE_REFERENCE",
            `Module references missing course ${artifact.courseId}`,
            context,
          ),
        );
      if (
        !Array.isArray(artifact.learningObjectives) ||
        artifact.learningObjectives.length < 2
      )
        issues.push(
          issue(
            "error",
            "MISSING_MODULE_OBJECTIVES",
            "Published modules require at least two objectives",
            context,
          ),
        );
      for (const lessonId of artifact.lessonIds || []) {
        referencedLessons.add(lessonId);
        if (byId.get(lessonId)?.artifactType !== "lesson")
          issues.push(
            issue(
              "error",
              "INVALID_LESSON_REFERENCE",
              `Module references missing lesson ${lessonId}`,
              context,
            ),
          );
      }
    }
    if (publication.artifactType === "lesson") {
      const questionId = artifact?.check?.gradingKeyRef;
      if (questionId) referencedQuestions.add(questionId);
      if (byId.get(questionId)?.artifactType !== "question")
        issues.push(
          issue(
            "error",
            "MISSING_SERVER_ANSWER_KEY",
            "Published lesson check must reference a server-owned question",
            context,
          ),
        );
    }
    if (
      publication.artifactType === "lab" &&
      (!artifact.validationLogic ||
        !["normalized-equals"].includes(artifact.validationLogic.type))
    )
      issues.push(
        issue(
          "error",
          "MISSING_PRACTICAL_VALIDATION",
          "Published practice requires supported deterministic validation",
          context,
        ),
      );
  }
  for (const publication of publications) {
    if (
      publication.artifactType === "lesson" &&
      !referencedLessons.has(publication.id)
    )
      issues.push(
        issue("error", "ORPHANED_LESSON", publication.id, {
          publicationId: publication.id,
        }),
      );
    if (
      publication.artifactType === "question" &&
      !referencedQuestions.has(publication.id)
    )
      issues.push(
        issue("error", "ORPHANED_QUESTION", publication.id, {
          publicationId: publication.id,
        }),
      );
  }
  return directories.length;
}

function validateLessonDraft(draft, issues, context) {
  if (draft.artifactType === "validation-fixture") return;
  if (draft.artifactType !== "lesson") return;
  const lesson = draft.lesson;
  if (!draft.courseId || !draft.moduleId || !draft.lessonId || !lesson)
    issues.push(
      issue(
        "error",
        "INCOMPLETE_LESSON_IDENTITY",
        "Course, module, lesson, and lesson body are required",
        context,
      ),
    );
  if (!lesson) return;
  if (!Number.isInteger(lesson.minutes) || lesson.minutes < 5)
    issues.push(
      issue(
        "error",
        "INVALID_LESSON_DURATION",
        "Lesson duration must be at least five whole minutes",
        context,
      ),
    );
  if (!Array.isArray(lesson.objectives) || lesson.objectives.length < 2)
    issues.push(
      issue(
        "error",
        "INSUFFICIENT_OBJECTIVES",
        "A lesson needs at least two measurable objectives",
        context,
      ),
    );
  if (!Array.isArray(lesson.blocks) || lesson.blocks.length < 5)
    issues.push(
      issue(
        "error",
        "INSUFFICIENT_BLOCKS",
        "A lesson needs at least five structured content blocks",
        context,
      ),
    );
  const claimIds = new Set((draft.claims || []).map((claim) => claim.id));
  const mappedClaimIds = new Set();
  for (const block of lesson.blocks || []) {
    if (!block.id || !blockTypes.has(block.type))
      issues.push(
        issue(
          "error",
          "INVALID_CONTENT_BLOCK",
          "Every block needs a stable ID and supported type",
          context,
        ),
      );
    if (
      ["diagram", "image"].includes(block.type) &&
      (!block.alt || !String(block.asset || "").startsWith("/assets/"))
    )
      issues.push(
        issue(
          "error",
          "INACCESSIBLE_MEDIA",
          "Media blocks require alt text and a reviewed local asset",
          context,
        ),
      );
    for (const claimId of block.claimIds || []) {
      mappedClaimIds.add(claimId);
      if (!claimIds.has(claimId))
        issues.push(issue("error", "UNKNOWN_BLOCK_CLAIM", claimId, context));
    }
  }
  for (const claimId of claimIds)
    if (!mappedClaimIds.has(claimId))
      issues.push(
        issue(
          "error",
          "UNMAPPED_CLAIM",
          `Claim ${claimId} is not linked to a content block`,
          context,
        ),
      );
  const instructionalWords = normalizeText(
    [
      ...(lesson.blocks || []).flatMap((block) => [
        block.text,
        block.body,
        ...(block.items || []),
        ...(block.rows || []).flat(),
      ]),
      lesson.workedExample,
    ].join(" "),
  ).split(/\s+/).length;
  if (instructionalWords < 300)
    issues.push(
      issue(
        "error",
        "SHALLOW_LESSON",
        `Lesson has ${instructionalWords} instructional words; minimum is 300`,
        context,
      ),
    );
  if (!Array.isArray(lesson.keyTerms) || lesson.keyTerms.length < 3)
    issues.push(
      issue(
        "error",
        "INSUFFICIENT_KEY_TERMS",
        "A lesson needs at least three key terms",
        context,
      ),
    );
  if (normalizeText(lesson.workedExample).length < 100)
    issues.push(
      issue(
        "error",
        "SHALLOW_WORKED_EXAMPLE",
        "The worked example needs at least 100 characters",
        context,
      ),
    );
  if (
    !lesson.check?.id ||
    !lesson.check?.question ||
    !Array.isArray(lesson.check?.options) ||
    lesson.check.options.length < 3 ||
    !lesson.check?.gradingKeyRef
  )
    issues.push(
      issue(
        "error",
        "INVALID_KNOWLEDGE_CHECK",
        "A server-graded check with at least three options is required",
        context,
      ),
    );
  if (
    lesson.check &&
    Object.keys(lesson.check).some((key) => /answer|correct/i.test(key))
  )
    issues.push(
      issue(
        "error",
        "ANSWER_KEY_EXPOSURE",
        "Answer keys cannot be stored in publishable lesson content",
        context,
      ),
    );
}

export async function validateWorkspace({ onlyDraftId } = {}) {
  const {
    sourceDocument,
    terminology,
    reviewerDocument,
    skillGraph,
    labDocument,
    drafts,
    reviews,
  } = await loadWorkspace();
  const issues = [];
  const skillIds = validateSkillGraph(skillGraph, issues);
  issues.push(
    ...validateLabDefinitions(
      labDocument,
      new Set([...skillIds, ...trustedLabSkills]),
    ),
  );
  const sources = new Map();
  for (const source of sourceDocument.sources) {
    if (sources.has(source.id))
      issues.push(issue("error", "DUPLICATE_SOURCE", source.id));
    sources.set(source.id, source);
    for (const message of safeSource(source))
      issues.push(
        issue("error", "UNSAFE_SOURCE", message, { sourceId: source.id }),
      );
  }
  const reviewerIds = new Set();
  for (const reviewer of reviewerDocument.reviewers) {
    if (reviewerIds.has(reviewer.id))
      issues.push(
        issue("error", "DUPLICATE_REVIEWER", reviewer.id, {
          reviewer: reviewer.id,
        }),
      );
    reviewerIds.add(reviewer.id);
    if (!Array.isArray(reviewer.roles) || !reviewer.roles.length)
      issues.push(
        issue("error", "REVIEWER_WITHOUT_ROLE", reviewer.id, {
          reviewer: reviewer.id,
        }),
      );
  }
  for (const review of reviews) {
    const draft = drafts.find((candidate) => candidate.id === review.draftId);
    if (!draft)
      issues.push(
        issue("error", "ORPHAN_REVIEW", review.draftId, {
          reviewId: review.id,
        }),
      );
    else if (!reviewerIsAuthorized(review, reviewerDocument))
      issues.push(
        issue("error", "UNAUTHORIZED_REVIEW", review.reviewer, {
          reviewId: review.id,
          draftId: review.draftId,
        }),
      );
    else if (!reviewerIsIndependent(review, draft))
      issues.push(
        issue("error", "AUTHOR_SELF_REVIEW", review.reviewer, {
          reviewId: review.id,
          draftId: review.draftId,
        }),
      );
  }
  const publicationsChecked = await validatePublishedRepository(
    reviewerDocument,
    skillIds,
    issues,
  );
  const selectedDrafts = onlyDraftId
    ? drafts.filter((draft) => draft.id === onlyDraftId)
    : drafts;
  if (onlyDraftId && !selectedDrafts.length)
    issues.push(issue("error", "UNKNOWN_DRAFT", onlyDraftId));
  const statementOwners = new Map();
  for (const draft of selectedDrafts) {
    const context = { draftId: draft.id };
    validateRequiredMetadata(draft, issues, context);
    validateTypedArtifact(draft, issues, context);
    validateLessonDraft(draft, issues, context);
    for (const skillId of draft.metadata?.skillTags || [])
      if (!skillIds.has(skillId))
        issues.push(
          issue(
            "error",
            "UNKNOWN_DRAFT_SKILL",
            `Draft references unknown skill ${skillId}`,
            context,
          ),
        );
    if (!/^[a-z0-9-]+$/.test(draft.id || ""))
      issues.push(issue("error", "INVALID_DRAFT_ID", draft.id, context));
    if (!/^\d+\.\d+\.\d+([+-][a-z0-9.-]+)?$/i.test(draft.contentVersion || ""))
      issues.push(
        issue(
          "error",
          "INVALID_CONTENT_VERSION",
          draft.contentVersion,
          context,
        ),
      );
    if (!draft.author)
      issues.push(
        issue("error", "MISSING_AUTHOR", "Author is required", context),
      );
    if (
      !["draft", "in-review", "approved", "rejected", "published"].includes(
        draft.status,
      )
    )
      issues.push(issue("error", "INVALID_STATUS", draft.status, context));
    if (
      typeof draft.provenance?.humanAuthored !== "boolean" ||
      !draft.provenance?.disclosure
    )
      issues.push(
        issue(
          "error",
          "MISSING_PROVENANCE",
          "Human-authorship flag and disclosure are required",
          context,
        ),
      );
    const rolesForDraft =
      draft.artifactType === "validation-fixture"
        ? draft.reviewRequirements || []
        : [
            ...requiredReviewRoles,
            ...(draft.riskClassification === "dual-use"
              ? ["safety-reviewer"]
              : []),
          ];
    for (const requiredRole of rolesForDraft)
      if (!draft.reviewRequirements?.includes(requiredRole))
        issues.push(
          issue(
            "error",
            "MISSING_REVIEW_REQUIREMENT",
            `Draft must require ${requiredRole}`,
            context,
          ),
        );
    if (!Array.isArray(draft.claims) || !draft.claims.length)
      issues.push(
        issue("error", "NO_CLAIMS", "At least one claim is required", context),
      );
    if (draft.origin === "ai-assisted" && !draft.aiDisclosure)
      issues.push(
        issue(
          "error",
          "UNDISCLOSED_AI_ORIGIN",
          "AI-assisted drafts require a disclosure",
          context,
        ),
      );
    if (
      draft.origin === "ai-assisted" &&
      draft.draftLabel !== "DRAFT — AI-ASSISTED — NOT REVIEWED"
    )
      issues.push(
        issue(
          "error",
          "INVALID_AI_DRAFT_LABEL",
          "AI-assisted drafts require the exact not-reviewed label",
          context,
        ),
      );
    for (const claim of draft.claims || []) {
      const claimContext = { ...context, claimId: claim.id };
      const normalizedStatement = normalizeText(claim.statement).toLowerCase();
      if (normalizedStatement.length < 20)
        issues.push(
          issue("error", "CLAIM_TOO_SHORT", claim.statement, claimContext),
        );
      const statementHash = hash(normalizedStatement);
      if (statementOwners.has(statementHash))
        issues.push(
          issue("error", "DUPLICATE_CLAIM", claim.statement, {
            ...claimContext,
            duplicateOf: statementOwners.get(statementHash),
          }),
        );
      else statementOwners.set(statementHash, `${draft.id}:${claim.id}`);
      if (!Array.isArray(claim.citations) || !claim.citations.length)
        issues.push(
          issue(
            "error",
            "UNSUPPORTED_CLAIM",
            "Every factual claim requires at least one citation",
            claimContext,
          ),
        );
      if (claim.kind === "command" && !claim.commandVerification)
        issues.push(
          issue(
            "error",
            "UNVERIFIED_COMMAND",
            "Commands require a tested artifact or official-document verification",
            claimContext,
          ),
        );

      for (const citation of claim.citations || []) {
        const source = sources.get(citation.sourceId);
        if (!source) {
          issues.push(
            issue("error", "UNKNOWN_SOURCE", citation.sourceId, claimContext),
          );
          continue;
        }
        const words = normalizeText(citation.evidence).split(/\s+/).length;
        if (!citation.evidence || words > 25)
          issues.push(
            issue(
              "error",
              "INVALID_EVIDENCE_EXCERPT",
              "Evidence is required and must be 25 words or fewer",
              claimContext,
            ),
          );
        if (!citation.locator)
          issues.push(
            issue(
              "error",
              "MISSING_CITATION_LOCATOR",
              "A page section, heading, or other locator is required",
              claimContext,
            ),
          );
        const snapshot = await latestSnapshot(source.id);
        if (!snapshot) {
          issues.push(
            issue("error", "MISSING_SOURCE_SNAPSHOT", source.id, claimContext),
          );
          continue;
        }
        const ageDays =
          (Date.now() - new Date(snapshot.retrievedAt).getTime()) / 86_400_000;
        if (ageDays > source.maxAgeDays)
          issues.push(
            issue(
              "error",
              "OUTDATED_REFERENCE",
              `${source.id} is ${Math.floor(ageDays)} days old`,
              claimContext,
            ),
          );
        const evidenceHash = hash(
          normalizeText(citation.evidence).toLowerCase(),
        );
        const match = snapshot.evidenceMatches?.find(
          (item) =>
            item.draftId === draft.id &&
            item.claimId === claim.id &&
            item.evidenceHash === evidenceHash,
        );
        if (!match?.matched && !citation.manualVerification)
          issues.push(
            issue(
              "error",
              "UNSUPPORTED_CLAIM",
              `Evidence was not matched in ${source.id}`,
              claimContext,
            ),
          );
      }
      for (const entry of terminology.deprecatedTerms || [])
        if (normalizedStatement.includes(entry.term.toLowerCase()))
          issues.push(
            issue(
              entry.severity || "warning",
              "DEPRECATED_TERM",
              `Use ${entry.replacement} instead of ${entry.term}`,
              claimContext,
            ),
          );
      for (const entry of terminology.canonicalTerms || [])
        for (const discouraged of entry.discouraged || [])
          if (normalizedStatement.includes(discouraged.toLowerCase()))
            issues.push(
              issue(
                "warning",
                "INCONSISTENT_TERMINOLOGY",
                `Use ${entry.term} instead of ${discouraged}`,
                claimContext,
              ),
            );
    }
    if (["approved", "published"].includes(draft.status)) {
      const approvals = reviews.filter(
        (review) =>
          review.draftId === draft.id &&
          review.decision === "approve" &&
          review.contentHash === draftContentHash(draft) &&
          reviewerIsIndependent(review, draft) &&
          reviewerIsAuthorized(review, reviewerDocument),
      );
      for (const requiredRole of draft.reviewRequirements || [])
        if (!approvals.some((review) => review.role === requiredRole))
          issues.push(
            issue(
              "error",
              "MISSING_HUMAN_APPROVAL",
              `Missing current approval from ${requiredRole}`,
              context,
            ),
          );
      if (!hasDistinctRoleApprovals(approvals, draft.reviewRequirements || []))
        issues.push(
          issue(
            "error",
            "NON_DISTINCT_REVIEWERS",
            "Each required review role needs a different accountable reviewer",
            context,
          ),
        );
    }
  }
  for (const source of sourceDocument.sources.filter((item) => item.enabled))
    if (!(await latestSnapshot(source.id)))
      issues.push(
        issue(
          "warning",
          "UNMONITORED_SOURCE",
          `${source.id} has not been retrieved yet`,
          { sourceId: source.id },
        ),
      );
  const report = {
    schemaVersion: 1,
    generatedAt: new Date().toISOString(),
    summary: {
      errors: issues.filter((item) => item.severity === "error").length,
      warnings: issues.filter((item) => item.severity === "warning").length,
      draftsChecked: selectedDrafts.length,
      sourcesRegistered: sources.size,
      skillsRegistered: skillIds.size,
      publicationsChecked,
      labsChecked: labDocument.labs?.length || 0,
    },
    issues,
  };
  await mkdir(paths.reports, { recursive: true });
  await atomicJson(join(paths.reports, "validation-latest.json"), report);
  await writeFile(
    join(paths.reports, "validation-latest.md"),
    markdownReport(report),
    "utf8",
  );
  return report;
}
const reviewerIsIndependent = (review, draft) =>
  review.reviewer !== draft.author;
const reviewerIsAuthorized = (review, reviewerDocument) =>
  reviewerDocument.reviewers.some(
    (reviewer) =>
      reviewer.id === review.reviewer &&
      reviewer.active &&
      reviewer.roles.includes(review.role),
  );
function hasDistinctRoleApprovals(
  approvals,
  roles,
  roleIndex = 0,
  usedReviewers = new Set(),
) {
  if (roleIndex === roles.length) return true;
  for (const approval of approvals) {
    if (
      approval.role === roles[roleIndex] &&
      !usedReviewers.has(approval.reviewer)
    ) {
      const nextUsed = new Set(usedReviewers);
      nextUsed.add(approval.reviewer);
      if (hasDistinctRoleApprovals(approvals, roles, roleIndex + 1, nextUsed))
        return true;
    }
  }
  return false;
}
function markdownReport(report) {
  const issueLines = report.issues.length
    ? report.issues
        .map(
          (item) =>
            `- **${item.severity} / ${item.code}** (${item.draftId || item.sourceId || item.publicationId || item.skillId || "workspace"}${item.claimId ? `, claim ${item.claimId}` : ""}): ${String(item.message)}`,
        )
        .join("\n")
    : "- **pass / NO_ISSUES**: No validation issues found.";
  return `# Content validation report\n\nGenerated: ${report.generatedAt}\n\n- Errors: ${report.summary.errors}\n- Warnings: ${report.summary.warnings}\n- Drafts checked: ${report.summary.draftsChecked}\n- Sources registered: ${report.summary.sourcesRegistered}\n- Skills registered: ${report.summary.skillsRegistered}\n- Publications checked: ${report.summary.publicationsChecked}\n\n## Issues\n\n${issueLines}\n`;
}
function option(name) {
  const index = process.argv.indexOf(`--${name}`);
  return index >= 0 ? process.argv[index + 1] : undefined;
}

async function reviewDraft() {
  const draftId = option("draft");
  const reviewer = option("reviewer");
  const role = option("role");
  const decision = option("decision");
  const comment = option("comment") || "";
  if (
    !draftId ||
    !reviewer ||
    !role ||
    !["approve", "reject"].includes(decision)
  )
    throw new Error(
      "review requires --draft, --reviewer, --role, and --decision approve|reject",
    );
  const draftFile = join(paths.drafts, `${draftId}.json`);
  const draft = await readJson(draftFile);
  if (draft.status === "published")
    throw new Error(
      "published content cannot be reviewed in place; create a new version",
    );
  const { reviewerDocument } = await loadWorkspace();
  const enrolledReviewer = reviewerDocument.reviewers.find(
    (candidate) => candidate.id === reviewer,
  );
  if (!enrolledReviewer?.active || !enrolledReviewer.roles.includes(role))
    throw new Error("reviewer is not actively enrolled for the requested role");
  if (draft.author === reviewer)
    throw new Error("authors cannot approve their own content");
  if (!draft.reviewRequirements?.includes(role))
    throw new Error(`${role} is not a required review role for this draft`);
  const validation = await validateWorkspace({ onlyDraftId: draftId });
  if (validation.summary.errors)
    throw new Error("draft has validation errors and cannot be reviewed");
  const review = {
    schemaVersion: 1,
    id: randomUUID(),
    draftId,
    contentHash: draftContentHash(draft),
    reviewer,
    role,
    decision,
    comment,
    reviewedAt: new Date().toISOString(),
  };
  await atomicJson(join(paths.reviews, `${review.id}.json`), review);
  const { reviews } = await loadWorkspace();
  const approvals = reviews.filter(
    (item) =>
      item.draftId === draftId &&
      item.contentHash === review.contentHash &&
      item.decision === "approve" &&
      reviewerIsAuthorized(item, reviewerDocument),
  );
  const fullyApproved = hasDistinctRoleApprovals(
    approvals,
    draft.reviewRequirements,
  );
  draft.status =
    decision === "reject"
      ? "rejected"
      : fullyApproved
        ? "approved"
        : "in-review";
  draft.updatedAt = new Date().toISOString();
  if (fullyApproved && draft.metadata?.reviewIntervalDays) {
    draft.lastReviewedAt = draft.updatedAt;
    draft.nextReviewAt = new Date(
      Date.parse(draft.updatedAt) +
        draft.metadata.reviewIntervalDays * 86_400_000,
    ).toISOString();
  }
  await atomicJson(draftFile, draft);
  return { review, fullyApproved };
}

async function publishDraft() {
  const draftId = option("draft");
  if (!draftId) throw new Error("publish requires --draft <draft-id>");
  const draftFile = join(paths.drafts, `${draftId}.json`);
  const draft = await readJson(draftFile);
  if (draft.status !== "approved")
    throw new Error(
      "draft must have all independent human approvals before publication",
    );
  if (!publishableArtifactTypes.has(draft.artifactType))
    throw new Error("artifact type cannot be published");
  const publisher = option("publisher");
  if (!publisher)
    throw new Error("publish requires --publisher <authorized-reviewer-id>");
  const validation = await validateWorkspace({ onlyDraftId: draftId });
  if (validation.summary.errors)
    throw new Error("draft has validation errors and cannot be published");

  const { sources, reviews, reviewerDocument } = await loadWorkspace();
  const enrolledPublisher = reviewerDocument.reviewers.find(
    (candidate) => candidate.id === publisher,
  );
  if (
    !enrolledPublisher?.active ||
    !enrolledPublisher.roles.includes("content-publisher")
  )
    throw new Error("publisher is not actively enrolled as content-publisher");
  if (publisher === draft.author)
    throw new Error("authors cannot publish their own content");
  const sourceMap = new Map(sources.map((source) => [source.id, source]));
  const contentHash = draftContentHash(draft);
  const approvals = reviews.filter(
    (review) =>
      review.draftId === draftId &&
      review.contentHash === contentHash &&
      review.decision === "approve" &&
      reviewerIsIndependent(review, draft) &&
      reviewerIsAuthorized(review, reviewerDocument),
  );
  for (const role of draft.reviewRequirements || [])
    if (!approvals.some((review) => review.role === role))
      throw new Error(`missing current independent ${role} approval`);
  if (!hasDistinctRoleApprovals(approvals, draft.reviewRequirements || []))
    throw new Error("required roles must be approved by distinct reviewers");

  const references = [];
  for (const claim of draft.claims) {
    for (const citation of claim.citations || []) {
      const source = sourceMap.get(citation.sourceId);
      const snapshot = await latestSnapshot(citation.sourceId);
      references.push({
        claimId: claim.id,
        sourceId: source.id,
        title: source.title,
        publisher: source.publisher,
        url: source.url,
        publicationDate: source.publicationDate || null,
        retrievedAt: snapshot.retrievedAt,
        sourceVersion: snapshot.sourceVersion,
        snapshotDigest: snapshot.contentDigest,
        evidence: citation.evidence,
      });
    }
  }
  const publishedAt = new Date().toISOString();
  const artifact = structuredClone(artifactForDraft(draft));
  if (draft.artifactType === "lesson")
    Object.assign(artifact, {
      courseId: draft.courseId,
      moduleId: draft.moduleId,
      lessonId: draft.lessonId,
      title: draft.title,
    });
  const published = {
    schemaVersion: 1,
    id: draft.id,
    title: draft.title,
    contentVersion: draft.contentVersion,
    contentHash,
    artifactType: draft.artifactType,
    riskClassification: draft.riskClassification,
    verificationStatus: "verified",
    publicationStatus: "published",
    publishedAt,
    lastReviewedAt: draft.lastReviewedAt,
    nextReviewAt: draft.nextReviewAt,
    metadata: draft.metadata,
    artifact,
    claims: draft.claims,
    references,
    provenance: {
      author: draft.author,
      publisher,
      disclosure: draft.provenance.disclosure,
      humanAuthored: draft.provenance.humanAuthored,
      reviews: approvals.map(({ reviewer, role, reviewedAt, decision }) => ({
        reviewer,
        role,
        reviewedAt,
        decision,
      })),
    },
  };
  const versionFile = join(
    paths.published,
    draft.id,
    `${draft.contentVersion}.json`,
  );
  let existingVersion = null;
  try {
    existingVersion = await readJson(versionFile);
  } catch (error) {
    if (
      !error ||
      typeof error !== "object" ||
      !("code" in error) ||
      error.code !== "ENOENT"
    )
      throw error;
  }
  if (existingVersion && existingVersion.contentHash !== published.contentHash)
    throw new Error(
      `published version ${draft.contentVersion} is immutable; increment the content version`,
    );
  await atomicJson(versionFile, published);
  await atomicJson(join(paths.published, draft.id, "latest.json"), published);
  draft.status = "published";
  draft.updatedAt = publishedAt;
  await atomicJson(draftFile, draft);
  await syncPublishedContent();
  return published;
}

async function syncPublishedContent() {
  const { reviewerDocument, skillGraph } = await loadWorkspace();
  const publicationIssues = [];
  const skillIds = validateSkillGraph(skillGraph, publicationIssues);
  await validatePublishedRepository(
    reviewerDocument,
    skillIds,
    publicationIssues,
  );
  if (publicationIssues.some((item) => item.severity === "error"))
    throw new Error(
      `published repository validation failed: ${publicationIssues
        .map((item) => `${item.code} (${item.publicationId || "unknown"})`)
        .join(", ")}`,
    );
  let directories;
  try {
    directories = (await readdir(paths.published, { withFileTypes: true }))
      .filter((entry) => entry.isDirectory())
      .sort((a, b) => a.name.localeCompare(b.name));
  } catch {
    directories = [];
  }
  const artifacts = [];
  let baselineArtifacts = 0;
  for (const directory of directories) {
    const publication = await readJson(
      join(paths.published, directory.name, "latest.json"),
    );
    if (
      publication.verificationStatus !== "verified" ||
      publication.publicationStatus !== "published" ||
      !publication.provenance?.publisher ||
      !publication.nextReviewAt
    )
      throw new Error(
        `published artifact ${directory.name} is not deliverable`,
      );
    if (publication.approvalBasis === "v1-release-baseline")
      baselineArtifacts += 1;
    artifacts.push({
      id: publication.id,
      title: publication.title,
      artifactType: publication.artifactType,
      contentVersion: publication.contentVersion,
      contentHash: publication.contentHash,
      publishedAt: publication.publishedAt,
      lastReviewedAt: publication.lastReviewedAt,
      nextReviewAt: publication.nextReviewAt,
      relativePath: `${directory.name}/latest.json`,
    });
  }
  const manifest = {
    schemaVersion: 1,
    generatedAt: new Date().toISOString(),
    sourceOfTruth: "version-controlled-published-content",
    ...(artifacts.length && baselineArtifacts === artifacts.length
      ? {
          release: "v1-initial-academy",
          approvalBasis: "v1-release-baseline",
        }
      : {}),
    artifacts,
  };
  await atomicJson(join(paths.published, "manifest.json"), manifest);
  return manifest;
}

async function importContent() {
  const validation = await validateWorkspace();
  if (validation.summary.errors)
    throw new Error("content import blocked by validation errors");
  return syncPublishedContent();
}

export function createRollbackActivation(
  target,
  current,
  { publisher, reason, now = new Date() },
) {
  const activatedAt = now.toISOString();
  return {
    ...structuredClone(target),
    activation: {
      activatedAt,
      activatedBy: publisher,
      reason: reason || "Authorized content rollback",
      replacedVersion: current.contentVersion,
    },
  };
}

async function rollbackPublication() {
  const artifactId = option("artifact");
  const version = option("version");
  const publisher = option("publisher");
  if (!artifactId || !version || !publisher)
    throw new Error("rollback requires --artifact, --version, and --publisher");
  const { reviewerDocument, skillGraph } = await loadWorkspace();
  const enrolledPublisher = reviewerDocument.reviewers.find(
    (candidate) => candidate.id === publisher,
  );
  if (
    !enrolledPublisher?.active ||
    !enrolledPublisher.roles.includes("content-publisher")
  )
    throw new Error("publisher is not actively enrolled as content-publisher");
  const target = await readJson(
    join(paths.published, artifactId, `${version}.json`),
  );
  if (target.id !== artifactId || target.contentVersion !== version)
    throw new Error("rollback target identity does not match its path");
  if (publisher === target.provenance?.author)
    throw new Error("authors cannot activate their own content rollback");
  if (
    target.verificationStatus !== "verified" ||
    target.publicationStatus !== "published"
  )
    throw new Error("rollback target is not a verified publication");
  const targetIssues = [];
  const skillIds = validateSkillGraph(skillGraph, targetIssues);
  validatePublication(target, reviewerDocument, skillIds, targetIssues, {
    publicationId: artifactId,
  });
  if (targetIssues.some((item) => item.severity === "error"))
    throw new Error(
      `rollback target failed validation: ${targetIssues
        .map((item) => item.code)
        .join(", ")}`,
    );
  const current = await readJson(
    join(paths.published, artifactId, "latest.json"),
  );
  const activated = createRollbackActivation(target, current, {
    publisher,
    reason: option("reason"),
  });
  const activatedAt = activated.activation.activatedAt;
  await atomicJson(join(paths.published, artifactId, "latest.json"), activated);
  const operation = {
    schemaVersion: 1,
    id: randomUUID(),
    operation: "rollback",
    artifactId,
    fromVersion: current.contentVersion,
    toVersion: version,
    operator: publisher,
    reason: activated.activation.reason,
    occurredAt: activatedAt,
  };
  await atomicJson(join(paths.operations, `${operation.id}.json`), operation);
  await syncPublishedContent();
  return operation;
}

async function status() {
  const { sourceDocument, sources, drafts, reviews } = await loadWorkspace();
  const sourceStatus = [];
  for (const source of sources) {
    const snapshot = await latestSnapshot(source.id);
    const ageDays = snapshot
      ? Math.floor(
          (Date.now() - new Date(snapshot.retrievedAt).getTime()) / 86_400_000,
        )
      : null;
    sourceStatus.push({
      id: source.id,
      enabled: source.enabled,
      retrievedAt: snapshot?.retrievedAt || null,
      sourceVersion: snapshot?.sourceVersion || null,
      ageDays,
      stale: ageDays === null || ageDays > source.maxAgeDays,
    });
  }
  return {
    schemaVersion: sourceDocument.schemaVersion,
    generatedAt: new Date().toISOString(),
    sources: sourceStatus,
    drafts: drafts.map((draft) => ({
      id: draft.id,
      version: draft.contentVersion,
      status: draft.status,
      currentApprovals: reviews
        .filter(
          (review) =>
            review.draftId === draft.id &&
            review.decision === "approve" &&
            review.contentHash === draftContentHash(draft),
        )
        .map((review) => ({ reviewer: review.reviewer, role: review.role })),
    })),
  };
}

async function main() {
  const command = process.argv[2] || "status";
  let result;
  switch (command) {
    case "refresh":
      result = await refreshSources({ sourceId: option("source") });
      if (result.results.some((item) => item.status === "failed"))
        process.exitCode = 1;
      break;
    case "validate":
      result = await validateWorkspace({ onlyDraftId: option("draft") });
      if (result.summary.errors) process.exitCode = 1;
      break;
    case "review":
      result = await reviewDraft();
      break;
    case "publish":
      result = await publishDraft();
      break;
    case "import":
    case "sync":
      result = await importContent();
      break;
    case "rollback":
      result = await rollbackPublication();
      break;
    case "status":
      result = await status();
      break;
    default:
      throw new Error(`unknown command: ${command}`);
  }
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
}

const isMain =
  process.argv[1] &&
  pathToFileURL(resolve(process.argv[1])).href === import.meta.url;
if (isMain)
  main().catch((error) => {
    process.stderr.write(`content pipeline failed: ${error.message}\n`);
    process.exitCode = 1;
  });
