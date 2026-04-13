from __future__ import annotations

from collections import defaultdict
from pathlib import Path, PurePosixPath

from .models import ScanResult


def build_repo_graph(scan_result: ScanResult) -> dict[str, set[str]]:
    available_paths = {file_summary.path for file_summary in scan_result.files}
    module_index = _build_module_index(available_paths)
    graph: dict[str, set[str]] = defaultdict(set)

    for file_summary in scan_result.files:
        current_path = Path(file_summary.path)
        for import_name in file_summary.imports:
            resolved = _resolve_import(current_path, import_name, available_paths, module_index)
            if resolved is None or resolved == file_summary.path:
                continue
            graph[file_summary.path].add(resolved)
            graph[resolved].add(file_summary.path)
    return {path: set(sorted(neighbors)) for path, neighbors in graph.items()}


def annotate_graph_links(scan_result: ScanResult) -> None:
    graph = build_repo_graph(scan_result)
    for file_summary in scan_result.files:
        file_summary.graph_links = sorted(graph.get(file_summary.path, set()))


def _build_module_index(paths: set[str]) -> dict[str, str]:
    index: dict[str, str] = {}
    for path in paths:
        p = Path(path)
        without_suffix = p.with_suffix("").as_posix().replace("/", ".")
        index[without_suffix] = path
        index[p.stem] = path
    return index


def _resolve_import(
    current_path: Path,
    import_name: str,
    available_paths: set[str],
    module_index: dict[str, str],
) -> str | None:
    if import_name.startswith("."):
        base = PurePosixPath(current_path.parent.as_posix()) / import_name
        normalized = PurePosixPath(base).as_posix()
        candidates = [
            f"{normalized}.py",
            f"{normalized}.js",
            f"{normalized}.ts",
            f"{normalized}.tsx",
            f"{normalized}/index.js",
            f"{normalized}/index.ts",
        ]
        for candidate in candidates:
            if candidate in available_paths:
                return candidate
        return None
    if import_name.startswith("/"):
        normalized = import_name.lstrip("/")
        return normalized if normalized in available_paths else None
    return module_index.get(import_name)
