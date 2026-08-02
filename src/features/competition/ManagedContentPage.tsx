import { useQuery } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link, useParams } from "wouter";
import { apiFetch } from "../../lib/api-client";

type ManagedQuestion = {
  question_id: string;
  title: string;
  metadata: {
    questionType?: string;
    prompt?: string;
    learnerContext?: string;
    options?: string[];
  };
};

type ManagedContent = {
  content_id: string;
  version_id: string;
  content_type: string;
  title: string;
  description: string;
  version: string;
  metadata: Record<string, unknown>;
  sections: Array<{
    key: string;
    type: string;
    title: string;
    body: string;
    accessibilityLabel?: string | null;
  }>;
  questions?: ManagedQuestion[];
};

type AssessmentResult = {
  content_version_id: string;
  score: number;
  passed: boolean;
  outcomes: Array<{
    question_id: string;
    credit: number;
    correct?: boolean;
    explanation?: string;
  }>;
};

function QuestionInput({
  question,
  value,
  onChange,
}: {
  question: ManagedQuestion;
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  const type = question.metadata.questionType;
  const options = question.metadata.options || [];
  if (
    type === "single_choice" ||
    type === "true_false" ||
    type === "scenario_decision"
  ) {
    const choices = type === "true_false" ? ["true", "false"] : options;
    return (
      <div className="cms-answer-options">
        {choices.map((option) => (
          <label key={option}>
            <input
              required
              type="radio"
              name={question.question_id}
              value={option}
              checked={value === option}
              onChange={() => onChange(option)}
            />
            {option}
          </label>
        ))}
      </div>
    );
  }
  if (type === "multiple_choice") {
    const selected = Array.isArray(value) ? (value as string[]) : [];
    return (
      <div className="cms-answer-options">
        {options.map((option) => (
          <label key={option}>
            <input
              type="checkbox"
              checked={selected.includes(option)}
              onChange={(event) =>
                onChange(
                  event.currentTarget.checked
                    ? [...selected, option]
                    : selected.filter((item) => item !== option),
                )
              }
            />
            {option}
          </label>
        ))}
      </div>
    );
  }
  if (["ordering", "matching"].includes(type || "")) {
    return (
      <label>
        Your ordered response, one item per line
        <textarea
          required
          value={Array.isArray(value) ? value.join("\n") : ""}
          onChange={(event) =>
            onChange(event.currentTarget.value.split("\n").filter(Boolean))
          }
        />
      </label>
    );
  }
  return (
    <label>
      Your response
      <textarea
        required
        value={String(value || "")}
        onChange={(event) => onChange(event.currentTarget.value)}
      />
    </label>
  );
}

export function ManagedContentPage() {
  const { contentType, slug } = useParams<{
    contentType: string;
    slug: string;
  }>();
  const [answers, setAnswers] = useState<Record<string, unknown>>({});
  const [result, setResult] = useState<AssessmentResult | null>(null);
  const [error, setError] = useState("");
  const query = useQuery({
    queryKey: ["managed-content", contentType, slug],
    queryFn: () =>
      apiFetch<ManagedContent>(
        `/api/v1/managed-content/${contentType}/${slug}`,
      ),
  });
  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      setResult(
        await apiFetch<AssessmentResult>(
          `/api/v1/managed-content/assessments/${slug}/submit`,
          {
            method: "POST",
            body: JSON.stringify({
              answers,
              idempotency_key: crypto.randomUUID(),
            }),
          },
        ),
      );
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Assessment submission failed.",
      );
    }
  }
  if (query.isLoading) return <p role="status">Loading published content…</p>;
  if (query.error)
    return (
      <section className="workflow-error" role="alert">
        <p>The published content could not be loaded.</p>
        <button onClick={() => void query.refetch()}>Retry</button>
      </section>
    );
  const content = query.data!;
  return (
    <article className="managed-content-page">
      <span className="eyebrow">PUBLISHED · VERSION {content.version}</span>
      <h1>{content.title}</h1>
      <p>{content.description}</p>
      {content.sections.map((section) => (
        <section key={section.key}>
          <h2>{section.title || section.type.replaceAll("_", " ")}</h2>
          <p className="cms-rendered-body">{section.body}</p>
          {section.accessibilityLabel && (
            <small>{section.accessibilityLabel}</small>
          )}
        </section>
      ))}
      {content.content_type === "assessment" && (
        <form
          onSubmit={(event) => void submit(event)}
          className="managed-assessment"
        >
          <h2>
            {String(content.metadata.instructions || "Answer every question.")}
          </h2>
          {content.questions?.map((question, index) => {
            const outcome = result?.outcomes.find(
              (item) => item.question_id === question.question_id,
            );
            return (
              <fieldset key={question.question_id}>
                <legend>
                  {index + 1}. {question.metadata.prompt || question.title}
                </legend>
                {question.metadata.learnerContext && (
                  <p>{question.metadata.learnerContext}</p>
                )}
                <QuestionInput
                  question={question}
                  value={answers[question.question_id]}
                  onChange={(value) =>
                    setAnswers((current) => ({
                      ...current,
                      [question.question_id]: value,
                    }))
                  }
                />
                {outcome && (
                  <p role="status">
                    {outcome.correct === undefined
                      ? `Submitted · ${Math.round(outcome.credit * 100)}% credit`
                      : outcome.correct
                        ? "Correct"
                        : `Review needed · ${Math.round(outcome.credit * 100)}% credit`}
                    {outcome.explanation ? ` · ${outcome.explanation}` : ""}
                  </p>
                )}
              </fieldset>
            );
          })}
          {!content.questions?.length && (
            <p>No published questions are attached.</p>
          )}
          <button className="primary" disabled={!content.questions?.length}>
            Submit assessment
          </button>
          {error && (
            <p className="workflow-error" role="alert">
              {error}
            </p>
          )}
          {result && (
            <section className="completion-panel">
              <h2>
                {result.passed
                  ? "Assessment passed"
                  : "Reassessment recommended"}
              </h2>
              <p>
                Score {Math.round(result.score * 100)}%. Evidence is bound to
                content version {result.content_version_id}.
              </p>
            </section>
          )}
        </form>
      )}
      <Link to="/academy">Return to academy</Link>
    </article>
  );
}
