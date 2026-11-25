"""Unit tests for TSK-01..TSK-05 (DAG cycles and evidence validation)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.modules.tsk.schemas import TaskEvidencePayload
from backend.modules.tsk.service import has_dependency_cycle


def test_has_dependency_cycle_detects_direct_and_indirect_cycles() -> None:
    deps = [("t2", "t1"), ("t3", "t2")]
    assert has_dependency_cycle(deps, "t1", "t1") is True
    assert has_dependency_cycle(deps, "t1", "t3") is True
    assert has_dependency_cycle(deps, "t4", "t3") is False


def test_task_evidence_payload_rejects_path_traversal() -> None:
    with pytest.raises(ValidationError, match="Referensi berkas bukti"):
        TaskEvidencePayload(
            institution_id="inst-1",
            exam_id="ex-1",
            task_id="t-1",
            evidence_asset_id="../secret.pdf",
            completed_by="Operator",
        )
