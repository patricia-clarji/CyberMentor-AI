export type CmsContentType =
  | "course"
  | "module"
  | "lesson"
  | "question"
  | "assessment"
  | "lab"
  | "mission"
  | "learning_path"
  | "skill"
  | "reference";

export type CmsContentSummary = {
  id: string;
  content_type: CmsContentType;
  title: string;
  public_slug: string;
  description: string;
  lifecycle_status: string;
  visibility: string;
  latest_version_id: string;
  latest_version: string;
  latest_revision: number;
  review_state: string;
  required_reviewer_types?: string[];
  updated_at: string;
  versions?: CmsVersionSummary[];
};

export type CmsVersionSummary = {
  id: string;
  revision: number;
  version: string;
  status: string;
  review_state: string;
  change_summary: string;
  created_at: string;
  published_at: string | null;
};

export type CmsSection = {
  key: string;
  type: string;
  title: string;
  body: string;
  data: Record<string, unknown>;
  visibility: "visible" | "hidden";
  accessibilityLabel: string | null;
  order: number;
  createdAt?: string;
  updatedAt?: string;
};

export type CmsObjective = {
  key: string;
  title: string;
  description: string;
  bloomLevel: string;
  skills: string[];
  assessmentCoverage: boolean;
  practicalCoverage: boolean;
  reviewStatus: string;
};

export type CmsRelationship = {
  id?: string;
  targetContentId: string;
  targetVersionId: string | null;
  type: string;
  required: boolean;
  order: number;
  configuration: Record<string, unknown>;
};

export type CmsReview = {
  id: string;
  reviewer_type: string;
  reviewer_user_id: string;
  status: string;
  decision: string | null;
  notes: string | null;
  due_at: string | null;
};

export type CmsComment = {
  id: string;
  parent_comment_id: string | null;
  author_user_id: string;
  reviewer_type: string;
  body: string;
  location_type: string;
  location_key: string | null;
  severity: string;
  status: string;
  created_at: string;
  updated_at: string;
  resolved_by_user_id: string | null;
  resolved_at: string | null;
};

export type CmsValidation = {
  category: string;
  rule_id: string;
  severity: string;
  state: string;
  field_location: string | null;
  explanation: string;
  remediation: string | null;
};

export type CmsVersion = CmsContentSummary & {
  version_id: string;
  revision: number;
  version: string;
  language: string;
  required_reviewer_types: string[];
  lock_version: number;
  version_status: string;
  change_summary: string;
  metadata: Record<string, unknown>;
  sections: CmsSection[];
  objectives: CmsObjective[];
  relationships: CmsRelationship[];
  reviews: CmsReview[];
  comments: CmsComment[];
  review_history: Array<{
    id: string;
    reviewer_type: string;
    decision: string;
    notes: string;
    decided_at: string;
  }>;
  validation: CmsValidation[];
  scheduled_at: string | null;
  published_at: string | null;
};

export const CMS_TYPES: CmsContentType[] = [
  "course",
  "module",
  "lesson",
  "question",
  "assessment",
  "lab",
  "mission",
  "learning_path",
  "skill",
  "reference",
];
