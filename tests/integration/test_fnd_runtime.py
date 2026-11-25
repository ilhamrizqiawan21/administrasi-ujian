"""Integration tests for FND-03..FND-08 runtime bootstrap, DB, and bridge."""

from __future__ import annotations

from pathlib import Path

import pytest
import sqlalchemy
from sqlalchemy import text

from backend.bridge.api import BridgeApi
from backend.core.app_shell import bootstrap_runtime
from backend.core.errors import StorageError


def test_runtime_bootstrap_migrations_fk_and_bridge(tmp_path: Path) -> None:
    runtime = bootstrap_runtime(workspace_root=tmp_path, institution_slug="mts_test")
    try:
        api = BridgeApi(runtime=runtime)
        health = api.invoke(
            {"method": "app.health", "request_id": "int-1", "payload": {}}
        )
        assert health["ok"] is True
        assert health["data"]["db"]["ok"] is True
        assert health["data"]["db"]["foreign_keys"] == 1

        with runtime.engine.begin() as conn:
            tables = {
                row[0]
                for row in conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table'")
                )
            }
            assert "app_meta" in tables
            assert "jobs" in tables
            assert "alembic_version" in tables

            conn.execute(text("CREATE TABLE p_test (id TEXT PRIMARY KEY)"))
            conn.execute(
                text(
                    "CREATE TABLE c_test ("
                    "id TEXT PRIMARY KEY, "
                    "p_id TEXT NOT NULL REFERENCES p_test(id)"
                    ")"
                )
            )
            with pytest.raises(sqlalchemy.exc.IntegrityError):
                conn.execute(text("INSERT INTO c_test VALUES ('c1', 'missing')"))

        with pytest.raises(StorageError):
            bootstrap_runtime(workspace_root=tmp_path, institution_slug="mts_test")
    finally:
        runtime.shutdown()

    runtime2 = bootstrap_runtime(workspace_root=tmp_path, institution_slug="mts_test")
    runtime2.shutdown()
