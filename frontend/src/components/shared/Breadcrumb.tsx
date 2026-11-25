import { ChevronRight } from "lucide-react";

export interface BreadcrumbItem {
  label: string;
  route?: string;
}

export interface BreadcrumbProps {
  items: BreadcrumbItem[];
  onNavigate?: (route: string) => void;
}

export function Breadcrumb({ items, onNavigate }: BreadcrumbProps) {
  return (
    <nav className="uc-breadcrumb" aria-label="Breadcrumb">
      <ol className="uc-breadcrumb-list">
        {items.map((item, idx) => {
          const isLast = idx === items.length - 1;
          return (
            <li key={`${item.label}-${idx}`} className="uc-breadcrumb-item">
              {idx > 0 && <ChevronRight size={14} aria-hidden="true" />}
              {isLast || !item.route || !onNavigate ? (
                <span
                  className={isLast ? "uc-breadcrumb-current" : undefined}
                  aria-current={isLast ? "page" : undefined}
                >
                  {item.label}
                </span>
              ) : (
                <button
                  type="button"
                  className="uc-breadcrumb-link"
                  onClick={() => onNavigate(item.route!)}
                >
                  {item.label}
                </button>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
