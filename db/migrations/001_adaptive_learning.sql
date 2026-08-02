BEGIN;

CREATE TABLE skill (
  id text PRIMARY KEY,
  parent_skill_id text REFERENCES skill(id),
  name text NOT NULL,
  domain text NOT NULL,
  description text NOT NULL,
  difficulty text NOT NULL,
  version text NOT NULL
);

CREATE TABLE skill_prerequisite (
  skill_id text NOT NULL REFERENCES skill(id),
  prerequisite_skill_id text NOT NULL REFERENCES skill(id),
  minimum_mastery numeric(4,3) NOT NULL CHECK (minimum_mastery BETWEEN 0 AND 1),
  PRIMARY KEY (skill_id, prerequisite_skill_id),
  CHECK (skill_id <> prerequisite_skill_id)
);

CREATE TABLE learning_objective (
  id text PRIMARY KEY,
  course_id text NOT NULL,
  module_id text NOT NULL,
  lesson_id text NOT NULL,
  description text NOT NULL,
  skill_id text NOT NULL REFERENCES skill(id)
);

CREATE TABLE learner_skill_state (
  organization_id uuid NOT NULL,
  learner_id uuid NOT NULL,
  skill_id text NOT NULL REFERENCES skill(id),
  mastery_estimate numeric(4,3) NOT NULL CHECK (mastery_estimate BETWEEN 0 AND 1),
  mastery_confidence numeric(4,3) NOT NULL CHECK (mastery_confidence BETWEEN 0 AND 1),
  evidence_count integer NOT NULL DEFAULT 0 CHECK (evidence_count >= 0),
  last_practiced_at timestamptz,
  next_review_at timestamptz,
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, learner_id, skill_id)
);

CREATE TABLE mastery_evidence (
  id uuid PRIMARY KEY,
  organization_id uuid NOT NULL,
  learner_id uuid NOT NULL,
  skill_id text NOT NULL REFERENCES skill(id),
  source_type text NOT NULL,
  source_id text NOT NULL,
  score numeric(4,3) NOT NULL CHECK (score BETWEEN 0 AND 1),
  independence_level numeric(4,3) NOT NULL CHECK (independence_level BETWEEN 0 AND 1),
  hints_used integer NOT NULL DEFAULT 0 CHECK (hints_used >= 0),
  attempts integer NOT NULL DEFAULT 1 CHECK (attempts > 0),
  duration_seconds integer NOT NULL DEFAULT 0 CHECK (duration_seconds >= 0),
  evidence_weight numeric(4,3) NOT NULL CHECK (evidence_weight BETWEEN 0 AND 1),
  occurred_at timestamptz NOT NULL,
  UNIQUE (organization_id, learner_id, skill_id, source_type, source_id, occurred_at)
);

CREATE TABLE practice_activity (
  id text PRIMARY KEY,
  activity_type text NOT NULL,
  difficulty text NOT NULL,
  estimated_minutes integer NOT NULL CHECK (estimated_minutes > 0),
  version text NOT NULL,
  publication_status text NOT NULL CHECK (publication_status IN ('draft', 'approved', 'published', 'retired'))
);

CREATE TABLE practice_activity_skill (
  activity_id text NOT NULL REFERENCES practice_activity(id),
  skill_id text NOT NULL REFERENCES skill(id),
  weight numeric(4,3) NOT NULL CHECK (weight > 0 AND weight <= 1),
  PRIMARY KEY (activity_id, skill_id)
);

CREATE TABLE adaptive_recommendation (
  id uuid PRIMARY KEY,
  organization_id uuid NOT NULL,
  learner_id uuid NOT NULL,
  activity_id text NOT NULL REFERENCES practice_activity(id),
  reason_code text NOT NULL,
  reason_text text NOT NULL,
  priority numeric NOT NULL,
  status text NOT NULL CHECK (status IN ('active', 'dismissed', 'accepted', 'expired', 'overridden')),
  generated_at timestamptz NOT NULL,
  expires_at timestamptz NOT NULL
);

CREATE TABLE adaptive_decision_log (
  id uuid PRIMARY KEY,
  organization_id uuid NOT NULL,
  learner_id uuid NOT NULL,
  decision_type text NOT NULL,
  selected_item_id text,
  candidate_summary jsonb NOT NULL,
  input_features jsonb NOT NULL,
  explanation text NOT NULL,
  engine_version text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (NOT (input_features ? 'chain_of_thought'))
);

CREATE TABLE instructor_adaptive_policy (
  organization_id uuid NOT NULL,
  learner_id uuid NOT NULL,
  instructor_id uuid NOT NULL,
  practice_mode text NOT NULL CHECK (practice_mode IN ('fixed', 'adaptive-practice', 'adaptive-low-stakes')),
  disable_skipping boolean NOT NULL DEFAULT false,
  minimum_mastery numeric(4,3) CHECK (minimum_mastery BETWEEN 0 AND 1),
  mandatory_activity_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
  forced_prerequisite_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
  accommodation_notes text,
  override_note text,
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, learner_id)
);

CREATE INDEX mastery_evidence_learner_skill_time
  ON mastery_evidence (organization_id, learner_id, skill_id, occurred_at DESC);
CREATE INDEX adaptive_recommendation_learner_status
  ON adaptive_recommendation (organization_id, learner_id, status, priority DESC);

COMMIT;
