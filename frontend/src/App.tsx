import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Archive,
  Banknote,
  Calendar,
  CheckSquare,
  ClipboardCheck,
  Cpu,
  DatabaseBackup,
  FileCode2,
  FileSpreadsheet,
  Grid2x2,
  LayoutDashboard,
  Network,
  Package,
  Settings,
  UserCheck,
  Users,
} from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";
import { AppShell, type NavGroup } from "./components/shared/AppShell";
import { DataTable } from "./components/shared/DataTable";
import { RowActions } from "./components/shared/RowActions";
import { ExportActionGroup } from "./components/ui/Button";
import { StatusIndicator, useToast } from "./components/ui/Feedback";
import { ConfirmDialog } from "./components/ui/Modal";
import { FirstRunWizard } from "./features/cfg/FirstRunWizard";
import { SettingsPage } from "./features/cfg/SettingsPage";
import type { OnboardingStatus } from "./features/cfg/types";
import { DashboardPage } from "./features/evt/DashboardPage";
import { EventsPage } from "./features/evt/EventsPage";
import { FinancePage } from "./features/fin/FinancePage";
import { LpjPage } from "./features/lpj/LpjPage";
import { ArchivePage } from "./features/arc/ArchivePage";
import { BackupPage } from "./features/bak/BackupPage";
import type { ExamItem } from "./features/evt/types";
import { MasterDataPage } from "./features/mst/MasterDataPage";
import { ExecutionPage } from "./features/ops/ExecutionPage";
import { CommitteePage } from "./features/com/CommitteePage";
import { DocumentCenterPage } from "./features/doc/DocumentCenterPage";
import { ExpeditionPage } from "./features/exp/ExpeditionPage";
import { SeatingPage } from "./features/rom/SeatingPage";
import { InvigilationPage } from "./features/sch/InvigilationPage";
import { TimetablePage } from "./features/ses/TimetablePage";
import { TemplatesPage } from "./features/tpl/TemplatesPage";
import { TasksPage } from "./features/tsk/TasksPage";
import { invokeBridge } from "./lib/bridge";
import { useHashRoute } from "./lib/router";

interface AppInfo {
  app_version: string;
  bridge_version: string;
  python_version: string;
  platform: string;
  packages: Record<string, string>;
}

interface DiagnosticRow {
  id: string;
  name: string;
  version: string;
  status: string;
}

const NAV_GROUPS: NavGroup[] = [
  {
    label: "Workspace",
    items: [
      {
        id: "overview",
        label: "Dashboard",
        route: "/",
        icon: <LayoutDashboard size={18} aria-hidden="true" />,
      },
      {
        id: "events",
        label: "Kegiatan Ujian",
        route: "/events",
        icon: <Calendar size={18} aria-hidden="true" />,
      },
    ],
  },
  {
    label: "Persiapan",
    items: [
      {
        id: "master",
        label: "Master Data",
        route: "/master",
        icon: <Users size={18} aria-hidden="true" />,
      },
      {
        id: "timetable",
        label: "Jadwal Ujian",
        route: "/timetable",
        icon: <Calendar size={18} aria-hidden="true" />,
      },
      {
        id: "seating",
        label: "Denah Duduk",
        route: "/seating",
        icon: <Grid2x2 size={18} aria-hidden="true" />,
      },
      {
        id: "invigilation",
        label: "Jadwal Pengawas",
        route: "/invigilation",
        icon: <UserCheck size={18} aria-hidden="true" />,
      },
      {
        id: "committee",
        label: "Kepanitiaan",
        route: "/committee",
        icon: <Network size={18} aria-hidden="true" />,
      },
      {
        id: "tasks",
        label: "Tugas & Timeline",
        route: "/tasks",
        icon: <CheckSquare size={18} aria-hidden="true" />,
      },
      {
        id: "expedition",
        label: "Ekspedisi & Bahan",
        route: "/expedition",
        icon: <Package size={18} aria-hidden="true" />,
      },
      {
        id: "execution",
        label: "Pelaksanaan Ujian",
        route: "/execution",
        icon: <ClipboardCheck size={18} aria-hidden="true" />,
      },
      {
        id: "documents",
        label: "Pusat Dokumen",
        route: "/documents",
        icon: <FileSpreadsheet size={18} aria-hidden="true" />,
      },
      {
        id: "finance",
        label: "Keuangan & Honor",
        route: "/finance",
        icon: <Banknote size={18} aria-hidden="true" />,
      },
      {
        id: "lpj",
        label: "LPJ & Laporan",
        route: "/lpj",
        icon: <FileSpreadsheet size={18} aria-hidden="true" />,
      },
      {
        id: "archive",
        label: "Arsip & Retensi",
        route: "/archive",
        icon: <Archive size={18} aria-hidden="true" />,
      },
    ],
  },
  {
    label: "Sistem",
    items: [
      {
        id: "pengaturan",
        label: "Pengaturan",
        route: "/pengaturan",
        icon: <Settings size={18} aria-hidden="true" />,
      },
      {
        id: "templates",
        label: "Template & Kop",
        route: "/templates",
        icon: <FileCode2 size={18} aria-hidden="true" />,
      },
      {
        id: "backup",
        label: "Backup & Pemulihan",
        route: "/backup",
        icon: <DatabaseBackup size={18} aria-hidden="true" />,
      },
      {
        id: "diagnostik",
        label: "Diagnostik",
        route: "/diagnostik",
        icon: <Cpu size={18} aria-hidden="true" />,
      },
    ],
  },
];

export function App() {
  const [route, navigate] = useHashRoute();
  const { pushToast } = useToast();
  const [onboarding, setOnboarding] = useState<OnboardingStatus | null>(null);
  const [activeInstitutionId, setActiveInstitutionId] = useState<string>("");
  const [showAddInstitution, setShowAddInstitution] = useState(false);
  const [exams, setExams] = useState<ExamItem[]>([]);
  const [activeExamId, setActiveExamId] = useState<string>("");

  const [info, setInfo] = useState<AppInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmTarget, setConfirmTarget] = useState<string | null>(null);

  const refreshBootstrap = useCallback(async () => {
    const [appInfo, onboard] = await Promise.all([
      invokeBridge<AppInfo>("app.info"),
      invokeBridge<OnboardingStatus>("cfg.onboarding.status"),
    ]);
    setInfo(appInfo);
    setOnboarding(onboard);
    if (onboard.institutions.length > 0) {
      setActiveInstitutionId((prev) =>
        onboard.institutions.some((i) => i.id === prev)
          ? prev
          : onboard.institutions[0].id
      );
    }
  }, []);

  const refreshExams = useCallback(async (institutionId: string) => {
    if (!institutionId) return;
    const res = await invokeBridge<{ items: ExamItem[] }>("evt.exams.list", {
      institution_id: institutionId,
    });
    setExams(res.items);
    setActiveExamId((prev) =>
      res.items.some((e) => e.id === prev) ? prev : (res.items[0]?.id ?? "")
    );
  }, []);

  useEffect(() => {
    let active = true;
    refreshBootstrap().catch((err: unknown) => {
      if (!active) return;
      setError(err instanceof Error ? err.message : "Gagal memuat data.");
    });
    return () => {
      active = false;
    };
  }, [refreshBootstrap]);

  useEffect(() => {
    if (!activeInstitutionId) return;
    void refreshExams(activeInstitutionId);
  }, [activeInstitutionId, refreshExams]);

  const activeInstitution = useMemo(
    () =>
      onboarding?.institutions.find((i) => i.id === activeInstitutionId) ??
      onboarding?.institutions[0] ??
      null,
    [onboarding, activeInstitutionId]
  );

  const activeExam = useMemo(
    () => exams.find((e) => e.id === activeExamId) ?? exams[0] ?? null,
    [exams, activeExamId]
  );

  const packageRows = useMemo<DiagnosticRow[]>(() => {
    if (!info) return [];
    return Object.entries(info.packages).map(([name, version]) => ({
      id: name,
      name,
      version,
      status: "Terpasang",
    }));
  }, [info]);

  const columns = useMemo<ColumnDef<DiagnosticRow, unknown>[]>(
    () => [
      { accessorKey: "name", header: "Komponen" },
      { accessorKey: "version", header: "Versi" },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ row }) => (
          <StatusIndicator label={row.original.status} tone="success" />
        ),
      },
      {
        id: "actions",
        header: "Aksi",
        enableSorting: false,
        cell: ({ row }) => (
          <RowActions
            itemLabel={row.original.name}
            onView={() =>
              pushToast(
                `${row.original.name} v${row.original.version}`,
                "info"
              )
            }
            onDelete={() => setConfirmTarget(row.original.name)}
          />
        ),
      },
    ],
    [pushToast]
  );

  if (onboarding?.needs_onboarding || showAddInstitution) {
    return (
      <main style={{ padding: 20 }}>
        <FirstRunWizard
          workspaceRoot={onboarding?.workspace_root ?? ""}
          levelPresets={onboarding?.level_presets ?? {}}
          allowCancel={showAddInstitution}
          onCancel={() => setShowAddInstitution(false)}
          onCompleted={(created) => {
            setShowAddInstitution(false);
            setActiveInstitutionId(created.id);
            void refreshBootstrap();
          }}
        />
      </main>
    );
  }

  const breadcrumbs =
    route === "/events"
      ? [{ label: "Workspace", route: "/" }, { label: "Kegiatan Ujian" }]
      : route === "/timetable"
        ? [
            { label: "Workspace", route: "/" },
            { label: "Persiapan" },
            { label: "Jadwal Ujian" },
          ]
        : route === "/seating"
          ? [
              { label: "Workspace", route: "/" },
              { label: "Persiapan" },
              { label: "Denah Duduk" },
            ]
          : route === "/invigilation"
            ? [
                { label: "Workspace", route: "/" },
                { label: "Persiapan" },
                { label: "Jadwal Pengawas" },
              ]
            : route === "/committee"
              ? [
                  { label: "Workspace", route: "/" },
                  { label: "Persiapan" },
                  { label: "Kepanitiaan" },
                ]
              : route === "/tasks"
                ? [
                    { label: "Workspace", route: "/" },
                    { label: "Persiapan" },
                    { label: "Tugas & Timeline" },
                  ]
                : route === "/expedition"
                  ? [
                      { label: "Workspace", route: "/" },
                      { label: "Persiapan" },
                      { label: "Ekspedisi & Bahan" },
                    ]
                  : route === "/execution"
                    ? [
                        { label: "Workspace", route: "/" },
                        { label: "Pelaksanaan" },
                        { label: "Pelaksanaan Ujian" },
                      ]
                    : route === "/documents"
                      ? [
                          { label: "Workspace", route: "/" },
                          { label: "Dokumen" },
                          { label: "Pusat Dokumen" },
                        ]
                      : route === "/finance"
                        ? [
                            { label: "Workspace", route: "/" },
                            { label: "Keuangan" },
                            { label: "Keuangan & Honor" },
                          ]
        : route === "/master"
        ? [
            { label: "Workspace", route: "/" },
            { label: "Persiapan" },
            { label: "Master Data" },
          ]
        : route === "/pengaturan"
          ? [
              { label: "Workspace", route: "/" },
              { label: "Sistem" },
              { label: "Pengaturan" },
            ]
          : route === "/templates"
            ? [
                { label: "Workspace", route: "/" },
                { label: "Sistem" },
                { label: "Template & Kop" },
              ]
          : route === "/diagnostik"
            ? [
                { label: "Workspace", route: "/" },
                { label: "Sistem" },
                { label: "Diagnostik" },
              ]
            : [{ label: "Workspace" }, { label: "Dashboard" }];

  const pageTitle =
    route === "/events"
      ? "Kegiatan Ujian"
      : route === "/timetable"
        ? "Jadwal Ujian"
        : route === "/seating"
          ? "Denah & Alokasi Ruang"
          : route === "/invigilation"
            ? "Jadwal Pengawas"
            : route === "/committee"
              ? "Kepanitiaan & Rapat"
              : route === "/tasks"
                ? "Tugas & Timeline"
                : route === "/expedition"
                  ? "Ekspedisi & Bahan Ujian"
                  : route === "/execution"
                    ? "Pelaksanaan Ujian"
                    : route === "/documents"
                      ? "Pusat Dokumen"
                      : route === "/finance"
                        ? "Anggaran & Honorarium"
        : route === "/master"
        ? "Master Data"
        : route === "/pengaturan"
          ? "Pengaturan Lembaga"
          : route === "/templates"
            ? "Template & Branding"
          : route === "/diagnostik"
            ? "Diagnostik Runtime"
            : "Dashboard Ujian";

  const contextOptions =
    exams.length > 0
      ? exams.map((e) => ({ id: e.id, label: e.title }))
      : [{ id: "", label: "Belum ada kegiatan" }];

  return (
    <AppShell
      navGroups={NAV_GROUPS}
      currentRoute={route}
      onNavigate={navigate}
      breadcrumbs={breadcrumbs}
      events={contextOptions}
      activeEventId={activeExam?.id ?? ""}
      onChangeEvent={setActiveExamId}
    >
      <div className="uc-pagehead">
        <div>
          <p className="uc-eyebrow">
            {activeInstitution?.name ?? "Ujian Cerdas"}
          </p>
          <h1>{pageTitle}</h1>
          <p className="uc-sub">
            {activeExam
              ? `${activeExam.title} · ${activeExam.starts_on} – ${activeExam.ends_on}`
              : "Workspace desktop lokal terisolasi per lembaga."}
          </p>
        </div>
      </div>

      {error && (
        <section className="uc-panel" role="alert">
          <div className="uc-panel-body uc-field-error">
            <strong>Status Bridge:</strong> {error}
          </div>
        </section>
      )}

      {route === "/events" && activeInstitution ? (
        <EventsPage
          institutionId={activeInstitution.id}
          exams={exams}
          activeExam={activeExam}
          onSelectExam={setActiveExamId}
          onExamsChanged={() => void refreshExams(activeInstitution.id)}
        />
      ) : route === "/timetable" && activeInstitution ? (
        <TimetablePage
          institutionId={activeInstitution.id}
          activeExam={activeExam}
        />
      ) : route === "/seating" && activeInstitution ? (
        <SeatingPage
          institutionId={activeInstitution.id}
          activeExam={activeExam}
        />
      ) : route === "/invigilation" && activeInstitution ? (
        <InvigilationPage
          institutionId={activeInstitution.id}
          activeExam={activeExam}
        />
      ) : route === "/committee" && activeInstitution ? (
        <CommitteePage
          institutionId={activeInstitution.id}
          activeExam={activeExam}
        />
      ) : route === "/tasks" && activeInstitution ? (
        <TasksPage
          institutionId={activeInstitution.id}
          activeExam={activeExam}
        />
      ) : route === "/expedition" && activeInstitution ? (
        <ExpeditionPage
          institutionId={activeInstitution.id}
          activeExam={activeExam}
        />
      ) : route === "/execution" && activeInstitution ? (
        <ExecutionPage
          institutionId={activeInstitution.id}
          activeExam={activeExam}
        />
      ) : route === "/documents" && activeInstitution ? (
        <DocumentCenterPage
          institutionId={activeInstitution.id}
          activeExam={activeExam}
        />
      ) : route === "/finance" && activeInstitution ? (
        <FinancePage
          institutionId={activeInstitution.id}
          activeExam={activeExam}
        />
      ) : route === "/lpj" && activeInstitution ? (
        <LpjPage
          institutionId={activeInstitution.id}
          activeExam={activeExam}
        />
      ) : route === "/archive" && activeInstitution ? (
        <ArchivePage
          institutionId={activeInstitution.id}
          onEventsChanged={() => void refreshBootstrap()}
        />
      ) : route === "/master" && activeInstitution ? (
        <MasterDataPage institutionId={activeInstitution.id} />
      ) : route === "/pengaturan" && activeInstitution ? (
        <SettingsPage
          institution={activeInstitution}
          levelPresets={onboarding?.level_presets ?? {}}
          onInstitutionUpdated={() => void refreshBootstrap()}
          onAddInstitution={() => setShowAddInstitution(true)}
        />
      ) : route === "/templates" && activeInstitution ? (
        <TemplatesPage institutionId={activeInstitution.id} />
      ) : route === "/backup" && activeInstitution ? (
        <BackupPage
          institutionId={activeInstitution.id}
          onRestored={() => void refreshBootstrap()}
        />
      ) : route === "/diagnostik" ? (
        <DataTable
          data={packageRows}
          columns={columns}
          searchPlaceholder="Cari komponen..."
          enableSelection
          toolbarExtra={
            <ExportActionGroup
              onExportPdf={() => pushToast("Ekspor PDF siap di modul DOC", "info")}
              onExportExcel={() => pushToast("Ekspor Excel siap di modul DOC", "info")}
            />
          }
          getCellAlign={(id) => (id === "status" ? "center" : "left")}
        />
      ) : activeInstitution ? (
        <DashboardPage
          institutionId={activeInstitution.id}
          activeExam={activeExam}
          onNavigate={navigate}
        />
      ) : null}

      <ConfirmDialog
        open={confirmTarget !== null}
        title={`Tutup detail ${confirmTarget ?? ""}?`}
        impactMessage="Ini hanya simulasi dialog konfirmasi pada komponen diagnostik; tidak ada paket yang dihapus."
        confirmLabel="Konfirmasi"
        onCancel={() => setConfirmTarget(null)}
        onConfirm={() => {
          pushToast(`Konfirmasi dicatat untuk ${confirmTarget}`, "info");
          setConfirmTarget(null);
        }}
      />
    </AppShell>
  );
}
