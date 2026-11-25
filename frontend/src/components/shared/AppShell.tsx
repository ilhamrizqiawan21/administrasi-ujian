import {
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { Menu, ShieldCheck } from "lucide-react";
import { ThemeSwitcher } from "../../lib/theme";
import { Button } from "../ui/Button";
import { Breadcrumb, type BreadcrumbItem } from "./Breadcrumb";

export interface NavItem {
  id: string;
  label: string;
  route: string;
  icon: ReactNode;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

export interface EventOption {
  id: string;
  label: string;
}

export interface AppShellProps {
  navGroups: NavGroup[];
  currentRoute: string;
  onNavigate: (route: string) => void;
  breadcrumbs: BreadcrumbItem[];
  events: EventOption[];
  activeEventId: string;
  onChangeEvent: (eventId: string) => void;
  hasUnsavedChanges?: boolean;
  children: ReactNode;
}

const SIDEBAR_STORAGE_KEY = "ujian-cerdas:sidebar-collapsed";

export function AppShell({
  navGroups,
  currentRoute,
  onNavigate,
  breadcrumbs,
  events,
  activeEventId,
  onChangeEvent,
  hasUnsavedChanges = false,
  children,
}: AppShellProps) {
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    try {
      return window.localStorage.getItem(SIDEBAR_STORAGE_KEY) === "1";
    } catch {
      return false;
    }
  });
  const [drawerExpanded, setDrawerExpanded] = useState(false);
  const hamburgerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape" && drawerExpanded) {
        e.preventDefault();
        setDrawerExpanded(false);
        hamburgerRef.current?.focus();
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [drawerExpanded]);

  function toggleSidebar() {
    if (window.innerWidth <= 1024) {
      setDrawerExpanded((prev) => !prev);
      return;
    }
    setCollapsed((prev) => {
      const next = !prev;
      try {
        window.localStorage.setItem(SIDEBAR_STORAGE_KEY, next ? "1" : "0");
      } catch {
        // Ignore storage write errors.
      }
      return next;
    });
  }

  function safeNavigate(route: string) {
    if (
      hasUnsavedChanges &&
      !window.confirm("Ada perubahan belum disimpan. Lanjutkan pindah halaman?")
    ) {
      return;
    }
    setDrawerExpanded(false);
    onNavigate(route);
  }

  function handleEventChange(nextId: string) {
    if (
      hasUnsavedChanges &&
      !window.confirm("Ada perubahan belum disimpan. Lanjutkan ganti kegiatan?")
    ) {
      return;
    }
    onChangeEvent(nextId);
  }

  const shellClasses = [
    "uc-app",
    collapsed ? "is-collapsed" : "",
    drawerExpanded ? "is-expanded" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={shellClasses}>
      <div
        className="uc-mobile-backdrop"
        aria-hidden="true"
        onClick={() => {
          setDrawerExpanded(false);
          hamburgerRef.current?.focus();
        }}
      />

      <aside className="uc-sidebar" aria-label="Navigasi utama">
        <div className="uc-brand">
          <div className="uc-brand-mark" aria-hidden="true">
            <ShieldCheck size={20} />
          </div>
          <div className="uc-brand-meta">
            <span className="uc-brand-title">Ujian Cerdas</span>
            <span className="uc-brand-sub">Studio Administrasi</span>
          </div>
        </div>

        <nav className="uc-nav-scroll" aria-label="Menu modul">
          {navGroups.map((group) => (
            <div key={group.label}>
              <div className="uc-nav-group">{group.label}</div>
              {group.items.map((item) => {
                const active = currentRoute === item.route;
                return (
                  <button
                    key={item.id}
                    type="button"
                    className={`uc-nav-item ${active ? "is-active" : ""}`}
                    title={item.label}
                    aria-current={active ? "page" : undefined}
                    onClick={() => safeNavigate(item.route)}
                  >
                    {item.icon}
                    <span className="uc-nav-text">{item.label}</span>
                  </button>
                );
              })}
            </div>
          ))}
        </nav>

        <div className="uc-nav-foot">
          <span>Workspace lokal · Offline</span>
        </div>
      </aside>

      <div className="uc-main">
        <header className="uc-topbar">
          <Button
            ref={hamburgerRef}
            variant="neutral"
            size="sm"
            iconOnly
            aria-label="Buka atau tutup navigasi"
            aria-expanded={drawerExpanded || !collapsed}
            onClick={toggleSidebar}
          >
            <Menu size={18} aria-hidden="true" />
          </Button>

          <div className="uc-context">
            <label htmlFor="uc-event-select" className="uc-sub">
              Kegiatan aktif
            </label>
            <select
              id="uc-event-select"
              className="uc-select"
              style={{ width: "auto", minWidth: 200 }}
              value={activeEventId}
              onChange={(e) => handleEventChange(e.target.value)}
            >
              {events.map((ev) => (
                <option key={ev.id} value={ev.id}>
                  {ev.label}
                </option>
              ))}
            </select>
          </div>

          <div className="uc-topbar-spacer" />

          <ThemeSwitcher />
        </header>

        <Breadcrumb items={breadcrumbs} onNavigate={safeNavigate} />

        <main className="uc-workspace">
          <div className="uc-workspace-inner">{children}</div>
        </main>

        <footer className="uc-statusbar">
          <span>Penyimpanan lokal aktif · Tidak memerlukan internet</span>
          <span>Ujian Cerdas v0.1</span>
        </footer>
      </div>
    </div>
  );
}
