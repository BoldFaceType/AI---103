from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai103.operations.doctor import DoctorCheck, DoctorReport, render_report, run_doctor


def test_doctor_offline_passes_without_azure_credentials():
    report = run_doctor(root=ROOT, live=False, environ={})

    assert report.ok
    checks = {check.name: check for check in report.checks}
    assert checks["Azure CLI availability"].status == "SKIP"
    assert checks["Selected tenant/subscription"].status == "SKIP"
    assert checks["Foundry/Search/Content Understanding settings"].status == "SKIP"
    assert checks["Foundry/model/Search/Content Understanding access"].status == "SKIP"
    assert checks["Curriculum freshness and coverage"].status == "PASS"
    assert checks["Offline fixture availability"].status == "PASS"


def test_doctor_live_checks_are_read_only_and_report_missing_login():
    commands: list[tuple[str, ...]] = []

    def runner(command: list[str] | tuple[str, ...]) -> subprocess.CompletedProcess[str]:
        commands.append(tuple(command))
        if command[:2] == ["az", "--version"]:
            return subprocess.CompletedProcess(command, 0, stdout="azure-cli 2.80.0", stderr="")
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="Please run az login.")

    report = run_doctor(root=ROOT, live=True, environ={}, command_runner=runner)

    assert not report.ok
    assert ("az", "--version") in commands
    assert any(command[:3] == ("az", "account", "show") for command in commands)
    assert not any("create" in command or "delete" in command or "deployment" in command for command in commands)
    assert any("az login" in check.remediation for check in report.checks)


def test_doctor_live_redacts_settings_and_secret_markers():
    report = DoctorReport(
        (
            DoctorCheck(
                "redaction",
                "FAIL",
                "endpoint https://acct.services.ai.azure.com/api/projects/project-a token abc password xyz",
                "set key value after checking tenant 00000000-1111-2222-3333-444444444444",
            ),
        )
    )

    output = render_report(report, live=True)

    assert "token" not in output.casefold()
    assert "password" not in output.casefold()
    assert "key" not in output.casefold()
    assert "00000000-1111-2222-3333-444444444444" not in output


def test_doctor_live_requires_cost_acknowledgment_and_settings():
    env = {
        "FOUNDRY_PROJECT_ENDPOINT": "https://acct.services.ai.azure.com/api/projects/project-a",
        "FOUNDRY_MODEL_NAME": "gpt-4.1-mini",
        "AZURE_SEARCH_ENDPOINT": "https://search-a.search.windows.net",
        "AZURE_SEARCH_INDEX": "ai103-index",
        "CONTENTUNDERSTANDING_ENDPOINT": "https://acct.services.ai.azure.com",
    }

    report = run_doctor(
        root=ROOT,
        live=True,
        environ=env,
        command_runner=lambda command: subprocess.CompletedProcess(command, 0, stdout=json.dumps({}), stderr=""),
    )

    checks = {check.name: check for check in report.checks}
    assert checks["Foundry/Search/Content Understanding settings"].status == "PASS"
    assert checks["Quota, region, cost acknowledgment, and teardown state"].status == "FAIL"
    assert "AI103_COST_ACKNOWLEDGED" in checks["Quota, region, cost acknowledgment, and teardown state"].detail


def test_alo_parser_includes_doctor_modes():
    sys.path.insert(0, str(ROOT / "scripts"))
    import alo

    parser = alo.build_parser()
    assert parser.parse_args(["doctor", "--offline"]).command == "doctor"
    assert parser.parse_args(["doctor", "--live"]).live is True
