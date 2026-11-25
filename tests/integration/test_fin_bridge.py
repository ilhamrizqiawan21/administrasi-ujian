"""Integration tests for FIN-01..FIN-08 via BridgeApi."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.bridge.api import BridgeApi
from backend.core.app_shell import bootstrap_runtime


def _call(
    api: BridgeApi, method: str, payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    return api.invoke(
        {"request_id": f"req-{method}", "method": method, "payload": payload or {}}
    )


def test_fin_bridge_end_to_end(tmp_path: Path) -> None:
    runtime = bootstrap_runtime(workspace_root=tmp_path, institution_slug="fin_bridge")
    api = BridgeApi(runtime=runtime)

    inst_id = _call(
        api,
        "cfg.first_run.setup",
        {
            "name": "SMPN 1 Nusantara",
            "level_preset": "SMP/MTs",
            "academic_year_label": "2026/2027",
        },
    )["data"]["institution"]["id"]
    year_id = _call(api, "cfg.years.list", {"institution_id": inst_id})["data"][
        "items"
    ][0]["id"]
    et_id = _call(api, "cfg.exam_types.list", {"institution_id": inst_id})["data"][
        "items"
    ][0]["id"]
    _call(
        api,
        "mst.staff.save",
        {
            "institution_id": inst_id,
            "staff_code": "G01",
            "full_name": "Guru 1",
            "role": "teacher",
        },
    )
    exam_id = _call(
        api,
        "evt.exams.create",
        {
            "institution_id": inst_id,
            "year_id": year_id,
            "exam_type_id": et_id,
            "title": "PAS Ganjil",
            "semester_label": "Ganjil",
            "starts_on": "2026-12-01",
            "ends_on": "2026-12-05",
        },
    )["data"]["exam"]["id"]

    # FIN-01: category CRUD & cycle rejection
    c1 = _call(
        api,
        "fin.categories.save",
        {"institution_id": inst_id, "exam_id": exam_id, "label": "Honorarium"},
    )["data"]["id"]
    c2 = _call(
        api,
        "fin.categories.save",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "label": "Honor Panitia",
            "parent_id": c1,
        },
    )["data"]["id"]
    cyc = _call(
        api,
        "fin.categories.save",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "id": c1,
            "label": "Honorarium",
            "parent_id": c2,
        },
    )
    assert cyc["ok"] is False
    assert cyc["error"]["code"] == "CONFLICT"

    # FIN-02: RAB version, line, approve
    bv = _call(
        api,
        "fin.budget.create_version",
        {"institution_id": inst_id, "exam_id": exam_id},
    )["data"]["id"]
    ln = _call(
        api,
        "fin.budget.save_line",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "budget_version_id": bv,
            "category_id": c1,
            "description": "Honor Panitia",
            "qty_decimal": "2",
            "unit": "org",
            "unit_rate_idr": 150000,
        },
    )
    assert ln["data"]["amount_idr"] == 300000
    assert (
        _call(
            api,
            "fin.budget.approve",
            {"institution_id": inst_id, "exam_id": exam_id, "budget_version_id": bv},
        )["ok"]
        is True
    )

    # FIN-03: income post + reversal (second reversal blocked)
    inc = _call(
        api,
        "fin.ledger.save",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "category_id": c1,
            "kind": "income",
            "amount_idr": 500000,
            "entry_date": "2026-12-01",
            "reference": "BOS-01",
        },
    )["data"]["id"]
    _call(
        api,
        "fin.ledger.post",
        {"institution_id": inst_id, "exam_id": exam_id, "entry_id": inc},
    )
    exp = _call(
        api,
        "fin.ledger.save",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "category_id": c1,
            "kind": "expense",
            "amount_idr": 100000,
            "entry_date": "2026-12-02",
        },
    )["data"]["id"]
    _call(
        api,
        "fin.ledger.post",
        {"institution_id": inst_id, "exam_id": exam_id, "entry_id": exp},
    )
    rev1 = _call(
        api,
        "fin.ledger.reverse",
        {"institution_id": inst_id, "exam_id": exam_id, "entry_id": exp},
    )
    assert rev1["ok"] is True
    rev2 = _call(
        api,
        "fin.ledger.reverse",
        {"institution_id": inst_id, "exam_id": exam_id, "entry_id": exp},
    )
    assert rev2["ok"] is False

    # FIN-05..07: committee attendance -> honor rule -> generate (deduped) -> pay
    com_det = _call(api, "com.detail", {"institution_id": inst_id, "exam_id": exam_id})
    staff_id = com_det["data"]["staff"][0]["id"]
    _call(
        api,
        "ops.committee.attendance",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "att_date": "2026-12-01",
            "shift": "Pagi",
            "exam_person_id": staff_id,
            "state": "present",
        },
    )
    _call(
        api,
        "fin.honor.save_rule",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "role_code": "committee",
            "unit_type": "day",
            "rate_idr": 75000,
            "effective_date": "2026-12-01",
        },
    )
    gen1 = _call(
        api, "fin.honor.generate", {"institution_id": inst_id, "exam_id": exam_id}
    )
    assert gen1["data"]["created_count"] == 1
    gen2 = _call(
        api, "fin.honor.generate", {"institution_id": inst_id, "exam_id": exam_id}
    )
    assert gen2["data"]["created_count"] == 0

    fin_det = _call(api, "fin.detail", {"institution_id": inst_id, "exam_id": exam_id})
    hl_id = fin_det["data"]["honor_lines"][0]["id"]
    pay1 = _call(
        api,
        "fin.honor.pay",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "honor_line_id": hl_id,
            "category_id": c1,
            "entry_date": "2026-12-03",
        },
    )
    assert pay1["ok"] is True
    assert "tujuh puluh lima ribu rupiah" in pay1["data"]["amount_words"]
    pay2 = _call(
        api,
        "fin.honor.pay",
        {
            "institution_id": inst_id,
            "exam_id": exam_id,
            "honor_line_id": hl_id,
            "category_id": c1,
            "entry_date": "2026-12-03",
        },
    )
    assert pay2["ok"] is False

    # FIN-08: closing balance = 500000 - 100000 + 100000 - 75000 = 425000
    fin_det2 = _call(api, "fin.detail", {"institution_id": inst_id, "exam_id": exam_id})
    assert fin_det2["data"]["closing_balance_idr"] == 425000
