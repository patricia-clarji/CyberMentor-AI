import type { ProgressState } from "../types";
const empty: ProgressState = {
  completedLessons: [],
  enrolledCourses: ["course-1", "course-4"],
  bookmarks: [],
  notes: {},
  quizScores: {},
  labCompleted: [],
  labBookmarks: [],
  labReflections: {},
  labAttempts: {},
  projectCompleted: [],
  projectSubmissions: {},
  skillStates: {},
  dismissedRecommendations: [],
};
export function loadProgress(): ProgressState {
  try {
    const value = JSON.parse(
      localStorage.getItem("cm-progress") || "{}",
    ) as Partial<ProgressState>;
    return {
      completedLessons: strings(value.completedLessons),
      enrolledCourses: strings(value.enrolledCourses, empty.enrolledCourses),
      bookmarks: strings(value.bookmarks),
      notes: recordOf(value.notes, "string") as Record<string, string>,
      quizScores: recordOf(value.quizScores, "number") as Record<
        string,
        number
      >,
      labCompleted: strings(value.labCompleted),
      labBookmarks: strings(value.labBookmarks),
      labReflections: recordOf(value.labReflections, "string") as Record<
        string,
        string
      >,
      labAttempts: labAttempts(value.labAttempts),
      projectCompleted: strings(value.projectCompleted),
      projectSubmissions: recordOf(
        value.projectSubmissions,
        "string",
      ) as Record<string, string>,
      skillStates: skillStates(value.skillStates),
      dismissedRecommendations: strings(value.dismissedRecommendations),
    };
  } catch {
    return empty;
  }
}
function labAttempts(value: unknown): ProgressState["labAttempts"] {
  if (!value || typeof value !== "object" || Array.isArray(value)) return {};
  return Object.fromEntries(
    Object.entries(value).filter(([, item]) => {
      if (!item || typeof item !== "object" || Array.isArray(item))
        return false;
      const attempt = item as Record<string, unknown>;
      return (
        typeof attempt.correct === "number" &&
        attempt.correct >= 0 &&
        typeof attempt.incorrect === "number" &&
        attempt.incorrect >= 0 &&
        typeof attempt.hintsUsed === "number" &&
        attempt.hintsUsed >= 0 &&
        typeof attempt.lastAttemptAt === "string"
      );
    }),
  ) as ProgressState["labAttempts"];
}
function skillStates(value: unknown): ProgressState["skillStates"] {
  if (!value || typeof value !== "object" || Array.isArray(value)) return {};
  return Object.fromEntries(
    Object.entries(value).filter(([, item]) => {
      if (!item || typeof item !== "object" || Array.isArray(item))
        return false;
      const state = item as Record<string, unknown>;
      return (
        typeof state.masteryEstimate === "number" &&
        state.masteryEstimate >= 0 &&
        state.masteryEstimate <= 1 &&
        typeof state.masteryConfidence === "number" &&
        state.masteryConfidence >= 0 &&
        state.masteryConfidence <= 1 &&
        typeof state.evidenceCount === "number" &&
        state.evidenceCount >= 0
      );
    }),
  ) as ProgressState["skillStates"];
}
function strings(value: unknown, fallback: string[] = []) {
  return Array.isArray(value) && value.every((item) => typeof item === "string")
    ? value
    : fallback;
}
function recordOf(value: unknown, kind: "string" | "number") {
  if (!value || typeof value !== "object" || Array.isArray(value)) return {};
  return Object.fromEntries(
    Object.entries(value).filter(([, item]) => typeof item === kind),
  );
}
export function saveProgress(p: ProgressState) {
  localStorage.setItem("cm-progress", JSON.stringify(p));
}
export function toggle(list: string[], id: string) {
  return list.includes(id) ? list.filter((x) => x !== id) : [...list, id];
}
