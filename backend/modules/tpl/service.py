"""Transactional service layer for TPL-01..TPL-06."""

from __future__ import annotations

import base64
import binascii
import io
import json
import re
import uuid
import zipfile
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from backend.core.db import session_scope
from backend.core.errors import ConflictError, NotFoundError, ValidationError
from backend.modules.cfg.repository import CfgRepository
from backend.modules.tpl.models import Letterhead, TemplateRecord, ThemeProfile
from backend.modules.tpl.repository import TplRepository
from backend.modules.tpl.schemas import (
    ALLOWLISTED_PLACEHOLDERS,
    PAPER_DIMENSIONS_MM,
    LetterheadImagePayload,
    LetterheadManualPayload,
    TemplateDocxValidatePayload,
    TemplateSavePayload,
    ThemeProfileSavePayload,
    TplScopedPayload,
)

BUILTIN_DOC_TYPES: list[tuple[str, str]] = [
    ("kartu_peserta", "Kartu Peserta Ujian"),
    ("daftar_hadir", "Daftar Hadir Peserta"),
    ("berita_acara", "Berita Acara Pelaksanaan"),
    ("denah_ruang", "Denah Tempat Duduk"),
    ("sk_panitia", "SK & Struktur Panitia"),
    ("program_kerja", "Program Kerja Panitia"),
]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex


def _relative_luminance(hex_color: str) -> float:
    r = int(hex_color[1:3], 16) / 255.0
    g = int(hex_color[3:5], 16) / 255.0
    b = int(hex_color[5:7], 16) / 255.0

    def _lin(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast_ratio(hex_a: str, hex_b: str) -> float:
    """Compute WCAG 2.1 contrast ratio between two #RRGGBB colors."""
    la = _relative_luminance(hex_a)
    lb = _relative_luminance(hex_b)
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


def validate_image_bytes(raw: bytes) -> str:
    """Validate PNG/JPEG magic bytes (TPL-02)."""
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if raw.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    raise ValidationError("Berkas gambar tidak valid (hanya PNG atau JPEG).")


def inspect_docx_bytes(raw: bytes) -> dict[str, Any]:
    """Inspect DOCX archive for macros, external rels, and placeholders (TPL-04)."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile as exc:
        raise ValidationError("Berkas DOCX tidak valid atau rusak.") from exc

    with zf:
        names = zf.namelist()
        if any("vbaproject.bin" in n.lower() for n in names):
            raise ConflictError("Dokumen DOCX mengandung macro (dilarang).")

        for n in names:
            if n.endswith(".rels"):
                rel_xml = zf.read(n).decode("utf-8", errors="ignore")
                if 'TargetMode="External"' in rel_xml:
                    raise ConflictError(
                        "Dokumen DOCX mengandung relasi eksternal (dilarang)."
                    )

        if "word/document.xml" not in names:
            raise ValidationError("Struktur word/document.xml tidak ditemukan.")
        doc_xml = zf.read("word/document.xml").decode("utf-8", errors="ignore")
        plain = re.sub(r"<[^>]+>", "", doc_xml)
        tags = sorted(set(re.findall(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", plain)))
        unknown = [t for t in tags if t not in ALLOWLISTED_PLACEHOLDERS]
        return {
            "valid": len(unknown) == 0,
            "found_tags": tags,
            "unknown_tags": unknown,
            "allowlisted": sorted(ALLOWLISTED_PLACEHOLDERS),
        }


class TplService:
    """Application service for Template & Branding (TPL-01..TPL-06)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._repo = TplRepository()
        self._cfg_repo = CfgRepository()

    def _require_inst(self, session: Session, institution_id: str) -> None:
        if self._cfg_repo.get_institution(session, institution_id) is None:
            raise NotFoundError("Lembaga tidak ditemukan.")

    def get_detail(self, payload: TplScopedPayload) -> dict[str, Any]:
        with session_scope(self._session_factory) as session:
            self._require_inst(session, payload.institution_id)
            lhs = self._repo.list_letterheads(session, payload.institution_id)
            tpls = self._repo.list_templates(session, payload.institution_id)
            themes = self._repo.list_theme_profiles(session, payload.institution_id)

            builtins = [
                {
                    "id": f"builtin-{dt}",
                    "doc_type": dt,
                    "name": label,
                    "version": 1,
                    "engine": "reportlab",
                    "layout": {"paper_size": "A4"},
                    "active": True,
                    "builtin": True,
                }
                for dt, label in BUILTIN_DOC_TYPES
            ]

            custom_tpls = [
                {
                    "id": t.id,
                    "doc_type": t.doc_type,
                    "name": t.name,
                    "version": t.version,
                    "engine": t.engine,
                    "layout": json.loads(t.layout_json),
                    "active": bool(t.active),
                    "builtin": False,
                }
                for t in tpls
            ]

            return {
                "paper_dimensions_mm": PAPER_DIMENSIONS_MM,
                "allowlisted_placeholders": sorted(ALLOWLISTED_PLACEHOLDERS),
                "letterheads": [
                    {
                        "id": lh.id,
                        "name": lh.name,
                        "mode": lh.mode,
                        "config": json.loads(lh.config_json),
                        "version": lh.version,
                        "active": bool(lh.active),
                    }
                    for lh in lhs
                ],
                "templates": [*builtins, *custom_tpls],
                "theme_profiles": [
                    {
                        "id": th.id,
                        "name": th.name,
                        "tokens": json.loads(th.tokens_json),
                        "version": th.version,
                        "active": bool(th.active),
                    }
                    for th in themes
                ],
            }

    def save_manual_letterhead(
        self, payload: LetterheadManualPayload
    ) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            self._require_inst(session, payload.institution_id)
            existing = self._repo.list_letterheads(session, payload.institution_id)
            next_ver = max((lh.version for lh in existing), default=0) + 1
            for old in existing:
                old.active = 0

            lh = Letterhead(
                id=_new_id(),
                institution_id=payload.institution_id,
                name=payload.name.strip(),
                mode="manual",
                config_json=json.dumps(
                    {
                        "header_lines": payload.header_lines,
                        "alignment": payload.alignment,
                        "line_style": payload.line_style,
                        "paper_size": payload.paper_size,
                    }
                ),
                asset_id=None,
                version=next_ver,
                active=1,
                created_at=now,
            )
            session.add(lh)
            session.flush()
            return {"id": lh.id, "version": lh.version}

    def upload_image_letterhead(
        self, payload: LetterheadImagePayload
    ) -> dict[str, Any]:
        now = _now_iso()
        try:
            raw = base64.b64decode(payload.image_b64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValidationError("Data base64 gambar tidak valid.") from exc
        fmt = validate_image_bytes(raw)

        with session_scope(self._session_factory) as session:
            self._require_inst(session, payload.institution_id)
            existing = self._repo.list_letterheads(session, payload.institution_id)
            next_ver = max((lh.version for lh in existing), default=0) + 1
            for old in existing:
                old.active = 0

            lh = Letterhead(
                id=_new_id(),
                institution_id=payload.institution_id,
                name=payload.name.strip(),
                mode="image",
                config_json=json.dumps(
                    {"format": fmt, "paper_size": payload.paper_size, "bytes": len(raw)}
                ),
                asset_id=f"letterhead-v{next_ver}.{fmt}",
                version=next_ver,
                active=1,
                created_at=now,
            )
            session.add(lh)
            session.flush()
            return {"id": lh.id, "version": lh.version, "format": fmt}

    def save_template(self, payload: TemplateSavePayload) -> dict[str, Any]:
        now = _now_iso()
        with session_scope(self._session_factory) as session:
            self._require_inst(session, payload.institution_id)
            existing = [
                t
                for t in self._repo.list_templates(session, payload.institution_id)
                if t.institution_id == payload.institution_id
                and t.doc_type == payload.doc_type
            ]
            next_ver = max((t.version for t in existing), default=0) + 1
            if payload.activate:
                for old in existing:
                    old.active = 0

            tpl = TemplateRecord(
                id=_new_id(),
                institution_id=payload.institution_id,
                doc_type=payload.doc_type,
                name=payload.name.strip(),
                version=next_ver,
                engine=payload.engine,
                asset_id=None,
                layout_json=payload.layout.model_dump_json(),
                mapping_json=json.dumps(payload.mapping),
                active=1 if payload.activate else 0,
                created_at=now,
            )
            session.add(tpl)
            session.flush()
            return {"id": tpl.id, "version": tpl.version}

    def validate_docx_template(
        self, payload: TemplateDocxValidatePayload
    ) -> dict[str, Any]:
        try:
            raw = base64.b64decode(payload.docx_b64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValidationError("Data base64 DOCX tidak valid.") from exc
        return inspect_docx_bytes(raw)

    def save_theme_profile(self, payload: ThemeProfileSavePayload) -> dict[str, Any]:
        now = _now_iso()
        ratio = contrast_ratio(payload.surface_hex, payload.text_hex)
        if ratio < 4.5:
            raise ValidationError(
                f"Kontras teks terhadap latar ({ratio:.2f}:1) di bawah minimum 4.5:1."
            )
        with session_scope(self._session_factory) as session:
            self._require_inst(session, payload.institution_id)
            existing = self._repo.list_theme_profiles(session, payload.institution_id)
            next_ver = max((th.version for th in existing), default=0) + 1
            for old in existing:
                old.active = 0

            th = ThemeProfile(
                id=_new_id(),
                institution_id=payload.institution_id,
                name=payload.name.strip(),
                tokens_json=json.dumps(
                    {
                        "app_title": payload.app_title,
                        "palette_preset": payload.palette_preset,
                        "density": payload.density,
                        "surface_hex": payload.surface_hex,
                        "text_hex": payload.text_hex,
                        "accent_hex": payload.accent_hex,
                        "contrast_ratio": round(ratio, 2),
                    }
                ),
                version=next_ver,
                active=1,
                created_at=now,
            )
            session.add(th)
            session.flush()
            return {
                "id": th.id,
                "version": th.version,
                "contrast_ratio": round(ratio, 2),
            }
