export interface PlanItem {
  id: string;
  exam_id: string;
  version: number;
  state: "draft" | "validated" | "published" | "superseded";
  parent_id: string | null;
  input_hash: string;
  calendar: {
    holidays: string[];
    break_windows: Array<{
      label: string;
      local_date?: string | null;
      start_local: string;
      end_local: string;
    }>;
    allow_overnight: boolean;
  };
  published_at: string | null;
  revision: number;
}

export interface SessionItem {
  id: string;
  plan_id: string;
  label: string;
  local_date: string;
  starts_at: string;
  ends_at: string;
  start_local: string;
  end_local: string;
  sort_order: number;
  mode: "paper" | "cbt" | "practice" | "hybrid";
  revision: number;
}

export interface PlanDetail {
  plan: PlanItem;
  sessions: SessionItem[];
  session_overlaps: Array<{
    session_a_id: string;
    session_b_id: string;
    message: string;
  }>;
  rooms: Array<{
    id: string;
    code: string;
    name: string;
    mode: string;
    capacity_limit: number;
  }>;
  requirements: Array<{
    id: string;
    group_id: string;
    group_label: string;
    exam_subject_id: string;
    subject_code: string;
    subject_name: string;
    duration_min: number;
    mode: string;
  }>;
  papers: Array<{
    id: string;
    room_session_id: string;
    session_id: string;
    exam_room_id: string;
    requirement_id: string;
    group_id: string;
    locked: boolean;
  }>;
}

export interface ScheduleConflict {
  code: string;
  message: string;
  conflicting_ids: string[];
  resolution_path: string;
}
