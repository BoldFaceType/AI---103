from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {} if default is None else default


def atomic_write_text(path: Path, content: str) -> None:
    ensure_directory(path.parent)
    with NamedTemporaryFile("w", delete=False, dir=path.parent, encoding="utf-8") as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    temp_path.replace(path)


def save_json(path: Path, data: Any) -> None:
    atomic_write_text(path, json.dumps(data, indent=2, sort_keys=True) + "\n")


def load_ndjson(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def append_ndjson(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    ensure_directory(path.parent)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    payload = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    atomic_write_text(path, existing + payload)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def relative_key(path: Path, root: Path | None = None) -> str:
    return path.relative_to(root or ROOT).as_posix()


def update_vmeta(path: Path, actor: str, root: Path | None = None) -> None:
    meta_dir = (root or ROOT) / "_meta" / "vmeta"
    ensure_directory(meta_dir)
    relative = relative_key(path, root).replace("/", "__")
    meta_path = meta_dir / f"{relative}.json"
    save_json(
        meta_path,
        {
            "path": relative_key(path, root),
            "hash": file_sha256(path),
            "updatedAt": utc_now(),
            "actor": actor,
        },
    )


def append_audit(action: str, path: str, actor: str, result: str, details: dict[str, Any] | None = None) -> None:
    audit_path = ROOT / "_meta" / "audit.log"
    row = {
        "ts": utc_now(),
        "action": action,
        "path": path,
        "actor": actor,
        "result": result,
        "details": details or {},
    }
    append_ndjson(audit_path, [row])