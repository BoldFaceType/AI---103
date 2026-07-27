from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai103.services.content_understanding import create_content_understanding_client
from ai103.services.fakes import FakeAzureClient, FakeCredential
from ai103.services.foundry import create_foundry_project_client, foundry_model_name
from ai103.services.search import create_search_client, create_search_index_client
from ai103.services.settings import AzureServiceSettings, SettingsError


def valid_settings() -> AzureServiceSettings:
    return AzureServiceSettings(
        foundry_project_endpoint="https://acct.services.ai.azure.com/api/projects/project-a",
        foundry_model_name="gpt-4.1-mini",
        search_endpoint="https://search-a.search.windows.net",
        search_index="ai103-index",
        content_understanding_endpoint="https://acct.services.ai.azure.com",
    )


def test_client_factories_accept_injected_clients_and_do_not_request_credentials_offline():
    credential = FakeCredential()
    settings = valid_settings()

    foundry = create_foundry_project_client(settings, credential=credential, client_cls=FakeAzureClient)
    search = create_search_client(settings, credential=credential, client_cls=FakeAzureClient)
    index = create_search_index_client(settings, credential=credential, client_cls=FakeAzureClient)
    content = create_content_understanding_client(settings, credential=credential, client_cls=FakeAzureClient)

    assert foundry.endpoint == settings.foundry_project_endpoint
    assert search.index_name == settings.search_index
    assert index.endpoint == settings.search_endpoint
    assert content.endpoint == settings.content_understanding_endpoint
    assert credential.requested_scopes == []


def test_live_validation_can_probe_credentials_when_requested():
    credential = FakeCredential()

    create_search_client(valid_settings(), credential=credential, client_cls=FakeAzureClient, validate_credential=True)

    assert credential.requested_scopes == [("https://search.azure.com/.default",)]


def test_factories_fail_before_importing_sdks_when_settings_are_missing():
    settings = AzureServiceSettings()

    with pytest.raises(SettingsError, match="FOUNDRY_PROJECT_ENDPOINT is required"):
        create_foundry_project_client(settings, credential=FakeCredential(), client_cls=FakeAzureClient)
    with pytest.raises(SettingsError, match="AZURE_SEARCH_ENDPOINT is required"):
        create_search_client(settings, credential=FakeCredential(), client_cls=FakeAzureClient)
    with pytest.raises(SettingsError, match="CONTENTUNDERSTANDING_ENDPOINT is required"):
        create_content_understanding_client(settings, credential=FakeCredential(), client_cls=FakeAzureClient)


def test_foundry_model_name_is_non_secret_deployment_identifier():
    assert foundry_model_name(valid_settings()) == "gpt-4.1-mini"

    with pytest.raises(SettingsError, match="secret material"):
        foundry_model_name(
            AzureServiceSettings(
                foundry_project_endpoint="https://acct.services.ai.azure.com/api/projects/project-a",
                foundry_model_name="contains-secret-token",
            )
        )


def test_env_example_documents_keyless_settings_only():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")

    assert "DefaultAzureCredential" in text
    assert "FOUNDRY_PROJECT_ENDPOINT=" in text
    assert "FOUNDRY_MODEL_NAME=" in text
    assert "AZURE_SEARCH_ENDPOINT=" in text
    assert "AZURE_SEARCH_INDEX=" in text
    assert "CONTENTUNDERSTANDING_ENDPOINT=" in text
    assert "API_KEY=" not in text
    assert "CLIENT_SECRET=" not in text
    assert "CONNECTION_STRING=" not in text


def test_local_env_files_are_gitignored_but_example_is_tracked():
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert ".env" in text
    assert ".env.local" in text
    assert ".env.example" not in text


def test_pyproject_pins_azure_sdk_dependencies():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "azure-identity" in text
    assert "azure-ai-projects" in text
    assert "azure-search-documents" in text
    assert "azure-ai-contentunderstanding" in text
