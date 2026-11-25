import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { Monitor, Moon, Sun } from "lucide-react";
import { Button } from "../components/ui/Button";

export type ThemePreference = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

const STORAGE_KEY = "ujian-cerdas:theme";

interface ThemeContextValue {
  preference: ThemePreference;
  resolved: ResolvedTheme;
  setPreference: (pref: ThemePreference) => void;
  cycleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

function getSystemTheme(): ResolvedTheme {
  if (typeof window === "undefined" || !window.matchMedia) {
    return "light";
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function readStoredPreference(): ThemePreference {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw === "light" || raw === "dark" || raw === "system") {
      return raw;
    }
  } catch {
    // Ignore storage access errors in restricted contexts.
  }
  return "system";
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [preference, setPreferenceState] = useState<ThemePreference>(
    readStoredPreference
  );
  const [systemTheme, setSystemTheme] = useState<ResolvedTheme>(getSystemTheme);

  const resolved: ResolvedTheme =
    preference === "system" ? systemTheme : preference;

  useEffect(() => {
    document.documentElement.dataset.theme = resolved;
  }, [resolved]);

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) {
      return;
    }
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = (e: MediaQueryListEvent) => {
      setSystemTheme(e.matches ? "dark" : "light");
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  const value = useMemo<ThemeContextValue>(
    () => ({
      preference,
      resolved,
      setPreference(pref: ThemePreference) {
        setPreferenceState(pref);
        try {
          window.localStorage.setItem(STORAGE_KEY, pref);
        } catch {
          // Ignore storage write errors.
        }
      },
      cycleTheme() {
        const order: ThemePreference[] = ["light", "dark", "system"];
        const next = order[(order.indexOf(preference) + 1) % order.length];
        setPreferenceState(next);
        try {
          window.localStorage.setItem(STORAGE_KEY, next);
        } catch {
          // Ignore storage write errors.
        }
      },
    }),
    [preference, resolved]
  );

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error("useTheme harus dipanggil di dalam ThemeProvider.");
  }
  return ctx;
}

export function ThemeSwitcher() {
  const { preference, resolved, cycleTheme } = useTheme();
  const label =
    preference === "system"
      ? `Tema: Sistem (${resolved === "dark" ? "Gelap" : "Terang"})`
      : preference === "dark"
        ? "Tema: Gelap"
        : "Tema: Terang";

  const icon =
    preference === "system" ? (
      <Monitor size={18} aria-hidden="true" />
    ) : preference === "dark" ? (
      <Sun size={18} aria-hidden="true" />
    ) : (
      <Moon size={18} aria-hidden="true" />
    );

  return (
    <Button
      variant="neutral"
      size="sm"
      iconOnly
      aria-label={label}
      title={label}
      onClick={cycleTheme}
    >
      {icon}
    </Button>
  );
}
