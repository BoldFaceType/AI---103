from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FakeCredential:
    token: str = "fake-token"
    requested_scopes: list[tuple[str, ...]] = field(default_factory=list)

    def get_token(self, *scopes: str, **kwargs: object) -> object:
        self.requested_scopes.append(tuple(scopes))
        return type("FakeAccessToken", (), {"token": self.token, "expires_on": 4_102_444_800})()


@dataclass
class FakeAzureClient:
    endpoint: str
    credential: object
    index_name: str | None = None

    def search(self, search_text: str, **kwargs: object) -> list[dict[str, str]]:
        return [{"search_text": search_text}]

    def begin_analyze(self, *args: object, **kwargs: object) -> dict[str, str]:
        return {"status": "notStarted"}

    def __enter__(self) -> "FakeAzureClient":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

