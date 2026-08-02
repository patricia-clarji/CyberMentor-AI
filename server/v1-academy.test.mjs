// @vitest-environment node
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import {
  isDeliverablePublication,
  publicLab,
  publicProject,
} from "./content-repository.mjs";

const root = resolve();
const readJson = async (file) =>
  JSON.parse(await readFile(resolve(root, file), "utf8"));

describe("Version 1 seeded academy", () => {
  it("publishes the complete normalized academy inventory", async () => {
    const manifest = await readJson("content/published/manifest.json");
    const counts = manifest.artifacts.reduce((result, item) => {
      result[item.artifactType] = (result[item.artifactType] || 0) + 1;
      return result;
    }, {});
    expect(manifest.approvalBasis).toBe("v1-release-baseline");
    expect(counts).toMatchObject({
      course: 12,
      module: 48,
      lesson: 144,
      question: 144,
      lab: 80,
      project: 12,
      rubric: 12,
      "completion-rule": 12,
      "practice-activity": 24,
    });
    expect(manifest.artifacts).toHaveLength(488);
    const databaseSeed = await readJson("db/seeds/001_v1_academy.seed.json");
    expect(databaseSeed.courses).toHaveLength(12);
    expect(databaseSeed.lessons).toHaveLength(144);
    expect(databaseSeed.questions).toHaveLength(144);
    expect(databaseSeed.labs).toHaveLength(80);
  });

  it("ships substantial, distinct structured lessons with private grading keys", async () => {
    const manifest = await readJson("content/published/manifest.json");
    const lessonItems = manifest.artifacts.filter(
      (item) => item.artifactType === "lesson",
    );
    const questionIds = new Set(
      manifest.artifacts
        .filter((item) => item.artifactType === "question")
        .map((item) => item.id),
    );
    const openingBlocks = new Set();
    for (const item of lessonItems) {
      const publication = await readJson(
        `content/published/${item.id}/latest.json`,
      );
      const lesson = publication.artifact;
      const words = lesson.blocks
        .flatMap((block) => [
          block.text,
          block.body,
          ...(block.items || []),
          ...(block.rows || []).flat(),
        ])
        .filter(Boolean)
        .join(" ")
        .split(/\s+/).length;
      expect(isDeliverablePublication(publication)).toBe(true);
      expect(lesson.blocks.length).toBeGreaterThanOrEqual(9);
      expect(words).toBeGreaterThanOrEqual(500);
      expect(questionIds.has(lesson.check.gradingKeyRef)).toBe(true);
      expect(JSON.stringify(lesson)).not.toMatch(/correctOption|expectedValue/);
      openingBlocks.add(lesson.blocks[0].text);
    }
    expect(openingBlocks.size).toBe(144);
  });

  it("keeps lab validators and project evaluator evidence private", async () => {
    const labPublication = await readJson(
      "content/published/course-1-range-01/latest.json",
    );
    const projectPublication = await readJson(
      "content/published/course-1-project/latest.json",
    );
    expect(JSON.stringify(publicLab(labPublication))).not.toMatch(
      /validationLogic|expectedEvidence|expectedValue/,
    );
    expect(JSON.stringify(publicProject(projectPublication))).not.toMatch(
      /expectedEvidence/,
    );
  });

  it("links every course to twelve lessons, multiple labs, a project, rubric, and completion rule", async () => {
    const databaseSeed = await readJson("db/seeds/001_v1_academy.seed.json");
    for (const course of databaseSeed.courses) {
      expect(
        databaseSeed.lessons.filter((item) => item.courseId === course.id),
      ).toHaveLength(12);
      expect(
        databaseSeed.labs.filter((item) => item.courseId === course.id).length,
      ).toBeGreaterThanOrEqual(6);
      expect(
        databaseSeed.projects.some((item) => item.courseId === course.id),
      ).toBe(true);
      expect(
        databaseSeed.rubrics.some((item) => item.courseId === course.id),
      ).toBe(true);
      expect(
        databaseSeed.completionRules.some(
          (item) => item.courseId === course.id,
        ),
      ).toBe(true);
    }
  });

  it("ships eighty complete, usable and truthfully classified range activities", async () => {
    const manifest = await readJson("content/published/manifest.json");
    const labItems = manifest.artifacts.filter(
      (item) => item.artifactType === "lab",
    );
    const counts = {
      interactive: 0,
      artifact: 0,
      configuration: 0,
      awareness: 0,
      career: 0,
      executable: 0,
    };
    for (const item of labItems) {
      const publication = await readJson(
        `content/published/${item.id}/latest.json`,
      );
      const lab = publication.artifact;
      expect(isDeliverablePublication(publication)).toBe(true);
      expect(lab.environmentStatus).toBe("usable");
      expect(lab.story.length).toBeGreaterThan(80);
      expect(lab.businessContext.length).toBeGreaterThan(80);
      expect(lab.learningObjectives.length).toBeGreaterThanOrEqual(3);
      expect(lab.tasks.length).toBeGreaterThanOrEqual(2);
      expect(lab.hints).toHaveLength(5);
      expect(lab.validationLogic.type).toBe("normalized-equals");
      expect(lab.environment.networkAccess).toBe(false);
      expect(lab.environment.externalTargets).toBe(false);
      expect(lab.environment.arbitraryCommands).toBe(false);
      expect(lab.rulesOfEngagement.length).toBeGreaterThanOrEqual(3);
      expect(lab.debrief.length).toBeGreaterThan(100);
      const type = lab.environment.type;
      if (type.includes("simulation")) counts.interactive += 1;
      if (type === "artifact-analysis") counts.artifact += 1;
      if (type === "secure-configuration") counts.configuration += 1;
      if (type === "awareness-simulation") counts.awareness += 1;
      if (type === "career-simulation") counts.career += 1;
      if (type.includes("docker") || type.includes("microvm"))
        counts.executable += 1;
    }
    expect(labItems).toHaveLength(80);
    expect(counts).toMatchObject({
      interactive: 40,
      artifact: 20,
      configuration: 20,
      awareness: 10,
      career: 10,
      executable: 0,
    });
  });
});
