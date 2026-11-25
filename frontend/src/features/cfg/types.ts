export interface Institution {
  id: string;
  name: string;
  short_name: string | null;
  npsn: string | null;
  nsm: string | null;
  address: string | null;
  timezone: string;
  logo_asset_id: string | null;
  logo_relative_path: string | null;
  revision: number;
}

export interface OnboardingStatus {
  needs_onboarding: boolean;
  workspace_root: string;
  institutions: Institution[];
  level_presets: Record<string, string[]>;
}

export interface AcademicYear {
  id: string;
  institution_id: string;
  label: string;
  starts_on: string | null;
  ends_on: string | null;
  is_active: boolean;
  revision: number;
}

export interface LevelItem {
  id: string;
  institution_id: string;
  label: string;
  sort_order: number;
  revision: number;
}

export interface ExamTypeItem {
  id: string;
  institution_id: string;
  code: string;
  label: string;
  mode_default: "paper" | "cbt" | "practice" | "hybrid";
  terminology: {
    participant_term: string;
    room_term: string;
    invigilator_term: string;
  };
  revision: number;
}

export interface NumberPolicyConfig {
  participant: {
    prefix: string;
    separator: string;
    padding: number;
    start_seq: number;
    reset_scope: "event" | "year" | "month" | "never";
  };
  document: {
    pattern: string;
    padding: number;
    reset_scope: "event" | "year" | "month" | "never";
  };
}

export interface ExtensionFieldDef {
  key: string;
  label: string;
  scope: "student" | "staff" | "room" | "exam";
  field_type: "string" | "date" | "int" | "enum";
  required: boolean;
  enum_options: string[];
}

export interface TypedSettingsConfig {
  default_paper_size: "A4" | "F4" | "Letter";
  solver_time_limit_sec: number;
  allow_part_time_weights: boolean;
  extension_fields: ExtensionFieldDef[];
}
