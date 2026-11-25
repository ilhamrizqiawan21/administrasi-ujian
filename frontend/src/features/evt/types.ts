export type ExamState =
  | "DRAFT"
  | "PREPARATION"
  | "READY"
  | "RUNNING"
  | "COMPLETED"
  | "ARCHIVED";

export interface ExamItem {
  id: string;
  institution_id: string;
  year_id: string;
  exam_type_id: string;
  title: string;
  semester_label: string;
  mode: "paper" | "cbt" | "practice" | "hybrid";
  starts_on: string;
  ends_on: string;
  state: ExamState;
  config: {
    numbering_revision?: number;
    cards_printed?: boolean;
    cards_stale?: boolean;
    documents_stale?: boolean;
  };
  revision: number;
}

export interface ExamParticipantItem {
  id: string;
  exam_person_id: string;
  code: string;
  display_name: string;
  level_label: string | null;
  class_label: string | null;
  participant_number: string | null;
  eligibility: string;
  revision: number;
}

export interface ExamGroupItem {
  id: string;
  label: string;
  member_count: number;
  requirements: Array<{
    id: string;
    exam_subject_id: string;
    subject_code: string;
    subject_name: string;
    attempt_no: number;
    duration_min: number;
    mode: string;
  }>;
}

export interface ExamDashboardData {
  exam: ExamItem;
  counts: {
    participants: number;
    numbered_participants: number;
    rooms: number;
    total_capacity: number;
    staff: number;
    groups: number;
    requirements: number;
  };
  checklist: Array<{
    id: string;
    label: string;
    done: boolean;
    detail: string;
    route: string;
  }>;
  blockers: string[];
}
