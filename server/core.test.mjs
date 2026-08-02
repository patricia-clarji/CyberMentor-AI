// @vitest-environment node
import { describe, expect, it } from "vitest";
import {
  allowedOrigin,
  assessProjectSubmission,
  gradeCheck,
  legacyLabs,
  securityHeaders,
  verifyLab,
} from "./core.mjs";
const question = {
  id: "verified-question",
  contentVersion: "1.0.0",
  verificationStatus: "verified",
  publicationStatus: "published",
  artifact: {
    options: ["Weak", "Defensible", "Unsafe"],
    correctOption: 1,
    explanation: "The defensible option uses verified evidence.",
    distractorExplanations: {
      0: "This option lacks evidence.",
      2: "This option violates the approved scope.",
    },
    skillTags: ["security-foundations"],
    assessmentUse: "quiz",
  },
};
const lab = {
  id: "verified-lab",
  contentVersion: "1.0.0",
  verificationStatus: "verified",
  publicationStatus: "published",
  artifact: {
    validationLogic: {
      type: "normalized-equals",
      expectedValue: "bounded evidence",
    },
    skillTags: ["evidence-analysis"],
  },
};
const project = {
  id: "verified-project",
  contentVersion: "1.0.0",
  verificationStatus: "verified",
  publicationStatus: "published",
  artifact: {
    deliverables: ["Report", "Evidence appendix"],
    minimumEvidenceLength: 40,
    rubric: [{ criterion: "Evidence" }],
    skillTags: ["case-documentation"],
  },
};
describe("server security boundary", () => {
  it("grades without returning an answer key", () => {
    const result = gradeCheck("verified-question", 1, [question]);
    expect(result.body.correct).toBe(true);
    expect(JSON.stringify(result)).not.toMatch(/expected|answer/i);
  });
  it("rejects malformed assessment submissions", () =>
    expect(gradeCheck("../answer-key", 1, [question]).status).toBe(404));
  it("blocks every legacy assessment and lab by default", () => {
    expect(gradeCheck("course-1-m1-l1-check", 1).status).toBe(404);
    expect(verifyLab(legacyLabs[0].id, legacyLabs[0].expected).status).toBe(
      404,
    );
  });
  it("verifies evidence and rejects guesses", () => {
    expect(
      verifyLab("verified-lab", " BOUNDED   EVIDENCE ", [lab]).body.correct,
    ).toBe(true);
    expect(verifyLab("verified-lab", "guess", [lab]).body.correct).toBe(false);
  });
  it("checks a published project submission without exposing evaluator evidence", () => {
    const accepted = assessProjectSubmission(
      "verified-project",
      "A sufficiently detailed evidence summary with a verified outcome.",
      ["Report", "Evidence appendix"],
      [project],
    );
    expect(accepted.body.accepted).toBe(true);
    expect(JSON.stringify(accepted.body)).not.toMatch(/expectedEvidence/);
    expect(
      assessProjectSubmission(
        "verified-project",
        "short",
        ["Report"],
        [project],
      ).body.accepted,
    ).toBe(false);
  });
  it("restricts origins and emits defensive headers", () => {
    expect(allowedOrigin("https://evil.example", "cybermentor.example")).toBe(
      false,
    );
    expect(
      allowedOrigin("https://cybermentor.example", "cybermentor.example"),
    ).toBe(true);
    const headers = securityHeaders("test");
    expect(headers["Content-Security-Policy"]).toContain(
      "frame-ancestors 'none'",
    );
    expect(headers["X-Request-ID"]).toBe("test");
  });
});
