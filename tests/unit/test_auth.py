from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai103.services.auth import AzureAuthError, assert_credential_ready
from ai103.services.settings import SettingsError, load_service_settings, redact_mapping, redact_value


class FailingCredential:
    def __init__(self, message: str) -> None:
        self.message = message

    def get_token(self, *scopes: str, **kwargs: object) -> object:
        raise RuntimeError(self.message)


class RecordingCredential:
    def __init__(self) -> None:
        self.scopes: list[tuple[str, ...]] = []

    def get_token(self, *scopes: str, **kwargs: object) -> object:
        self.scopes.append(tuple(scopes))
        return object()


def test_load_service_settings_rejects_committed_key_environment():
    with pytest.raises(SettingsError, match="API keys/tokens are not supported"):
        load_service_settings({"AZURE_SEARCH_API_KEY": "not-allowed"})


def test_foundry_search_and_content_settings_validate_expected_shapes():
    settings = load_service_settings(
        {
            "FOUNDRY_PROJECT_ENDPOINT": "https://acct.services.ai.azure.com/api/projects/project-a",
            "FOUNDRY_MODEL_NAME": "gpt-4.1-mini",
            "AZURE_SEARCH_ENDPOINT": "https://search-a.search.windows.net",
            "AZURE_SEARCH_INDEX": "ai103-index",
            "CONTENTUNDERSTANDING_ENDPOINT": "https://acct.services.ai.azure.com",
        }
    )

    settings.require_foundry()
    settings.require_search()
    settings.require_content_understanding()


def test_settings_validation_reports_missing_live_values():
    settings = load_service_settings({})

    with pytest.raises(SettingsError, match="FOUNDRY_PROJECT_ENDPOINT is required"):
        settings.require_foundry()
    with pytest.raises(SettingsError, match="AZURE_SEARCH_ENDPOINT is required"):
        settings.require_search()
    with pytest.raises(SettingsError, match="CONTENTUNDERSTANDING_ENDPOINT is required"):
        settings.require_content_understanding()


def test_credential_probe_has_actionable_login_and_role_errors():
    with pytest.raises(AzureAuthError, match="az login"):
        assert_credential_ready(FailingCredential("Credential unavailable. Please run az login."))

    with pytest.raises(AzureAuthError, match="Assign the required least-privilege Azure role"):
        assert_credential_ready(FailingCredential("Forbidden: role assignment missing."))


def test_credential_probe_uses_requested_scope():
    credential = RecordingCredential()

    assert_credential_ready(credential, "https://search.azure.com/.default")

    assert credential.scopes == [("https://search.azure.com/.default",)]


def test_redaction_removes_endpoints_guids_and_tokens():
    assert redact_value("https://acct.services.ai.azure.com/api/projects/project-a") == "https://<redacted-endpoint>"
    assert redact_value("00000000-1111-2222-3333-444444444444") == "<redacted-id>"
    assert redact_value("secret-token-value") == "secr…<redacted>…alue"
    assert redact_mapping({"endpoint": "https://search.search.windows.net"}) == {"endpoint": "https://<redacted-endpoint>"}
