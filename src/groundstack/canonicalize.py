from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

import yaml

from .models import CanonicalDocument, Category, DocumentBlock
from .serialization import sha256_text, stable_json_dumps


def _line_count(text: str) -> int:
    return len(text.splitlines()) if text else 0


def _markdown_blocks(text: str) -> list[DocumentBlock]:
    lines = text.splitlines()
    blocks: list[DocumentBlock] = []
    current_title: str | None = None
    current_start = 1
    current_lines: list[str] = []

    for index, line in enumerate(lines, start=1):
        if line.startswith("#"):
            if current_lines or current_title is not None:
                blocks.append(
                    DocumentBlock(
                        kind="markdown_section",
                        title=current_title,
                        content="\n".join(current_lines).strip(),
                        start_line=current_start,
                        end_line=max(index - 1, current_start),
                    )
                )
            current_title = line.lstrip("#").strip() or None
            current_start = index
            current_lines = [line]
            continue
        current_lines.append(line)

    if current_lines or current_title is not None:
        blocks.append(
            DocumentBlock(
                kind="markdown_section",
                title=current_title,
                content="\n".join(current_lines).strip(),
                start_line=current_start,
                end_line=max(len(lines), current_start),
            )
        )
    return blocks or [DocumentBlock(kind="markdown_section", content=text)]


def _mapping_blocks(data: Any, language: str) -> list[DocumentBlock]:
    if isinstance(data, dict):
        blocks: list[DocumentBlock] = []
        for key, value in data.items():
            if language == "yaml":
                rendered = yaml.safe_dump(value, sort_keys=True).strip()
            elif language == "toml":
                rendered = stable_json_dumps(value)
            else:
                rendered = stable_json_dumps(value)
            blocks.append(
                DocumentBlock(
                    kind="mapping_entry",
                    title=str(key),
                    content=rendered,
                    metadata={"key": str(key)},
                )
            )
        return blocks
    if isinstance(data, list):
        preview = stable_json_dumps(data[:10])
        return [DocumentBlock(kind="list_preview", title="items", content=preview)]
    return [DocumentBlock(kind="scalar", content=str(data))]


def _plain_blocks(text: str) -> list[DocumentBlock]:
    lines = text.splitlines()
    blocks: list[DocumentBlock] = []
    current_title: str | None = None
    current_start = 1
    current_lines: list[str] = []

    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if current_lines or current_title is not None:
                blocks.append(
                    DocumentBlock(
                        kind="section",
                        title=current_title,
                        content="\n".join(current_lines).strip(),
                        start_line=current_start,
                        end_line=max(index - 1, current_start),
                    )
                )
            current_title = stripped.strip("[]")
            current_start = index
            current_lines = [line]
            continue
        current_lines.append(line)

    if current_lines or current_title is not None:
        blocks.append(
            DocumentBlock(
                kind="section",
                title=current_title,
                content="\n".join(current_lines).strip(),
                start_line=current_start,
                end_line=max(len(lines), current_start),
            )
        )
    return blocks or [DocumentBlock(kind="text", content=text)]


def canonicalize_document(
    path: str,
    category: Category,
    language: str | None,
    source_text: str,
    size_bytes: int,
) -> CanonicalDocument:
    suffix = Path(path).suffix.lower()
    blocks: list[DocumentBlock]

    if suffix == ".md":
        blocks = _markdown_blocks(source_text)
    elif suffix == ".json":
        blocks = _mapping_blocks(json.loads(source_text), "json")
    elif suffix in {".yaml", ".yml"}:
        blocks = _mapping_blocks(yaml.safe_load(source_text), "yaml")
    elif suffix == ".toml":
        blocks = _mapping_blocks(tomllib.loads(source_text), "toml")
    else:
        blocks = _plain_blocks(source_text)

    if category == "code":
        summary = f"{language or 'code'} file with {_line_count(source_text)} lines"
    elif category == "test":
        summary = f"test file with {_line_count(source_text)} lines"
    else:
        block_count = len(blocks)
        summary = f"{category} file with {block_count} structured block{'s' if block_count != 1 else ''}"

    return CanonicalDocument(
        path=path,
        category=category,
        language=language,
        size_bytes=size_bytes,
        line_count=_line_count(source_text),
        sha256=sha256_text(source_text),
        source_text=source_text,
        blocks=blocks,
        summary=summary,
    )
