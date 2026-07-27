from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from .runner import LabRun, run_lab

Mode = Literal["offline", "live"]


class MediaGenerationLabError(ValueError):
    """Raised when media generation lab requirements are not safe or complete."""


def run_media_generation_lab(*, root: Path, mode: Mode = "offline", event_log_path: Path | None = None, event_id: str | None = None) -> LabRun:
    if mode != "offline":
        raise MediaGenerationLabError("media generation live mode requires regional availability, quota, policy review, and approval")
    validate_media_generation_fixture(root / "fixtures" / "media-generation" / "README.md")
    return run_lab("LAB-MEDIA-GENERATION", root=root, mode="offline", event_log_path=event_log_path, event_id=event_id)


def validate_media_generation_fixture(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    required = ("offline simulation", "generated media must be labeled", "preview or unavailable services")
    missing = [phrase for phrase in required if phrase not in text.casefold()]
    if missing:
        raise MediaGenerationLabError(f"media fixture missing policy notes: {', '.join(missing)}")
    fixture = json.loads((path.parents[1] / "azure-responses" / "LAB-MEDIA-GENERATION.offline.json").read_text(encoding="utf-8"))
    media = fixture["responses"]["media_generation"]
    if not media["policy"]["generated_media_labeled"]:
        raise MediaGenerationLabError("generated media must be labeled")

