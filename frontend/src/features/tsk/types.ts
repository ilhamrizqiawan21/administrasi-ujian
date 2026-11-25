export type TaskPhase = "preparation" | "implementation" | "closing";
export type TaskPriority = "low" | "medium" | "high" | "critical";
export type TaskState = "todo" | "in_progress" | "blocked" | "done";

export interface TaskStaffItem {
  id: string;
  code: string;
  display_name: string;
}

export interface TaskDependencyItem {
  id: string;
  prerequisite_id: string;
}

export interface TaskItem {
  id: string;
  phase: TaskPhase;
  title: string;
  description: string;
  pic_id: string | null;
  pic_name: string | null;
  missing_pic: boolean;
  priority: TaskPriority;
  due_date: string;
  is_overdue: boolean;
  state: TaskState;
  blocked_reason: string;
  parent_id: string | null;
  evidence_asset_id: string | null;
  evidence_note: string;
  completed_at: string | null;
  completed_by: string | null;
  dependencies: TaskDependencyItem[];
}

export interface TasksDetail {
  is_archived: boolean;
  today_local: string;
  overdue_count: number;
  staff: TaskStaffItem[];
  tasks: TaskItem[];
}
