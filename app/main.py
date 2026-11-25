"""Application entrypoint for Ujian Cerdas desktop shell."""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

import webview

from backend.bridge.api import BridgeApi
from backend.core.app_shell import AppRuntime, bootstrap_runtime
from backend.core.errors import AppError


def _resolve_frontend_entry() -> Path:
    base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base_dir / "frontend" / "dist" / "index.html"


def _render_recovery_html(message: str) -> str:
    safe_msg = html.escape(message)
    return (
        "<!doctype html><html lang='id'><head><meta charset='utf-8'>"
        "<title>Pemulihan Startup — Ujian Cerdas</title>"
        "<style>body{font-family:'Segoe UI',sans-serif;background:#E7EFF3;"
        "color:#193440;display:grid;place-items:center;min-height:100vh;margin:0;}"
        ".card{background:#F1F6F7;border:1px solid #C5D7DE;border-radius:8px;"
        "padding:24px;max-width:520px;}"
        "h1{font-size:20px;margin:0 0 8px;}p{margin:8px 0;color:#4D6570;}"
        "</style></head><body><main class='card'>"
        "<h1>Aplikasi Gagal Dimulai</h1>"
        f"<p>{safe_msg}</p>"
        "<p>Pastikan folder workspace dapat ditulis dan tidak ada instance lain "
        "yang sedang membuka database yang sama.</p>"
        "</main></body></html>"
    )


def run_self_test() -> int:
    """Verify full foundation runtime, bridge, DB, and solver without GUI."""
    runtime: AppRuntime | None = None
    try:
        runtime = bootstrap_runtime()
        api = BridgeApi(runtime=runtime)
        info = api.invoke(
            {"method": "app.info", "request_id": "selftest-1", "payload": {}}
        )
        health = api.invoke(
            {"method": "app.health", "request_id": "selftest-2", "payload": {}}
        )
        solver = api.invoke(
            {"method": "spike.solver_ping", "request_id": "selftest-3", "payload": {}}
        )
        print(
            json.dumps(
                {"app_info": info, "app_health": health, "solver_ping": solver},
                indent=2,
            )
        )
        if not (info.get("ok") and health.get("ok") and solver.get("ok")):
            return 1
        if not health["data"]["db"].get("ok"):
            return 1
        if not solver["data"].get("fk_enforced"):
            return 1
        if solver["data"].get("solver_status") != "OPTIMAL":
            return 1
        return 0
    finally:
        if runtime is not None:
            runtime.shutdown()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ujian Cerdas Desktop")
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run headless foundation verification.",
    )
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    index_html = _resolve_frontend_entry()
    runtime: AppRuntime | None = None
    try:
        runtime = bootstrap_runtime()
    except AppError as exc:
        webview.create_window(
            "Ujian Cerdas — Pemulihan",
            html=_render_recovery_html(exc.message),
            width=640,
            height=420,
        )
        webview.start(debug=False)
        return 1
    except Exception:
        webview.create_window(
            "Ujian Cerdas — Pemulihan",
            html=_render_recovery_html(
                "Terjadi kesalahan tak terduga saat inisialisasi."
            ),
            width=640,
            height=420,
        )
        webview.start(debug=False)
        return 1

    if not index_html.exists():
        runtime.shutdown()
        print(
            f"Frontend build tidak ditemukan di {index_html}.",
            file=sys.stderr,
        )
        return 1

    api = BridgeApi(runtime=runtime)
    window = webview.create_window(
        "Ujian Cerdas",
        url=index_html.as_uri(),
        js_api=api,
        width=1280,
        height=800,
        min_size=(800, 600),
    )

    def _on_closed() -> None:
        if runtime is not None:
            runtime.shutdown()

    if window is not None:
        window.events.closed += _on_closed
    try:
        webview.start(debug=False)
    finally:
        runtime.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
