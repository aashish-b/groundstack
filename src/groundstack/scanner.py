from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path

import pathspec

from .canonicalize import canonicalize_document
from .filetypes import (
    classify_path,
    is_probably_binary,
    should_hard_skip_dir,
    should_hard_skip_file,
)
from .graph import annotate_graph_links
from .models import Category, FileSummary, RepoNode, ScanResult
from .symbols import extract_symbols

MAX_FILE_BYTES = 256_000


def scan_repo(repo_root: str | Path) -> ScanResult:
    root = Path(repo_root).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Repo root does not exist: {root}")
    repo_label = root.name or "."

    ignore_spec = _load_gitignore(root)
    nodes: dict[str, RepoNode] = {".": RepoNode(path=".", kind="directory", parent=None)}
    file_summaries: list[FileSummary] = []
    documents = []
    skipped_paths: list[str] = []

    for current_root, dirnames, filenames in os.walk(root, topdown=True):
        current_path = Path(current_root)
        rel_dir = _relative(current_path, root)
        _ensure_dir_node(nodes, rel_dir)

        dirnames[:] = sorted(
            d
            for d in dirnames
            if not should_hard_skip_dir(current_path / d)
            and not _is_ignored(_relative(current_path / d, root), ignore_spec)
        )

        for filename in sorted(filenames):
            absolute_path = current_path / filename
            relative_path = _relative(absolute_path, root)
            if should_hard_skip_file(absolute_path) or _is_ignored(relative_path, ignore_spec):
                skipped_paths.append(relative_path)
                continue

            payload = absolute_path.read_bytes()
            if len(payload) > MAX_FILE_BYTES or is_probably_binary(absolute_path, payload):
                skipped_paths.append(relative_path)
                continue

            category, language = classify_path(Path(relative_path))
            text = payload.decode("utf-8", errors="replace")
            document = canonicalize_document(relative_path, category, language, text, len(payload))
            symbols, imports = extract_symbols(relative_path, text, language)
            file_summaries.append(
                FileSummary(
                    path=relative_path,
                    category=category,
                    language=language,
                    size_bytes=len(payload),
                    line_count=document.line_count,
                    summary=_summarize_file(category, language, document.line_count, symbols, imports),
                    imports=imports,
                    symbols=symbols,
                )
            )
            documents.append(document)
            _ensure_file_node(nodes, relative_path, category)

    _populate_children(nodes)
    scan_result = ScanResult(
        repo_root=repo_label,
        nodes=[nodes[key] for key in sorted(nodes)],
        files=sorted(file_summaries, key=lambda item: item.path),
        documents=sorted(documents, key=lambda item: item.path),
        skipped_paths=sorted(skipped_paths),
    )
    annotate_graph_links(scan_result)
    return scan_result


def _load_gitignore(root: Path) -> pathspec.PathSpec:
    gitignore_path = root / ".gitignore"
    patterns: list[str] = []
    if gitignore_path.exists():
        patterns = gitignore_path.read_text(encoding="utf-8").splitlines()
    return pathspec.PathSpec.from_lines("gitignore", patterns)


def _relative(path: Path, root: Path) -> str:
    relative = path.relative_to(root).as_posix()
    return relative or "."


def _is_ignored(relative_path: str, ignore_spec: pathspec.PathSpec) -> bool:
    return bool(relative_path != "." and ignore_spec.match_file(relative_path))


def _ensure_dir_node(nodes: dict[str, RepoNode], relative_dir: str) -> None:
    if relative_dir in nodes:
        return
    parent = str(Path(relative_dir).parent).replace("\\", "/")
    parent = "." if parent == "" else parent
    nodes[relative_dir] = RepoNode(path=relative_dir, kind="directory", parent=parent)
    _ensure_dir_node(nodes, parent)


def _ensure_file_node(nodes: dict[str, RepoNode], relative_file: str, category: Category) -> None:
    parent = str(Path(relative_file).parent).replace("\\", "/")
    parent = "." if parent == "." or parent == "" else parent
    _ensure_dir_node(nodes, parent)
    nodes[relative_file] = RepoNode(path=relative_file, kind="file", parent=parent, category=category)


def _populate_children(nodes: dict[str, RepoNode]) -> None:
    for node in nodes.values():
        node.children = []
    for path, node in nodes.items():
        if path == "." or node.parent is None or node.parent not in nodes:
            continue
        nodes[node.parent].children.append(path)
    for node in nodes.values():
        node.children = sorted(node.children)


def _summarize_file(
    category: Category,
    language: str | None,
    line_count: int,
    symbols: Sequence[object],
    imports: list[str],
) -> str:
    symbol_count = len(symbols)
    import_count = len(imports)
    if category in {"code", "test"}:
        return (
            f"{language or category} file with {symbol_count} symbol"
            f"{'s' if symbol_count != 1 else ''}, {import_count} import"
            f"{'s' if import_count != 1 else ''}, and {line_count} lines"
        )
    return f"{category} file with {line_count} lines"
