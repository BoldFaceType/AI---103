from __future__ import annotations

from typing import Protocol

from .auth import CredentialProtocol, SEARCH_SCOPE, assert_credential_ready, create_default_credential
from .settings import AzureServiceSettings


class SearchClientProtocol(Protocol):
    def search(self, search_text: str, **kwargs: object) -> object: ...


def create_search_client(
    settings: AzureServiceSettings,
    *,
    credential: CredentialProtocol | None = None,
    client_cls: type | None = None,
    validate_credential: bool = False,
) -> SearchClientProtocol:
    settings.require_search()
    credential = credential or create_default_credential()
    if validate_credential:
        assert_credential_ready(credential, SEARCH_SCOPE)
    if client_cls is None:
        from azure.search.documents import SearchClient

        client_cls = SearchClient
    return client_cls(endpoint=settings.search_endpoint, index_name=settings.search_index, credential=credential)


def create_search_index_client(
    settings: AzureServiceSettings,
    *,
    credential: CredentialProtocol | None = None,
    client_cls: type | None = None,
    validate_credential: bool = False,
) -> object:
    settings.require_search()
    credential = credential or create_default_credential()
    if validate_credential:
        assert_credential_ready(credential, SEARCH_SCOPE)
    if client_cls is None:
        from azure.search.documents.indexes import SearchIndexClient

        client_cls = SearchIndexClient
    return client_cls(endpoint=settings.search_endpoint, credential=credential)

