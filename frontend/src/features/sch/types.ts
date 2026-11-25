export type RoleCode = "primary" | "secondary" | "proctor" | "backup";

export interface InvigilationRules {
  hard_avoid_own_class: boolean;
  hard_avoid_own_subject: boolean;
  hard_max_daily: boolean;
  hard_max_total: boolean;
  respect_locks: boolean;
  weight_load_deviation: number;
  weight_own_class: number;
  weight_own_subject: number;
  weight_consecutive: number;
}

export interface SchStaffItem {
  id: string;
  code: string;
  display_name: string;
  role_skills: RoleCode[];
  max_daily: number | null;
  max_total: number | null;
  target_weight_pct: number;
}

export interface StaffAvailabilityItem {
  id: string;
  exam_person_id: string;
  starts_at: string;
  ends_at: string;
  state: "unavailable" | "preferred";
  reason: string;
}

export interface InvigilationSlotItem {
  id: string;
  room_session_id: string;
  session_id: string;
  session_label: string;
  local_date: string;
  room_code: string;
  role_code: RoleCode;
  slot_index: number;
  exam_person_id: string | null;
  person_name: string | null;
  locked: boolean;
}

export interface ReserveItem {
  id: string;
  session_id: string;
  session_label: string;
  exam_person_id: string;
  person_name: string;
}

export interface WorkloadItem {
  exam_person_id: string;
  code: string;
  display_name: string;
  active_count: number;
  reserve_count: number;
  target_weight_pct: number;
  expected_load: number;
  deviation: number;
  daily_counts: Record<string, number>;
}

export interface InvigilationValidation {
  valid: boolean;
  hard_conflicts: Array<{
    code: string;
    message: string;
    conflicting_ids: string[];
  }>;
  soft_violations: Array<{
    code: string;
    message: string;
  }>;
  workload: WorkloadItem[];
  summary: {
    total_slots: number;
    assigned_slots: number;
    min_load: number;
    max_load: number;
    own_class_count: number;
    own_subject_count: number;
  };
}

export interface InvigilationDetail {
  plan_id: string;
  plan_state: string;
  plan_revision: number;
  staff: SchStaffItem[];
  availability: StaffAvailabilityItem[];
  slots: InvigilationSlotItem[];
  reserves: ReserveItem[];
  validation: InvigilationValidation;
}
