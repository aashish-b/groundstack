from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .tokenizer import DEFAULT_TOKENIZER


class ProviderAdapter(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def tokenizer_id(self) -> str: ...

    @property
    def min_cache_prefix_tokens(self) -> int: ...

    @property
    def ttl_hint_seconds(self) -> int | None: ...

    def count_tokens(self, text: str) -> int: ...


@dataclass(frozen=True)
class LocalProviderAdapter:
    name: str = "local"
    tokenizer_id: str = DEFAULT_TOKENIZER.identifier
    min_cache_prefix_tokens: int = 1024
    ttl_hint_seconds: int | None = None

    def count_tokens(self, text: str) -> int:
        return DEFAULT_TOKENIZER.count_tokens(text)


DEFAULT_PROVIDER = LocalProviderAdapter()
