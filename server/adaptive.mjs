const weights = {
  "lesson-check": 0.2,
  quiz: 0.45,
  exam: 0.65,
  lab: 0.8,
  scenario: 0.7,
  project: 0.9,
  retention: 0.75,
  "command-recall": 0.12,
};

const practicalTypes = new Set(["lab", "scenario", "project"]);
const theoryTypes = new Set([
  "lesson",
  "explanation-variant",
  "lesson-check",
  "quiz",
  "exam",
  "retention",
]);

const clamp = (value, minimum = 0, maximum = 1) =>
  Math.min(maximum, Math.max(minimum, value));

export function updateMastery(previous, evidence, now = new Date()) {
  const accepted = evidence.filter(
    (item) =>
      weights[item.sourceType] &&
      Number.isFinite(item.score) &&
      item.score >= 0 &&
      item.score <= 1,
  );
  if (!accepted.length)
    return {
      ...previous,
      masteryEstimate: clamp(previous.masteryEstimate || 0),
      masteryConfidence: clamp(previous.masteryConfidence || 0),
    };
  let weightedScore = 0;
  let totalWeight = 0;
  const sourceTypes = new Set();
  for (const item of accepted) {
    const independence = clamp(item.independenceLevel ?? 1, 0.25, 1);
    const attemptPenalty = 1 / Math.max(1, item.attempts || 1);
    const hintPenalty = clamp(1 - (item.hintsUsed || 0) * 0.08, 0.5, 1);
    const evidenceWeight =
      weights[item.sourceType] *
      independence *
      attemptPenalty *
      hintPenalty *
      clamp(item.evidenceWeight ?? 1, 0.1, 1);
    weightedScore += item.score * evidenceWeight;
    totalWeight += evidenceWeight;
    sourceTypes.add(item.sourceType);
  }
  const observed = totalWeight ? weightedScore / totalWeight : 0;
  const priorConfidence = clamp(previous.masteryConfidence || 0);
  const newEvidenceConfidence =
    (1 - Math.exp(-totalWeight / 1.7)) *
    Math.min(1, accepted.length / 3) *
    Math.min(1, sourceTypes.size / 2);
  const combinedConfidence = clamp(
    1 - (1 - priorConfidence) * (1 - newEvidenceConfidence),
    0,
    0.98,
  );
  const priorInfluence = priorConfidence * 2;
  const masteryEstimate = clamp(
    ((previous.masteryEstimate || 0) * priorInfluence +
      observed * totalWeight) /
      Math.max(0.001, priorInfluence + totalWeight),
  );
  const latest = accepted
    .map((item) => Date.parse(item.occurredAt || ""))
    .filter(Number.isFinite)
    .sort((a, b) => b - a)[0];
  return {
    ...previous,
    masteryEstimate,
    masteryConfidence: combinedConfidence,
    evidenceCount: (previous.evidenceCount || 0) + accepted.length,
    lastPracticedAt: latest
      ? new Date(latest).toISOString()
      : now.toISOString(),
    quizAccuracy: averageFor(accepted, new Set(["quiz", "exam"])),
    labPerformance: averageFor(accepted, new Set(["lab"])),
    scenarioPerformance: averageFor(accepted, new Set(["scenario"])),
    projectEvidence: accepted.filter((item) => item.sourceType === "project")
      .length,
    averageHintsUsed: average(accepted.map((item) => item.hintsUsed || 0)),
    averageAttempts: average(accepted.map((item) => item.attempts || 1)),
    timeOnTaskSeconds: accepted.reduce(
      (total, item) => total + Math.max(0, item.durationSeconds || 0),
      0,
    ),
  };
}

function average(values) {
  return values.length
    ? values.reduce((total, value) => total + value, 0) / values.length
    : null;
}

function averageFor(evidence, types) {
  return average(
    evidence
      .filter((item) => types.has(item.sourceType))
      .map((item) => item.score),
  );
}

export function masteryWithRecency(state, now = new Date()) {
  const practiced = Date.parse(state.lastPracticedAt || "");
  if (!Number.isFinite(practiced)) return state;
  const inactiveDays = Math.max(0, (now.getTime() - practiced) / 86_400_000);
  const recencyFactor = clamp(Math.exp(-inactiveDays / 365), 0.72, 1);
  return {
    ...state,
    recencyFactor,
    masteryEstimate: clamp(state.masteryEstimate * recencyFactor),
    masteryConfidence: clamp(
      state.masteryConfidence * Math.sqrt(recencyFactor),
    ),
  };
}

function published(activity) {
  return (
    activity.publicationStatus === "published" &&
    activity.verificationStatus === "verified"
  );
}

function prerequisiteReady(activity, skills) {
  return (activity.prerequisites || []).every((requirement) => {
    const state = skills[requirement.skillId];
    return (
      state &&
      state.masteryEstimate >= requirement.minimumMastery &&
      state.masteryConfidence >= 0.45
    );
  });
}

function skillGap(activity, skills) {
  const states = (activity.skillTags || [])
    .map((skill) => skills[skill])
    .filter(Boolean);
  return states.length
    ? average(
        states.map(
          (state) =>
            1 -
            state.masteryEstimate *
              (0.4 + 0.6 * clamp(state.masteryConfidence)),
        ),
      )
    : 0.5;
}

function difficultyFit(activity, skills) {
  const mastery = 1 - skillGap(activity, skills);
  const target = {
    foundation: 0.2,
    guided: 0.35,
    standard: 0.55,
    advanced: 0.78,
    "expert-challenge": 0.9,
  }[activity.difficulty];
  return 1 - Math.min(1, Math.abs(mastery - (target ?? 0.5)));
}

export function recommendActivities({
  skills,
  activities,
  goals = [],
  roleTrack,
  timeAvailable = 60,
  recentMistakes = [],
  failureCounts = {},
  instructorPolicy = {},
  now = new Date(),
  limit = 5,
}) {
  const normalizedSkills = Object.fromEntries(
    Object.entries(skills).map(([id, state]) => [
      id,
      masteryWithRecency(state, now),
    ]),
  );
  const newLearner = Object.keys(normalizedSkills).length === 0;
  const candidates = activities
    .filter(published)
    .filter(
      (activity) =>
        instructorPolicy.mandatoryActivityIds?.includes(activity.id) ||
        (newLearner &&
          activity.difficulty === "foundation" &&
          !(activity.prerequisites || []).length) ||
        (activity.skillTags || []).some(
          (skill) =>
            skill in normalizedSkills ||
            goals.includes(skill) ||
            recentMistakes.includes(skill),
        ),
    )
    .filter(
      (activity) =>
        activity.estimatedMinutes <= timeAvailable ||
        instructorPolicy.mandatoryActivityIds?.includes(activity.id),
    )
    .map((activity) => {
      const mandatory =
        instructorPolicy.mandatoryActivityIds?.includes(activity.id) || false;
      const ready = prerequisiteReady(activity, normalizedSkills);
      const gap = skillGap(activity, normalizedSkills);
      const goalMatch = (activity.skillTags || []).some((skill) =>
        goals.includes(skill),
      );
      const roleMatch = activity.roleTracks?.includes(roleTrack);
      const mistakeMatch = (activity.skillTags || []).some((skill) =>
        recentMistakes.includes(skill),
      );
      const repeatedFailure = (activity.skillTags || []).some(
        (skill) => (failureCounts[skill] || 0) >= 3,
      );
      const taggedMasteries = (activity.skillTags || [])
        .map((skill) => normalizedSkills[skill]?.masteryEstimate)
        .filter(Number.isFinite);
      const crossDomainBridge =
        taggedMasteries.some((mastery) => mastery >= 0.75) &&
        taggedMasteries.some((mastery) => mastery < 0.5);
      const practicalNeed =
        Object.values(normalizedSkills).some((state) =>
          state.recentMistakePatterns?.includes("weak-practical-work"),
        ) && practicalTypes.has(activity.activityType);
      const theoryNeed =
        Object.values(normalizedSkills).some((state) =>
          state.recentMistakePatterns?.includes("command-recall-only"),
        ) && theoryTypes.has(activity.activityType);
      const returningAfterInactivity =
        activity.activityType === "retention" &&
        Object.values(normalizedSkills).some(
          (state) => (state.recencyFactor || 1) < 0.9,
        );
      const score =
        (mandatory ? 10 : 0) +
        (ready ? 1.2 : -1.8) +
        gap * 3 +
        difficultyFit(activity, normalizedSkills) * 1.4 +
        (goalMatch ? 0.8 : 0) +
        (roleMatch ? 0.5 : 0) +
        (mistakeMatch ? 1.1 : 0) +
        (repeatedFailure ? 1.5 : 0) +
        (crossDomainBridge ? 0.7 : 0) +
        (practicalNeed ? 1.4 : 0) +
        (theoryNeed ? 1.4 : 0) +
        (returningAfterInactivity ? 1.6 : 0);
      return {
        activity,
        score,
        ready,
        reason: recommendationReason({
          activity,
          gap,
          mandatory,
          ready,
          mistakeMatch,
          repeatedFailure,
          crossDomainBridge,
          practicalNeed,
          theoryNeed,
          returningAfterInactivity,
          normalizedSkills,
        }),
      };
    })
    .filter((candidate) => candidate.ready || candidate.score >= 9)
    .sort(
      (a, b) => b.score - a.score || a.activity.id.localeCompare(b.activity.id),
    )
    .slice(0, limit);
  return candidates.map(({ activity, score, reason }) => ({
    activityId: activity.id,
    activityType: activity.activityType,
    difficulty: activity.difficulty,
    title: activity.title,
    reason,
    priority: Number(score.toFixed(3)),
    hintStartLevel: hintStartLevel(activity, normalizedSkills),
    instructorFlag: (activity.skillTags || []).some(
      (skill) => (failureCounts[skill] || 0) >= 3,
    ),
    engineVersion: "rules-1.0.0",
  }));
}

function recommendationReason({
  activity,
  gap,
  mandatory,
  ready,
  mistakeMatch,
  repeatedFailure,
  crossDomainBridge,
  practicalNeed,
  theoryNeed,
  returningAfterInactivity,
  normalizedSkills,
}) {
  if (mandatory) return "Assigned by your instructor as required work.";
  if (repeatedFailure)
    return "Recommended as a targeted prerequisite intervention after repeated difficulty; an instructor review flag is included.";
  if (!ready)
    return "A prerequisite intervention was selected before the dependent activity.";
  if (mistakeMatch)
    return `Recommended because recent evidence shows difficulty with ${activity.skillTags.join(", ")}.`;
  if (practicalNeed)
    return "Recommended to convert strong theory into supervised practical evidence.";
  if (theoryNeed)
    return "Recommended to strengthen conceptual reasoning beyond command recall.";
  if (returningAfterInactivity)
    return "Recommended as a short retention check after an extended break; prior progress is preserved.";
  if (crossDomainBridge)
    return "Recommended to connect a demonstrated strength to a developing skill using an approved explanation variant.";
  const weakest = (activity.skillTags || [])
    .map((id) => ({ id, mastery: normalizedSkills[id]?.masteryEstimate ?? 0 }))
    .sort((a, b) => a.mastery - b.mastery)[0];
  return gap > 0.55
    ? `Recommended to develop ${weakest?.id || "a required skill"} using approved material.`
    : "Recommended as an appropriate next challenge based on current evidence.";
}

export function hintStartLevel(activity, skills) {
  const mastery = 1 - skillGap(activity, skills);
  if (mastery < 0.35) return 2;
  if (mastery < 0.6) return 1;
  return 0;
}

export function nextHint(activity, usedLevels, skills) {
  const start = hintStartLevel(activity, skills);
  const nextIndex = Math.max(0, start - 1, usedLevels.length);
  return activity.hints?.[nextIndex] || null;
}

export function selectDiagnosticQuestion({
  questions,
  skillId,
  recentResults = [],
}) {
  const approved = questions.filter(
    (question) =>
      published(question) &&
      question.skillTags.includes(skillId) &&
      question.assessmentUse === "diagnostic",
  );
  if (!approved.length) return null;
  if (recentResults.length >= 3) {
    const accuracy = average(recentResults.slice(-3).map((item) => item.score));
    if (accuracy === 0 || accuracy === 1) return null;
  }
  const recent = recentResults.slice(-2);
  const level =
    recent.length === 2 && recent.every((item) => item.score >= 0.8)
      ? "advanced"
      : recent.length === 2 && recent.every((item) => item.score < 0.5)
        ? "foundation"
        : "standard";
  return (
    approved.find(
      (question) =>
        question.difficulty === level &&
        !recentResults.some((result) => result.sourceId === question.id),
    ) ||
    approved.find(
      (question) =>
        !recentResults.some((result) => result.sourceId === question.id),
    ) ||
    null
  );
}

export function decisionLog(input, recommendations, now = new Date()) {
  return {
    decisionType: "adaptive-recommendation",
    selectedItemIds: recommendations.map((item) => item.activityId),
    candidateSummary: {
      approvedCandidates: input.activities.filter(published).length,
      selected: recommendations.length,
    },
    inputFeatures: {
      skillIds: Object.keys(input.skills),
      goals: input.goals || [],
      roleTrack: input.roleTrack || null,
      timeAvailable: input.timeAvailable || 60,
      recentMistakes: input.recentMistakes || [],
      failureCounts: input.failureCounts || {},
    },
    explanation: recommendations.map((item) => item.reason),
    engineVersion: "rules-1.0.0",
    createdAt: now.toISOString(),
  };
}
