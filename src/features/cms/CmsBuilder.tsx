import { useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useEffect, useMemo, useState, type ReactNode } from "react";
import { Link, useLocation, useRoute } from "wouter";
import { apiFetch } from "../../lib/api-client";
import { CmsEmpty, CmsError, CmsPage, StatusBadge } from "./CmsShared";
import type {
  CmsContentSummary,
  CmsContentType,
  CmsObjective,
  CmsRelationship,
  CmsSection,
  CmsVersion,
} from "./cms-types";
import { CMS_TYPES } from "./cms-types";

type Field = {
  key: string;
  label: string;
  kind?: "text" | "textarea" | "number" | "select" | "lines" | "check";
  options?: string[];
  required?: boolean;
  help?: string;
};

const COMMON_FIELDS: Field[] = [
  { key: "audience", label: "Target audience", required: true },
  {
    key: "difficulty",
    label: "Difficulty",
    kind: "select",
    options: ["beginner", "intermediate", "advanced"],
    required: true,
  },
  {
    key: "estimatedMinutes",
    label: "Estimated minutes",
    kind: "number",
    required: true,
  },
  { key: "skillKeys", label: "Linked skill IDs", kind: "lines" },
  { key: "tags", label: "Tags", kind: "lines" },
];

const FIELDS: Record<CmsContentType, Field[]> = {
  course: [
    {
      key: "summary",
      label: "Short summary",
      kind: "textarea",
      required: true,
    },
    ...COMMON_FIELDS,
    { key: "prerequisiteNotes", label: "Prerequisite notes", kind: "textarea" },
    {
      key: "outcomes",
      label: "Learning outcomes",
      kind: "lines",
      required: true,
    },
    {
      key: "completionRule",
      label: "Completion rule",
      kind: "textarea",
      required: true,
    },
    { key: "project", label: "Course project" },
    { key: "completionPolicy", label: "Completion policy", kind: "textarea" },
    { key: "languageNotes", label: "Localization notes", kind: "textarea" },
  ],
  module: [
    { key: "purpose", label: "Purpose", kind: "textarea", required: true },
    ...COMMON_FIELDS.slice(2),
    { key: "practices", label: "Guided practices", kind: "lines" },
    {
      key: "prerequisiteNotes",
      label: "Prerequisite modules or skills",
      kind: "lines",
    },
    {
      key: "completionRule",
      label: "Completion rule",
      kind: "textarea",
      required: true,
    },
  ],
  lesson: COMMON_FIELDS,
  question: [
    {
      key: "questionType",
      label: "Question type",
      kind: "select",
      options: [
        "single_choice",
        "multiple_choice",
        "true_false",
        "ordering",
        "matching",
        "command_interpretation",
        "log_interpretation",
        "scenario_decision",
        "short_response",
      ],
      required: true,
    },
    { key: "prompt", label: "Prompt", kind: "textarea", required: true },
    {
      key: "learnerContext",
      label: "Learner-visible context",
      kind: "textarea",
    },
    {
      key: "options",
      label: "Options or ordered/matching items",
      kind: "lines",
    },
    {
      key: "answerKey",
      label: "Server-only answer key",
      kind: "lines",
      required: true,
      help: "Never included in learner previews or published learner responses.",
    },
    {
      key: "explanation",
      label: "Post-submission explanation",
      kind: "textarea",
      required: true,
    },
    { key: "partialCreditRules", label: "Partial-credit rules", kind: "lines" },
    {
      key: "skillKeys",
      label: "Linked skill IDs",
      kind: "lines",
      required: true,
    },
    { key: "objectiveKeys", label: "Linked objective IDs", kind: "lines" },
    {
      key: "difficulty",
      label: "Difficulty",
      kind: "select",
      options: ["beginner", "intermediate", "advanced"],
    },
    { key: "estimatedMinutes", label: "Estimated minutes", kind: "number" },
    { key: "tags", label: "Tags", kind: "lines" },
  ],
  assessment: [
    { key: "purpose", label: "Purpose", kind: "textarea", required: true },
    {
      key: "instructions",
      label: "Learner instructions",
      kind: "textarea",
      required: true,
    },
    {
      key: "passingScore",
      label: "Passing score (0–1)",
      kind: "number",
      required: true,
    },
    {
      key: "attemptLimit",
      label: "Attempt limit",
      kind: "number",
      required: true,
    },
    { key: "timeLimitMinutes", label: "Time limit in minutes", kind: "number" },
    { key: "partialCredit", label: "Allow partial credit", kind: "check" },
    { key: "randomize", label: "Randomize questions", kind: "check" },
    {
      key: "feedbackPolicy",
      label: "Feedback policy",
      kind: "select",
      options: ["after_attempt", "after_pass", "after_close"],
      required: true,
    },
    { key: "retakePolicy", label: "Retake policy", kind: "textarea" },
    { key: "explanationPolicy", label: "Explanation policy", kind: "textarea" },
    { key: "sections", label: "Assessment sections", kind: "lines" },
    { key: "skillKeys", label: "Linked skill IDs", kind: "lines" },
  ],
  lab: [
    { key: "scenario", label: "Scenario", kind: "textarea", required: true },
    { key: "businessContext", label: "Business context", kind: "textarea" },
    ...COMMON_FIELDS,
    { key: "labType", label: "Lab type", required: true },
    {
      key: "availableTools",
      label: "Available tools",
      kind: "lines",
      required: true,
    },
    { key: "directories", label: "Virtual directories", kind: "lines" },
    { key: "filePermissions", label: "File permissions", kind: "lines" },
    { key: "logDatasets", label: "Log datasets", kind: "lines" },
    { key: "networkEvidence", label: "Network evidence", kind: "lines" },
    {
      key: "allowedCommands",
      label: "Allowed commands",
      kind: "lines",
      required: true,
    },
    {
      key: "expectedEvidence",
      label: "Expected evidence",
      kind: "lines",
      required: true,
    },
    {
      key: "validationRules",
      label: "Validation rules",
      kind: "lines",
      required: true,
    },
    { key: "hints", label: "Progressive hints", kind: "lines", required: true },
    { key: "scoringRules", label: "Scoring rules", kind: "lines" },
    { key: "reflectionPrompts", label: "Reflection prompts", kind: "lines" },
    {
      key: "completionRule",
      label: "Completion rule",
      kind: "textarea",
      required: true,
    },
    { key: "portfolioEligible", label: "Portfolio eligible", kind: "check" },
  ],
  mission: [
    {
      key: "briefing",
      label: "Mission briefing",
      kind: "textarea",
      required: true,
    },
    {
      key: "fictionalOrganization",
      label: "Fictional organization",
      required: true,
    },
    { key: "learnerRole", label: "Learner role", required: true },
    { key: "businessContext", label: "Business context", kind: "textarea" },
    {
      key: "objectives",
      label: "Mission objectives",
      kind: "lines",
      required: true,
    },
    { key: "branching", label: "Branching rules", kind: "lines" },
    {
      key: "alternativePaths",
      label: "Alternative valid paths",
      kind: "lines",
    },
    {
      key: "requiredEvidence",
      label: "Required evidence",
      kind: "lines",
      required: true,
    },
    { key: "optionalEvidence", label: "Optional evidence", kind: "lines" },
    { key: "falsePositives", label: "False positives", kind: "lines" },
    { key: "decisionPoints", label: "Decision points", kind: "lines" },
    { key: "hints", label: "Progressive hints", kind: "lines" },
    {
      key: "sentinelInterventions",
      label: "Sentinel intervention points",
      kind: "lines",
    },
    { key: "reportRequirements", label: "Report requirements", kind: "lines" },
    {
      key: "scoring",
      label: "Scoring dimensions",
      kind: "lines",
      required: true,
    },
    {
      key: "completionRule",
      label: "Completion rule",
      kind: "textarea",
      required: true,
    },
    { key: "skillKeys", label: "Skill evidence mappings", kind: "lines" },
    { key: "replayPolicy", label: "Replay configuration", kind: "textarea" },
    {
      key: "portfolioArtifacts",
      label: "Portfolio artifact settings",
      kind: "textarea",
    },
  ],
  learning_path: [
    { key: "targetRole", label: "Target role", required: true },
    { key: "audience", label: "Target audience" },
    { key: "estimatedMinutes", label: "Estimated minutes", kind: "number" },
    {
      key: "completionCriteria",
      label: "Completion criteria",
      kind: "textarea",
      required: true,
    },
    {
      key: "readinessCriteria",
      label: "Readiness evidence criteria",
      kind: "textarea",
      required: true,
    },
    {
      key: "prerequisiteSkills",
      label: "Prerequisite skill IDs",
      kind: "lines",
    },
    { key: "sequencing", label: "Sequencing rules", kind: "lines" },
    { key: "branches", label: "Branch rules", kind: "lines" },
    { key: "completionPolicy", label: "Completion policy", kind: "textarea" },
  ],
  skill: [
    { key: "stableSkillId", label: "Stable skill ID", required: true },
    { key: "category", label: "Category", required: true },
    {
      key: "difficulty",
      label: "Difficulty",
      kind: "select",
      options: ["foundation", "intermediate", "advanced"],
    },
    {
      key: "evidenceRequirements",
      label: "Evidence requirements",
      kind: "lines",
      required: true,
    },
    { key: "linkedObjectives", label: "Linked objective IDs", kind: "lines" },
    {
      key: "status",
      label: "Status",
      kind: "select",
      options: ["active", "retired"],
    },
  ],
  reference: [
    { key: "publisher", label: "Publisher", required: true },
    { key: "url", label: "HTTPS URL", required: true },
    { key: "publicationDate", label: "Publication date" },
    { key: "retrievalDate", label: "Retrieval date", required: true },
    { key: "sourceVersion", label: "Source version or date" },
    { key: "licenseNote", label: "License or usage note", kind: "textarea" },
    {
      key: "freshnessDays",
      label: "Freshness interval in days",
      kind: "number",
      required: true,
    },
    { key: "lastVerifiedDate", label: "Last verified date" },
    {
      key: "brokenLinkStatus",
      label: "Link status",
      kind: "select",
      options: ["unchecked", "working", "broken"],
    },
  ],
};

const BLOCK_TYPES = [
  "heading",
  "paragraph",
  "learning_objectives",
  "definition",
  "worked_example",
  "investigation_example",
  "callout",
  "tip",
  "warning",
  "misconception",
  "code",
  "command",
  "terminal_output",
  "log_sample",
  "table",
  "image",
  "knowledge_checkpoint",
  "guided_practice",
  "reflection",
  "summary",
  "references",
];

function blankSection(type = "paragraph", order = 0): CmsSection {
  return {
    key: crypto.randomUUID(),
    type,
    title: "",
    body: "",
    data: {},
    visibility: "visible",
    accessibilityLabel: null,
    order,
  };
}

function lines(value: unknown) {
  return Array.isArray(value) ? value.join("\n") : String(value ?? "");
}

function normalizeField(field: Field, value: string | boolean) {
  if (field.kind === "lines")
    return String(value)
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean);
  if (field.kind === "number") return value === "" ? null : Number(value);
  return value;
}

function FieldControl({
  field,
  value,
  onChange,
}: {
  field: Field;
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  const id = `cms-field-${field.key}`;
  let control: ReactNode;
  if (field.kind === "textarea" || field.kind === "lines") {
    control = (
      <textarea
        id={id}
        required={field.required}
        value={field.kind === "lines" ? lines(value) : String(value ?? "")}
        onChange={(event) =>
          onChange(normalizeField(field, event.currentTarget.value))
        }
        rows={field.kind === "lines" ? 4 : 5}
      />
    );
  } else if (field.kind === "select") {
    control = (
      <select
        id={id}
        required={field.required}
        value={String(value ?? "")}
        onChange={(event) => onChange(event.currentTarget.value)}
      >
        <option value="">Select…</option>
        {field.options?.map((option) => (
          <option key={option} value={option}>
            {option.replaceAll("_", " ")}
          </option>
        ))}
      </select>
    );
  } else if (field.kind === "check") {
    control = (
      <input
        id={id}
        type="checkbox"
        checked={Boolean(value)}
        onChange={(event) => onChange(event.currentTarget.checked)}
      />
    );
  } else {
    control = (
      <input
        id={id}
        type={field.kind === "number" ? "number" : "text"}
        step={field.key === "passingScore" ? "0.01" : "1"}
        required={field.required}
        value={value == null ? "" : String(value)}
        onChange={(event) =>
          onChange(normalizeField(field, event.currentTarget.value))
        }
      />
    );
  }
  return (
    <label
      className={field.kind === "check" ? "check-row" : undefined}
      htmlFor={id}
    >
      {field.label}
      {control}
      {field.help && <small>{field.help}</small>}
    </label>
  );
}

type MissionStage = {
  id: string;
  title: string;
  goal: string;
  evidence: string[];
  actions: string[];
  requiredAction: string;
  hints: string[];
  instructions: string;
  tools: string[];
  alternativeActions: string[];
  validation: string[];
  feedback: string;
  completionCondition: string;
  skillKeys: string[];
};

function MissionStages({
  value,
  onChange,
}: {
  value: unknown;
  onChange: (value: MissionStage[]) => void;
}) {
  const stages = Array.isArray(value) ? (value as MissionStage[]) : [];
  function update(index: number, patch: Partial<MissionStage>) {
    onChange(
      stages.map((stage, position) =>
        position === index ? { ...stage, ...patch } : stage,
      ),
    );
  }
  return (
    <fieldset>
      <legend>Mission stages</legend>
      {stages.map((stage, index) => (
        <article className="cms-builder-card" key={stage.id}>
          <label>
            Stage title
            <input
              value={stage.title}
              onChange={(e) => update(index, { title: e.currentTarget.value })}
            />
          </label>
          <label>
            Goal
            <textarea
              value={stage.goal}
              onChange={(e) => update(index, { goal: e.currentTarget.value })}
            />
          </label>
          <label>
            Evidence sources
            <textarea
              value={lines(stage.evidence)}
              onChange={(e) =>
                update(index, { evidence: linesToArray(e.currentTarget.value) })
              }
            />
          </label>
          <label>
            Available decisions/actions
            <textarea
              value={lines(stage.actions)}
              onChange={(e) =>
                update(index, { actions: linesToArray(e.currentTarget.value) })
              }
            />
          </label>
          <label>
            Required decision/action
            <input
              value={stage.requiredAction || ""}
              onChange={(e) =>
                update(index, { requiredAction: e.currentTarget.value })
              }
            />
          </label>
          <label>
            Progressive hints
            <textarea
              value={lines(stage.hints)}
              onChange={(e) =>
                update(index, { hints: linesToArray(e.currentTarget.value) })
              }
            />
          </label>
          <label>
            Instructions
            <textarea
              value={stage.instructions || ""}
              onChange={(e) =>
                update(index, { instructions: e.currentTarget.value })
              }
            />
          </label>
          <label>
            Available tools
            <textarea
              value={lines(stage.tools)}
              onChange={(e) =>
                update(index, { tools: linesToArray(e.currentTarget.value) })
              }
            />
          </label>
          <label>
            Alternative valid actions
            <textarea
              value={lines(stage.alternativeActions)}
              onChange={(e) =>
                update(index, {
                  alternativeActions: linesToArray(e.currentTarget.value),
                })
              }
            />
          </label>
          <label>
            Validation rules
            <textarea
              value={lines(stage.validation)}
              onChange={(e) =>
                update(index, {
                  validation: linesToArray(e.currentTarget.value),
                })
              }
            />
          </label>
          <label>
            Feedback
            <textarea
              value={stage.feedback || ""}
              onChange={(e) =>
                update(index, { feedback: e.currentTarget.value })
              }
            />
          </label>
          <label>
            Completion condition
            <textarea
              value={stage.completionCondition || ""}
              onChange={(e) =>
                update(index, { completionCondition: e.currentTarget.value })
              }
            />
          </label>
          <label>
            Linked skills
            <textarea
              value={lines(stage.skillKeys)}
              onChange={(e) =>
                update(index, {
                  skillKeys: linesToArray(e.currentTarget.value),
                })
              }
            />
          </label>
          <div>
            <button
              type="button"
              disabled={index === 0}
              onClick={() => {
                const next = [...stages];
                [next[index - 1], next[index]] = [next[index], next[index - 1]];
                onChange(next);
              }}
              aria-label={`Move stage ${index + 1} up`}
            >
              ↑
            </button>
            <button
              type="button"
              disabled={index === stages.length - 1}
              onClick={() => {
                const next = [...stages];
                [next[index + 1], next[index]] = [next[index], next[index + 1]];
                onChange(next);
              }}
              aria-label={`Move stage ${index + 1} down`}
            >
              ↓
            </button>
          </div>
          <button
            type="button"
            onClick={() =>
              onChange(stages.filter((_, position) => position !== index))
            }
          >
            Remove stage
          </button>
        </article>
      ))}
      <button
        type="button"
        onClick={() =>
          onChange([
            ...stages,
            {
              id: crypto.randomUUID(),
              title: "",
              goal: "",
              evidence: [],
              actions: [],
              requiredAction: "",
              hints: [],
              instructions: "",
              tools: [],
              alternativeActions: [],
              validation: [],
              feedback: "",
              completionCondition: "",
              skillKeys: [],
            },
          ])
        }
      >
        Add mission stage
      </button>
    </fieldset>
  );
}

type CommandResponse = { command: string; response: string };

function CommandResponses({
  value,
  onChange,
}: {
  value: unknown;
  onChange: (value: Record<string, string>) => void;
}) {
  const rows: CommandResponse[] =
    value && typeof value === "object"
      ? Object.entries(value as Record<string, string>).map(
          ([command, response]) => ({ command, response }),
        )
      : [];
  function update(index: number, patch: Partial<CommandResponse>) {
    const next = rows.map((row, position) =>
      position === index ? { ...row, ...patch } : row,
    );
    onChange(
      Object.fromEntries(
        next
          .filter((row) => row.command)
          .map((row) => [row.command, row.response]),
      ),
    );
  }
  return (
    <fieldset>
      <legend>Deterministic command responses</legend>
      {rows.map((row, index) => (
        <article className="cms-builder-card" key={`${row.command}-${index}`}>
          <label>
            Exact command
            <input
              value={row.command}
              onChange={(event) =>
                update(index, { command: event.currentTarget.value })
              }
            />
          </label>
          <label>
            Response
            <textarea
              value={row.response}
              onChange={(event) =>
                update(index, { response: event.currentTarget.value })
              }
            />
          </label>
          <button
            type="button"
            onClick={() =>
              onChange(
                Object.fromEntries(
                  rows
                    .filter((_, position) => position !== index)
                    .map((item) => [item.command, item.response]),
                ),
              )
            }
          >
            Remove response
          </button>
        </article>
      ))}
      <button
        type="button"
        onClick={() =>
          onChange({
            ...((value as Record<string, string>) || {}),
            [`command-${rows.length + 1}`]: "",
          })
        }
      >
        Add command response
      </button>
    </fieldset>
  );
}

type VirtualFile = {
  id: string;
  path: string;
  content: string;
  mode: string;
  owner: string;
  group: string;
};

function VirtualFiles({
  value,
  onChange,
}: {
  value: unknown;
  onChange: (value: VirtualFile[]) => void;
}) {
  const files = Array.isArray(value) ? (value as VirtualFile[]) : [];
  function update(index: number, patch: Partial<VirtualFile>) {
    onChange(
      files.map((file, position) =>
        position === index ? { ...file, ...patch } : file,
      ),
    );
  }
  return (
    <fieldset>
      <legend>Virtual filesystem</legend>
      {files.map((file, index) => (
        <article className="cms-builder-card" key={file.id}>
          <label>
            Path
            <input
              value={file.path}
              onChange={(e) => update(index, { path: e.currentTarget.value })}
            />
          </label>
          <label>
            Contents
            <textarea
              value={file.content}
              onChange={(e) =>
                update(index, { content: e.currentTarget.value })
              }
            />
          </label>
          <div className="cms-inline-fields">
            <label>
              Mode
              <input
                value={file.mode}
                onChange={(e) => update(index, { mode: e.currentTarget.value })}
              />
            </label>
            <label>
              Owner
              <input
                value={file.owner}
                onChange={(e) =>
                  update(index, { owner: e.currentTarget.value })
                }
              />
            </label>
            <label>
              Group
              <input
                value={file.group}
                onChange={(e) =>
                  update(index, { group: e.currentTarget.value })
                }
              />
            </label>
          </div>
          <button
            type="button"
            onClick={() =>
              onChange(files.filter((_, position) => position !== index))
            }
          >
            Remove file
          </button>
        </article>
      ))}
      <button
        type="button"
        onClick={() =>
          onChange([
            ...files,
            {
              id: crypto.randomUUID(),
              path: "/home/analyst/evidence.txt",
              content: "",
              mode: "0644",
              owner: "analyst",
              group: "analyst",
            },
          ])
        }
      >
        Add virtual file
      </button>
    </fieldset>
  );
}

function linesToArray(value: string) {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function LessonBlocks({
  sections,
  onChange,
}: {
  sections: CmsSection[];
  onChange: (value: CmsSection[]) => void;
}) {
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [previewKey, setPreviewKey] = useState<string | null>(null);
  function update(index: number, patch: Partial<CmsSection>) {
    onChange(
      sections.map((section, position) =>
        position === index ? { ...section, ...patch } : section,
      ),
    );
  }
  function move(index: number, delta: number) {
    const destination = index + delta;
    if (destination < 0 || destination >= sections.length) return;
    const next = [...sections];
    [next[index], next[destination]] = [next[destination], next[index]];
    onChange(next.map((section, order) => ({ ...section, order })));
  }
  return (
    <fieldset>
      <legend>Structured lesson blocks</legend>
      {sections.map((section, index) => (
        <article
          className="cms-builder-card"
          key={section.key}
          id={`block-${section.key}`}
        >
          <div className="cms-builder-card-header">
            <strong>Block {index + 1}</strong>
            <div>
              <button
                type="button"
                disabled={index === 0}
                onClick={() => move(index, -1)}
                aria-label={`Move block ${index + 1} up`}
              >
                ↑
              </button>
              <button
                type="button"
                disabled={index === sections.length - 1}
                onClick={() => move(index, 1)}
                aria-label={`Move block ${index + 1} down`}
              >
                ↓
              </button>
              <button
                type="button"
                onClick={() =>
                  onChange(
                    [
                      ...sections.slice(0, index + 1),
                      { ...section, key: crypto.randomUUID() },
                      ...sections.slice(index + 1),
                    ].map((item, order) => ({ ...item, order })),
                  )
                }
              >
                Duplicate
              </button>
              <button
                type="button"
                aria-expanded={!collapsed.has(section.key)}
                onClick={() =>
                  setCollapsed((current) => {
                    const next = new Set(current);
                    if (next.has(section.key)) next.delete(section.key);
                    else next.add(section.key);
                    return next;
                  })
                }
              >
                {collapsed.has(section.key) ? "Expand" : "Collapse"}
              </button>
              <button
                type="button"
                onClick={() =>
                  setPreviewKey(previewKey === section.key ? null : section.key)
                }
              >
                Preview block
              </button>
              <button
                type="button"
                onClick={() =>
                  onChange(
                    sections
                      .filter((_, position) => position !== index)
                      .map((item, order) => ({ ...item, order })),
                  )
                }
              >
                Remove
              </button>
            </div>
          </div>
          {!collapsed.has(section.key) && (
            <>
              <label>
                Block type
                <select
                  value={section.type}
                  onChange={(e) =>
                    update(index, { type: e.currentTarget.value })
                  }
                >
                  {BLOCK_TYPES.map((type) => (
                    <option value={type} key={type}>
                      {type.replaceAll("_", " ")}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Title
                <input
                  value={section.title}
                  onChange={(e) =>
                    update(index, { title: e.currentTarget.value })
                  }
                />
              </label>
              <label>
                Content
                <textarea
                  value={section.body}
                  onChange={(e) =>
                    update(index, { body: e.currentTarget.value })
                  }
                  rows={6}
                />
              </label>
              {(section.type === "image" || section.type === "table") && (
                <label>
                  Accessibility description
                  <input
                    value={section.accessibilityLabel || ""}
                    onChange={(e) =>
                      update(index, {
                        accessibilityLabel: e.currentTarget.value || null,
                      })
                    }
                  />
                </label>
              )}
              {(section.type === "code" || section.type === "command") && (
                <label>
                  Language or shell
                  <input
                    value={String(section.data.language || "")}
                    onChange={(e) =>
                      update(index, {
                        data: {
                          ...section.data,
                          language: e.currentTarget.value,
                        },
                      })
                    }
                  />
                </label>
              )}
              {section.type === "table" && (
                <label>
                  Table rows, pipe-separated
                  <textarea
                    value={
                      Array.isArray(section.data.rows)
                        ? (section.data.rows as string[][])
                            .map((row) => row.join(" | "))
                            .join("\n")
                        : ""
                    }
                    onChange={(event) =>
                      update(index, {
                        data: {
                          ...section.data,
                          rows: event.currentTarget.value
                            .split("\n")
                            .filter(Boolean)
                            .map((row) =>
                              row.split("|").map((cell) => cell.trim()),
                            ),
                        },
                      })
                    }
                  />
                </label>
              )}
              <label className="check-row">
                <input
                  type="checkbox"
                  checked={section.visibility === "visible"}
                  onChange={(e) =>
                    update(index, {
                      visibility: e.currentTarget.checked
                        ? "visible"
                        : "hidden",
                    })
                  }
                />
                Visible to learners
              </label>
            </>
          )}
          {previewKey === section.key && (
            <aside className="cms-block-preview">
              <span className="cms-draft-ribbon">BLOCK PREVIEW</span>
              <h3>{section.title || section.type.replaceAll("_", " ")}</h3>
              <p className="cms-rendered-body">{section.body}</p>
            </aside>
          )}
        </article>
      ))}
      <button
        type="button"
        onClick={() =>
          onChange([...sections, blankSection("paragraph", sections.length)])
        }
      >
        Add block
      </button>
    </fieldset>
  );
}

function ObjectiveEditor({
  objectives,
  onChange,
}: {
  objectives: CmsObjective[];
  onChange: (value: CmsObjective[]) => void;
}) {
  function update(index: number, patch: Partial<CmsObjective>) {
    onChange(
      objectives.map((objective, position) =>
        position === index ? { ...objective, ...patch } : objective,
      ),
    );
  }
  return (
    <fieldset>
      <legend>Learning objectives</legend>
      {objectives.map((objective, index) => (
        <article className="cms-builder-card" key={objective.key}>
          <label>
            Objective title
            <input
              required
              value={objective.title}
              onChange={(event) =>
                update(index, { title: event.currentTarget.value })
              }
            />
          </label>
          <label>
            Description
            <textarea
              required
              value={objective.description}
              onChange={(event) =>
                update(index, { description: event.currentTarget.value })
              }
            />
          </label>
          <label>
            Bloom level
            <select
              value={objective.bloomLevel}
              onChange={(event) =>
                update(index, { bloomLevel: event.currentTarget.value })
              }
            >
              {[
                "remember",
                "understand",
                "apply",
                "analyze",
                "evaluate",
                "create",
              ].map((item) => (
                <option key={item}>{item}</option>
              ))}
            </select>
          </label>
          <label>
            Linked skill IDs
            <textarea
              value={lines(objective.skills)}
              onChange={(event) =>
                update(index, {
                  skills: linesToArray(event.currentTarget.value),
                })
              }
            />
          </label>
          <label className="check-row">
            <input
              type="checkbox"
              checked={objective.assessmentCoverage}
              onChange={(event) =>
                update(index, {
                  assessmentCoverage: event.currentTarget.checked,
                })
              }
            />
            Assessment coverage
          </label>
          <label className="check-row">
            <input
              type="checkbox"
              checked={objective.practicalCoverage}
              onChange={(event) =>
                update(index, {
                  practicalCoverage: event.currentTarget.checked,
                })
              }
            />
            Practical coverage
          </label>
          <button
            type="button"
            onClick={() =>
              onChange(objectives.filter((_, position) => position !== index))
            }
          >
            Remove objective
          </button>
        </article>
      ))}
      <button
        type="button"
        onClick={() =>
          onChange([
            ...objectives,
            {
              key: crypto.randomUUID(),
              title: "",
              description: "",
              bloomLevel: "apply",
              skills: [],
              assessmentCoverage: false,
              practicalCoverage: false,
              reviewStatus: "pending",
            },
          ])
        }
      >
        Add objective
      </button>
    </fieldset>
  );
}

function RelationshipPicker({
  type,
  relationships,
  onChange,
}: {
  type: CmsContentType;
  relationships: CmsRelationship[];
  onChange: (value: CmsRelationship[]) => void;
}) {
  const library = useQuery({
    queryKey: ["cms-relationship-library"],
    queryFn: () =>
      apiFetch<{ items: CmsContentSummary[] }>(
        "/api/v1/cms/contents?page_size=100",
      ),
  });
  const [target, setTarget] = useState("");
  const [dragged, setDragged] = useState<number | null>(null);
  const [relationType, setRelationType] = useState(
    type === "course" ? "module" : "prerequisite",
  );
  function move(index: number, delta: number) {
    const destination = index + delta;
    if (destination < 0 || destination >= relationships.length) return;
    const next = [...relationships];
    [next[index], next[destination]] = [next[destination], next[index]];
    onChange(next.map((item, order) => ({ ...item, order })));
  }
  return (
    <fieldset>
      <legend>Reusable content relationships</legend>
      {relationships.map((relationship, index) => {
        const item = library.data?.items.find(
          (candidate) => candidate.id === relationship.targetContentId,
        );
        return (
          <article
            className="cms-relation-row"
            draggable
            key={`${relationship.targetContentId}-${relationship.type}`}
            onDragStart={() => setDragged(index)}
            onDragOver={(event) => event.preventDefault()}
            onDrop={() => {
              if (dragged == null || dragged === index) return;
              const next = [...relationships];
              const [moved] = next.splice(dragged, 1);
              next.splice(index, 0, moved);
              onChange(next.map((entry, order) => ({ ...entry, order })));
              setDragged(null);
            }}
            onDragEnd={() => setDragged(null)}
          >
            <span>
              {relationship.type}: {item?.title || relationship.targetContentId}
            </span>
            <button
              type="button"
              disabled={index === 0}
              onClick={() => move(index, -1)}
              aria-label={`Move ${item?.title || "relationship"} up`}
            >
              ↑
            </button>
            <button
              type="button"
              disabled={index === relationships.length - 1}
              onClick={() => move(index, 1)}
              aria-label={`Move ${item?.title || "relationship"} down`}
            >
              ↓
            </button>
            <button
              type="button"
              onClick={() =>
                onChange(
                  relationships.filter((_, position) => position !== index),
                )
              }
            >
              Detach
            </button>
          </article>
        );
      })}
      {relationships.length === 0 && (
        <CmsEmpty>No reusable content attached.</CmsEmpty>
      )}
      {(type === "skill" || type === "learning_path") &&
        relationships.length > 0 && (
          <section
            className="cms-relationship-views"
            aria-label={`${type.replaceAll("_", " ")} relationship views`}
          >
            <div className="cms-graph-view" aria-hidden="true">
              <span className="cms-graph-node">
                Current {type.replaceAll("_", " ")}
              </span>
              {relationships.map((relationship) => {
                const targetItem = library.data?.items.find(
                  (candidate) => candidate.id === relationship.targetContentId,
                );
                return (
                  <span
                    className="cms-graph-edge"
                    key={`graph-${relationship.targetContentId}-${relationship.type}`}
                  >
                    → {relationship.type} →{" "}
                    <b className="cms-graph-node">
                      {targetItem?.title || relationship.targetContentId}
                    </b>
                  </span>
                );
              })}
            </div>
            <div className="cms-table-wrap">
              <table>
                <caption>Accessible relationship graph alternative</caption>
                <thead>
                  <tr>
                    <th>Order</th>
                    <th>Relationship</th>
                    <th>Target</th>
                    <th>Required</th>
                  </tr>
                </thead>
                <tbody>
                  {relationships.map((relationship, index) => {
                    const targetItem = library.data?.items.find(
                      (candidate) =>
                        candidate.id === relationship.targetContentId,
                    );
                    return (
                      <tr
                        key={`table-${relationship.targetContentId}-${relationship.type}`}
                      >
                        <td>{index + 1}</td>
                        <td>{relationship.type}</td>
                        <td>
                          {targetItem?.title || relationship.targetContentId}
                        </td>
                        <td>{relationship.required ? "Yes" : "No"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>
        )}
      <div className="cms-inline-fields">
        <label>
          Relationship
          <select
            value={relationType}
            onChange={(e) => setRelationType(e.currentTarget.value)}
          >
            <option>prerequisite</option>
            <option>module</option>
            <option>lesson</option>
            <option>question</option>
            <option>assessment</option>
            <option>lab</option>
            <option>mission</option>
            <option>project</option>
            <option>skill</option>
            <option>reference</option>
            <option>parent_skill</option>
            <option>elective</option>
          </select>
        </label>
        <label>
          Content
          <select
            value={target}
            onChange={(e) => setTarget(e.currentTarget.value)}
          >
            <option value="">Select…</option>
            {library.data?.items.map((item) => (
              <option key={item.id} value={item.id}>
                {item.content_type}: {item.title}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          disabled={!target}
          onClick={() => {
            if (
              !target ||
              relationships.some(
                (item) =>
                  item.targetContentId === target && item.type === relationType,
              )
            )
              return;
            onChange([
              ...relationships,
              {
                targetContentId: target,
                targetVersionId: null,
                type: relationType,
                required: true,
                order: relationships.length,
                configuration: {},
              },
            ]);
            setTarget("");
          }}
        >
          Attach
        </button>
      </div>
    </fieldset>
  );
}

export function CmsBuilder() {
  const [, createParams] = useRoute("/cms/builders/:type");
  const [, editParams] = useRoute("/cms/builders/:type/:contentId");
  const type = (editParams?.type ||
    createParams?.type ||
    "lesson") as CmsContentType;
  const contentId = editParams?.contentId;
  const [, navigate] = useLocation();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [slug, setSlug] = useState("");
  const [description, setDescription] = useState("");
  const [language, setLanguage] = useState("en");
  const [versionNumber, setVersionNumber] = useState("1.0.0");
  const [metadata, setMetadata] = useState<Record<string, unknown>>({});
  const [sections, setSections] = useState<CmsSection[]>([]);
  const [objectives, setObjectives] = useState<CmsObjective[]>([]);
  const [relationships, setRelationships] = useState<CmsRelationship[]>([]);
  const [dirty, setDirty] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState<unknown>();
  const [preview, setPreview] = useState<Record<string, unknown> | null>(null);
  const [testCommand, setTestCommand] = useState("ls");
  const [testOutput, setTestOutput] = useState<Record<string, unknown> | null>(
    null,
  );
  const recoveryKey = `cybermentor:cms:draft:${type}:${contentId || "new"}`;
  const [hasRecovery, setHasRecovery] = useState(() => {
    try {
      return Boolean(localStorage.getItem(recoveryKey));
    } catch {
      return false;
    }
  });

  const contentQuery = useQuery({
    queryKey: ["cms-content", contentId],
    queryFn: () =>
      apiFetch<CmsContentSummary>(`/api/v1/cms/contents/${contentId}`),
    enabled: Boolean(contentId),
  });
  const selectedVersionId = contentQuery.data?.versions?.[0]?.id;
  const versionQuery = useQuery({
    queryKey: ["cms-version", contentId, selectedVersionId],
    queryFn: () =>
      apiFetch<CmsVersion>(
        `/api/v1/cms/contents/${contentId}/versions/${selectedVersionId}`,
      ),
    enabled: Boolean(contentId && selectedVersionId),
  });

  useEffect(() => {
    const item = versionQuery.data;
    if (!item) return;
    // The draft form must be hydrated when its persisted version arrives.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTitle(item.title);
    setSlug(item.public_slug);
    setDescription(item.description);
    setLanguage(item.language || "en");
    setVersionNumber(item.version);
    setMetadata(item.metadata || {});
    setSections(item.sections || []);
    setObjectives(item.objectives || []);
    setRelationships(item.relationships || []);
    setDirty(false);
  }, [versionQuery.data]);

  useEffect(() => {
    const guard = (event: BeforeUnloadEvent) => {
      if (!dirty) return;
      event.preventDefault();
    };
    window.addEventListener("beforeunload", guard);
    return () => window.removeEventListener("beforeunload", guard);
  }, [dirty]);

  useEffect(() => {
    if (!dirty || contentId) return;
    const timeout = window.setTimeout(() => {
      try {
        localStorage.setItem(
          recoveryKey,
          JSON.stringify({
            title,
            slug,
            description,
            language,
            versionNumber,
            metadata,
            sections,
            objectives,
            relationships,
          }),
        );
        setHasRecovery(true);
      } catch {
        /* Browser storage can be unavailable in locked-down sessions. */
      }
    }, 250);
    return () => window.clearTimeout(timeout);
  }, [
    contentId,
    description,
    dirty,
    language,
    metadata,
    objectives,
    recoveryKey,
    relationships,
    sections,
    slug,
    title,
    versionNumber,
  ]);

  function restoreLocalDraft() {
    try {
      const raw = localStorage.getItem(recoveryKey);
      if (!raw) return;
      const recovered = JSON.parse(raw) as {
        title?: string;
        slug?: string;
        description?: string;
        language?: string;
        versionNumber?: string;
        metadata?: Record<string, unknown>;
        sections?: CmsSection[];
        objectives?: CmsObjective[];
        relationships?: CmsRelationship[];
      };
      setTitle(recovered.title || "");
      setSlug(recovered.slug || "");
      setDescription(recovered.description || "");
      setLanguage(recovered.language || "en");
      setVersionNumber(recovered.versionNumber || "1.0.0");
      setMetadata(recovered.metadata || {});
      setSections(recovered.sections || []);
      setObjectives(recovered.objectives || []);
      setRelationships(recovered.relationships || []);
      setDirty(true);
      setMessage("Recovered the locally saved unsaved draft.");
    } catch {
      setError(new Error("The locally saved draft could not be restored."));
    }
  }

  const fields = useMemo(() => FIELDS[type] || [], [type]);
  function changeMetadata(key: string, value: unknown) {
    setMetadata((current) => ({ ...current, [key]: value }));
    setDirty(true);
  }
  function payload() {
    return {
      title,
      public_slug: slug,
      description,
      visibility: "private",
      metadata,
      sections: sections.map((section, order) => ({
        section_key: section.key,
        section_type: section.type,
        title: section.title,
        body: section.body,
        structured_data: section.data,
        visibility: section.visibility,
        accessibility_label: section.accessibilityLabel,
        sort_order: order,
      })),
      objectives: objectives.map((objective) => ({
        objective_key: objective.key,
        title: objective.title,
        description: objective.description,
        bloom_level: objective.bloomLevel,
        linked_skill_keys: objective.skills,
        assessment_coverage: objective.assessmentCoverage,
        practical_coverage: objective.practicalCoverage,
        review_status: objective.reviewStatus,
      })),
      relationships: relationships.map((relationship, order) => ({
        target_content_id: relationship.targetContentId,
        target_version_id: relationship.targetVersionId,
        relation_type: relationship.type,
        required: relationship.required,
        sort_order: order,
        configuration: relationship.configuration,
      })),
    };
  }
  async function save(event: FormEvent) {
    event.preventDefault();
    setError(undefined);
    try {
      if (versionQuery.data && contentId) {
        const saved = await apiFetch<CmsVersion>(
          `/api/v1/cms/contents/${contentId}/versions/${versionQuery.data.version_id}`,
          {
            method: "PUT",
            body: JSON.stringify({
              ...payload(),
              expected_lock_version: versionQuery.data.lock_version,
              change_summary: "Saved in the dedicated CMS builder",
            }),
          },
        );
        setMessage("Draft saved safely.");
        setDirty(false);
        try {
          localStorage.removeItem(recoveryKey);
          setHasRecovery(false);
        } catch {
          /* no-op */
        }
        queryClient.setQueryData(
          ["cms-version", contentId, selectedVersionId],
          saved,
        );
      } else {
        const created = await apiFetch<CmsVersion>("/api/v1/cms/contents", {
          method: "POST",
          body: JSON.stringify({
            content_type: type,
            language,
            version: versionNumber,
            change_summary: "Initial builder draft",
            ...payload(),
          }),
        });
        setDirty(false);
        try {
          localStorage.removeItem(recoveryKey);
          setHasRecovery(false);
        } catch {
          /* no-op */
        }
        navigate(`/cms/builders/${type}/${created.id}`, { replace: true });
      }
      await queryClient.invalidateQueries({ queryKey: ["cms-library"] });
    } catch (caught) {
      setError(caught);
    }
  }
  async function validate() {
    if (!contentId || !versionQuery.data) return;
    setError(undefined);
    try {
      const result = await apiFetch<{ failures: number }>(
        `/api/v1/cms/contents/${contentId}/versions/${versionQuery.data.version_id}/validate`,
        { method: "POST" },
      );
      setMessage(
        result.failures
          ? `${result.failures} blocking validation issue(s).`
          : "Validation passed.",
      );
      await versionQuery.refetch();
    } catch (caught) {
      setError(caught);
    }
  }
  async function showPreview() {
    if (!contentId || !versionQuery.data) return;
    try {
      const result = await apiFetch<{ content: Record<string, unknown> }>(
        `/api/v1/cms/contents/${contentId}/versions/${versionQuery.data.version_id}/preview`,
      );
      setPreview(result.content);
    } catch (caught) {
      setError(caught);
    }
  }
  async function runDraftTest() {
    if (!contentId || !versionQuery.data) return;
    setError(undefined);
    try {
      if (type === "lab") {
        setTestOutput(
          await apiFetch<Record<string, unknown>>(
            `/api/v1/cms/contents/${contentId}/versions/${versionQuery.data.version_id}/test-lab/command`,
            {
              method: "POST",
              body: JSON.stringify({
                command: testCommand,
                cwd: "/home/analyst",
              }),
            },
          ),
        );
      } else if (type === "mission") {
        setTestOutput(
          await apiFetch<Record<string, unknown>>(
            `/api/v1/cms/contents/${contentId}/versions/${versionQuery.data.version_id}/test-mission`,
          ),
        );
      }
    } catch (caught) {
      setError(caught);
    }
  }

  if (!CMS_TYPES.includes(type))
    return (
      <CmsPage>
        <CmsError error={new Error("Unsupported builder type.")} />
      </CmsPage>
    );
  if (contentQuery.isLoading || versionQuery.isLoading)
    return (
      <CmsPage>
        <p role="status">Loading {type.replaceAll("_", " ")} builder…</p>
      </CmsPage>
    );
  if (contentQuery.error || versionQuery.error)
    return (
      <CmsPage>
        <CmsError
          error={contentQuery.error || versionQuery.error}
          retry={() => void (contentQuery.refetch(), versionQuery.refetch())}
        />
      </CmsPage>
    );

  const immutable =
    versionQuery.data &&
    !["draft", "revision_requested"].includes(versionQuery.data.version_status);
  return (
    <CmsPage>
      <header className="cms-page-header">
        <div>
          <span className="eyebrow">{type.replaceAll("_", " ")} builder</span>
          <h1>
            {contentId
              ? title || "Untitled draft"
              : `Create ${type.replaceAll("_", " ")}`}
          </h1>
        </div>
        {versionQuery.data && (
          <div>
            <StatusBadge value={versionQuery.data.version_status} />{" "}
            <span>
              v{versionQuery.data.version} · revision{" "}
              {versionQuery.data.revision}
            </span>
          </div>
        )}
      </header>
      {message && (
        <p className="completion-panel" role="status">
          {message}
        </p>
      )}
      {Boolean(error) && <CmsError error={error} />}
      {!contentId && hasRecovery && (
        <div className="portal-state">
          <p>A recoverable unsaved local draft is available.</p>
          <button onClick={restoreLocalDraft}>Restore unsaved work</button>
          <button
            onClick={() => {
              try {
                localStorage.removeItem(recoveryKey);
              } finally {
                setHasRecovery(false);
              }
            }}
          >
            Discard recovery
          </button>
        </div>
      )}
      {immutable && (
        <div className="portal-state">
          This version is immutable.{" "}
          <Link to={`/cms/content/${contentId}`}>
            Create a new draft version from version history.
          </Link>
        </div>
      )}
      <form
        className="cms-builder"
        onSubmit={(event) => void save(event)}
        onChange={() => setDirty(true)}
      >
        <fieldset disabled={Boolean(immutable)}>
          <legend>Identity and version</legend>
          <label>
            Title
            <input
              required
              minLength={2}
              value={title}
              onChange={(e) => setTitle(e.currentTarget.value)}
            />
          </label>
          <label>
            Slug
            <input
              required
              pattern="[a-z0-9]+(?:-[a-z0-9]+)*"
              value={slug}
              onChange={(e) => setSlug(e.currentTarget.value)}
            />
          </label>
          <label>
            Description
            <textarea
              value={description}
              onChange={(e) => setDescription(e.currentTarget.value)}
            />
          </label>
          <label>
            Language
            <input
              required
              pattern="[a-z]{2,3}(?:-[A-Z]{2})?"
              value={language}
              disabled={Boolean(contentId)}
              onChange={(e) => setLanguage(e.currentTarget.value)}
            />
          </label>
          {!contentId && (
            <label>
              Version
              <input
                required
                pattern="\d+\.\d+\.\d+"
                value={versionNumber}
                onChange={(e) => setVersionNumber(e.currentTarget.value)}
              />
            </label>
          )}
        </fieldset>
        <fieldset disabled={Boolean(immutable)}>
          <legend>{type.replaceAll("_", " ")} configuration</legend>
          {fields.map((field) => (
            <FieldControl
              key={field.key}
              field={field}
              value={metadata[field.key]}
              onChange={(value) => changeMetadata(field.key, value)}
            />
          ))}
        </fieldset>
        {type === "lesson" && (
          <LessonBlocks
            sections={sections}
            onChange={(value) => {
              setSections(value);
              setDirty(true);
            }}
          />
        )}
        {(type === "lesson" || type === "module") && (
          <ObjectiveEditor
            objectives={objectives}
            onChange={(value) => {
              setObjectives(value);
              setDirty(true);
            }}
          />
        )}
        {type === "lab" && (
          <VirtualFiles
            value={metadata.virtualFiles}
            onChange={(value) => changeMetadata("virtualFiles", value)}
          />
        )}
        {type === "lab" && (
          <CommandResponses
            value={metadata.commandResponses}
            onChange={(value) => changeMetadata("commandResponses", value)}
          />
        )}
        {type === "mission" && (
          <MissionStages
            value={metadata.stages}
            onChange={(value) => changeMetadata("stages", value)}
          />
        )}
        <RelationshipPicker
          type={type}
          relationships={relationships}
          onChange={(value) => {
            setRelationships(value);
            setDirty(true);
          }}
        />
        <div className="cms-action-bar">
          <button className="primary" disabled={Boolean(immutable)}>
            Save draft
          </button>
          <button
            type="button"
            onClick={() => void validate()}
            disabled={!contentId}
          >
            Validate
          </button>
          <button
            type="button"
            onClick={() => void showPreview()}
            disabled={!contentId}
          >
            Preview learner view
          </button>
          {dirty && <span role="status">Unsaved changes</span>}
        </div>
      </form>
      {type === "lab" && contentId && (
        <aside className="cms-preview">
          <h2>Protected real lab terminal · preview mode</h2>
          <p>
            Commands execute through the deterministic lab engine. No learner
            evidence or credentials are created.
          </p>
          <Link
            className="primary"
            to={`/cms/preview/lab/${contentId}/${versionQuery.data?.version_id}`}
          >
            Launch full draft lab workspace
          </Link>
          <label>
            Command
            <input
              value={testCommand}
              onChange={(event) => setTestCommand(event.currentTarget.value)}
            />
          </label>
          <button onClick={() => void runDraftTest()}>Run draft command</button>
          {testOutput && <PreviewValue value={testOutput} />}
        </aside>
      )}
      {type === "mission" && contentId && (
        <aside className="cms-preview">
          <h2>Protected mission workspace · preview mode</h2>
          <p>
            This projection uses the configured stages without creating
            sessions, mastery, or portfolio evidence.
          </p>
          <Link
            className="primary"
            to={`/cms/preview/mission/${contentId}/${versionQuery.data?.version_id}`}
          >
            Launch full draft mission workspace
          </Link>
          <button onClick={() => void runDraftTest()}>
            Test mission projection
          </button>
          {testOutput && <PreviewValue value={testOutput} />}
        </aside>
      )}
      {versionQuery.data?.validation.length ? (
        <aside className="cms-validation" aria-label="Validation results">
          <h2>Validation results</h2>
          {versionQuery.data.validation.map((item) => (
            <article
              key={item.rule_id}
              className={`cms-validation-${item.state}`}
            >
              <strong>{item.explanation}</strong>
              <span>{item.field_location || "Content"}</span>
              {item.remediation && <p>{item.remediation}</p>}
            </article>
          ))}
        </aside>
      ) : null}
      {preview && (
        <aside className="cms-preview">
          <div>
            <h2>Learner-safe preview</h2>
            <button onClick={() => setPreview(null)}>Close preview</button>
          </div>
          <PreviewValue value={preview} />
        </aside>
      )}
    </CmsPage>
  );
}

function PreviewValue({ value }: { value: Record<string, unknown> }) {
  const sections = Array.isArray(value.sections)
    ? (value.sections as CmsSection[])
    : [];
  const metadata = (value.metadata ||
    (!sections.length ? value : {})) as Record<string, unknown>;
  return (
    <article>
      <span className="cms-draft-ribbon">DRAFT PREVIEW</span>
      <h1>{String(value.title || "Untitled")}</h1>
      <p>{String(value.description || "")}</p>
      {sections.map((section) => (
        <section key={section.key}>
          <h3>{section.title || section.type.replaceAll("_", " ")}</h3>
          <pre className="cms-preview-text">{section.body}</pre>
          {section.accessibilityLabel && (
            <small>Accessibility: {section.accessibilityLabel}</small>
          )}
        </section>
      ))}
      {!sections.length &&
        Object.entries(metadata)
          .filter(
            ([key]) =>
              ![
                "answerKey",
                "explanation",
                "partialCreditRules",
                "validationRules",
                "commandResponses",
                "title",
                "description",
              ].includes(key),
          )
          .map(([key, item]) => (
            <section key={key}>
              <h3>{key.replaceAll(/([A-Z])/g, " $1")}</h3>
              <p>
                {Array.isArray(item)
                  ? item.join(", ")
                  : typeof item === "object"
                    ? "Structured configuration available"
                    : String(item)}
              </p>
            </section>
          ))}
    </article>
  );
}
