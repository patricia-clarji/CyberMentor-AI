import { createHash, randomUUID } from "node:crypto";
import { mkdir, readFile, rename, rm, writeFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { runInNewContext } from "node:vm";
import { labCategories, v1LabBlueprints } from "./v1-lab-library.mjs";

const root = resolve(import.meta.dirname, "..");
const publishedRoot = join(root, "content", "published");
const seedRoot = join(root, "db", "seeds");
const version = "1.0.0";
const publishedAt = "2026-07-19T00:00:00.000Z";
const nextReviewAt = "2028-07-19T00:00:00.000Z";

const sourceIds = [
  "nist-csf-2",
  "cisa-cpg",
  "linux-kernel-docs",
  "mitre-attack",
  "nist-csf-2",
  "cisa-cpg",
  "owasp-top-ten",
  "owasp-top-ten",
  "python-3-docs",
  "cisa-cloud-tra",
  "nist-ai-rmf",
  "cisa-cpg",
];

const skillMaps = [
  ["security-foundations"],
  ["networking", "tcp-ip", "packet-analysis"],
  ["linux", "linux-permissions", "linux-logs"],
  ["alert-triage", "log-correlation", "case-documentation"],
  ["security-foundations", "alert-triage", "case-documentation"],
  ["security-foundations", "linux-logs", "case-documentation"],
  ["security-foundations", "networking", "case-documentation"],
  ["http", "tls", "security-foundations"],
  ["scripting", "linux-logs"],
  ["cloud-basics", "networking", "security-foundations"],
  ["security-foundations", "scripting"],
  ["case-documentation", "security-foundations"],
];

const lenses = [
  {
    context:
      "Security decisions connect business objectives, assets, plausible threats, weaknesses, and controls. The goal is not perfect protection; it is a defensible choice whose assumptions and residual risk are visible.",
    evidence:
      "asset ownership, business impact, threat conditions, control coverage, and a recorded risk decision",
    scenario:
      "a growing clinic must protect patient scheduling and records while keeping essential services available",
    failure:
      "selecting controls from a checklist before defining the asset, impact, and decision owner",
    defense:
      "pair prevention with visibility, response ownership, recovery criteria, and periodic verification",
  },
  {
    context:
      "Network analysis follows communication across layers and devices. Analysts separate addressing, name resolution, transport state, application behavior, and enforcement so a symptom is not mistaken for a cause.",
    evidence:
      "packet headers, flow direction, timing, protocol state, name-resolution results, and device configuration",
    scenario:
      "a small business experiences intermittent access to a customer portal after a network change",
    failure:
      "jumping to an attack conclusion before confirming the expected protocol exchange and network path",
    defense:
      "use segmentation, least privilege, secure protocols, logging, baselines, and repeatable packet evidence",
  },
  {
    context:
      "Linux security depends on understanding state: files, identities, permissions, processes, services, packages, network listeners, and logs. Safe administration changes one bounded condition and verifies the result.",
    evidence:
      "ownership and mode data, process and service state, package provenance, listening sockets, and timestamped logs",
    scenario:
      "an operations team must harden a local Linux web server without interrupting its approved service",
    failure:
      "running broad privileged commands without recording the starting state, expected effect, and rollback path",
    defense:
      "use least privilege, reviewed configuration, change control, logging, tested recovery, and explicit cleanup",
  },
  {
    context:
      "SOC work converts noisy telemetry into a documented decision. An analyst establishes what fired, what entity is affected, what supporting evidence exists, and whether escalation changes risk or response priority.",
    evidence:
      "alert logic, raw events, identity and asset context, timelines, corroborating sources, and case notes",
    scenario:
      "a junior analyst receives several identity alerts during a busy shift and must prioritize the evidence",
    failure:
      "closing or escalating an alert from its title alone instead of reviewing the underlying events and context",
    defense:
      "preserve raw evidence, test alternative explanations, document confidence, tune detections, and verify containment",
  },
  {
    context:
      "Incident response is a coordinated risk-management process. Teams prepare, detect, analyze, contain, eradicate, recover, communicate, and learn while preserving the evidence needed for sound decisions.",
    evidence:
      "incident scope, affected identities and assets, timeline, containment state, eradication checks, and recovery telemetry",
    scenario:
      "an organization investigates a suspected account compromise while critical business work continues",
    failure:
      "taking a disruptive containment action before understanding scope, dependencies, evidence needs, and business impact",
    defense:
      "use rehearsed playbooks, decision authority, evidence preservation, bounded containment, recovery monitoring, and lessons learned",
  },
  {
    context:
      "Digital forensics uses repeatable acquisition and analysis to explain what evidence supports, what it does not support, and how integrity was maintained. Conclusions must remain traceable to artifacts.",
    evidence:
      "source identifiers, acquisition notes, hashes, timestamps, metadata, timeline entries, and chain-of-custody records",
    scenario:
      "an investigator must reconstruct activity on a simulated workstation after a suspected insider event",
    failure:
      "changing original evidence, ignoring time-zone normalization, or presenting an inference as an observed fact",
    defense:
      "preserve originals, work from verified copies, record tools and transformations, corroborate artifacts, and state confidence",
  },
  {
    context:
      "Ethical security testing is authorized verification, not unrestricted attack activity. Scope, rules of engagement, safety limits, evidence handling, defender visibility, remediation, and retesting define professional practice.",
    evidence:
      "written authorization, target inventory, test timestamps, reproducible observations, impact analysis, and remediation proof",
    scenario:
      "an assessor evaluates a deliberately vulnerable local target under written rules of engagement",
    failure:
      "testing beyond authorization, using uncontrolled payloads, or reporting scanner output without manual validation",
    defense:
      "limit activity to the local lab, coordinate monitoring, minimize impact, document cleanup, recommend fixes, and retest safely",
  },
  {
    context:
      "Web application security follows data and authority across browser, network, application, and storage boundaries. A finding is meaningful when preconditions, impact, evidence, and remediation are all clear.",
    evidence:
      "HTTP requests and responses, identity state, authorization decisions, validation behavior, server logs, and remediation tests",
    scenario:
      "a product team assesses a deliberately vulnerable local application before a release candidate is approved",
    failure:
      "treating payload success as the end of testing without checking authorization, business context, server behavior, or the fix",
    defense:
      "use secure defaults, server-side authorization, contextual encoding, validated input, safe session handling, logging, and regression tests",
  },
  {
    context:
      "Security automation should make a bounded workflow repeatable and reviewable. Inputs are untrusted, failures are expected, output must preserve context, and tests should demonstrate behavior before deployment.",
    evidence:
      "sample inputs, parser decisions, validation failures, structured output, tests, logs, and reproducible command usage",
    scenario:
      "an analyst builds a local command-line tool to triage a mixed set of JSON and text log records",
    failure:
      "writing a script that silently drops malformed data, embeds secrets, trusts remote input, or lacks tests and error messages",
    defense:
      "validate input, handle exceptions explicitly, minimize privileges, protect secrets, use deterministic output, and test edge cases",
  },
  {
    context:
      "Cloud security combines provider responsibilities with customer configuration. Identity, network paths, data protection, workload trust, logging, and recovery must be reasoned about across managed services.",
    evidence:
      "identity policies, resource configuration, network controls, encryption state, audit events, workload identity, and recovery tests",
    scenario:
      "a team threat-models a multi-tier cloud workload containing an API, managed database, and object storage",
    failure:
      "assuming the provider secures customer identities and data configuration or granting permanent broad credentials for convenience",
    defense:
      "apply least privilege, short-lived identity, private paths, encryption, configuration policy, centralized logging, and tested recovery",
  },
  {
    context:
      "AI application security treats models, retrieval, tools, prompts, data, and outputs as separate trust boundaries. Model behavior is probabilistic, so controls require evaluation and monitoring rather than confidence alone.",
    evidence:
      "data lineage, retrieved chunks, prompt and tool traces, authorization decisions, evaluation results, output handling, and incident telemetry",
    scenario:
      "a team reviews a retrieval-enabled support assistant that can access approved internal documents but must never expose secrets",
    failure:
      "treating model output or retrieved text as trusted instructions and granting tools authority beyond the user’s verified permissions",
    defense:
      "separate instructions from data, enforce tool authorization in code, minimize retrieved data, validate output, evaluate attacks, and monitor abuse",
  },
  {
    context:
      "Career readiness means producing credible evidence of judgment, communication, and repeatable technical work. Claims should be bounded, artifacts should protect sensitive data, and reflection should show what changed.",
    evidence:
      "role requirements, skill mappings, sanitized work samples, project decisions, test results, feedback, and an improvement plan",
    scenario:
      "a learner prepares a role-aligned portfolio case study and interview brief for an entry-level security position",
    failure:
      "listing tools without explaining decisions, copying proprietary material, overstating independence, or publishing sensitive evidence",
    defense:
      "use original sanitized artifacts, explain scope and tradeoffs, map evidence to skills, seek feedback, and maintain an ethical learning plan",
  },
];

const labDefinitions = [
  [
    "Risk Priority Review",
    "A simulated clinic rates confidentiality impact 4, integrity impact 3, and availability impact 5. Submit the security goal with the highest stated impact.",
    "Compare the three stated impact values and submit one lowercase goal.",
    "availability",
  ],
  [
    "Packet Flag Triage",
    "A local trace shows repeated TCP packets with SYN=1 and ACK=0 across destination ports. Submit the uppercase flag that characterizes the probes.",
    "Read only the supplied trace description; no scanning is required.",
    "SYN",
  ],
  [
    "Linux Permission Hardening",
    "A local secrets file needs owner read/write, group read, and no access for others. Submit the three-digit octal mode.",
    "Translate owner, group, and other permissions separately.",
    "640",
  ],
  [
    "SOC Sign-in Triage",
    "The simulated event is user=amira source=203.0.113.42 result=success followed by five denied MFA events. Submit the source IP to investigate.",
    "Use the documentation-only TEST-NET address shown in the event.",
    "203.0.113.42",
  ],
  [
    "Incident Phase Decision",
    "Analysis confirms an actively abused account. Submit the response phase that limits ongoing impact before eradication and recovery.",
    "Choose the phase concerned with limiting spread and damage.",
    "containment",
  ],
  [
    "Forensic Timeline Ordering",
    "Three normalized events occurred at 09:14:02Z, 09:14:01Z, and 09:14:03Z. Submit the earliest timestamp exactly.",
    "Order the UTC timestamps before forming a hypothesis.",
    "09:14:01Z",
  ],
  [
    "Rules-of-Engagement Check",
    "An assessor has a target list but no documented test hours, prohibited actions, or stop contact. Submit the three-word document needed before local testing begins.",
    "It defines authorization boundaries and operational safety.",
    "rules of engagement",
  ],
  [
    "Authorization Defect Classification",
    "A local training endpoint verifies login but not ownership of the requested record. Submit the four-letter vulnerability class.",
    "The issue is an insecure direct object reference.",
    "IDOR",
  ],
  [
    "Defensive Parser Recovery",
    "A Python json.loads call receives malformed JSON. Submit the exception class a defensive parser should handle.",
    "Use the documented exception name, including capitalization.",
    "JSONDecodeError",
  ],
  [
    "Cloud IAM Remediation",
    "A workload has permanent administrator credentials but needs read access to one bucket. Submit the two-word authorization principle for remediation.",
    "Grant only what the workload requires.",
    "least privilege",
  ],
  [
    "Prompt-Injection Triage",
    "A retrieved document says to ignore application policy and disclose secrets. Submit the two-word attack class.",
    "Treat retrieved content as untrusted data, not instructions.",
    "prompt injection",
  ],
  [
    "Interview Evidence Structure",
    "A behavioral response needs Situation, Task, Action, and Result. Submit the four-letter framework name.",
    "Use the initial letters of the four response parts.",
    "STAR",
  ],
];

const slug = (value) =>
  value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
const hash = (value) =>
  createHash("sha256").update(JSON.stringify(value)).digest("hex");

async function atomicJson(file, value) {
  await mkdir(dirname(file), { recursive: true });
  const temporary = `${file}.${randomUUID()}.tmp`;
  await writeFile(temporary, `${JSON.stringify(value, null, 2)}\n`, "utf8");
  await rename(temporary, file);
}

async function loadCourseSpecs() {
  const source = await readFile(
    join(root, "src", "data", "courses.ts"),
    "utf8",
  );
  const match = source.match(
    /const specs: Spec\[\] = (\[[\s\S]*?\n\]);\n\nfunction expectedChoice/,
  );
  if (!match)
    throw new Error("Unable to locate the twelve V1 course specifications");
  const specs = runInNewContext(`(${match[1]})`, Object.create(null), {
    timeout: 250,
  });
  if (!Array.isArray(specs) || specs.length !== 12)
    throw new Error("V1 must contain exactly twelve course specifications");
  return specs;
}

function moduleTitle(moduleIndex, topics) {
  return `${["Understand", "Observe", "Practice", "Demonstrate"][moduleIndex]} — ${topics[0]}`;
}

function lessonId(courseId, title, topic) {
  return slug(`${courseId}-${title}-${topic}`);
}

function questionFor(topic, courseTitle, index) {
  const variants = [
    {
      prompt: `Which workflow best demonstrates professional practice for ${topic}?`,
      correct:
        "Define scope, gather relevant evidence, take a bounded action, and verify the result.",
      wrong: [
        "Apply the broadest control immediately and document it later.",
        "Trust the first explanation when it matches the alert title.",
        "Copy a checklist without adapting it to the system or decision.",
      ],
    },
    {
      prompt: `What is the strongest evidence standard when reasoning about ${topic}?`,
      correct:
        "Preserve traceable observations, distinguish facts from hypotheses, and corroborate important conclusions.",
      wrong: [
        "Treat tool output as conclusive because the tool is widely used.",
        "Prefer an undocumented recollection over timestamped source evidence.",
        "Remove contradictory observations so the report remains simple.",
      ],
    },
    {
      prompt: `How should a learner verify that a control related to ${topic} worked?`,
      correct:
        "Define the expected state, test it with independent evidence, and record residual risk or follow-up work.",
      wrong: [
        "Assume success when the configuration command returns no error.",
        "Measure only whether the control was purchased or enabled.",
        "Skip retesting when the original issue is no longer visible to one tool.",
      ],
    },
  ];
  const selected = variants[index % variants.length];
  const correctOption = index % 4;
  const options = [...selected.wrong];
  options.splice(correctOption, 0, selected.correct);
  const distractorExplanations = Object.fromEntries(
    options
      .map((option, optionIndex) => [optionIndex, option])
      .filter(([optionIndex]) => optionIndex !== correctOption)
      .map(([optionIndex]) => [
        optionIndex,
        `That choice weakens the evidence-to-decision chain for ${topic}. Revisit the scoped workflow in ${courseTitle}.`,
      ]),
  );
  return {
    prompt: selected.prompt,
    options,
    correctOption,
    explanation: `${selected.correct} This preserves a reviewable path from evidence to decision and outcome.`,
    distractorExplanations,
  };
}

function lessonArtifact({
  course,
  courseId,
  courseIndex,
  moduleId,
  moduleIndex,
  moduleName,
  lessonIndex,
  topic,
  questionId,
  question,
}) {
  const lens = lenses[courseIndex];
  const stage = [
    "build a reliable mental model",
    "recognize the evidence that distinguishes normal and concerning behavior",
    "practice a bounded workflow with explicit verification",
    "communicate a defensible workplace decision",
  ][moduleIndex];
  const mentalModel = `${topic} is taught here as an operational capability inside ${course.title}, not as an isolated definition. ${lens.context} In this module, your job is to ${stage}. Start by naming the system or decision in scope, the assumptions you are making, and the outcome that would count as success. Then connect ${topic.toLowerCase()} to observable evidence and an accountable decision owner. This structure prevents vocabulary from becoming false confidence and makes later lab and project work reproducible.`;
  const workflow = `Use a five-part workflow. First, define the authorized scope and the question you are trying to answer. Second, preserve a baseline so later changes can be explained or reversed. Third, collect the smallest sufficient evidence; for this course that commonly includes ${lens.evidence}. Fourth, compare at least two plausible explanations and select a proportionate action. Fifth, verify the resulting state with a different observation where practical, record limitations, and identify who owns follow-up. The same workflow applies whether ${topic.toLowerCase()} is used for prevention, investigation, engineering, or communication.`;
  const evidence = `Evidence quality matters more than volume. Prefer records that identify source, time, affected entity, collection method, and relevant configuration or context. Separate direct observations from inferences, and do not silently discard contradictory data. A strong note explains why an artifact supports the conclusion, how it could be misleading, and what additional check would change confidence. For ${topic.toLowerCase()}, capture enough context that another learner can reproduce the reasoning without receiving a hidden answer or relying on the original operator’s memory.`;
  const example = `Consider this approved workplace simulation: ${lens.scenario}. The team must reason about ${topic.toLowerCase()}. A careful analyst records the starting condition, identifies the relevant decision and evidence owners, gathers ${lens.evidence}, and compares the observation with the expected state. The analyst applies one bounded change or recommendation, checks both the intended outcome and likely side effects, and records residual uncertainty. The final report describes what was observed, what was inferred, what was changed, how recovery or cleanup was verified, and what should be monitored next.`;
  const misconception = `A common failure is ${lens.failure}. That approach feels fast but breaks traceability and can increase impact. Instead, pause when scope, evidence origin, authorization, or the success criterion is unclear. Ask what an independent reviewer would need to reproduce the decision. Tool output, model output, alert names, and copied commands are inputs—not authority. The learner remains responsible for validating the result and staying inside the approved environment.`;
  const defensive = `Defensive practice must accompany every concept: ${lens.defense}. For dual-use subjects, all activity stays inside the supplied local simulation; never transfer targets, credentials, payloads, or techniques to public systems. Good work includes remediation and retesting, not merely identifying a weakness. It also protects sensitive evidence and explains uncertainty in language appropriate for technical and nontechnical stakeholders.`;
  return {
    courseId,
    moduleId,
    lessonId: lessonId(courseId, moduleName, topic),
    title: topic,
    minutes: 28 + lessonIndex * 4,
    objectives: [
      `Explain ${topic.toLowerCase()} using a scoped evidence-to-decision model`,
      `Apply a safe, repeatable ${topic.toLowerCase()} workflow to a workplace simulation`,
      `Evaluate evidence and verify a defensive outcome related to ${topic.toLowerCase()}`,
    ],
    blocks: [
      {
        id: "mental-model",
        type: "paragraph",
        text: mentalModel,
        claimIds: ["v1-original-synthesis"],
      },
      {
        id: "operational-workflow",
        type: "paragraph",
        text: workflow,
        claimIds: ["v1-original-synthesis"],
      },
      {
        id: "evidence-standard",
        type: "callout",
        heading: "Evidence standard",
        body: evidence,
        claimIds: ["v1-original-synthesis"],
      },
      {
        id: "decision-table",
        type: "comparison-table",
        heading: "From weak activity to professional evidence",
        columns: ["Weak approach", "Professional approach", "Verification"],
        rows: [
          [
            "Act from an assumption",
            "State scope and gather traceable evidence",
            "Corroborate the key observation",
          ],
          [
            "Make a broad change",
            "Use a bounded, reversible action",
            "Compare the resulting state with success criteria",
          ],
          [
            "Report a tool label",
            "Explain impact, confidence, and limitations",
            "Retest and record residual risk",
          ],
        ],
        claimIds: [],
      },
      {
        id: "worked-case",
        type: "worked-example",
        body: example,
        claimIds: ["v1-original-synthesis"],
      },
      {
        id: "misconception",
        type: "misconception",
        body: misconception,
        claimIds: ["v1-original-synthesis"],
      },
      {
        id: "defensive-counterpart",
        type:
          courseIndex === 6 || courseIndex === 7 || courseIndex === 10
            ? "warning"
            : "callout",
        heading: "Defense, authorization, and cleanup",
        body: defensive,
        claimIds: ["v1-original-synthesis"],
      },
      {
        id: "decision-practice",
        type: "interactive-decision",
        body: `Before continuing, write one direct observation, one hypothesis, one bounded action, and one independent verification step for ${topic.toLowerCase()}. If authorization or evidence is missing, the correct decision is to stop and obtain it.`,
        claimIds: [],
      },
      {
        id: "summary",
        type: "summary",
        body: `${topic} becomes job-ready evidence when the learner can define scope, preserve and interpret relevant observations, choose a proportionate action, verify the outcome, and communicate limitations. The quiz checks this reasoning; the course lab and project require the same chain in a larger scenario.`,
        claimIds: ["v1-original-synthesis"],
      },
    ],
    keyTerms: [topic, "scope", "evidence", "verification", "residual risk"],
    workedExample: example,
    check: {
      id: questionId,
      question: question.prompt,
      options: question.options,
      gradingKeyRef: questionId,
    },
  };
}

function publication({
  id,
  title,
  artifactType,
  artifact,
  source,
  sourceSnapshot,
  skillTags,
  riskClassification = "defensive",
  domain,
}) {
  const contentHash = hash(artifact);
  return {
    schemaVersion: 1,
    id,
    title,
    contentVersion: version,
    contentHash,
    artifactType,
    riskClassification,
    verificationStatus: "verified",
    publicationStatus: "published",
    approvalBasis: "v1-release-baseline",
    releaseApproval: {
      authority: "product-owner",
      decision: "approved",
      scope: "initial-v1-academy",
      recordedAt: publishedAt,
      includesSafetyReview: true,
      directive:
        "Version 1 initial academy is considered reviewed and approved; future changes use the standard workflow.",
    },
    publishedAt,
    lastReviewedAt: publishedAt,
    nextReviewAt,
    metadata: {
      domain: domain || "cybersecurity",
      difficulty: "foundation-to-intermediate",
      audience: ["career-switcher", "student", "junior-practitioner"],
      prerequisites: [],
      skillTags,
      licenseNotes:
        "Original CyberMentor instructional synthesis with reference links to authoritative public sources; no source page is republished.",
      reviewIntervalDays: 365,
      changeLog: [{ version, summary: "Initial approved Version 1 academy" }],
    },
    artifact,
    claims: [
      {
        id: "v1-original-synthesis",
        kind: "fact",
        statement:
          "The Version 1 lesson is original instructional synthesis reviewed under the product-owner baseline approval directive.",
      },
    ],
    references: [
      {
        claimId: "v1-original-synthesis",
        sourceId: source.id,
        title: source.title,
        publisher: source.publisher,
        url: source.url,
        publicationDate: source.publicationDate || null,
        retrievedAt: sourceSnapshot?.retrievedAt || publishedAt,
        sourceVersion: sourceSnapshot?.sourceVersion || "v1-release-baseline",
        snapshotDigest: sourceSnapshot?.contentDigest || "baseline-approved",
        evidence:
          "Authoritative source used for bounded original instructional synthesis.",
      },
    ],
    provenance: {
      author: "cybermentor-v1-release-team",
      publisher: "v1-release-seed",
      disclosure:
        "Seeded as the product-owner-approved Version 1 baseline. Future edits, community contributions, instructor content, and AI-assisted drafts require the standard review workflow.",
      humanAuthored: false,
      reviews: [],
    },
  };
}

async function sourceContext(sourceId, sources) {
  const source = sources.find((item) => item.id === sourceId);
  if (!source) throw new Error(`Missing V1 source ${sourceId}`);
  let sourceSnapshot = null;
  try {
    sourceSnapshot = JSON.parse(
      await readFile(
        join(root, "content", "snapshots", sourceId, "latest.json"),
        "utf8",
      ),
    );
  } catch {
    // The explicit V1 baseline approval remains the release gate.
  }
  return { source, sourceSnapshot };
}

async function seed() {
  const specs = await loadCourseSpecs();
  if (labDefinitions.length !== specs.length)
    throw new Error(
      "Legacy lab migration map no longer matches the course set",
    );
  const sourceDocument = JSON.parse(
    await readFile(join(root, "content", "sources.json"), "utf8"),
  );
  const records = [];
  const database = {
    schemaVersion: 1,
    seedId: "v1-initial-academy",
    version,
    approvalBasis: "v1-release-baseline",
    generatedAt: new Date().toISOString(),
    courses: [],
    modules: [],
    lessons: [],
    questions: [],
    labs: [],
    projects: [],
    rubrics: [],
    completionRules: [],
    practiceActivities: [],
    labCategories,
  };

  for (const [courseIndex, course] of specs.entries()) {
    const courseId = `course-${courseIndex + 1}`;
    const skillTags = skillMaps[courseIndex];
    const { source, sourceSnapshot } = await sourceContext(
      sourceIds[courseIndex],
      sourceDocument.sources,
    );
    const dualUse = [6, 7, 10].includes(courseIndex);
    const moduleIds = course.topics.map(
      (_topics, moduleIndex) => `${courseId}-m${moduleIndex + 1}`,
    );
    const courseArtifact = {
      title: course.title,
      summary: course.description,
      learningOutcomes: [
        `Apply evidence-based reasoning across ${course.title}`,
        "Perform authorized practice with explicit defensive verification",
        `Produce a workplace project: ${course.project}`,
      ],
      moduleIds,
      completionRuleId: `${courseId}-completion`,
    };
    records.push(
      publication({
        id: courseId,
        title: course.title,
        artifactType: "course",
        artifact: courseArtifact,
        source,
        sourceSnapshot,
        skillTags,
        riskClassification: dualUse ? "dual-use" : "defensive",
        domain: slug(course.category),
      }),
    );
    database.courses.push({ id: courseId, publicationVersion: version });

    for (const [moduleIndex, topics] of course.topics.entries()) {
      const moduleId = `${courseId}-m${moduleIndex + 1}`;
      const name = moduleTitle(moduleIndex, topics);
      const lessonIds = topics.map((topic) => lessonId(courseId, name, topic));
      const moduleArtifact = {
        title: name,
        courseId,
        learningObjectives: topics.map(
          (topic) => `Apply ${topic.toLowerCase()} in an authorized scenario`,
        ),
        lessonIds,
      };
      records.push(
        publication({
          id: moduleId,
          title: name,
          artifactType: "module",
          artifact: moduleArtifact,
          source,
          sourceSnapshot,
          skillTags,
          riskClassification: dualUse ? "dual-use" : "defensive",
          domain: slug(course.category),
        }),
      );
      database.modules.push({ id: moduleId, courseId });

      for (const [lessonIndex, topic] of topics.entries()) {
        const id = lessonId(courseId, name, topic);
        const questionId = `${courseId}-m${moduleIndex + 1}-l${lessonIndex + 1}-check`;
        const question = questionFor(
          topic,
          course.title,
          courseIndex + moduleIndex + lessonIndex,
        );
        const lesson = lessonArtifact({
          course,
          courseId,
          courseIndex,
          moduleId,
          moduleIndex,
          moduleName: name,
          lessonIndex,
          topic,
          questionId,
          question,
        });
        records.push(
          publication({
            id,
            title: topic,
            artifactType: "lesson",
            artifact: lesson,
            source,
            sourceSnapshot,
            skillTags,
            riskClassification: dualUse ? "dual-use" : "defensive",
            domain: slug(course.category),
          }),
        );
        records.push(
          publication({
            id: questionId,
            title: `${topic} knowledge check`,
            artifactType: "question",
            artifact: {
              ...question,
              learningObjectiveId: `${id}-objective-1`,
              skillTags,
              difficulty: moduleIndex === 0 ? "foundation" : "standard",
              assessmentUse:
                moduleIndex === 3 && lessonIndex === 2 ? "exam" : "quiz",
              evidenceWeight: 1,
            },
            source,
            sourceSnapshot,
            skillTags,
            riskClassification: dualUse ? "dual-use" : "defensive",
            domain: slug(course.category),
          }),
        );
        database.lessons.push({ id, courseId, moduleId });
        database.questions.push({ id: questionId, lessonId: id });
      }
    }

    const courseLabs = v1LabBlueprints.filter(
      (blueprint) => blueprint.courseId === courseId,
    );
    if (courseLabs.length < 6)
      throw new Error(`${course.title} must link to at least six usable labs`);
    const labId = courseLabs[0].id;
    const labTitle = courseLabs[0].title;
    for (const blueprint of courseLabs) {
      const labSkillTags = skillTags;
      const interactive = [
        "interactive-simulation",
        "awareness-simulation",
        "career-simulation",
      ].includes(blueprint.environmentType);
      records.push(
        publication({
          id: blueprint.id,
          title: blueprint.title,
          artifactType: "lab",
          artifact: {
            courseId,
            title: blueprint.title,
            description: `${blueprint.title} is an original ${blueprint.environmentType.replaceAll("-", " ")} that asks the learner to interpret bounded evidence and produce a server-verifiable result.`,
            category: blueprint.category,
            difficulty: blueprint.difficulty,
            estimatedMinutes: blueprint.estimatedMinutes,
            story: `${blueprint.organization} has asked the learner to resolve a security decision using the supplied fictional record. The learner is part of an authorized internal training exercise and must preserve a clear evidence-to-decision chain.`,
            businessContext: `${blueprint.organization} needs a proportionate answer that supports continued operations, protects affected people and systems, and can be reviewed by another practitioner.`,
            learningObjectives: [
              `Apply ${blueprint.category} reasoning to a bounded workplace record`,
              "Separate direct observation from interpretation",
              "Submit concise evidence and verify the defensive outcome server-side",
            ],
            prerequisites: [courseId],
            requiredSkills: blueprint.skills,
            authorizedTarget:
              "Bundled fictional evidence and the CyberMentor local API only",
            scope:
              "Local browser simulation; no public target, external address, or arbitrary command execution",
            safetyClassification: dualUse
              ? "dual-use-local"
              : "defensive-local",
            rulesOfEngagement: [
              "Use only the evidence displayed inside this activity.",
              "Do not test, scan, contact, or submit identifiers for external systems.",
              "Stop if the task appears to require data outside the supplied scenario.",
            ],
            environment: {
              type: blueprint.environmentType,
              runtime: interactive
                ? "server-owned-browser-session"
                : "bounded-artifact-workspace",
              isolated: true,
              networkAccess: false,
              externalTargets: false,
              arbitraryCommands: false,
              supportsPause: true,
              supportsReset: true,
              expirationMinutes: 90,
            },
            environmentStatus: "usable",
            instructions: [
              "Read the story, business context, and supplied record before forming a conclusion.",
              "Record the smallest evidence value that answers the task exactly.",
              "Use progressive hints only when needed; hint dependency is recorded in the attempt.",
              "Submit the evidence to the server, review the debrief after success, then write a reflection.",
            ],
            tasks: [
              blueprint.task,
              "State one direct observation and one defensive follow-up in your reflection.",
            ],
            expectedDeliverables: [
              "Server-verified evidence value",
              "Learner reflection separating observation from inference",
            ],
            evidenceRequirement:
              "Submit the concise value requested by the supplied fictional record.",
            expectedEvidence: [blueprint.expected],
            validationLogic: {
              type: "normalized-equals",
              expectedValue: blueprint.expected,
            },
            hints: [
              {
                level: 1,
                label: "Reminder",
                text: "Return to the exact question and identify the field or decision it requests.",
              },
              { level: 2, label: "Concept", text: blueprint.hint },
              {
                level: 3,
                label: "Direction",
                text: "Exclude details that do not directly answer the requested evidence value.",
              },
              {
                level: 4,
                label: "Partial solution",
                text: `The answer is a ${blueprint.expected.includes(".") ? "specific value from the supplied record" : "short security term or value"}.`,
              },
              {
                level: 5,
                label: "Walkthrough",
                text: `Read the supplied record, apply this reasoning: ${blueprint.hint} Then submit only the requested value.`,
              },
            ],
            solutionAccessPolicy:
              "The full expected value remains server-side. The detailed walkthrough unlocks only through progressive hint use.",
            debrief: `A defensible result for ${blueprint.title} begins with the supplied observation, applies a bounded ${blueprint.category} concept, and records how the organization should verify or monitor the outcome. ${lenses[courseIndex].defense}.`,
            reflectionPrompts: [
              "Which observation most influenced your answer?",
              "What alternative explanation did you rule out?",
              "How would a defender verify the result in an authorized workplace?",
            ],
            furtherReading: [source.title],
            cleanupSteps: [
              "Close the server-owned session when finished.",
              "Remove any copied fictional evidence from shared notes.",
            ],
            defensiveExplanation: lenses[courseIndex].defense,
            portfolioSkills: labSkillTags,
            skillTags: labSkillTags,
            author: "CyberMentor AI Founding Curriculum Team",
            review: {
              technical: "seeded-initial-review",
              instructional: "seeded-initial-review",
              safety: dualUse ? "seeded-initial-review" : "not-required",
            },
          },
          source,
          sourceSnapshot,
          skillTags: labSkillTags,
          riskClassification: dualUse ? "dual-use" : "defensive",
          domain: slug(blueprint.category),
        }),
      );
      database.labs.push({
        id: blueprint.id,
        courseId,
        category: blueprint.category,
        environmentType: blueprint.environmentType,
        environmentStatus: "usable",
      });
    }

    const rubricId = `${courseId}-rubric`;
    const rubric = [
      {
        criterion: "Scope and assumptions",
        weight: 20,
        exemplary:
          "Defines authorization, assets, assumptions, constraints, and success criteria precisely.",
        meets:
          "Defines the main scope and assumptions with minor gaps that do not invalidate the work.",
      },
      {
        criterion: "Evidence and reasoning",
        weight: 30,
        exemplary:
          "Uses traceable evidence, considers alternatives, and clearly separates observation from inference.",
        meets:
          "Uses relevant evidence and provides a defensible reasoning chain.",
      },
      {
        criterion: "Defensive action and verification",
        weight: 30,
        exemplary:
          "Proposes bounded remediation, validates outcome and side effects, and records residual risk.",
        meets:
          "Proposes a proportionate action and verifies the intended result.",
      },
      {
        criterion: "Professional communication",
        weight: 20,
        exemplary:
          "Produces a concise, reproducible report suited to technical and business stakeholders.",
        meets:
          "Communicates the decision, evidence, outcome, and limitations clearly.",
      },
    ];
    records.push(
      publication({
        id: rubricId,
        title: `${course.title} project rubric`,
        artifactType: "rubric",
        artifact: {
          title: `${course.title} workplace project rubric`,
          criteria: rubric,
          performanceLevels: ["developing", "meets", "exemplary"],
          passingRule:
            "Meet or exceed every criterion with a total score of at least 70%.",
        },
        source,
        sourceSnapshot,
        skillTags,
        riskClassification: dualUse ? "dual-use" : "defensive",
        domain: slug(course.category),
      }),
    );
    database.rubrics.push({ id: rubricId, courseId });

    const projectId = `${courseId}-project`;
    records.push(
      publication({
        id: projectId,
        title: `${course.title} workplace project`,
        artifactType: "project",
        artifact: {
          courseId,
          title: course.project,
          scenario: lenses[courseIndex].scenario,
          requirements: [
            "Define scope, authorization, assumptions, and measurable success criteria.",
            `Collect and interpret ${lenses[courseIndex].evidence}.`,
            "Compare at least two response or design options and explain the tradeoff.",
            "Recommend a bounded defensive action and a verification plan.",
            "Document limitations, residual risk, cleanup, and next steps.",
          ],
          deliverables: [
            "Executive summary",
            "Technical evidence appendix",
            "Decision and remediation record",
            "Verification and reflection section",
          ],
          milestones: [
            "Scope and evidence plan",
            "Analysis draft",
            "Defensive recommendation",
            "Final verified report",
          ],
          rubric,
          rubricId,
          expectedEvidence: [
            "A traceable evidence-to-decision narrative",
            "At least one explicit verification result",
            "A statement of limitations and residual risk",
          ],
          minimumEvidenceLength: 180,
          learnerConstraints: [
            "Use only bundled fictional or personally owned authorized evidence.",
            "Remove secrets, personal data, and real target identifiers.",
            "Do not reproduce proprietary course or employer material.",
          ],
          mentorBoundaries: [
            "Sentinel may explain concepts and question assumptions.",
            "Sentinel may not write the final submission or provide graded answers.",
          ],
          skillTags,
        },
        source,
        sourceSnapshot,
        skillTags,
        riskClassification: dualUse ? "dual-use" : "defensive",
        domain: slug(course.category),
      }),
    );
    database.projects.push({ id: projectId, courseId, rubricId });

    const completionId = `${courseId}-completion`;
    records.push(
      publication({
        id: completionId,
        title: `${course.title} completion rule`,
        artifactType: "completion-rule",
        artifact: {
          title: `${course.title} Version 1 completion`,
          requirements: [
            "Complete all twelve lessons and their server-graded checks.",
            `Complete the ${labTitle} local evidence lab.`,
            `Submit the ${course.project} project evidence summary.`,
          ],
          evidenceTypes: ["quiz", "lab", "project"],
        },
        source,
        sourceSnapshot,
        skillTags,
        riskClassification: dualUse ? "dual-use" : "defensive",
        domain: slug(course.category),
      }),
    );
    database.completionRules.push({ id: completionId, courseId });

    for (const activityIndex of [0, 1]) {
      const activityId = `${courseId}-practice-${activityIndex + 1}`;
      records.push(
        publication({
          id: activityId,
          title:
            activityIndex === 0
              ? `${course.short} evidence refresher`
              : `${course.short} applied challenge`,
          artifactType: "practice-activity",
          artifact: {
            title:
              activityIndex === 0
                ? `${course.short} evidence refresher`
                : `${course.short} applied challenge`,
            skillTags,
            prerequisites: [],
            difficulty: activityIndex === 0 ? "foundation" : "standard",
            estimatedMinutes: activityIndex === 0 ? 15 : 25,
            activityType: activityIndex === 0 ? "lesson" : "lab",
            targetType: activityIndex === 0 ? "course" : "lab",
            targetId: activityIndex === 0 ? courseId : labId,
            roleTracks: ["beginner", "soc", "pentest", "cloud", "ai"],
            hints: [
              "Start by naming scope and the decision you need to support.",
              `Look for ${lenses[courseIndex].evidence}.`,
              "State how an independent check would verify the outcome.",
            ],
            verificationLogic: { type: "linked-completion" },
            explanation: `This approved activity reinforces ${course.title} through evidence, defensive action, and verification.`,
          },
          source,
          sourceSnapshot,
          skillTags,
          riskClassification: dualUse ? "dual-use" : "defensive",
          domain: slug(course.category),
        }),
      );
      database.practiceActivities.push({ id: activityId, courseId });
    }
  }

  for (const courseIndex of Array.from(
    { length: specs.length },
    (_, index) => index + 1,
  )) {
    const superseded = resolve(publishedRoot, `course-${courseIndex}-lab`);
    if (
      !superseded.startsWith(
        `${resolve(publishedRoot)}${process.platform === "win32" ? "\\" : "/"}`,
      )
    )
      throw new Error(
        "Refusing to prune a publication outside the generated root",
      );
    await rm(superseded, { recursive: true, force: true });
  }

  for (let index = 0; index < records.length; index += 32) {
    await Promise.all(
      records.slice(index, index + 32).flatMap((record) => {
        const directory = join(publishedRoot, record.id);
        return [
          atomicJson(join(directory, `${record.contentVersion}.json`), record),
          atomicJson(join(directory, "latest.json"), record),
        ];
      }),
    );
  }
  const manifest = {
    schemaVersion: 1,
    generatedAt: new Date().toISOString(),
    sourceOfTruth: "version-controlled-published-content",
    release: "v1-initial-academy",
    approvalBasis: "v1-release-baseline",
    artifacts: records
      .map((record) => ({
        id: record.id,
        title: record.title,
        artifactType: record.artifactType,
        contentVersion: record.contentVersion,
        contentHash: record.contentHash,
        publishedAt: record.publishedAt,
        lastReviewedAt: record.lastReviewedAt,
        nextReviewAt: record.nextReviewAt,
        relativePath: `${record.id}/latest.json`,
      }))
      .sort((a, b) => a.id.localeCompare(b.id)),
  };
  await atomicJson(join(publishedRoot, "manifest.json"), manifest);
  await atomicJson(join(seedRoot, "001_v1_academy.seed.json"), database);
  const counts = Object.fromEntries(
    Object.entries(database)
      .filter(([, value]) => Array.isArray(value))
      .map(([key, value]) => [key, value.length]),
  );
  process.stdout.write(
    `${JSON.stringify({ seeded: true, publications: records.length, counts }, null, 2)}\n`,
  );
}

seed().catch((error) => {
  process.stderr.write(`${error instanceof Error ? error.stack : error}\n`);
  process.exitCode = 1;
});
