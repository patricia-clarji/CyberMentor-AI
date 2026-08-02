// @vitest-environment node
import { spawnSync } from "node:child_process";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import {
  createRollbackActivation,
  draftContentHash,
  normalizeText,
  safeSource,
  validateLabDefinitions,
  validatePublishedGraph,
  validateWorkspace,
} from "./content-pipeline.mjs";

describe("authoritative content pipeline", () => {
  it("normalizes evidence before hashing and matching", () => {
    expect(normalizeText("  risk\n\tmanagement  ")).toBe("risk management");
  });

  it("rejects unencrypted and non-allowlisted source URLs", () => {
    expect(
      safeSource({
        id: "unsafe-source",
        publisher: "Example",
        url: "http://attacker.example/source",
        allowedHosts: ["trusted.example"],
        reproductionPolicy: "Metadata only",
      }),
    ).toEqual(
      expect.arrayContaining([
        "source URL must use HTTPS",
        "host attacker.example is not allowlisted",
      ]),
    );
  });

  it("invalidates approvals on content edits but not workflow status changes", () => {
    const draft = {
      id: "lesson",
      status: "draft",
      updatedAt: "2026-01-01",
      claims: [{ id: "one", statement: "Original verified statement." }],
    };
    const original = draftContentHash(draft);
    expect(
      draftContentHash({
        ...draft,
        status: "approved",
        updatedAt: "2026-02-01",
      }),
    ).toBe(original);
    expect(
      draftContentHash({
        ...draft,
        claims: [{ id: "one", statement: "Changed statement." }],
      }),
    ).not.toBe(original);
  });

  it("validates the cited fixture against the stored source snapshot", async () => {
    const report = await validateWorkspace({
      onlyDraftId: "pipeline-validation-fixture",
    });
    expect(report.summary.errors).toBe(0);
    expect(report.summary.skillsRegistered).toBe(23);
    expect(report.summary.publicationsChecked).toBe(488);
  }, 120_000);

  it("rejects duplicate publication IDs and invalid learning references", () => {
    const issues = validatePublishedGraph([
      {
        id: "course-one",
        artifactType: "course",
        artifact: { moduleIds: ["missing-module"] },
      },
      {
        id: "course-one",
        artifactType: "module",
        artifact: { lessonIds: ["missing-lesson"] },
      },
    ]);
    expect(issues.map((item) => item.code)).toEqual(
      expect.arrayContaining([
        "DUPLICATE_PUBLICATION_ID",
        "INVALID_MODULE_REFERENCE",
        "INVALID_LESSON_REFERENCE",
      ]),
    );
  });

  it("rejects unsafe lab tools and incomplete hint ladders", () => {
    const issues = validateLabDefinitions(
      {
        schemaVersion: 1,
        labs: [
          {
            id: "soc-lab-invalid",
            labType: "guided",
            availableTools: ["bash"],
            hints: [{ level: 1 }],
            linkedSkills: ["unknown"],
            virtualEnvironment: { files: [{ path: "relative.log" }] },
          },
        ],
      },
      new Set(["alert-triage"]),
    );
    expect(issues.map((item) => item.code)).toEqual(
      expect.arrayContaining([
        "MISSING_LAB_FIELD",
        "UNSAFE_LAB_TOOL",
        "INVALID_LAB_HINT_LADDER",
        "UNKNOWN_LAB_SKILL",
        "INVALID_VIRTUAL_FILE_PATH",
      ]),
    );
  });

  it("blocks publication before independent human approvals", () => {
    const result = spawnSync(
      process.execPath,
      [
        resolve("scripts/content-pipeline.mjs"),
        "publish",
        "--draft",
        "pipeline-validation-fixture",
      ],
      { encoding: "utf8" },
    );
    expect(result.status).toBe(1);
    expect(result.stderr).toContain(
      "draft must have all independent human approvals before publication",
    );
  });

  it("reactivates an immutable version without mutating its content", () => {
    const target = {
      id: "lesson-one",
      contentVersion: "1.0.0",
      contentHash: "a".repeat(64),
      artifact: { blocks: [{ id: "one" }] },
    };
    const original = structuredClone(target);
    const activated = createRollbackActivation(
      target,
      { contentVersion: "1.1.0" },
      {
        publisher: "publisher-one",
        reason: "Verified regression",
        now: new Date("2026-07-19T12:00:00.000Z"),
      },
    );
    expect(target).toEqual(original);
    expect(activated.contentVersion).toBe("1.0.0");
    expect(activated.contentHash).toBe(target.contentHash);
    expect(activated.activation).toEqual({
      activatedAt: "2026-07-19T12:00:00.000Z",
      activatedBy: "publisher-one",
      reason: "Verified regression",
      replacedVersion: "1.1.0",
    });
  });
});
