"""Unit tests for COM-01..COM-06 (org tree, signatories validation)."""

from __future__ import annotations

from backend.modules.com.models import CommitteeRole, ExamSignatory
from backend.modules.com.service import build_org_tree, validate_signatories_list


def test_build_org_tree_nests_children_and_members() -> None:
    r1 = CommitteeRole(
        id="r1",
        exam_id="e1",
        name="Ketua Panitia",
        parent_id=None,
        sort_order=1,
        jobdesc="Koordinator",
        revision=1,
        created_at="2026-11-25",
        updated_at="2026-11-25",
    )
    r2 = CommitteeRole(
        id="r2",
        exam_id="e1",
        name="Sekretaris",
        parent_id="r1",
        sort_order=2,
        jobdesc="Administrasi",
        revision=1,
        created_at="2026-11-25",
        updated_at="2026-11-25",
    )
    tree = build_org_tree([r1, r2], {"r1": [{"person_name": "Budi"}], "r2": []})
    assert len(tree) == 1
    assert tree[0]["name"] == "Ketua Panitia"
    assert len(tree[0]["children"]) == 1
    assert tree[0]["children"][0]["name"] == "Sekretaris"


def test_validate_signatories_blocks_missing_required_signer() -> None:
    s1 = ExamSignatory(
        id="s1",
        exam_id="e1",
        role_key="headmaster",
        role_label="Kepala Sekolah",
        exam_person_id=None,
        signer_name="",
        signer_title="Kepala Sekolah",
        signer_nip="",
        signed_date="",
        signature_asset_id=None,
        required=1,
        sort_order=1,
        revision=1,
        created_at="2026-11-25",
        updated_at="2026-11-25",
    )
    res = validate_signatories_list([s1])
    assert res["valid"] is False
    assert "Kepala Sekolah" in res["missing_required"]
