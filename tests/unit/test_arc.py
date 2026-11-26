"""Unit tests for ARC-01..ARC-04."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.core.errors import StorageError
from backend.modules.arc.schemas import ArcRetentionPurgePayload
from backend.modules.arc.service import _resolve_under_root, _safe_zip_member_name


def test_safe_zip_member_name_blocks_traversal() -> None:
    assert _safe_zip_member_name("metadata\\event.json") == "metadata/event.json"
    assert _safe_zip_member_name("/manifest.json") == "manifest.json"
    with pytest.raises(StorageError):
        _safe_zip_member_name("../secrets.txt")
    with pytest.raises(StorageError):
        _safe_zip_member_name("documents/../../evil.pdf")
    with pytest.raises(StorageError):
        _safe_zip_member_name("")


def test_resolve_under_root_blocks_escape(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    inside = _resolve_under_root(root, "exports/archives/test.zip")
    assert inside == (root / "exports/archives/test.zip").resolve()

    with pytest.raises(StorageError):
        _resolve_under_root(root, "../outside.txt")


def test_retention_purge_payload_requires_authorization() -> None:
    with pytest.raises(ValidationError):
        ArcRetentionPurgePayload(
            institution_id="inst1",
            exam_id="ex1",
            authorized_by="",
            confirm_title="PAS Ganjil",
        )
    valid = ArcRetentionPurgePayload(
        institution_id="inst1",
        exam_id="ex1",
        authorized_by="Kepala Sekolah",
        confirm_title="PAS Ganjil",
    )
    assert valid.authorized_by == "Kepala Sekolah"
