export interface BackupRecordItem {
  id: string;
  institution_id: string;
  kind: string;
  file_path: string;
  sha256: string;
  byte_size: number;
  schema_revision: string;
  status: string;
  error_message: string;
  exists_on_disk: boolean;
  created_at: string;
}

export interface BackupScheduleItem {
  institution_id: string;
  auto_on_startup: boolean;
  auto_on_close: boolean;
  retention_count: number;
  last_run_at: string | null;
  last_status: string;
  last_error: string;
}

export interface RestorePreviewResult {
  file_path: string;
  can_restore: boolean;
  errors: string[];
  counts: Record<string, number>;
}

export interface RecoveryDiagnostics {
  healthy: boolean;
  integrity_ok: boolean;
  foreign_keys_ok: boolean;
  interrupted_jobs: Array<{
    id: string;
    job_type: string;
    status: string;
    updated_at: string;
  }>;
  temp_files: string[];
  missing_document_outputs: string[];
  guidance: string[];
}
