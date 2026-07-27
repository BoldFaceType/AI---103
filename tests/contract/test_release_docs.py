from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RELEASES = ROOT / "docs" / "releases"


def read_release_doc(name: str) -> str:
    return (RELEASES / name).read_text(encoding="utf-8")


def test_acceptance_doc_keeps_final_release_blocked_until_human_live_gates():
    text = read_release_doc("v1.0.0-acceptance.md")

    assert "Final v1.0.0 release is not approved" in text
    assert "No live Azure resources were created" in text
    assert "No live model calls were made" in text
    assert "docs/releases/v1.0.0-live-gates.md" in text
    for gate in ("H1", "H2", "H3", "H4"):
        assert f"| {gate} |" in text
        assert "Pending user" in text


def test_coverage_matrix_has_one_complete_row_per_official_competency():
    text = read_release_doc("v1.0.0-coverage.md")
    rows = [line for line in text.splitlines() if re.match(r"^\| (PM|GA|CV|TA|IE)-\d{2} \|", line)]

    assert len(rows) == 64
    assert "Covered competencies: 64/64" in text
    for row in rows:
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        assert len(cells) == 8
        assert all(cells)
        assert cells[-2] == "Yes: offline eval/test pass"
        assert cells[-1] == "Pending H1-H3; live not run"


def test_live_gate_checklist_requires_explicit_owner_approval_before_live_actions():
    text = read_release_doc("v1.0.0-live-gates.md")

    required_fragments = (
        "Do not create or select an Azure subscription on behalf of the learner.",
        "Do not accept billing, legal, or marketplace terms on behalf of the learner.",
        "Do not run live deployment, live model calls, or live tests without explicit approval.",
        "az account show",
        "uv run alo doctor --live",
        'powershell -ExecutionPolicy Bypass -File scripts/azure/deploy.ps1 -Live -WhatIf -Confirmation "deploy AI-103 live lab" -Location <region>',
        'powershell -ExecutionPolicy Bypass -File scripts/azure/deploy.ps1 -Live -Confirmation "deploy AI-103 live lab" -Location <region>',
        "release: complete AI-103 adaptive study system v1.0.0",
    )
    for fragment in required_fragments:
        assert fragment in text

    for gate in ("## H1", "## H2", "## H3", "## H4"):
        assert gate in text
