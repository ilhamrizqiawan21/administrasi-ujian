export interface SubmissionVersionItem {
  id: string;
  version: number;
  asset_id: string;
  received_at: string;
  state: string;
  note: string;
}

export interface SubmissionMatrixItem {
  id: string;
  subject_label: string;
  class_label: string;
  type_code: string;
  owner_id: string | null;
  owner_name: string | null;
  due_date: string;
  is_late: boolean;
  state: string;
  current_version: number;
  versions: SubmissionVersionItem[];
}

export interface PrintQuantityItem {
  id: string;
  plan_id: string;
  room_session_id: string;
  requirement_id: string;
  roster_count: number;
  reserve_count: number;
  override_qty: number | null;
  exclude_cbt: boolean;
  effective_qty: number;
}

export interface HandoverItem {
  id: string;
  room_session_id: string | null;
  kind: "out" | "in";
  material_type: string;
  expected_qty: number;
  actual_qty: number;
  discrepancy: number;
  mismatch: boolean;
  from_person_name: string;
  to_person_name: string;
  handed_at: string;
  note: string;
}

export interface ExpeditionDetail {
  today_local: string;
  staff: Array<{ id: string; code: string; display_name: string }>;
  items: SubmissionMatrixItem[];
  counts: {
    total: number;
    missing: number;
    received: number;
    revision: number;
    valid: number;
    ready: number;
    late: number;
  };
  print_quantities: PrintQuantityItem[];
  handovers: HandoverItem[];
}
