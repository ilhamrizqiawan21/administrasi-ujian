export interface ArcEventItem {
  id: string;
  institution_id: string;
  year_id: string;
  year_label: string;
  exam_type_id: string;
  exam_type_label: string;
  title: string;
  semester_label: string;
  mode: string;
  starts_on: string;
  ends_on: string;
  state: string;
  is_archived: boolean;
  package_count: number;
  updated_at: string;
}

export interface ArcFilterOption {
  id: string;
  label: string;
}

export interface ArcListResponse {
  items: ArcEventItem[];
  years: ArcFilterOption[];
  exam_types: ArcFilterOption[];
}

export interface ArcPackageItem {
  id: string;
  file_path: string;
  sha256: string;
  file_count: number;
  include_personal_info: boolean;
  created_at: string;
}

export interface ArcEventDetailResponse {
  exam: ArcEventItem & { active_plan_id: string | null };
  counts: {
    people: number;
    participants: number;
    rooms: number;
    subjects: number;
    plans: number;
    sessions: number;
    documents: number;
    lpj_versions: number;
    ledger_entries: number;
  };
  documents: Array<{
    id: string;
    doc_type: string;
    format: string;
    status: string;
    output_path: string;
    output_hash: string;
    generated_at: string;
  }>;
  packages: ArcPackageItem[];
}

export interface ArcRetentionEvent {
  id: string;
  title: string;
  year_label: string;
  exam_type_label: string;
  state: string;
  ends_on: string;
  age_days: number;
  eligible_for_purge: boolean;
}

export interface ArcBackupItem {
  id: string;
  exam_id: string | null;
  exam_title: string;
  file_path: string;
  sha256: string;
  byte_size: number;
  authorized_by: string;
  created_at: string;
}

export interface ArcRetentionReviewResponse {
  min_age_days: number;
  events: ArcRetentionEvent[];
  backups: ArcBackupItem[];
  last_good_backup: ArcBackupItem | null;
}

export interface ArcRetentionPreviewResponse {
  exam_id: string;
  exam_title: string;
  state: string;
  can_purge: boolean;
  blockers: string[];
  impact_counts: Record<string, number>;
  total_affected_rows: number;
}
