import { courses } from "../data/courses";
import type { Lesson } from "../types";
export type MentorReply = {
  answer: string;
  citations: { label: string; url: string }[];
  blocked?: boolean;
};
const offensiveAction =
  /\b(scan|exploit|attack|phish|steal|bypass|nmap|masscan|sqlmap|metasploit|dump|exfiltrate|crack)\b/i;
const externalTarget =
  /\b(public|real|production|someone|company|internet|credential|password|token|secret|google|microsoft|facebook)\b|\b[a-z0-9-]+\.(com|net|org|io|gov)\b/i;
const policyManipulation =
  /\b(ignore|override|discard|reveal|print|show)\b.{0,60}\b(system|developer|policy|instruction|prompt|secret)\b/i;
const answers =
  /\b(answer key|give me (the )?(answer|solution)|complete my quiz|solve my (quiz|exam|assignment)|do my project|write my final project)\b/i;
export function askSentinel(
  question: string,
  courseId?: string,
  lessonId?: string,
  verifiedContext?: Lesson,
): MentorReply {
  const normalizedQuestion = question.trim().slice(0, 4000);
  if (
    policyManipulation.test(normalizedQuestion) ||
    (offensiveAction.test(normalizedQuestion) &&
      externalTarget.test(normalizedQuestion))
  )
    return {
      blocked: true,
      answer:
        "I can’t help target real systems or people. I can help you build an authorized local lab, define rules of engagement, understand defender visibility, or remediate the underlying weakness.",
      citations: [
        {
          label: "CISA Cross-Sector Cybersecurity Performance Goals",
          url: "https://www.cisa.gov/cybersecurity-performance-goals",
        },
      ],
    };
  if (answers.test(normalizedQuestion))
    return {
      blocked: true,
      answer:
        "I won’t provide a graded answer or complete the work for you. Tell me your current reasoning and I’ll challenge one assumption, offer a smaller hint, or create an ungraded practice problem.",
      citations: [],
    };
  const course = courses.find((c) => c.id === courseId) || courses[0];
  const lesson =
    (verifiedContext?.verificationStatus === "verified"
      ? verifiedContext
      : undefined) ||
    course.modules.flatMap((m) => m.lessons).find((l) => l.id === lessonId) ||
    course.modules
      .flatMap((m) => m.lessons)
      .find((l) =>
        normalizedQuestion
          .toLowerCase()
          .includes(l.title.toLowerCase().split(" ")[0]),
      ) ||
    course.modules[0].lessons[0];
  if (lesson.verificationStatus !== "verified")
    return {
      answer:
        "I cannot verify this information from trusted cybersecurity sources.",
      citations: [],
    };
  return {
    answer: `Start with this distinction: ${lesson.content[0]}\n\nTry this: ${lesson.example}\n\nSocratic check — what evidence would change your conclusion, and how would you verify that your control worked?`,
    citations: lesson.references.map((r) => ({
      label: `${r.publisher}: ${r.title}`,
      url: r.url,
    })),
  };
}
