"""Unit tests for FND-01 bridge, SQLite FK enforcement, and OR-Tools spike."""

from __future__ import annotations

from backend.bridge.api import BridgeApi


def test_app_info_returns_runtime_metadata() -> None:
    api = BridgeApi()
    res = api.invoke({"method": "app.info", "request_id": "req-1", "payload": {}})
    assert res["ok"] is True
    assert res["request_id"] == "req-1"
    data = res["data"]
    assert data["bridge_version"] == "1"
    assert "ortools" in data["packages"]
    assert "pywebview" in data["packages"]


def test_solver_ping_verifies_fk_and_cp_sat() -> None:
    api = BridgeApi()
    res = api.invoke(
        {"method": "spike.solver_ping", "request_id": "req-2", "payload": {}}
    )
    assert res["ok"] is True
    data = res["data"]
    assert data["fk_enforced"] is True
    assert data["solver_status"] == "OPTIMAL"
    assert len(data["assignments"]) == 2
    staff_ids = {item["staff_index"] for item in data["assignments"]}
    slot_ids = {item["slot_index"] for item in data["assignments"]}
    assert len(staff_ids) == 2
    assert slot_ids == {0, 1}
    assert {"staff_index": 0, "slot_index": 0} not in data["assignments"]


def test_unknown_method_rejected_with_method_not_allowed() -> None:
    api = BridgeApi()
    res = api.invoke({"method": "os.exec", "request_id": "req-3", "payload": {}})
    assert res["ok"] is False
    assert res["error"]["code"] == "METHOD_NOT_ALLOWED"


def test_invalid_envelope_rejected_with_validation_error() -> None:
    api = BridgeApi()
    res = api.invoke({"method": "BAD METHOD!", "request_id": "", "payload": {}})
    assert res["ok"] is False
    assert res["error"]["code"] == "VALIDATION"
