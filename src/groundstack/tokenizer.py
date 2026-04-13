from __future__ import annotations

import re
from dataclasses import dataclass

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[^\sA-Za-z0-9_]")


@dataclass(frozen=True)
class HeuristicTokenizer:
    identifier: str = "heuristic-v1"

    def count_tokens(self, text: str) -> int:
        return len(TOKEN_PATTERN.findall(text))


DEFAULT_TOKENIZER = HeuristicTokenizer()
