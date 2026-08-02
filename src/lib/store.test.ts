// @vitest-environment node
import { beforeEach, describe, expect, it, vi } from "vitest";
import { loadProgress, saveProgress, toggle } from "./store";

const values = new Map<string, string>();
vi.stubGlobal("localStorage", {
  get length() {
    return values.size;
  },
  clear: () => values.clear(),
  getItem: (key: string) => values.get(key) ?? null,
  key: (index: number) => [...values.keys()][index] ?? null,
  removeItem: (key: string) => values.delete(key),
  setItem: (key: string, value: string) => values.set(key, value),
});

describe("progress persistence", () => {
  beforeEach(() => localStorage.clear());
  it("round-trips valid local progress", () => {
    const progress = loadProgress();
    progress.completedLessons.push("lesson-1");
    saveProgress(progress);
    expect(loadProgress().completedLessons).toContain("lesson-1");
  });
  it("rejects malformed local state instead of crashing the application", () => {
    localStorage.setItem(
      "cm-progress",
      JSON.stringify({
        completedLessons: null,
        notes: [],
        labCompleted: "all",
      }),
    );
    const progress = loadProgress();
    expect(progress.completedLessons).toEqual([]);
    expect(progress.notes).toEqual({});
    expect(progress.labCompleted).toEqual([]);
  });
  it("toggles identifiers without duplicates", () => {
    expect(toggle(toggle([], "a"), "a")).toEqual([]);
  });
});
