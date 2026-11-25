export interface ComStaffItem {
  id: string;
  code: string;
  display_name: string;
}

export interface CommitteeRoleItem {
  id: string;
  name: string;
  parent_id: string | null;
  sort_order: number;
  jobdesc: string;
}

export interface CommitteeMemberItem {
  id: string;
  role_id: string;
  exam_person_id: string;
  person_name: string;
  person_code: string;
  appointed_on: string;
  note: string;
}

export interface OrgTreeNode {
  id: string;
  name: string;
  parent_id: string | null;
  sort_order: number;
  jobdesc: string;
  members: CommitteeMemberItem[];
  children: OrgTreeNode[];
}

export interface ProgramKerjaItem {
  basis_text: string;
  objectives: string[];
  milestones: Array<{ label: string; target_date: string }>;
  sections: Array<{ title: string; body: string }>;
  revision: number;
}

export interface MeetingAttendanceItem {
  id: string;
  exam_person_id: string;
  person_name: string;
  state: "present" | "absent" | "excused" | "unrecorded";
  note: string;
}

export interface MeetingItem {
  id: string;
  title: string;
  meeting_date: string;
  start_time: string;
  end_time: string;
  location: string;
  agenda: string;
  minutes: string;
  decisions: string[];
  attendance: MeetingAttendanceItem[];
}

export interface SignatoryItem {
  id: string;
  role_key: string;
  role_label: string;
  exam_person_id: string | null;
  signer_name: string;
  signer_title: string;
  signer_nip: string;
  signed_date: string;
  signature_asset_id: string | null;
  required: boolean;
  sort_order: number;
}

export interface CommitteeDetail {
  staff: ComStaffItem[];
  roles: CommitteeRoleItem[];
  members: CommitteeMemberItem[];
  org_tree: OrgTreeNode[];
  program_kerja: ProgramKerjaItem;
  meetings: MeetingItem[];
  signatories: SignatoryItem[];
  signatory_validation: {
    valid: boolean;
    missing_required: string[];
  };
}
