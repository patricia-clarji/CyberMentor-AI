export type Difficulty = "Beginner" | "Intermediate" | "Advanced";
export type Course = {
  id: string;
  title: string;
  shortTitle: string;
  category: string;
  description: string;
  difficulty: Difficulty;
  color: string;
  icon: string;
  skills: string[];
  modules: Module[];
  project: string;
};
export type Module = {
  id: string;
  title: string;
  description: string;
  lessons: Lesson[];
  quiz: QuizQuestion[];
};
export type Lesson = {
  id: string;
  title: string;
  contentVersion: string;
  verificationStatus: "legacy-unverified" | "verified";
  retrievedAt: string;
  minutes: number;
  objectives: string[];
  content: string[];
  blocks?: ContentBlock[];
  keyTerms: string[];
  example: string;
  check: { id: string; question: string; options: string[] };
  references: Reference[];
};
export type ContentBlock = {
  id: string;
  type:
    | "heading"
    | "paragraph"
    | "objective-list"
    | "definition"
    | "callout"
    | "warning"
    | "diagram"
    | "image"
    | "comparison-table"
    | "code"
    | "terminal"
    | "packet-breakdown"
    | "log-sample"
    | "forensic-artifact"
    | "worked-example"
    | "misconception"
    | "knowledge-check"
    | "interactive-decision"
    | "practice-launch"
    | "lab-launch"
    | "project-milestone"
    | "reference-list"
    | "summary";
  heading?: string;
  text?: string;
  body?: string;
  code?: string;
  language?: string;
  alt?: string;
  asset?: string;
  items?: string[];
  columns?: string[];
  rows?: string[][];
};
export type Reference = {
  title: string;
  publisher: string;
  url: string;
  accessed: string;
};
export type QuizQuestion = { id: string; question: string; options: string[] };
export type Track = {
  id: string;
  title: string;
  description: string;
  duration: string;
  level: string;
  color: string;
  courseIds: string[];
  roles: string[];
};
export type ProgressState = {
  completedLessons: string[];
  enrolledCourses: string[];
  bookmarks: string[];
  notes: Record<string, string>;
  quizScores: Record<string, number>;
  labCompleted: string[];
  labBookmarks: string[];
  labReflections: Record<string, string>;
  labAttempts: Record<
    string,
    {
      correct: number;
      incorrect: number;
      hintsUsed: number;
      lastAttemptAt: string;
    }
  >;
  projectCompleted: string[];
  projectSubmissions: Record<string, string>;
  skillStates: Record<string, LearnerSkillState>;
  dismissedRecommendations: string[];
};
export type LearnerSkillState = {
  masteryEstimate: number;
  masteryConfidence: number;
  evidenceCount: number;
  lastPracticedAt?: string;
  nextReviewAt?: string;
  recentMistakePatterns?: string[];
};
