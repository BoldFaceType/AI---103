from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai103.labs.governance import GovernanceLabError, run_governance_lab
from ai103.labs.media_generation import MediaGenerationLabError, run_media_generation_lab
from ai103.labs.speech import SpeechLabError, run_speech_lab


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run remaining AI-103 media, speech, and governance labs offline.")
    parser.add_argument("--offline", action="store_true", help="Run deterministic offline fixtures.")
    return parser


def main(argv: list[str] | None = None) -> int:
    build_parser().parse_args(argv)
    try:
        runs = {
            "media": run_media_generation_lab(root=ROOT),
            "speech": run_speech_lab(root=ROOT),
            "governance": run_governance_lab(root=ROOT),
        }
    except (GovernanceLabError, MediaGenerationLabError, SpeechLabError) as exc:
        print(f"Remaining labs failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({key: {"result": value.result, "event": value.event} for key, value in runs.items()}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

