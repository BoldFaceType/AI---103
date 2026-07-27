from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def main() -> None:
    root = Path.cwd()
    script_path = root / "scripts" / "alo.py"
    if not script_path.exists():
        raise SystemExit("Run the alo CLI from the AI---103 repository root.")
    sys.path.insert(0, str(root / "scripts"))
    sys.path.insert(0, str(root / "src"))
    spec = importlib.util.spec_from_file_location("alo_script", script_path)
    if spec is None or spec.loader is None:
        raise SystemExit("Unable to load scripts/alo.py.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main()

