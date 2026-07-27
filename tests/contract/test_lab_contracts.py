from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai103.labs.registry import default_registry


def test_registered_labs_have_replayable_offline_and_live_shape_fixtures():
    registry = default_registry(ROOT)

    assert "LAB-SEARCH-RAG" in registry
    for spec in registry.values():
        offline = json.loads(spec.fixture_path.read_text(encoding="utf-8"))
        live_raw_path = spec.fixture_path.with_name(spec.fixture_path.name.replace(".offline.json", ".live-raw.json"))
        live_raw = json.loads(live_raw_path.read_text(encoding="utf-8"))

        assert set(offline["responses"]) == set(spec.required_response_shapes)
        assert all(shape in live_raw for shape in spec.required_response_shapes)
        assert spec.passing_score == 0.8


def test_lab_runner_source_keeps_offline_default_and_requires_explicit_live_adapter():
    text = (ROOT / "src" / "ai103" / "labs" / "runner.py").read_text(encoding="utf-8")

    assert 'mode: Mode = "offline"' in text
    assert "live_adapter is None" in text
    assert "live mode requires an explicit live_adapter" in text
    assert "_append_event" in text
