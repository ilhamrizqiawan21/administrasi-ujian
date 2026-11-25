export type PaperSize = "A4" | "F4";

export interface LetterheadItem {
  id: string;
  name: string;
  mode: "manual" | "image";
  config: Record<string, unknown>;
  version: number;
  active: boolean;
}

export interface TemplateCatalogItem {
  id: string;
  doc_type: string;
  name: string;
  version: number;
  engine: "reportlab" | "docx";
  layout: Record<string, unknown>;
  active: boolean;
  builtin: boolean;
}

export interface ThemeProfileItem {
  id: string;
  name: string;
  tokens: {
    app_title?: string;
    palette_preset?: string;
    density?: string;
    surface_hex?: string;
    text_hex?: string;
    accent_hex?: string;
    contrast_ratio?: number;
  };
  version: number;
  active: boolean;
}

export interface TplDetail {
  paper_dimensions_mm: Record<PaperSize, [number, number]>;
  allowlisted_placeholders: string[];
  letterheads: LetterheadItem[];
  templates: TemplateCatalogItem[];
  theme_profiles: ThemeProfileItem[];
}
