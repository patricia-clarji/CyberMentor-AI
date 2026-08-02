// @vitest-environment node
import { beforeEach, describe, expect, it } from "vitest";
import {
  authorizeLabVerification,
  clearLabSessionsForTests,
  getLabSession,
  launchLab,
  recordLabVerification,
  revealLabHint,
  transitionLab,
} from "./lab-runtime.mjs";

const labBank = [
  {
    id: "range-lab-1",
    publicationStatus: "published",
    verificationStatus: "verified",
    artifact: {
      environmentStatus: "usable",
      environment: { expirationMinutes: 90 },
      hints: [
        { level: 1, label: "Reminder", text: "Read the question." },
        { level: 2, label: "Concept", text: "Correlate the records." },
      ],
    },
  },
];
const owner = "learner_12345678";

describe("server-owned lab runtime", () => {
  beforeEach(clearLabSessionsForTests);

  it("launches and resumes one owned usable instance", () => {
    const launched = launchLab(owner, "range-lab-1", labBank);
    expect(launched.status).toBe(201);
    expect(launched.body.instance.status).toBe("active");
    const resumed = launchLab(owner, "range-lab-1", labBank);
    expect(resumed.status).toBe(200);
    expect(resumed.body.resumed).toBe(true);
    expect(resumed.body.instance.id).toBe(launched.body.instance.id);
  });

  it("denies cross-owner reads and submissions without disclosing the instance", () => {
    const launched = launchLab(owner, "range-lab-1", labBank).body.instance;
    expect(getLabSession(launched.id, "attacker_123456").status).toBe(404);
    expect(
      authorizeLabVerification(launched.id, "attacker_123456", "range-lab-1")
        .status,
    ).toBe(404);
  });

  it("reveals hints progressively and blocks evidence while paused", () => {
    const instance = launchLab(owner, "range-lab-1", labBank).body.instance;
    expect(revealLabHint(instance.id, owner, 2, labBank).status).toBe(400);
    expect(revealLabHint(instance.id, owner, 1, labBank).body.hint.level).toBe(
      1,
    );
    expect(revealLabHint(instance.id, owner, 2, labBank).body.hint.level).toBe(
      2,
    );
    expect(
      transitionLab(instance.id, owner, "pause").body.instance.status,
    ).toBe("paused");
    expect(
      authorizeLabVerification(instance.id, owner, "range-lab-1").status,
    ).toBe(409);
    expect(
      transitionLab(instance.id, owner, "resume").body.instance.status,
    ).toBe("active");
  });

  it("records wrong and correct attempts, then resets and closes", () => {
    const instance = launchLab(owner, "range-lab-1", labBank).body.instance;
    const authorized = authorizeLabVerification(
      instance.id,
      owner,
      "range-lab-1",
    );
    expect(
      recordLabVerification(authorized.session, false).attempts,
    ).toHaveLength(1);
    const completed = recordLabVerification(authorized.session, true);
    expect(completed.completed).toBe(true);
    expect(completed.status).toBe("completed");
    const reset = transitionLab(instance.id, owner, "reset");
    expect(reset.body.instance).toMatchObject({
      status: "active",
      completed: false,
      hintsUsed: 0,
      resetCount: 1,
    });
    expect(reset.body.instance.attempts).toHaveLength(0);
    expect(transitionLab(instance.id, owner, "close").status).toBe(200);
    expect(getLabSession(instance.id, owner).status).toBe(404);
  });
});
