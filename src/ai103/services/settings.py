from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Mapping
from urllib.parse import urlparse


FORBIDDEN_SECRET_ENV_VARS = (
    "AZURE_OPENAI_API_KEY",
    "FOUNDRY_API_KEY",
    "FOUNDRY_KEY",
    "AZURE_SEARCH_API_KEY",
    "SEARCH_API_KEY",
    "CONTENTUNDERSTANDING_KEY",
    "AZURE_CONTENTUNDERSTANDING_KEY",
    "AZURE_CLIENT_SECRET",
    "AZURE_TOKEN",
)
GUID_RE = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")


class SettingsError(ValueError):
    """Raised when Azure live settings are missing or unsafe."""


@dataclass(frozen=True)
class AzureServiceSettings:
    foundry_project_endpoint: str | None = None
    foundry_model_name: str | None = None
    search_endpoint: str | None = None
    search_index: str | None = None
    content_understanding_endpoint: str | None = None
    tenant_id: str | None = None
    subscription_id: str | None = None

    def require_foundry(self) -> None:
        _require_url("FOUNDRY_PROJECT_ENDPOINT", self.foundry_project_endpoint, must_contain="/api/projects/")
        _require_name("FOUNDRY_MODEL_NAME", self.foundry_model_name)

    def require_search(self) -> None:
        _require_url("AZURE_SEARCH_ENDPOINT", self.search_endpoint, host_suffix=".search.windows.net")
        _require_name("AZURE_SEARCH_INDEX", self.search_index)

    def require_content_understanding(self) -> None:
        _require_url("CONTENTUNDERSTANDING_ENDPOINT", self.content_understanding_endpoint)


def load_service_settings(environ: Mapping[str, str] | None = None) -> AzureServiceSettings:
    env = environ or os.environ
    forbidden = sorted(name for name in FORBIDDEN_SECRET_ENV_VARS if env.get(name))
    if forbidden:
        raise SettingsError(
            "Committed or environment API keys/tokens are not supported for this repo; "
            f"remove these variables and use Entra ID with DefaultAzureCredential: {', '.join(forbidden)}"
        )
    return AzureServiceSettings(
        foundry_project_endpoint=_clean(env.get("FOUNDRY_PROJECT_ENDPOINT")),
        foundry_model_name=_clean(env.get("FOUNDRY_MODEL_NAME")),
        search_endpoint=_clean(env.get("AZURE_SEARCH_ENDPOINT")),
        search_index=_clean(env.get("AZURE_SEARCH_INDEX")),
        content_understanding_endpoint=_clean(env.get("CONTENTUNDERSTANDING_ENDPOINT")),
        tenant_id=_clean(env.get("AZURE_TENANT_ID")),
        subscription_id=_clean(env.get("AZURE_SUBSCRIPTION_ID")),
    )


def redact_value(value: object) -> str:
    text = "" if value is None else str(value)
    if not text:
        return ""
    parsed = urlparse(text)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://<redacted-endpoint>"
    text = GUID_RE.sub("<redacted-id>", text)
    if text == "<redacted-id>":
        return text
    if len(text) > 12:
        return f"{text[:4]}…<redacted>…{text[-4:]}"
    return "<redacted>"


def redact_mapping(values: Mapping[str, object]) -> dict[str, str]:
    return {key: redact_value(value) for key, value in values.items()}


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _require_name(name: str, value: str | None) -> None:
    if not value:
        raise SettingsError(f"{name} is required for live Azure use.")
    if any(marker in value.lower() for marker in ("key", "secret", "token", "password")):
        raise SettingsError(f"{name} appears to contain secret material; use only non-secret identifiers.")


def _require_url(name: str, value: str | None, *, host_suffix: str | None = None, must_contain: str | None = None) -> None:
    if not value:
        raise SettingsError(f"{name} is required for live Azure use.")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise SettingsError(f"{name} must be an https URL.")
    if host_suffix and not parsed.netloc.endswith(host_suffix):
        raise SettingsError(f"{name} must use a {host_suffix} endpoint.")
    if must_contain and must_contain not in parsed.path:
        raise SettingsError(f"{name} must include '{must_contain}' in the endpoint path.")
