from __future__ import annotations

import importlib.metadata
import importlib.util
import os
import platform
import re
import shutil
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ai103.services.auth import AzureAuthError, assert_credential_ready, create_default_credential
from ai103.services.settings import SettingsError, load_service_settings, redact_value


GUID_RE = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
URL_RE = re.compile(r"https://[^\s,]+")


CommandRunner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    status: str
    detail: str
    remediation: str


@dataclass(frozen=True)
class DoctorReport:
    checks: tuple[DoctorCheck, ...]

    @property
    def ok(self) -> bool:
        return all(check.status != "FAIL" for check in self.checks)


def run_doctor(
    *,
    root: Path,
    live: bool,
    environ: Mapping[str, str] | None = None,
    command_runner: CommandRunner | None = None,
) -> DoctorReport:
    env = environ or os.environ
    runner = command_runner or _run_command
    checks = [
        _check_python_and_dependencies(),
        _check_curriculum(root),
        _check_writable_paths(root),
        _check_offline_fixtures(root),
        _check_azure_cli(live, runner),
        _check_azure_account(live, runner),
        _check_live_settings(live, env),
        _check_live_credentials(live, env),
        _check_cost_teardown_state(root, live, env),
    ]
    return DoctorReport(tuple(checks))


def render_report(report: DoctorReport, *, live: bool) -> str:
    lines = [f"AI-103 doctor ({'live read-only' if live else 'offline'})"]
    for check in report.checks:
        detail = _sanitize(check.detail)
        remediation = _sanitize(check.remediation)
        lines.append(f"[{check.status}] {check.name}: {detail}")
        lines.append(f"  remediation: {remediation}")
    lines.append(f"overall: {'PASS' if report.ok else 'FAIL'}")
    return "\n".join(lines)


def _check_python_and_dependencies() -> DoctorCheck:
    required = ("pytest", "azure-identity", "azure-ai-projects", "azure-search-documents", "azure-ai-contentunderstanding")
    versions: list[str] = [f"python {platform.python_version()}"]
    missing: list[str] = []
    for package in required:
        try:
            versions.append(f"{package} {importlib.metadata.version(package)}")
        except importlib.metadata.PackageNotFoundError:
            missing.append(package)
    if missing:
        return DoctorCheck(
            "Python and dependency versions",
            "FAIL",
            f"missing packages: {', '.join(missing)}",
            "Run 'uv sync --dev' from the repository root.",
        )
    return DoctorCheck("Python and dependency versions", "PASS", ", ".join(versions), "No action required.")


def _check_curriculum(root: Path) -> DoctorCheck:
    audit_path = root / "scripts" / "curriculum_audit.py"
    if not audit_path.exists():
        return DoctorCheck("Curriculum freshness and coverage", "FAIL", "curriculum audit script is missing", "Restore scripts/curriculum_audit.py.")
    spec = importlib.util.spec_from_file_location("ai103_doctor_curriculum_audit", audit_path)
    if spec is None or spec.loader is None:
        return DoctorCheck("Curriculum freshness and coverage", "FAIL", "curriculum audit script cannot be loaded", "Check script syntax and path.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    errors, report = module.audit()
    coverage = next((line for line in report if "Covered competencies:" in line), "coverage unavailable")
    if errors:
        return DoctorCheck(
            "Curriculum freshness and coverage",
            "FAIL",
            "; ".join(errors),
            "Run 'uv run python scripts/curriculum_audit.py' and fix the reported curriculum issue.",
        )
    return DoctorCheck("Curriculum freshness and coverage", "PASS", coverage, "No action required.")


def _check_writable_paths(root: Path) -> DoctorCheck:
    paths = [root / "state", root / "logs", root / "_meta"]
    missing = [path.relative_to(root).as_posix() for path in paths if not path.exists() and not os.access(path.parent, os.W_OK)]
    blocked = [path.relative_to(root).as_posix() for path in paths if path.exists() and not os.access(path, os.W_OK)]
    if missing or blocked:
        detail = f"missing or blocked paths: {', '.join(missing + blocked)}"
        return DoctorCheck("Writable state and audit paths", "FAIL", detail, "Create the path or fix filesystem permissions.")
    return DoctorCheck("Writable state and audit paths", "PASS", "state, logs, and audit paths are writable or creatable", "No action required.")


def _check_offline_fixtures(root: Path) -> DoctorCheck:
    lessons = list((root / "content" / "lessons" / "ai103").rglob("*.md"))
    assessments = list((root / "content" / "assessments" / "ai103").rglob("*.json"))
    if not lessons or not assessments:
        return DoctorCheck(
            "Offline fixture availability",
            "FAIL",
            "lesson or assessment fixtures are missing",
            "Restore content/lessons/ai103 and content/assessments/ai103 before running offline study.",
        )
    return DoctorCheck(
        "Offline fixture availability",
        "PASS",
        f"{len(lessons)} lesson files and {len(assessments)} assessment fixtures found",
        "No action required.",
    )


def _check_azure_cli(live: bool, runner: CommandRunner) -> DoctorCheck:
    if not live:
        return DoctorCheck("Azure CLI availability", "SKIP", "offline mode does not require Azure CLI", "Use --live for Azure readiness checks.")
    if not shutil.which("az"):
        return DoctorCheck("Azure CLI availability", "FAIL", "az executable not found", "Install Azure CLI and rerun 'alo doctor --live'.")
    result = runner(["az", "--version"])
    if result.returncode != 0:
        return DoctorCheck("Azure CLI availability", "FAIL", result.stderr or result.stdout, "Repair Azure CLI installation.")
    return DoctorCheck("Azure CLI availability", "PASS", "Azure CLI responded to --version", "No action required.")


def _check_azure_account(live: bool, runner: CommandRunner) -> DoctorCheck:
    if not live:
        return DoctorCheck("Selected tenant/subscription", "SKIP", "offline mode does not require Azure login", "Use --live after 'az login'.")
    result = runner(["az", "account", "show", "--query", "{tenantId:tenantId,subscriptionId:id,name:name}", "-o", "json"])
    if result.returncode != 0:
        return DoctorCheck(
            "Selected tenant/subscription",
            "FAIL",
            result.stderr or result.stdout or "az account show failed",
            "Run 'az login' and 'az account set --subscription <subscription-id>'.",
        )
    return DoctorCheck("Selected tenant/subscription", "PASS", result.stdout, "No action required.")


def _check_live_settings(live: bool, environ: Mapping[str, str]) -> DoctorCheck:
    if not live:
        return DoctorCheck("Foundry/Search/Content Understanding settings", "SKIP", "offline mode does not require Azure endpoints", "Use --live after setting .env values.")
    try:
        settings = load_service_settings(environ)
        settings.require_foundry()
        settings.require_search()
        settings.require_content_understanding()
    except SettingsError as exc:
        return DoctorCheck(
            "Foundry/Search/Content Understanding settings",
            "FAIL",
            str(exc),
            "Populate non-secret .env settings from .env.example; do not use API keys.",
        )
    detail = (
        f"Foundry {redact_value(settings.foundry_project_endpoint)}, "
        f"Search {redact_value(settings.search_endpoint)}, "
        f"Content Understanding {redact_value(settings.content_understanding_endpoint)}"
    )
    return DoctorCheck("Foundry/Search/Content Understanding settings", "PASS", detail, "No action required.")


def _check_live_credentials(live: bool, environ: Mapping[str, str]) -> DoctorCheck:
    if not live:
        return DoctorCheck("Foundry/model/Search/Content Understanding access", "SKIP", "offline mode does not request credentials", "Use --live after Azure login.")
    try:
        load_service_settings(environ)
        assert_credential_ready(create_default_credential())
    except (SettingsError, AzureAuthError) as exc:
        return DoctorCheck(
            "Foundry/model/Search/Content Understanding access",
            "FAIL",
            str(exc),
            "Run 'az login', select the subscription, and verify least-privilege role assignments.",
        )
    return DoctorCheck("Foundry/model/Search/Content Understanding access", "PASS", "credential token acquired", "No action required.")


def _check_cost_teardown_state(root: Path, live: bool, environ: Mapping[str, str]) -> DoctorCheck:
    state_path = root / "state" / "azure-live" / "last-deployment.json"
    cost_ack = environ.get("AI103_COST_ACKNOWLEDGED") == "true"
    if not live:
        detail = "offline mode; cost acknowledgment and teardown state are checked only in live mode"
        return DoctorCheck("Quota, region, cost acknowledgment, and teardown state", "SKIP", detail, "Use --live before live labs.")
    if not cost_ack:
        return DoctorCheck(
            "Quota, region, cost acknowledgment, and teardown state",
            "FAIL",
            "AI103_COST_ACKNOWLEDGED is not true",
            "Review docs/operations/COST_AND_TEARDOWN.md, confirm quota/region/budget, then set AI103_COST_ACKNOWLEDGED=true.",
        )
    detail = "cost acknowledgment present"
    if state_path.exists():
        detail += "; prior live state file exists"
    return DoctorCheck("Quota, region, cost acknowledgment, and teardown state", "PASS", detail, "No action required.")


def _run_command(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


def _sanitize(text: str) -> str:
    cleaned = text
    cleaned = URL_RE.sub("https://<redacted-endpoint>", cleaned)
    cleaned = GUID_RE.sub("<redacted-id>", cleaned)
    for marker in ("token", "secret", "password", "key"):
        cleaned = cleaned.replace(marker, "<redacted>")
        cleaned = cleaned.replace(marker.upper(), "<redacted>")
    return cleaned


def main(*, root: Path, live: bool) -> int:
    report = run_doctor(root=root, live=live)
    print(render_report(report, live=live))
    return 0 if report.ok else 1
