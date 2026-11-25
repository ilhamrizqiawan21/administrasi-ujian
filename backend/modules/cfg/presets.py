"""Built-in presets and defaults for CFG onboarding and configuration."""

from __future__ import annotations

from typing import Any

LEVEL_PRESETS: dict[str, list[str]] = {
    "SD/MI": ["I", "II", "III", "IV", "V", "VI"],
    "SMP/MTs": ["VII", "VIII", "IX"],
    "SMA/MA": ["X", "XI", "XII"],
    "SMK": ["X", "XI", "XII", "XIII"],
    "PKBM": ["Paket A", "Paket B", "Paket C"],
    "Kustom": [],
}

DEFAULT_EXAM_TYPES: list[dict[str, Any]] = [
    {
        "code": "STS",
        "label": "Sumatif Tengah Semester",
        "mode_default": "paper",
        "terminology": {
            "participant_term": "Peserta",
            "room_term": "Ruang Ujian",
            "invigilator_term": "Pengawas",
        },
    },
    {
        "code": "SAS",
        "label": "Sumatif Akhir Semester",
        "mode_default": "paper",
        "terminology": {
            "participant_term": "Peserta",
            "room_term": "Ruang Ujian",
            "invigilator_term": "Pengawas",
        },
    },
    {
        "code": "SAT",
        "label": "Sumatif Akhir Tahun",
        "mode_default": "paper",
        "terminology": {
            "participant_term": "Peserta",
            "room_term": "Ruang Ujian",
            "invigilator_term": "Pengawas",
        },
    },
]

DEFAULT_NUMBER_POLICIES: dict[str, Any] = {
    "participant": {
        "prefix": "UC",
        "separator": "-",
        "padding": 4,
        "start_seq": 1,
        "reset_scope": "event",
    },
    "document": {
        "pattern": "{seq}/{series}/{exam_code}/{year}",
        "padding": 3,
        "reset_scope": "year",
    },
}

DEFAULT_TYPED_SETTINGS: dict[str, Any] = {
    "default_paper_size": "A4",
    "solver_time_limit_sec": 60,
    "allow_part_time_weights": True,
    "extension_fields": [],
}
