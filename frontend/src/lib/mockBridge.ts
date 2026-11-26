import type { BridgeResponse } from "./bridge";

export const DEV_MOCK_MARKER = "__DEV_MOCK_ADAPTER_ONLY__";

const mockInstitutions = [
  {
    id: "inst-mock-1",
    name: "MTs Nusantara (Mock Dev)",
    short_name: "MTsN",
    npsn: "00112233",
    nsm: null,
    address: "Jl. Pendidikan No. 1",
    timezone: "Asia/Jakarta",
    logo_asset_id: null,
    logo_relative_path: null,
    revision: 1,
  },
];

const mockLevels = [
  { id: "lvl-1", institution_id: "inst-mock-1", label: "VII", sort_order: 1, revision: 1 },
  { id: "lvl-2", institution_id: "inst-mock-1", label: "VIII", sort_order: 2, revision: 1 },
  { id: "lvl-3", institution_id: "inst-mock-1", label: "IX", sort_order: 3, revision: 1 },
];

const mockExamTypes = [
  {
    id: "et-1",
    institution_id: "inst-mock-1",
    code: "SAS",
    label: "Sumatif Akhir Semester",
    mode_default: "paper",
    terminology: {
      participant_term: "Peserta",
      room_term: "Ruang Ujian",
      invigilator_term: "Pengawas",
    },
    revision: 1,
  },
];

export async function invokeDevMock(
  method: string,
  requestId: string,
  payload: Record<string, unknown> = {}
): Promise<BridgeResponse<unknown>> {
  const ok = (data: unknown): BridgeResponse<unknown> => ({
    ok: true,
    request_id: requestId,
    data,
  });

  switch (method) {
    case "app.info":
      return ok({
        app_version: "0.1.0-dev-mock",
        bridge_version: "1",
        python_version: "mock",
        platform: "browser-dev",
        packages: { mock: DEV_MOCK_MARKER },
      });
    case "app.health":
      return ok({
        workspace_root: "browser-dev-mock",
        db: { ok: true, foreign_keys: 1, integrity: "ok" },
      });
    case "spike.solver_ping":
      return ok({
        fk_enforced: true,
        solver_status: "OPTIMAL",
        assignments: [
          { staff_index: 0, slot_index: 1 },
          { staff_index: 1, slot_index: 0 },
        ],
      });
    case "cfg.onboarding.status":
      return ok({
        needs_onboarding: false,
        workspace_root: "browser-dev-mock",
        institutions: mockInstitutions,
        level_presets: {
          "SD/MI": ["I", "II", "III", "IV", "V", "VI"],
          "SMP/MTs": ["VII", "VIII", "IX"],
          "SMA/MA": ["X", "XI", "XII"],
          SMK: ["X", "XI", "XII", "XIII"],
          PKBM: ["Paket A", "Paket B", "Paket C"],
          Kustom: [],
        },
      });
    case "cfg.first_run.setup":
      return ok({
        institution: {
          id: "inst-mock-new",
          name: String(payload.name ?? "Lembaga Baru"),
          short_name: null,
          npsn: (payload.npsn as string | null) ?? null,
          nsm: null,
          address: null,
          timezone: "Asia/Jakarta",
          logo_asset_id: null,
          logo_relative_path: null,
          revision: 1,
        },
      });
    case "cfg.institutions.save":
      return ok({
        institution: {
          ...mockInstitutions[0],
          ...payload,
          revision: 2,
        },
      });
    case "cfg.levels.list":
      return ok({ items: mockLevels, presets: {} });
    case "cfg.years.list":
      return ok({
        items: [
          {
            id: "yr-1",
            institution_id: "inst-mock-1",
            label: "2026/2027",
            starts_on: null,
            ends_on: null,
            is_active: true,
            revision: 1,
          },
        ],
      });
    case "cfg.exam_types.list":
      return ok({ items: mockExamTypes });
    case "cfg.number_policy.get":
      return ok({
        policy: {
          participant: {
            prefix: "UC",
            separator: "-",
            padding: 4,
            start_seq: 1,
            reset_scope: "event",
          },
          document: {
            pattern: "{seq}/{series}/{exam_code}/{year}",
            padding: 3,
            reset_scope: "year",
          },
        },
        revision: 1,
      });
    case "cfg.number_policy.preview":
      return ok({
        participant_samples: ["UC-0001", "UC-0002", "UC-0003"],
        document_samples: ["001/PAN/SAS/2026", "002/PAN/SAS/2026", "003/PAN/SAS/2026"],
      });
    case "cfg.settings.get":
    case "cfg.settings.update":
    case "cfg.settings.reset":
      return ok({
        settings: {
          default_paper_size: "A4",
          solver_time_limit_sec: 60,
          allow_part_time_weights: true,
          extension_fields: [],
        },
        revision: 1,
      });
    case "mst.students.list":
      return ok({
        items: [
          {
            id: "stu-1",
            institution_id: "inst-mock-1",
            nis: "0001",
            nisn: "0000000001",
            full_name: "Nabila Putri",
            gender: "P",
            class_id: null,
            active: true,
            revision: 1,
          },
        ],
        total: 1,
        page: 1,
        page_size: 50,
      });
    case "mst.staff.list":
      return ok({
        items: [
          {
            id: "stf-1",
            institution_id: "inst-mock-1",
            staff_code: "G01",
            nip: null,
            full_name: "Ahmad Fauzi",
            role: "teacher",
            active: true,
            revision: 1,
          },
        ],
        total: 1,
        page: 1,
        page_size: 50,
      });
    case "mst.classes.list":
      return ok({ items: [] });
    case "mst.subjects.list":
      return ok({ items: [], assignments: [], warnings: [] });
    case "mst.rooms.list":
      return ok({ items: [] });
    case "mst.quality.report":
      return ok({ total_issues: 0, issues: [] });
    case "evt.exams.list":
      return ok({
        items: [
          {
            id: "exam-mock-1",
            institution_id: "inst-mock-1",
            year_id: "yr-1",
            exam_type_id: "et-1",
            title: "SAS Ganjil 2026/2027",
            semester_label: "Ganjil",
            mode: "paper",
            starts_on: "2026-11-30",
            ends_on: "2026-12-08",
            state: "PREPARATION",
            config: {},
            revision: 1,
          },
        ],
      });
    case "evt.exams.dashboard":
      return ok({
        exam: {
          id: "exam-mock-1",
          institution_id: "inst-mock-1",
          year_id: "yr-1",
          exam_type_id: "et-1",
          title: "SAS Ganjil 2026/2027",
          semester_label: "Ganjil",
          mode: "paper",
          starts_on: "2026-11-30",
          ends_on: "2026-12-08",
          state: "PREPARATION",
          config: {},
          revision: 1,
        },
        counts: {
          participants: 1,
          numbered_participants: 1,
          rooms: 1,
          total_capacity: 20,
          staff: 1,
          groups: 1,
          requirements: 1,
        },
        checklist: [
          {
            id: "participants",
            label: "Peserta kegiatan",
            done: true,
            detail: "1 peserta · 1 bernomor",
            route: "/events",
          },
        ],
        blockers: [],
      });
    case "evt.participants.list":
      return ok({ items: [] });
    case "evt.groups.list":
      return ok({ groups: [], subjects: [] });
    case "ses.plans.list":
      return ok({
        items: [
          {
            id: "plan-mock-1",
            exam_id: "exam-mock-1",
            version: 1,
            state: "draft",
            parent_id: null,
            input_hash: "abc",
            calendar: { holidays: [], break_windows: [], allow_overnight: false },
            published_at: null,
            revision: 1,
          },
        ],
      });
    case "ses.plans.detail":
      return ok({
        plan: {
          id: "plan-mock-1",
          exam_id: "exam-mock-1",
          version: 1,
          state: "draft",
          parent_id: null,
          input_hash: "abc",
          calendar: { holidays: [], break_windows: [], allow_overnight: false },
          published_at: null,
          revision: 1,
        },
        sessions: [
          {
            id: "ses-1",
            plan_id: "plan-mock-1",
            label: "Sesi 1",
            local_date: "2026-11-30",
            starts_at: "2026-11-30T00:30:00Z",
            ends_at: "2026-11-30T02:00:00Z",
            start_local: "07:30",
            end_local: "09:00",
            sort_order: 1,
            mode: "paper",
            revision: 1,
          },
        ],
        session_overlaps: [],
        rooms: [
          {
            id: "rm-1",
            code: "R01",
            name: "Ruang 01",
            mode: "paper",
            capacity_limit: 20,
          },
        ],
        requirements: [],
        papers: [],
      });
    case "rom.seating.detail":
      return ok({
        plan_id: "plan-mock-1",
        plan_state: "draft",
        plan_revision: 1,
        rooms: [
          {
            id: "rm-1",
            code: "R01",
            name: "Ruang 01",
            mode: "paper",
            capacity_limit: 4,
            rows: 2,
            cols: 2,
            seats_per_desk: 1,
            board_position: "top",
          },
        ],
        seats: [
          {
            id: "s-1",
            exam_room_id: "rm-1",
            seat_code: "R1C1S1",
            desk_row: 1,
            desk_col: 1,
            seat_index: 1,
            enabled: 1,
            accessible: 1,
            locked: false,
            participant: {
              id: "pt-1",
              participant_number: "001",
              display_name: "Siswa Satu",
              level_label: "7",
              class_label: "7A",
            },
          },
          {
            id: "s-2",
            exam_room_id: "rm-1",
            seat_code: "R1C2S1",
            desk_row: 1,
            desk_col: 2,
            seat_index: 1,
            enabled: 1,
            accessible: 0,
            locked: false,
            participant: {
              id: "pt-2",
              participant_number: "002",
              display_name: "Siswa Dua",
              level_label: "8",
              class_label: "8A",
            },
          },
        ],
        validation: {
          valid: true,
          hard_conflicts: [],
          diagnostics: {
            capacity_shortfall: 0,
            same_grade_adjacent: 0,
            same_class_adjacent: 0,
            accommodation_conflicts: 0,
            total_seated: 2,
            total_eligible: 2,
          },
        },
      });
    case "rom.seating.solve":
      return ok({
        ok: true,
        status: "OPTIMAL",
        plan_revision: 2,
        validation: {
          valid: true,
          hard_conflicts: [],
          diagnostics: {
            capacity_shortfall: 0,
            same_grade_adjacent: 0,
            same_class_adjacent: 0,
            accommodation_conflicts: 0,
            total_seated: 2,
            total_eligible: 2,
          },
        },
      });
    case "rom.seats.swap":
      return ok({ plan_revision: 3, validation: { valid: true, hard_conflicts: [], diagnostics: { capacity_shortfall: 0, same_grade_adjacent: 0, same_class_adjacent: 0, accommodation_conflicts: 0, total_seated: 2, total_eligible: 2 } } });
    case "rom.seats.lock":
      return ok({ locked: true, plan_revision: 3 });
    case "rom.rooms.update_layout":
      return ok({ room_id: "rm-1", plan_revision: 2 });
    case "rom.seating.print_context":
      return ok({
        exam_title: "PAS Ganjil",
        plan_version: 1,
        plan_state: "draft",
        room_code: "R01",
        room_name: "Ruang 01",
        board_position: "top",
        rows: 2,
        cols: 2,
        desks: [],
      });
    case "sch.invigilation.detail":
      return ok({
        plan_id: "plan-mock-1",
        plan_state: "draft",
        plan_revision: 1,
        staff: [
          {
            id: "st-1",
            code: "G01",
            display_name: "Guru Satu",
            role_skills: ["primary", "secondary"],
            max_daily: 2,
            max_total: 6,
            target_weight_pct: 100,
          },
          {
            id: "st-2",
            code: "G02",
            display_name: "Guru Dua",
            role_skills: ["primary"],
            max_daily: 2,
            max_total: 4,
            target_weight_pct: 50,
          },
        ],
        availability: [],
        slots: [
          {
            id: "sl-1",
            room_session_id: "rs-1",
            session_id: "ses-1",
            session_label: "Sesi 1",
            local_date: "2026-11-30",
            room_code: "R01",
            role_code: "primary",
            slot_index: 1,
            exam_person_id: "st-1",
            person_name: "Guru Satu",
            locked: false,
          },
        ],
        reserves: [],
        validation: {
          valid: true,
          hard_conflicts: [],
          soft_violations: [],
          workload: [
            {
              exam_person_id: "st-1",
              code: "G01",
              display_name: "Guru Satu",
              active_count: 1,
              reserve_count: 0,
              target_weight_pct: 100,
              expected_load: 0.67,
              deviation: 0.33,
              daily_counts: { "2026-11-30": 1 },
            },
          ],
          summary: {
            total_slots: 1,
            assigned_slots: 1,
            min_load: 0,
            max_load: 1,
            own_class_count: 0,
            own_subject_count: 0,
          },
        },
      });
    case "sch.invigilation.solve":
      return ok({ ok: true, status: "OPTIMAL", plan_revision: 2 });
    case "sch.invigilation.assign":
    case "sch.slots.configure":
    case "sch.reserves.assign":
    case "sch.reserves.delete":
      return ok({ plan_revision: 2 });
    case "sch.availability.save":
      return ok({ id: "av-1" });
    case "sch.availability.delete":
      return ok({ deleted: true });
    case "sch.profiles.save":
      return ok({ saved: true });
    case "com.detail":
      return ok({
        staff: [{ id: "st-1", code: "G01", display_name: "Drs. Ahmad" }],
        roles: [
          {
            id: "r-1",
            name: "Ketua Panitia",
            parent_id: null,
            sort_order: 1,
            jobdesc: "Koordinator kegiatan",
          },
        ],
        members: [
          {
            id: "m-1",
            role_id: "r-1",
            exam_person_id: "st-1",
            person_name: "Drs. Ahmad",
            person_code: "G01",
            appointed_on: "2026-11-25",
            note: "",
          },
        ],
        org_tree: [
          {
            id: "r-1",
            name: "Ketua Panitia",
            parent_id: null,
            sort_order: 1,
            jobdesc: "Koordinator kegiatan",
            members: [
              {
                id: "m-1",
                role_id: "r-1",
                exam_person_id: "st-1",
                person_name: "Drs. Ahmad",
                person_code: "G01",
                appointed_on: "2026-11-25",
                note: "",
              },
            ],
            children: [],
          },
        ],
        program_kerja: {
          basis_text: "",
          objectives: [],
          milestones: [],
          sections: [],
          revision: 0,
        },
        meetings: [],
        signatories: [],
        signatory_validation: { valid: true, missing_required: [] },
      });
    case "com.roles.save":
    case "com.members.assign":
    case "com.meetings.save":
    case "com.meetings.attendance.save":
    case "com.signatories.save":
    case "com.program.save":
      return ok({ id: "com-1", revision: 1 });
    case "com.roles.delete":
    case "com.members.remove":
    case "com.meetings.delete":
    case "com.signatories.delete":
      return ok({ deleted: true });
    case "tsk.detail":
      return ok({
        is_archived: false,
        today_local: "2026-11-25",
        overdue_count: 0,
        staff: [{ id: "st-1", code: "G01", display_name: "Drs. Ahmad" }],
        tasks: [
          {
            id: "t-1",
            phase: "preparation",
            title: "Rapat koordinasi panitia",
            description: "",
            pic_id: null,
            pic_name: null,
            missing_pic: true,
            priority: "high",
            due_date: "2026-11-28",
            is_overdue: false,
            state: "todo",
            blocked_reason: "",
            parent_id: null,
            evidence_asset_id: null,
            evidence_note: "",
            completed_at: null,
            completed_by: null,
            dependencies: [],
          },
        ],
      });
    case "tsk.presets.apply":
      return ok({ created_count: 6 });
    case "tsk.tasks.save":
    case "tsk.dependencies.add":
      return ok({ id: "t-2" });
    case "tsk.tasks.delete":
    case "tsk.dependencies.remove":
      return ok({ deleted: true });
    case "tsk.evidence.attach":
      return ok({ id: "t-1", state: "done" });
    case "exp.detail":
      return ok({
        today_local: "2026-11-25",
        staff: [{ id: "st-1", code: "G01", display_name: "Drs. Ahmad" }],
        items: [
          {
            id: "it-1",
            subject_label: "Matematika",
            class_label: "7A",
            type_code: "naskah",
            owner_id: null,
            owner_name: null,
            due_date: "2026-11-28",
            is_late: false,
            state: "missing",
            current_version: 0,
            versions: [],
          },
        ],
        counts: {
          total: 1,
          missing: 1,
          received: 0,
          revision: 0,
          valid: 0,
          ready: 0,
          late: 0,
        },
        print_quantities: [],
        handovers: [],
      });
    case "exp.matrix.generate":
      return ok({ created_count: 5 });
    case "exp.items.save":
      return ok({ id: "it-2" });
    case "exp.submissions.receive":
    case "exp.submissions.review":
      return ok({ version: 1, state: "received" });
    case "exp.print.compute":
      return ok({ computed_count: 1 });
    case "exp.print.override":
      return ok({ override_qty: 12 });
    case "exp.handovers.record":
      return ok({ id: "ho-1", discrepancy: 0, mismatch: false });
    case "ops.detail":
      return ok({
        staff: [{ id: "st-1", code: "G01", display_name: "Guru 1" }],
        room_sessions: [
          {
            room_session_id: "rs-1",
            session_id: "ses-1",
            session_label: "Sesi 1",
            local_date: "2026-12-01",
            room_code: "R01",
            room_name: "Ruang 01",
            actual_state: "scheduled",
            counts: {
              total: 1,
              unrecorded: 1,
              present: 0,
              sick: 0,
              excused: 0,
              absent: 0,
              late: 0,
            },
            sittings: [
              {
                sitting_id: "sit-1",
                participant_id: "pt-1",
                participant_number: "001",
                display_name: "Siswa 1",
                state: "unrecorded",
                note: "",
              },
            ],
            report: { remarks: "", finalized_at: null },
          },
        ],
        staff_slots: [],
        committee_attendance: [],
        incidents: [],
        makeups: [],
      });
    case "ops.room_session.state":
      return ok({ actual_state: "in_progress" });
    case "ops.students.attendance":
      return ok({ updated_count: 1 });
    case "ops.staff.attendance":
      return ok({ state: "present", actual_person_id: "st-1" });
    case "ops.committee.attendance":
    case "ops.incidents.record":
    case "ops.makeup.create":
      return ok({ id: "ops-1" });
    case "ops.reports.save":
    case "ops.reports.finalize":
      return ok({ id: "rep-1", finalized: true, warnings: [] });
    case "ops.closing.complete":
      return ok({ closed: true });
    case "tpl.detail":
      return ok({
        paper_dimensions_mm: { A4: [210, 297], F4: [215, 330] },
        allowlisted_placeholders: ["institution_name", "exam_title"],
        letterheads: [
          {
            id: "lh-1",
            name: "Kop Resmi",
            mode: "manual",
            config: {},
            version: 1,
            active: true,
          },
        ],
        templates: [
          {
            id: "builtin-kartu_peserta",
            doc_type: "kartu_peserta",
            name: "Kartu Peserta Ujian",
            version: 1,
            engine: "reportlab",
            layout: { paper_size: "A4" },
            active: true,
            builtin: true,
          },
        ],
        theme_profiles: [],
      });
    case "tpl.letterheads.save_manual":
    case "tpl.letterheads.upload_image":
    case "tpl.templates.save":
      return ok({ id: "tpl-1", version: 1 });
    case "tpl.docx.validate":
      return ok({ valid: true, found_tags: [], unknown_tags: [], allowlisted: [] });
    case "tpl.themes.save":
      return ok({ id: "th-1", version: 1, contrast_ratio: 15.8 });
    case "doc.detail":
      return ok({
        runs: [
          {
            id: "run-1",
            doc_type: "daftar_hadir",
            format: "pdf",
            status: "final",
            document_number: "001/UJN/2026",
            output_path: "exports/daftar_hadir.pdf",
            output_hash: "abcdef123456",
            is_stale: false,
            generated_at: "2026-11-25T08:00:00Z",
          },
        ],
      });
    case "doc.generate":
      return ok({
        run_id: "run-2",
        status: "final",
        document_number: "002/UJN/2026",
        output_path: "exports/doc.pdf",
        output_hash: "123456abcdef",
        bytes_b64: "",
      });
    case "doc.batch":
      return ok({ run_id: "run-3", item_count: 10, output_path: "exports/batch.pdf", output_hash: "abc" });
    case "doc.reprint":
      return ok({ run_id: "run-1", output_hash: "abcdef123456", bytes_b64: "" });
    case "fin.detail":
      return ok({
        categories: [
          {
            id: "cat-1",
            label: "Honorarium",
            parent_id: null,
            source_fund: "BOS",
            default_unit: "org",
            archived: false,
          },
        ],
        budget_versions: [],
        cashbook: [
          {
            id: "le-1",
            category_id: "cat-1",
            category_label: "Honorarium",
            kind: "income",
            amount_idr: 500000,
            entry_date: "2026-12-01",
            reference: "BOS-01",
            payee: "",
            state: "posted",
            reverses_id: null,
            running_balance_idr: 500000,
          },
        ],
        closing_balance_idr: 500000,
        variance: [
          {
            category_id: "cat-1",
            category_label: "Honorarium",
            approved_rab_idr: 300000,
            actual_expense_idr: 0,
            remaining_idr: 300000,
            over_budget: false,
          },
        ],
        honor_rules: [],
        honor_lines: [],
      });
    case "fin.categories.save":
    case "fin.budget.create_version":
    case "fin.ledger.save":
    case "fin.honor.save_rule":
      return ok({ id: "fin-1" });
    case "fin.budget.save_line":
      return ok({ id: "bl-1", amount_idr: 150000 });
    case "fin.budget.approve":
    case "fin.ledger.post":
      return ok({ state: "posted" });
    case "fin.ledger.reverse":
      return ok({ reversal_id: "rev-1" });
    case "fin.honor.generate":
      return ok({ created_count: 1 });
    case "fin.honor.pay":
      return ok({ ledger_entry_id: "le-2", amount_words: "seratus ribu rupiah" });
    case "fin.categories.archive":
      return ok({ archived: true });
    case "lpj.detail":
    case "lpj.versions.create":
    case "lpj.sections.save":
    case "lpj.evaluations.save":
    case "lpj.attachments.save":
    case "lpj.finalize":
      return ok({
        exam: { id: "ex-1", code: "Ganjil", name: "PAS Ganjil 2026", status: "LOCKED" },
        versions: [
          {
            id: "lpj-v1",
            version: 1,
            state: method === "lpj.finalize" ? "final" : "draft",
            title: "LPJ PAS Ganjil 2026",
            doc_run_id: null,
            finalized_at: null,
            updated_at: "2026-11-25T10:00:00Z",
          },
        ],
        active_version: {
          id: "lpj-v1",
          version: 1,
          state: method === "lpj.finalize" ? "final" : "draft",
          title: "LPJ PAS Ganjil 2026",
          doc_run_id: null,
          finalized_at: null,
          updated_at: "2026-11-25T10:00:00Z",
        },
        sections: [
          { key: "cover", title: "Halaman Sampul", narrative: "Sampul LPJ" },
          { key: "intro", title: "Kata Pengantar", narrative: "Narasi pengantar" },
        ],
        snapshot: {
          source_versions: {
            institution_id: "inst-1",
            exam_id: "ex-1",
            exam_status: "LOCKED",
            approved_budget_version: 1,
            document_runs_count: 1,
          },
          derived_totals: {
            participants_total: 100,
            participants_eligible: 100,
            rooms_total: 4,
            committee_members_total: 8,
            participant_present: 98,
            participant_absent: 2,
            staff_present: 10,
            staff_absent: 0,
            incidents_total: 1,
            session_reports_total: 4,
            rab_approved_idr: 5000000,
            ledger_income_idr: 5000000,
            ledger_expense_idr: 4200000,
            ledger_closing_balance_idr: 800000,
            draft_ledger_count: 0,
            honor_total_idr: 2000000,
            honor_paid_idr: 2000000,
          },
          policy_checks: {
            signatories_valid: true,
            missing_signatories: [],
            has_unapproved_budget_only: false,
            draft_ledger_count: 0,
            closing_balance_idr: 800000,
          },
        },
        evaluations: [],
        attachments: [],
        missing_attachments: [],
        available_incidents: [],
        available_doc_runs: [],
      });
    case "lpj.export":
      return ok({
        doc_run_id: "run-lpj-1",
        lpj_version_id: "lpj-v1",
        version: 1,
        state: "final",
        format: "pdf",
        output_path: "exports/lpj_v1.pdf",
        output_hash: "abcdef",
        byte_size: 4096,
      });
    case "arc.events.list":
      return ok({
        items: [
          {
            id: "ex-1",
            institution_id: "inst-1",
            year_id: "yr-1",
            year_label: "2026/2027",
            exam_type_id: "et-1",
            exam_type_label: "PAS",
            title: "PAS Ganjil 2026",
            semester_label: "Ganjil",
            mode: "paper",
            starts_on: "2026-12-01",
            ends_on: "2026-12-05",
            state: "ARCHIVED",
            is_archived: true,
            package_count: 1,
            updated_at: "2026-12-06T00:00:00Z",
          },
        ],
        years: [{ id: "yr-1", label: "2026/2027" }],
        exam_types: [{ id: "et-1", label: "PAS" }],
      });
    case "arc.events.detail":
      return ok({
        exam: {
          id: "ex-1",
          institution_id: "inst-1",
          year_id: "yr-1",
          year_label: "2026/2027",
          exam_type_id: "et-1",
          exam_type_label: "PAS",
          title: "PAS Ganjil 2026",
          semester_label: "Ganjil",
          mode: "paper",
          starts_on: "2026-12-01",
          ends_on: "2026-12-05",
          state: "ARCHIVED",
          is_archived: true,
          active_plan_id: "plan-1",
          package_count: 1,
          updated_at: "2026-12-06T00:00:00Z",
        },
        counts: {
          people: 40,
          participants: 36,
          rooms: 2,
          subjects: 6,
          plans: 1,
          sessions: 4,
          documents: 3,
          lpj_versions: 1,
          ledger_entries: 5,
        },
        documents: [],
        packages: [
          {
            id: "pkg-1",
            file_path: "exports/archives/archive_pas_ganjil.zip",
            sha256: "abc123",
            file_count: 4,
            include_personal_info: false,
            created_at: "2026-12-06T01:00:00Z",
          },
        ],
      });
    case "arc.events.archive":
      return ok({ id: "ex-1", state: "ARCHIVED", is_archived: true });
    case "arc.package.export":
      return ok({
        id: "pkg-1",
        file_path: "exports/archives/archive_pas_ganjil.zip",
        sha256: "abc123",
        file_count: 4,
        include_personal_info: false,
        missing_files: [],
        created_at: "2026-12-06T01:00:00Z",
      });
    case "arc.package.verify":
      return ok({ package_id: "pkg-1", valid: true, checked_files: 3, errors: [] });
    case "arc.events.duplicate":
      return ok({
        id: "ex-dup-1",
        title: String(payload.title ?? "Salinan"),
        state: "DRAFT",
        source_exam_id: "ex-1",
        cloned: { subjects: 6, groups: 2, roles: 3, budget_categories: 4 },
      });
    case "arc.retention.review":
      return ok({
        min_age_days: 365,
        events: [
          {
            id: "ex-old",
            title: "PAS Ganjil 2024",
            year_label: "2024/2025",
            exam_type_label: "PAS",
            state: "ARCHIVED",
            ends_on: "2024-12-06",
            age_days: 720,
            eligible_for_purge: true,
          },
        ],
        backups: [],
        last_good_backup: null,
      });
    case "arc.retention.preview":
      return ok({
        exam_id: "ex-old",
        exam_title: "PAS Ganjil 2024",
        state: "ARCHIVED",
        can_purge: true,
        blockers: [],
        impact_counts: { documents: 3, participants: 36 },
        total_affected_rows: 40,
      });
    case "arc.retention.purge":
      return ok({
        purged_exam_id: "ex-old",
        purged_title: "PAS Ganjil 2024",
        backup: {
          id: "bak-1",
          file_path: "backups/pre_purge_pas.sqlite",
          sha256: "abc",
          byte_size: 1024,
        },
      });
    case "bak.list":
      return ok({
        items: [
          {
            id: "bak-1",
            institution_id: "inst-1",
            kind: "manual",
            file_path: "backups/backup_manual_1.zip",
            sha256: "abc123",
            byte_size: 16384,
            schema_revision: "0017_bak_tables",
            status: "valid",
            error_message: "",
            exists_on_disk: true,
            created_at: "2026-11-26T07:00:00Z",
          },
        ],
      });
    case "bak.create":
      return ok({
        id: "bak-2",
        institution_id: "inst-1",
        kind: "manual",
        file_path: "backups/backup_manual_2.zip",
        sha256: "def456",
        byte_size: 18432,
        schema_revision: "0017_bak_tables",
        status: "valid",
        error_message: "",
        exists_on_disk: true,
        created_at: "2026-11-26T07:10:00Z",
      });
    case "bak.verify":
      return ok({ valid: true, errors: [], counts: { students: 40 } });
    case "bak.schedule.get":
    case "bak.schedule.save":
      return ok({
        institution_id: "inst-1",
        auto_on_startup: true,
        auto_on_close: true,
        retention_count: 7,
        last_run_at: null,
        last_status: "idle",
        last_error: "",
      });
    case "bak.schedule.run":
      return ok({ executed: true, status: "ok", pruned_count: 0 });
    case "bak.restore.preview":
      return ok({
        file_path: String(payload.file_path ?? "backups/backup_manual_1.zip"),
        can_restore: true,
        errors: [],
        counts: { institutions: 1, students: 40, staff: 12, exams: 2 },
      });
    case "bak.restore.apply":
      return ok({ restored: true });
    case "bak.recovery.diagnose":
      return ok({
        healthy: true,
        integrity_ok: true,
        foreign_keys_ok: true,
        interrupted_jobs: [],
        temp_files: [],
        missing_document_outputs: [],
        guidance: [
          "Sistem sehat: tidak ada job terhenti, file sementara, atau pelanggaran integritas.",
        ],
      });
    case "bak.recovery.repair":
      return ok({
        cleaned_jobs: 0,
        cleaned_temp_files: 0,
        diagnostics: {
          healthy: true,
          integrity_ok: true,
          foreign_keys_ok: true,
          interrupted_jobs: [],
          temp_files: [],
          missing_document_outputs: [],
          guidance: ["Sistem sehat."],
        },
      });
    default:
      return {
        ok: false,
        request_id: requestId,
        error: {
          code: "METHOD_NOT_ALLOWED",
          message: `Metode '${method}' tidak tersedia pada mock dev.`,
          retryable: false,
        },
      };
  }
}
