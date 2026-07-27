from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai103.labs.agents import AgentLabError, run_agent_lab


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the AI-103 guarded agent workflow lab.")
    parser.add_argument("--offline", action="store_true", help="Run deterministic offline replay mode.")
    parser.add_argument("--fixture", type=Path, default=None, help="Optional agent fixture path.")
    parser.add_argument("--event-log", type=Path, default=None, help="Optional NDJSON event log path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        run = run_agent_lab(root=ROOT, mode="offline", fixture_path=args.fixture, event_log_path=args.event_log)
    except AgentLabError as exc:
        print(f"Agent lab failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"result": run.result, "event": run.event}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

