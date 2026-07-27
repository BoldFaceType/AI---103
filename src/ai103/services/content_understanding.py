from __future__ import annotations

from typing import Protocol

from .auth import CredentialProtocol, assert_credential_ready, create_default_credential
from .settings import AzureServiceSettings


class ContentUnderstandingClientProtocol(Protocol):
    def begin_analyze(self, *args: object, **kwargs: object) -> object: ...


def create_content_understanding_client(
    settings: AzureServiceSettings,
    *,
    credential: CredentialProtocol | None = None,
    client_cls: type | None = None,
    validate_credential: bool = False,
) -> ContentUnderstandingClientProtocol:
    settings.require_content_understanding()
    credential = credential or create_default_credential()
    if validate_credential:
        assert_credential_ready(credential)
    if client_cls is None:
        from azure.ai.contentunderstanding import ContentUnderstandingClient

        client_cls = ContentUnderstandingClient
    return client_cls(endpoint=settings.content_understanding_endpoint, credential=credential)

