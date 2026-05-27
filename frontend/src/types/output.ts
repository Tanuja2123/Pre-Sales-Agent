/** Shapes returned by GET /api/v1/rfp/{run_id}/output (loosely typed for UI). */

export type RFPSummaryOut = {
  client_overview?: string;
  strategic_objectives?: string;
  key_requirements?: string[];
  evaluation_criteria?: string;
  risk_flags?: string[];
  bid_strategy?: string;
  go_no_go_recommendation?: string;
};

export type RequirementOut = {
  requirement_id?: string;
  type?: string;
  priority?: string;
  maf_classification?: string;
  source_section?: string;
  text?: string;
  ambiguity_score?: number;
};

export type QuestionOut = {
  question_id?: string;
  category?: string;
  priority?: string;
  question_text?: string;
  assumption_if_unanswered?: string;
  source_requirement?: string;
};

export type TimelineMilestoneOut = {
  project_name?: string;
  milestone?: string;
  start_date?: string;
  end_deadline?: string;
  required_deliverables?: string;
  dependency?: string;
  escalation_sla?: string;
  status?: string;
  priority?: string;
};

export type DraftSectionOut = {
  section_id?: string;
  title?: string;
  body?: string;
};

export type ClarificationResolutionItemOut = {
  question_id?: string;
  source_requirement?: string;
  question_text?: string;
  suggested_input?: string;
  user_answer?: string;
  assumption_if_unanswered?: string;
  final_resolution?: string;
  resolution_source?: string;
};

export type ClarificationResolutionDocumentOut = {
  generated_at?: string;
  uploaded_reference_filename?: string;
  uploaded_reference_excerpt?: string;
  additional_notes?: string;
  chat_user_inputs_excerpt?: string;
  items?: ClarificationResolutionItemOut[];
};

export type ScopeRequirementOut = {
  requirement_id?: string;
  text?: string;
  priority?: string;
  notes?: string;
};

export type UserStoryOut = {
  story_id?: string;
  role?: string;
  story?: string;
  acceptance_criteria?: string[];
};

export type PresalesScopeOut = {
  project_summary?: string;
  business_requirements?: ScopeRequirementOut[];
  functional_requirements?: ScopeRequirementOut[];
  non_functional_requirements?: ScopeRequirementOut[];
  user_stories?: UserStoryOut[];
  draft_scope_document?: string;
  suggested_questions?: string[];
};

export type PipelineOutput = {
  run_id?: string;
  summary?: RFPSummaryOut | null;
  timeline?: TimelineMilestoneOut[];
  submission_date?: string | null;
  expected_completion_date?: string | null;
  scope?: PresalesScopeOut | null;
  requirements?: RequirementOut[];
  questions?: QuestionOut[];
  draft_response?: { sections?: DraftSectionOut[] } | null;
  clarification_document?: ClarificationResolutionDocumentOut | null;
  clarification_started?: boolean;
  maf_audit?: {
    minimum_met?: boolean;
    acceptable_coverage?: number;
    overall_rating?: string;
    blockers?: string[];
    full_opportunities?: string[];
  } | null;
  pipeline_duration_seconds?: number;
  rfp?: {
    filename?: string;
    document_id?: string;
    chunks?: Array<{ chunk_id?: string; text?: string }>;
    sections?: Record<string, string>;
    metadata?: Record<string, string>;
  };
};
