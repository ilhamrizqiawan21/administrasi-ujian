export interface LpjVersionItem {
  id: string;
  version: number;
  state: "draft" | "final";
  title: string;
  doc_run_id: string | null;
  finalized_at: string | null;
  updated_at: string;
}

export interface LpjSectionItem {
  key: string;
  title: string;
  narrative: string;
}

export interface LpjSnapshot {
  source_versions: {
    institution_id: string;
    exam_id: string;
    exam_status: string;
    approved_budget_version: number | null;
    document_runs_count: number;
  };
  derived_totals: {
    participants_total: number;
    participants_eligible: number;
    rooms_total: number;
    committee_members_total: number;
    participant_present: number;
    participant_absent: number;
    staff_present: number;
    staff_absent: number;
    incidents_total: number;
    session_reports_total: number;
    rab_approved_idr: number;
    ledger_income_idr: number;
    ledger_expense_idr: number;
    ledger_closing_balance_idr: number;
    draft_ledger_count: number;
    honor_total_idr: number;
    honor_paid_idr: number;
  };
  policy_checks: {
    signatories_valid: boolean;
    missing_signatories: string[];
    has_unapproved_budget_only: boolean;
    draft_ledger_count: number;
    closing_balance_idr: number;
  };
}

export interface LpjEvaluationItem {
  id: string;
  incident_id: string | null;
  issue_title: string;
  resolution: string;
  recommendation: string;
  pic_name: string;
  notes: string;
  sort_order: number;
}

export interface LpjAttachmentItem {
  id: string;
  doc_run_id: string | null;
  title: string;
  file_path: string;
  included: boolean;
  exclusion_reason: string;
  sort_order: number;
  file_exists: boolean;
}

export interface LpjDetail {
  exam: {
    id: string;
    code: string;
    name: string;
    status: string;
  };
  versions: LpjVersionItem[];
  active_version: LpjVersionItem;
  sections: LpjSectionItem[];
  snapshot: LpjSnapshot;
  evaluations: LpjEvaluationItem[];
  attachments: LpjAttachmentItem[];
  missing_attachments: string[];
  available_incidents: Array<{
    id: string;
    type_code: string;
    severity: string;
    summary: string;
  }>;
  available_doc_runs: Array<{
    id: string;
    doc_type: string;
    format: string;
    status: string;
    output_path: string;
  }>;
}
