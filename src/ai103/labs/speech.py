from __future__ import annotations

from pathlib import Path
from typing import Literal

from .runner import LabRun, run_lab

Mode = Literal["offline", "live"]


class SpeechLabError(ValueError):
    """Raised when speech fixture consent or license requirements fail."""


def run_speech_lab(*, root: Path, mode: Mode = "offline", event_log_path: Path | None = None, event_id: str | None = None) -> LabRun:
    if mode != "offline":
        raise SpeechLabError("speech live mode requires explicit service availability, consent, and approval")
    validate_audio_fixture_metadata(root / "fixtures" / "audio" / "README.md")
    return run_lab("LAB-SPEECH-TRANSLATION", root=root, mode="offline", event_log_path=event_log_path, event_id=event_id)


def validate_audio_fixture_metadata(path: Path) -> None:
    text = path.read_text(encoding="utf-8").casefold()
    for phrase in ("synthetic audio", "consent: granted", "license: repository fixture"):
        if phrase not in text:
            raise SpeechLabError(f"audio fixture metadata missing {phrase}")

