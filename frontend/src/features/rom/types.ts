export type MixMode = "mix_grade" | "mix_class" | "ordered" | "custom";

export interface AllocationPolicy {
  mode: MixMode;
  hard_mix_grade: boolean;
  hard_mix_class: boolean;
  diagonal_adjacent: boolean;
  balance_rooms: boolean;
  respect_locks: boolean;
  require_accessible: boolean;
  soft_same_grade_weight: number;
  soft_same_class_weight: number;
}

export interface RoomMeta {
  id: string;
  code: string;
  name: string;
  mode: string;
  capacity_limit: number;
  rows: number;
  cols: number;
  seats_per_desk: number;
  board_position: "top" | "bottom";
}

export interface SeatParticipant {
  id: string;
  participant_number: string | null;
  display_name: string;
  level_label: string;
  class_label: string;
}

export interface SeatItem {
  id: string;
  exam_room_id: string;
  seat_code: string;
  desk_row: number;
  desk_col: number;
  seat_index: number;
  enabled: number;
  accessible: number;
  locked: boolean;
  participant: SeatParticipant | null;
}

export interface HardConflict {
  code: string;
  message: string;
  conflicting_ids: string[];
}

export interface SeatingDiagnostics {
  capacity_shortfall: number;
  same_grade_adjacent: number;
  same_class_adjacent: number;
  accommodation_conflicts: number;
  total_seated: number;
  total_eligible: number;
}

export interface SeatingValidation {
  valid: boolean;
  hard_conflicts: HardConflict[];
  diagnostics: SeatingDiagnostics;
}

export interface SeatingDetail {
  plan_id: string;
  plan_state: string;
  plan_revision: number;
  rooms: RoomMeta[];
  seats: SeatItem[];
  validation: SeatingValidation;
}

export interface PrintDeskItem {
  seat_code: string;
  row: number;
  col: number;
  seat_index: number;
  enabled: boolean;
  accessible: boolean;
  participant_number: string | null;
  display_name: string | null;
  level_label: string | null;
  class_label: string | null;
}

export interface SeatingPrintContext {
  exam_title: string;
  plan_version: number;
  plan_state: string;
  room_code: string;
  room_name: string;
  board_position: "top" | "bottom";
  rows: number;
  cols: number;
  desks: PrintDeskItem[];
}
