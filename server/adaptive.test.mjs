// @vitest-environment node
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import {
  masteryWithRecency,
  nextHint,
  recommendActivities,
  selectDiagnosticQuestion,
  updateMastery,
} from "./adaptive.mjs";

const state = (masteryEstimate, masteryConfidence = 0.85, extra = {}) => ({
  masteryEstimate,
  masteryConfidence,
  evidenceCount: 5,
  lastPracticedAt: "2026-07-18T00:00:00.000Z",
  ...extra,
});

const activity = (
  id,
  title,
  skillTags,
  difficulty,
  activityType,
  extra = {},
) => ({
  id,
  title,
  skillTags,
  difficulty,
  activityType,
  estimatedMinutes: 20,
  prerequisites: [],
  hints: ["Concept reminder", "Inspection area", "Partial strategy"],
  publicationStatus: "published",
  verificationStatus: "verified",
  ...extra,
});

const pool = [
  activity(
    "networking-basics",
    "Networking foundations review",
    ["networking"],
    "foundation",
    "lesson",
  ),
  activity(
    "advanced-packets",
    "Advanced packet troubleshooting",
    ["networking"],
    "advanced",
    "scenario",
  ),
  activity(
    "linux-foundations",
    "Linux Foundations",
    ["linux"],
    "guided",
    "lesson",
  ),
  activity(
    "linux-permissions-practice",
    "Guided Linux permissions practice",
    ["linux", "linux-permissions"],
    "guided",
    "lab",
  ),
  activity(
    "linux-networking-bridge",
    "Linux networking through TCP/IP",
    ["networking", "linux"],
    "guided",
    "explanation-variant",
  ),
  activity(
    "security-practical",
    "Guided defensive investigation",
    ["security-foundations"],
    "standard",
    "lab",
  ),
  activity(
    "security-reading",
    "Security concept review",
    ["security-foundations"],
    "standard",
    "lesson",
  ),
  activity(
    "expert-scenario",
    "Expert network investigation",
    ["networking"],
    "expert-challenge",
    "scenario",
  ),
  activity(
    "network-retention",
    "Short networking retention check",
    ["networking"],
    "standard",
    "retention",
    { estimatedMinutes: 8 },
  ),
  activity(
    "permissions-alternative",
    "Visual permissions explanation",
    ["linux-permissions"],
    "foundation",
    "explanation-variant",
  ),
  {
    ...activity(
      "unreviewed",
      "Unreviewed generated exercise",
      ["linux"],
      "guided",
      "lab",
    ),
    verificationStatus: "draft",
    publicationStatus: "draft",
  },
];

describe("versioned skill graph", () => {
  it("defines complete, unique, resolvable draft taxonomy nodes", async () => {
    const graph = JSON.parse(
      await readFile(resolve("content/adaptive/skills.json"), "utf8"),
    );
    expect(graph.status).toBe("draft-taxonomy");
    expect(graph.skills).toHaveLength(23);
    const ids = new Set(graph.skills.map((skill) => skill.id));
    expect(ids.size).toBe(graph.skills.length);
    for (const skill of graph.skills) {
      expect(skill.description.length).toBeGreaterThanOrEqual(20);
      expect(skill.difficulty).toMatch(
        /^(foundation|guided|standard|advanced|expert-challenge)$/,
      );
      for (const linked of [skill.parentSkillId, ...skill.prerequisites].filter(
        Boolean,
      )) {
        expect(ids.has(linked)).toBe(true);
        expect(linked).not.toBe(skill.id);
      }
    }
  });
});

describe("transparent mastery model", () => {
  it("does not infer high confidence from one answer or passive opening", () => {
    const oneAnswer = updateMastery(state(0, 0, { evidenceCount: 0 }), [
      {
        sourceType: "quiz",
        sourceId: "q1",
        score: 1,
        independenceLevel: 1,
        attempts: 1,
        hintsUsed: 0,
        occurredAt: "2026-07-19T00:00:00.000Z",
      },
      { sourceType: "lesson-open", sourceId: "l1", score: 1 },
    ]);
    expect(oneAnswer.evidenceCount).toBe(1);
    expect(oneAnswer.masteryConfidence).toBeLessThan(0.2);
  });

  it("weights independent practical evidence above lesson checks", () => {
    const initial = state(0, 0, { evidenceCount: 0 });
    const lesson = updateMastery(initial, [
      {
        sourceType: "lesson-check",
        sourceId: "check",
        score: 1,
        independenceLevel: 1,
        attempts: 1,
        hintsUsed: 0,
      },
    ]);
    const lab = updateMastery(initial, [
      {
        sourceType: "lab",
        sourceId: "lab",
        score: 1,
        independenceLevel: 1,
        attempts: 1,
        hintsUsed: 0,
      },
    ]);
    expect(lab.masteryConfidence).toBeGreaterThan(lesson.masteryConfidence);
  });
});

describe("required adaptive profiles", () => {
  it("gives a new learner approved foundation activities", () => {
    const recommendations = recommendActivities({
      skills: {},
      activities: pool,
    });
    expect(recommendations.length).toBeGreaterThan(0);
    expect(
      recommendations.every((item) => item.difficulty === "foundation"),
    ).toBe(true);
    expect(
      recommendations.some((item) => item.activityId === "unreviewed"),
    ).toBe(false);
  });

  it("PROFILE A: strong networking, weak Linux", () => {
    const skills = {
      networking: state(0.86),
      linux: state(0.34),
      "web-fundamentals": state(0.7),
      "security-foundations": state(0.62),
    };
    const recommendations = recommendActivities({
      skills,
      activities: pool,
      limit: 8,
    });
    const ids = recommendations.map((item) => item.activityId);
    expect(ids).toContain("linux-foundations");
    expect(ids[0]).not.toBe("networking-basics");
    expect(ids).toContain("advanced-packets");
    expect(ids).toContain("linux-networking-bridge");
    expect(
      recommendations.find((item) => item.activityId === "unreviewed"),
    ).toBe(undefined);
    expect(
      recommendations.find(
        (item) => item.activityId === "linux-permissions-practice",
      )?.hintStartLevel,
    ).toBeGreaterThan(0);
    expect(
      recommendActivities({
        skills: { ...skills, linux: state(0.78) },
        activities: pool,
        limit: 10,
      }).find((item) => item.activityId === "linux-permissions-practice")
        ?.hintStartLevel,
    ).toBe(0);
  });

  it("PROFILE B: strong theory, weak practical work", () => {
    const recommendations = recommendActivities({
      skills: {
        "security-foundations": state(0.8, 0.8, {
          recentMistakePatterns: ["weak-practical-work"],
        }),
      },
      activities: pool,
    });
    expect(recommendations[0].activityId).toBe("security-practical");
    expect(recommendations[0].reason).toMatch(/practical evidence/i);
  });

  it("PROFILE C: weak theory, strong tool memorization", () => {
    const recommendations = recommendActivities({
      skills: {
        "security-foundations": state(0.45, 0.7, {
          recentMistakePatterns: ["command-recall-only"],
        }),
      },
      activities: pool,
    });
    expect(recommendations[0].activityId).toBe("security-reading");
    expect(recommendations[0].reason).toMatch(/conceptual reasoning/i);
  });

  it("PROFILE D: advanced learner", () => {
    const skills = { networking: state(0.93, 0.95) };
    const recommendations = recommendActivities({
      skills,
      activities: pool,
    });
    expect(recommendations[0].activityId).toBe("expert-scenario");
    expect(recommendations[0].hintStartLevel).toBe(0);
    expect(recommendations[0].difficulty).toBe("expert-challenge");
  });

  it("PROFILE E: inactive learner returning after two months", () => {
    const now = new Date("2026-07-19T00:00:00.000Z");
    const oldState = state(0.82, 0.9, {
      lastPracticedAt: "2026-05-19T00:00:00.000Z",
    });
    const adjusted = masteryWithRecency(oldState, now);
    expect(adjusted.masteryEstimate).toBeGreaterThan(0.5);
    const recommendations = recommendActivities({
      skills: { networking: oldState },
      activities: pool,
      now,
    });
    expect(recommendations[0].activityId).toBe("network-retention");
    expect(recommendations[0].reason).toMatch(/prior progress is preserved/i);
  });

  it("PROFILE F: repeated prerequisite failure", () => {
    const recommendations = recommendActivities({
      skills: {
        linux: state(0.3),
        "linux-permissions": state(0.2, 0.7),
      },
      activities: pool,
      recentMistakes: ["linux-permissions"],
      failureCounts: { "linux-permissions": 4 },
    });
    const targeted = recommendations.filter((item) =>
      ["permissions-alternative", "linux-permissions-practice"].includes(
        item.activityId,
      ),
    );
    expect(targeted).toHaveLength(2);
    expect(targeted.every((item) => item.instructorFlag)).toBe(true);
    expect(targeted[0].reason).toMatch(/instructor review flag/i);
  });
});

describe("bounded diagnostic and hint selection", () => {
  const questions = ["foundation", "standard", "advanced"].map(
    (difficulty) => ({
      id: `diagnostic-${difficulty}`,
      skillTags: ["networking"],
      difficulty,
      assessmentUse: "diagnostic",
      publicationStatus: "published",
      verificationStatus: "verified",
    }),
  );

  it("branches from medium toward easier or harder approved questions", () => {
    expect(
      selectDiagnosticQuestion({
        questions,
        skillId: "networking",
      })?.difficulty,
    ).toBe("standard");
    expect(
      selectDiagnosticQuestion({
        questions,
        skillId: "networking",
        recentResults: [
          { sourceId: "x", score: 0 },
          { sourceId: "y", score: 0.2 },
        ],
      })?.difficulty,
    ).toBe("foundation");
    expect(
      selectDiagnosticQuestion({
        questions,
        skillId: "networking",
        recentResults: [
          { sourceId: "x", score: 1 },
          { sourceId: "y", score: 0.9 },
        ],
      })?.difficulty,
    ).toBe("advanced");
  });

  it("uses only stored progressive hints", () => {
    const target = pool.find(
      (item) => item.id === "linux-permissions-practice",
    );
    expect(nextHint(target, [], { linux: state(0.2) })).toBe("Inspection area");
    expect(nextHint(target, ["one", "two"], { linux: state(0.8) })).toBe(
      "Partial strategy",
    );
  });
});
