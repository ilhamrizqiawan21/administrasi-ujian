export type RoomSessionActualState = "scheduled" | "in_progress" | "finished";
export type StudentAttState =
  | "unrecorded"
  | "present"
  | "sick"
  | "excused"
  | "absent"
  | "late";

export interface OpsSittingItem {
  sitting_id: string;
  participant_id: string;
  participant_number: string | null;
  display_name: string;
  state: StudentAttState;
  note: string;
}

export interface OpsRoomSessionItem {
  room_session_id: string;
  session_id: string;
  session_label: string;
  local_date: string;
  room_code: string;
  room_name: string;
  actual_state: RoomSessionActualState;
  counts: {
    total: number;
    unrecorded: number;
    present: number;
    sick: number;
    excused: number;
    absent: number;
    late: number;
  };
  sittings: OpsSittingItem[];
  report: {
    remarks: string;
    finalized_at: string | null;
  };
}

export interface OpsStaffSlotItem {
  slot_id: string;
  room_session_id: string;
  role_code: string;
  planned_person_id: string | null;
  planned_name: string | null;
  actual_person_id: string | null;
  actual_name: string | null;
  state: string;
}

export interface OpsCommitteeAttendanceItem {
  id: string;
  att_date: string;
  shift: string;
  exam_person_id: string;
  person_name: string;
  state: string;
  note: string;
}

export interface OpsIncidentItem {
  id: string;
  room_session_id: string;
  type_code: string;
  severity: string;
  note: string;
  resolution: string;
  confidential: boolean;
  recorded_at: string;
}

export interface OpsMakeupItem {
  id: string;
  original_sitting_id: string;
  target_room_session_id: string;
  reason: string;
}

export interface OpsDetail {
  staff: Array<{ id: string; code: string; display_name: string }>;
  room_sessions: OpsRoomSessionItem[];
  staff_slots: OpsStaffSlotItem[];
  committee_attendance: OpsCommitteeAttendanceItem[];
  incidents: OpsIncidentItem[];
  makeups: OpsMakeupItem[];
}
