export type DocFormat = "pdf" | "docx" | "xlsx";
export type PaperSize = "A4" | "F4";

export interface DocumentRunItem {
  id: string;
  doc_type: string;
  format: string;
  status: string;
  document_number: string | null;
  output_path: string;
  output_hash: string;
  is_stale: boolean;
  generated_at: string;
}

export interface DocDetail {
  runs: DocumentRunItem[];
}
