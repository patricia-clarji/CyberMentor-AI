// @vitest-environment node
import { describe, expect, it } from "vitest";
import {
  isDeliverablePublication,
  publicLab,
  publicLesson,
  publicProject,
} from "./content-repository.mjs";

const publication = {
  id: "artifact",
  artifactType: "lesson",
  riskClassification: "defensive",
  title: "Verified lesson",
  contentVersion: "1.0.0",
  verificationStatus: "verified",
  publicationStatus: "published",
  publishedAt: "2026-07-01T00:00:00.000Z",
  lastReviewedAt: "2026-07-01T00:00:00.000Z",
  nextReviewAt: "2027-01-01T00:00:00.000Z",
  metadata: { skillTags: ["security-foundations"] },
  references: [
    {
      title: "Source",
      publisher: "NIST",
      url: "https://www.nist.gov/",
      retrievedAt: "2026-07-01T00:00:00.000Z",
    },
  ],
  provenance: {
    author: "author",
    publisher: "publisher",
    reviews: [
      {
        role: "cybersecurity-subject-matter-expert",
        reviewedAt: "2026-07-01",
        decision: "approve",
      },
      {
        role: "instructional-reviewer",
        reviewedAt: "2026-07-01",
        decision: "approve",
      },
      {
        role: "accessibility-reviewer",
        reviewedAt: "2026-07-01",
        decision: "approve",
      },
      {
        role: "licensing-reviewer",
        reviewedAt: "2026-07-01",
        decision: "approve",
      },
    ],
  },
  artifact: {
    courseId: "course-1",
    moduleId: "course-1-m1",
    lessonId: "lesson-1",
    blocks: [],
  },
};

describe("published content repository", () => {
  it("delivers only current, reviewed publications", () => {
    expect(
      isDeliverablePublication(
        publication,
        new Date("2026-07-19T00:00:00.000Z"),
      ),
    ).toBe(true);
    expect(
      isDeliverablePublication(
        { ...publication, verificationStatus: "draft" },
        new Date("2026-07-19T00:00:00.000Z"),
      ),
    ).toBe(false);
    expect(
      isDeliverablePublication(
        publication,
        new Date("2027-02-01T00:00:00.000Z"),
      ),
    ).toBe(false);
    expect(
      isDeliverablePublication(
        {
          ...publication,
          provenance: {
            ...publication.provenance,
            reviews: publication.provenance.reviews.map((review) => ({
              ...review,
              role: "generic-reviewer",
            })),
          },
        },
        new Date("2026-07-19T00:00:00.000Z"),
      ),
    ).toBe(false);
  });

  it("requires safety approval for dual-use publications", () => {
    expect(
      isDeliverablePublication(
        { ...publication, riskClassification: "dual-use" },
        new Date("2026-07-19T00:00:00.000Z"),
      ),
    ).toBe(false);
    expect(
      isDeliverablePublication(
        {
          ...publication,
          riskClassification: "dual-use",
          provenance: {
            ...publication.provenance,
            reviews: [
              ...publication.provenance.reviews,
              {
                role: "safety-reviewer",
                reviewedAt: "2026-07-01",
                decision: "approve",
              },
            ],
          },
        },
        new Date("2026-07-19T00:00:00.000Z"),
      ),
    ).toBe(true);
  });

  it("accepts the explicit product-owner V1 baseline without weakening future workflow", () => {
    const baseline = {
      ...publication,
      approvalBasis: "v1-release-baseline",
      releaseApproval: {
        authority: "product-owner",
        decision: "approved",
        scope: "initial-v1-academy",
        recordedAt: "2026-07-19T00:00:00.000Z",
        includesSafetyReview: true,
      },
      provenance: { ...publication.provenance, reviews: [] },
    };
    expect(
      isDeliverablePublication(baseline, new Date("2026-07-19T00:00:00.000Z")),
    ).toBe(true);
    expect(
      isDeliverablePublication(
        {
          ...baseline,
          approvalBasis: "community-contribution",
        },
        new Date("2026-07-19T00:00:00.000Z"),
      ),
    ).toBe(false);
  });

  it("removes reviewer identity from learner lesson payloads", () => {
    expect(publicLesson(publication).provenance.reviews[0]).not.toHaveProperty(
      "reviewer",
    );
  });

  it("removes lab verification logic and expected evidence", () => {
    const lab = publicLab({
      ...publication,
      artifact: {
        title: "Lab",
        learningObjectives: ["Inspect evidence"],
        authorizedTarget: "local fixture",
        scope: "local",
        safetyClassification: "defensive",
        environment: {},
        tasks: ["Inspect"],
        hints: ["Review"],
        cleanupSteps: ["Reset"],
        defensiveExplanation: "Defensive review",
        expectedEvidence: ["secret"],
        validationLogic: { type: "normalized-equals", expectedValue: "secret" },
      },
    });
    expect(JSON.stringify(lab)).not.toMatch(
      /secret|validationLogic|expectedEvidence/,
    );
  });

  it("removes private project evaluator evidence", () => {
    const project = publicProject({
      ...publication,
      artifact: {
        courseId: "course-1",
        title: "Project",
        scenario: "Scenario",
        requirements: ["Requirement"],
        deliverables: ["Report"],
        milestones: ["Draft"],
        rubric: [],
        minimumEvidenceLength: 180,
        skillTags: ["security-foundations"],
        learnerConstraints: [],
        mentorBoundaries: [],
        expectedEvidence: ["private evaluator detail"],
      },
    });
    expect(project.courseId).toBe("course-1");
    expect(JSON.stringify(project)).not.toMatch(
      /private evaluator|expectedEvidence/,
    );
  });
});
