import { readFile, stat } from "node:fs/promises";
import { join, resolve } from "node:path";

const publishedRoot = resolve("content", "published");
const requiredReviewRoles = [
  "cybersecurity-subject-matter-expert",
  "instructional-reviewer",
  "accessibility-reviewer",
  "licensing-reviewer",
];
const publicationCache = new Map();
const publicationLoads = new Map();

async function readJson(file) {
  return JSON.parse(await readFile(file, "utf8"));
}

function current(publication, now = new Date()) {
  if (
    publication?.verificationStatus !== "verified" ||
    publication?.publicationStatus !== "published"
  )
    return false;
  const nextReviewAt = Date.parse(publication.nextReviewAt || "");
  return Number.isFinite(nextReviewAt) && nextReviewAt >= now.getTime();
}

export function isDeliverablePublication(publication, now) {
  const approvedRoles = new Set(
    (publication?.provenance?.reviews || [])
      .filter(
        (review) =>
          review?.decision === "approve" &&
          Number.isFinite(Date.parse(review?.reviewedAt || "")),
      )
      .map((review) => review.role),
  );
  const roles = [
    ...requiredReviewRoles,
    ...(publication?.riskClassification === "dual-use"
      ? ["safety-reviewer"]
      : []),
  ];
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
  const workflowApproved = roles.every((role) => approvedRoles.has(role));
  return Boolean(
    publication?.id &&
    publication?.contentVersion &&
    publication?.artifactType &&
    ["defensive", "dual-use"].includes(publication?.riskClassification) &&
    publication?.provenance?.author &&
    publication?.provenance?.publisher &&
    (baselineApproved || workflowApproved) &&
    Array.isArray(publication?.references) &&
    publication.references.length > 0 &&
    current(publication, now),
  );
}

export async function loadPublishedContent({ artifactType, now } = {}) {
  const manifestFile = join(publishedRoot, "manifest.json");
  let manifestStat;
  try {
    manifestStat = await stat(manifestFile);
  } catch {
    return [];
  }
  const reviewDay = (now || new Date()).toISOString().slice(0, 10);
  const key = `${manifestStat.mtimeMs}:${artifactType || "*"}:${reviewDay}`;
  if (publicationCache.has(key)) return publicationCache.get(key);
  if (publicationLoads.has(key)) return publicationLoads.get(key);
  const load = (async () => {
    try {
      const manifest = await readJson(manifestFile);
      const items = (manifest.artifacts || []).filter(
        (item) => !artifactType || item.artifactType === artifactType,
      );
      const records = (
        await Promise.all(
          items.map(async (item) => {
            try {
              const publication = await readJson(
                join(publishedRoot, item.relativePath),
              );
              return isDeliverablePublication(publication, now)
                ? publication
                : null;
            } catch {
              return null;
            }
          }),
        )
      )
        .filter(Boolean)
        .sort((a, b) => a.id.localeCompare(b.id));
      if (publicationCache.size > 20) publicationCache.clear();
      publicationCache.set(key, records);
      return records;
    } catch {
      return [];
    } finally {
      publicationLoads.delete(key);
    }
  })();
  publicationLoads.set(key, load);
  return load;
}

export function clearPublicationCacheForTests() {
  publicationCache.clear();
  publicationLoads.clear();
}

export function publicLesson(publication) {
  const lesson = publication.artifact;
  return {
    id: publication.id,
    artifactType: "lesson",
    contentVersion: publication.contentVersion,
    verificationStatus: publication.verificationStatus,
    publicationStatus: publication.publicationStatus,
    publishedAt: publication.publishedAt,
    lastReviewedAt: publication.lastReviewedAt,
    nextReviewAt: publication.nextReviewAt,
    metadata: publication.metadata,
    artifact: lesson,
    references: publication.references,
    provenance: {
      author: publication.provenance.author,
      publisher: publication.provenance.publisher,
      reviews: publication.provenance.reviews.map(
        ({ role, reviewedAt, decision }) => ({ role, reviewedAt, decision }),
      ),
    },
  };
}

export function publicLab(publication) {
  const lab = publication.artifact;
  return {
    id: publication.id,
    version: publication.contentVersion,
    courseId: lab.courseId,
    title: lab.title,
    description: lab.description,
    category: lab.category,
    difficulty: lab.difficulty,
    estimatedMinutes: lab.estimatedMinutes,
    story: lab.story,
    businessContext: lab.businessContext,
    learningObjectives: lab.learningObjectives,
    prerequisites: lab.prerequisites,
    requiredSkills: lab.requiredSkills,
    authorizedTarget: lab.authorizedTarget,
    scope: lab.scope,
    safetyClassification: lab.safetyClassification,
    rulesOfEngagement: lab.rulesOfEngagement,
    environment: lab.environment,
    environmentStatus: lab.environmentStatus,
    instructions: lab.instructions,
    tasks: lab.tasks,
    expectedDeliverables: lab.expectedDeliverables,
    evidenceRequirement: lab.evidenceRequirement,
    hints: lab.hints,
    solutionAccessPolicy: lab.solutionAccessPolicy,
    debrief: lab.debrief,
    reflectionPrompts: lab.reflectionPrompts,
    furtherReading: lab.furtherReading,
    cleanupSteps: lab.cleanupSteps,
    defensiveExplanation: lab.defensiveExplanation,
    portfolioSkills: lab.portfolioSkills,
    skillTags: lab.skillTags,
    author: lab.author,
    review: lab.review,
    verificationStatus: "verified",
    publicationStatus: "published",
  };
}

export function publicProject(publication) {
  const project = publication.artifact;
  return {
    id: publication.id,
    version: publication.contentVersion,
    courseId: project.courseId,
    title: project.title,
    scenario: project.scenario,
    requirements: project.requirements,
    deliverables: project.deliverables,
    milestones: project.milestones,
    rubric: project.rubric,
    minimumEvidenceLength: project.minimumEvidenceLength,
    skillTags: project.skillTags,
    learnerConstraints: project.learnerConstraints,
    mentorBoundaries: project.mentorBoundaries,
    verificationStatus: "verified",
    publicationStatus: "published",
  };
}
