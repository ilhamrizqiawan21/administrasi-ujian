export interface StudentItem {
  id: string;
  institution_id: string;
  nis: string | null;
  nisn: string | null;
  full_name: string;
  gender: string | null;
  class_id: string | null;
  active: boolean;
  revision: number;
}

export interface StaffItem {
  id: string;
  institution_id: string;
  staff_code: string;
  nip: string | null;
  full_name: string;
  role: "teacher" | "tu" | "external_invigilator";
  active: boolean;
  revision: number;
}

export interface ClassItem {
  id: string;
  institution_id: string;
  year_id: string;
  level_id: string;
  name: string;
  program: string | null;
  revision: number;
}

export interface SubjectItem {
  id: string;
  institution_id: string;
  code: string;
  name: string;
  category: string | null;
  revision: number;
}

export interface RoomItem {
  id: string;
  institution_id: string;
  code: string;
  name: string;
  mode: "paper" | "cbt" | "practice" | "hybrid";
  capacity_limit: number;
  layout: {
    rows: number;
    cols: number;
    seats_per_desk: number;
    disabled_cells: string[];
    accessible_seats: string[];
    board_position: "top" | "bottom";
  };
  stats: {
    enabled_seats: number;
    effective_capacity: number;
  };
  revision: number;
}

export interface ImportPreviewResult {
  preview_id: string;
  headers: string[];
  warnings: string[];
  counts: {
    total: number;
    valid: number;
    duplicate: number;
    invalid: number;
  };
  error_rows: Array<{ row_number: number; error: string }>;
}

export interface DataQualityIssue {
  id: string;
  severity: "warning" | "error";
  kind: string;
  entity_type: string;
  entity_id: string;
  message: string;
  fix_route: string;
}
