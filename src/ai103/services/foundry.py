from __future__ import annotations

from typing import Any, Protocol

from .auth import CredentialProtocol, assert_credential_ready, create_default_credential
from .settings import AzureServiceSettings


class FoundryProjectClientProtocol(Protocol):
    def __enter__(self) -> Any: ...
    def __exit__(self, exc_type: object, exc: object, tb: object) -> object: ...


def create_foundry_project_client(
    settings: AzureServiceSettings,
    *,
    credential: CredentialProtocol | None = None,
    client_cls: type | None = None,
    validate_credential: bool = False,
) -> FoundryProjectClientProtocol:
    settings.require_foundry()
    credential = credential or create_default_credential()
    if validate_credential:
        assert_credential_ready(credential)
    if client_cls is None:
        from azure.ai.projects import AIProjectClient

        client_cls = AIProjectClient
    return client_cls(endpoint=settings.foundry_project_endpoint, credential=credential)


def foundry_model_name(settings: AzureServiceSettings) -> str:
    settings.require_foundry()
    assert settings.foundry_model_name is not None
    return settings.foundry_model_name

