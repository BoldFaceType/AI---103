from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai103.labs.vision import VisionLabError, live_cost_notice, run_vision_lab
from ai103.services.settings import load_service_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the AI-103 multimodal vision analysis lab.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--offline", action="store_true", help="Run deterministic offline fixture mode.")
    mode.add_argument("--live", action="store_true", help="Run explicit live Azure Foundry vision analysis.")
    parser.add_argument("input_path", type=Path, help="Approved image file or directory.")
    parser.add_argument("--event-log", type=Path, default=None, help="Optional NDJSON event log path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    mode = "live" if args.live else "offline"
    settings = load_service_settings() if mode == "live" else None
    if settings is not None:
        print(live_cost_notice(settings))
    try:
        run = run_vision_lab(args.input_path, root=ROOT, mode=mode, settings=settings, event_log_path=args.event_log)
    except VisionLabError as exc:
        print(f"Vision lab failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"result": run.result, "event": run.event}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

