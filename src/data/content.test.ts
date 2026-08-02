// @vitest-environment node
import { describe, it, expect } from "vitest";
import { courses, domains, tracks } from "./courses";
describe("curriculum integrity", () => {
  it("retains 12 explicitly unverified migration-planning shells", () => {
    expect(courses).toHaveLength(12);
    for (const c of courses) {
      expect(c.modules.length).toBeGreaterThanOrEqual(4);
      expect(c.modules.flatMap((m) => m.lessons).length).toBeGreaterThanOrEqual(
        12,
      );
      expect(
        c.modules
          .flatMap((m) => m.lessons)
          .every((lesson) => lesson.verificationStatus === "legacy-unverified"),
      ).toBe(true);
    }
  });
  it("covers all requested domains and viable tracks", () => {
    expect(domains).toHaveLength(50);
    expect(tracks.length).toBeGreaterThanOrEqual(5);
  });
  it("labels legacy lesson references without claiming verification", () => {
    const approvedPublishers = new Set([
      "NIST",
      "CISA",
      "OWASP Foundation",
      "MITRE",
      "Python Software Foundation",
      "The Linux Kernel Organization",
    ]);
    for (const l of courses
      .flatMap((c) => c.modules)
      .flatMap((m) => m.lessons)) {
      expect(l.references[0].url).toMatch(/^https:\/\//);
      expect(l.references[0].accessed).toMatch(/^\d{4}-/);
      expect(approvedPublishers.has(l.references[0].publisher)).toBe(true);
      expect(l.verificationStatus).toBe("legacy-unverified");
      expect(l.contentVersion).toBe("0.0.0-legacy");
      expect(l.retrievedAt).toMatch(/^\d{4}-/);
    }
  });
  it("uses unique stable IDs and keeps answer keys out of client content", () => {
    const lessons = courses.flatMap((course) =>
      course.modules.flatMap((module) => module.lessons),
    );
    const ids = lessons.map((lesson) => lesson.id);
    expect(new Set(ids).size).toBe(ids.length);
    expect(JSON.stringify(courses)).not.toMatch(/"answer"\s*:/);
    for (const lesson of lessons) {
      expect(lesson.check.id).toMatch(/^course-\d+-m\d+-l\d+-check$/);
      expect(lesson.content.join(" ").split(/\s+/).length).toBeGreaterThan(100);
    }
  });
});
