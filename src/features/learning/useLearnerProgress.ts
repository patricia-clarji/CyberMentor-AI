import { useQuery } from "@tanstack/react-query";
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type Dispatch,
  type SetStateAction,
} from "react";
import { apiFetch } from "../../lib/api-client";
import type { ProgressState } from "../../types";

type Dashboard = {
  enrollments: { course_publication_id: string }[];
  lesson_progress: {
    lesson_publication_id: string;
    status: string;
  }[];
  notes: {
    lesson_publication_id: string;
    body: string;
  }[];
  bookmarks: {
    resource_type: string;
    resource_id: string;
  }[];
  skills: {
    skillId: string;
    mastery: number;
    confidence: number;
    nextReviewAt?: string;
  }[];
};

const emptyProgress: ProgressState = {
  completedLessons: [],
  enrolledCourses: [],
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

function mapDashboard(dashboard: Dashboard): ProgressState {
  return {
    ...emptyProgress,
    completedLessons: dashboard.lesson_progress
      .filter((item) => item.status === "completed")
      .map((item) => item.lesson_publication_id),
    enrolledCourses: dashboard.enrollments.map(
      (item) => item.course_publication_id,
    ),
    notes: Object.fromEntries(
      dashboard.notes.map((item) => [item.lesson_publication_id, item.body]),
    ),
    bookmarks: dashboard.bookmarks
      .filter((item) => item.resource_type === "lesson")
      .map((item) => item.resource_id),
    skillStates: Object.fromEntries(
      dashboard.skills.map((item) => [
        item.skillId,
        {
          masteryEstimate: item.mastery,
          masteryConfidence: item.confidence,
          evidenceCount: 0,
          nextReviewAt: item.nextReviewAt,
        },
      ]),
    ),
  };
}

export function useLearnerProgress(): {
  progress: ProgressState;
  setProgress: Dispatch<SetStateAction<ProgressState>>;
  loading: boolean;
  error: Error | null;
} {
  const query = useQuery({
    queryKey: ["learner-dashboard"],
    queryFn: () => apiFetch<Dashboard>("/api/v1/learning/dashboard"),
    staleTime: 10_000,
  });
  const [localProgress, setProgressState] = useState<ProgressState | null>(null);
  const [syncError, setSyncError] = useState<Error | null>(null);
  const progress = localProgress ?? (query.data ? mapDashboard(query.data) : emptyProgress);
  const dirty = useRef(false);
  const revision = useRef(0);
  const saving = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (!dirty.current) return;
    if (saving.current) clearTimeout(saving.current);
    const savingRevision = revision.current;
    saving.current = setTimeout(() => {
      void apiFetch("/api/v1/learning/progress-snapshot", {
        method: "PUT",
        body: JSON.stringify({
          enrolled_courses: progress.enrolledCourses,
          completed_lessons: progress.completedLessons,
          notes: progress.notes,
          lesson_bookmarks: progress.bookmarks,
        }),
      })
        .then(() => {
          if (savingRevision === revision.current) dirty.current = false;
          setSyncError(null);
        })
        .catch((error: Error) => setSyncError(error));
    }, 300);
    return () => {
      if (saving.current) clearTimeout(saving.current);
    };
  }, [
    progress.bookmarks,
    progress.completedLessons,
    progress.enrolledCourses,
    progress.notes,
  ]);
  const setProgress = useCallback<Dispatch<SetStateAction<ProgressState>>>(
    (update) => {
      dirty.current = true;
      revision.current += 1;
      setProgressState((current) =>
        typeof update === "function"
          ? update(current ?? progress)
          : update,
      );
    },
    [progress],
  );
  return {
    progress,
    setProgress,
    loading: query.isLoading,
    error: query.error || syncError,
  };
}
