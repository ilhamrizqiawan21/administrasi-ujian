export interface BudgetCategoryItem {
  id: string;
  label: string;
  parent_id: string | null;
  source_fund: string;
  default_unit: string;
  archived: boolean;
}

export interface BudgetLineItem {
  id: string;
  category_id: string;
  category_label: string;
  description: string;
  qty_decimal: string;
  unit: string;
  unit_rate_idr: number;
  amount_idr: number;
}

export interface BudgetVersionItem {
  id: string;
  number: number;
  state: "draft" | "approved" | "superseded";
  approved_at: string | null;
  total_idr: number;
  lines: BudgetLineItem[];
}

export interface CashbookEntryItem {
  id: string;
  category_id: string;
  category_label: string;
  kind: "income" | "expense" | "reversal";
  amount_idr: number;
  entry_date: string;
  reference: string;
  payee: string;
  state: "draft" | "posted";
  reverses_id: string | null;
  running_balance_idr: number | null;
}

export interface BudgetVarianceItem {
  category_id: string;
  category_label: string;
  approved_rab_idr: number;
  actual_expense_idr: number;
  remaining_idr: number;
  over_budget: boolean;
}

export interface HonorRuleItem {
  id: string;
  role_code: string;
  unit_type: "session" | "day" | "fixed";
  rate_idr: number;
  effective_date: string;
  active: boolean;
}

export interface HonorLineItem {
  id: string;
  exam_person_id: string;
  person_name: string;
  source_type: string;
  role_code: string;
  rate_idr: number;
  qty: number;
  amount_idr: number;
  amount_words: string;
  state: "draft" | "paid";
}

export interface FinanceDetail {
  categories: BudgetCategoryItem[];
  budget_versions: BudgetVersionItem[];
  cashbook: CashbookEntryItem[];
  closing_balance_idr: number;
  variance: BudgetVarianceItem[];
  honor_rules: HonorRuleItem[];
  honor_lines: HonorLineItem[];
}
