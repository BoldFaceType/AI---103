from __future__ import annotations

from typing import Protocol


COGNITIVE_SERVICES_SCOPE = "https://cognitiveservices.azure.com/.default"
SEARCH_SCOPE = "https://search.azure.com/.default"


class CredentialProtocol(Protocol):
    def get_token(self, *scopes: str, **kwargs: object) -> object: ...


class AzureAuthError(RuntimeError):
    """Actionable authentication failure for live Azure use."""


def create_default_credential() -> CredentialProtocol:
    try:
        from azure.identity import DefaultAzureCredential
    except ImportError as exc:  # pragma: no cover - exercised before dependency installation only
        raise AzureAuthError("Install Azure SDK dependencies before live use: azure-identity is missing.") from exc
    return DefaultAzureCredential(exclude_interactive_browser_credential=True)


def assert_credential_ready(credential: CredentialProtocol, scope: str = COGNITIVE_SERVICES_SCOPE) -> None:
    try:
        credential.get_token(scope)
    except Exception as exc:  # noqa: BLE001 - Azure SDK raises several auth exception types.
        message = str(exc)
        lowered = message.lower()
        if any(marker in lowered for marker in ("not logged", "az login", "credential unavailable", "authentication failed")):
            hint = "Run 'az login' and select the intended subscription, or configure managed identity."
        elif any(marker in lowered for marker in ("forbidden", "authorization", "role", "permission", "access denied")):
            hint = "Assign the required least-privilege Azure role for the target Foundry/Search/Content Understanding resource."
        else:
            hint = "Verify Entra ID login, tenant, subscription, role assignment, and endpoint configuration."
        raise AzureAuthError(f"Azure credential is not ready for live AI-103 use. {hint}") from exc

