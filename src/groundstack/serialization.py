from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel


def stable_json_dumps(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True)


def model_to_stable_json(model: BaseModel) -> str:
    return stable_json_dumps(model.model_dump(mode="json"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
