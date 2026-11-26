"""Unit tests for BAK-01..BAK-04."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.core.errors import StorageError
from backend.modules.bak.schemas import BakScheduleSavePayload
from backend.modules.bak.service import _resolve_under_root, _safe_zip_member


def test_safe_zip_member_blocks_traversal() -> None:
    assert _safe_zip_member("db\\database.sqlite") == "db/database.sqlite"
    with pytest.raises(StorageError):
        _safe_zip_member("../outside.sqlite")
    with pytest.raises(StorageError):
        _safe_zip_member("assets/../../secret.txt")


def test_resolve_under_root_blocks_escape(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    ok = _resolve_under_root(root, "backups/test.zip")
    assert ok == (root / "backups/test.zip").resolve()
    with pytest.raises(StorageError):
        _resolve_under_root(root, "../../etc/passwd")


def test_schedule_retention_count_min_one() -> None:
    with pytest.raises(ValidationError):
        BakScheduleSavePayload(institution_id="inst1", retention_count=0)
    valid = BakScheduleSavePayload(institution_id="inst1", retention_count=1)
    assert valid.retention_count == 1
