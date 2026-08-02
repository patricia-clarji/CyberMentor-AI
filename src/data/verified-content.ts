import type { ContentBlock, Course, Lesson, Reference } from "../types";

export type PublishedLesson = {
  courseId: string;
  moduleId: string;
  lessonId: string;
  title: string;
  minutes: number;
  objectives: string[];
  blocks: ContentBlock[];
  keyTerms: string[];
  workedExample: string;
  check: { id: string; question: string; options: string[] };
};

export type LessonPublication = {
  id: string;
  artifactType: "lesson";
  verificationStatus: "verified";
  publicationStatus: "published";
  contentVersion: string;
  publishedAt: string;
  artifact: PublishedLesson;
  references: {
    title: string;
    publisher: string;
    url: string;
    retrievedAt: string;
  }[];
};

function references(publication: LessonPublication): Reference[] {
  const unique = new Map<string, Reference>();
  for (const reference of publication.references)
    unique.set(reference.url, {
      title: reference.title,
      publisher: reference.publisher,
      url: reference.url,
      accessed: reference.retrievedAt.slice(0, 10),
    });
  return [...unique.values()];
}

function blockText(block: ContentBlock) {
  if ("text" in block && typeof block.text === "string") return block.text;
  if ("body" in block && typeof block.body === "string") return block.body;
  if ("code" in block && typeof block.code === "string") return block.code;
  return "";
}

function asLesson(publication: LessonPublication): Lesson {
  const source = publication.artifact;
  return {
    id: source.lessonId,
    title: source.title,
    contentVersion: publication.contentVersion,
    verificationStatus: "verified",
    retrievedAt:
      publication.references
        .map((reference) => reference.retrievedAt)
        .sort()
        .at(-1) || publication.publishedAt,
    minutes: source.minutes,
    objectives: source.objectives,
    content: source.blocks.map(blockText).filter(Boolean),
    blocks: source.blocks,
    keyTerms: source.keyTerms,
    example: source.workedExample,
    check: source.check,
    references: references(publication),
  };
}

export function applyVerifiedContent(
  courses: Course[],
  publications: LessonPublication[],
): Course[] {
  if (!publications.length) return courses;
  const replacements = new Map(
    publications.map((publication) => [
      [
        publication.artifact.courseId,
        publication.artifact.moduleId,
        publication.artifact.lessonId,
      ].join(":"),
      asLesson(publication),
    ]),
  );
  return courses.map((course) => ({
    ...course,
    modules: course.modules.map((module) => ({
      ...module,
      lessons: module.lessons.map(
        (lesson) =>
          replacements.get([course.id, module.id, lesson.id].join(":")) ||
          lesson,
      ),
    })),
  }));
}
