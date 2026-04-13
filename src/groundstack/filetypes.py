from __future__ import annotations

from pathlib import Path

from .models import Category

CODE_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "jsx",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".sh": "shell",
}
DOC_EXTENSIONS = {".md": "markdown", ".rst": "rst", ".txt": "text"}
CONFIG_EXTENSIONS = {
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".ini": "ini",
    ".cfg": "config",
}
BINARY_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".pdf",
    ".zip",
    ".gz",
    ".mp3",
    ".wav",
    ".ttf",
}
HARD_SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "target",
    ".next",
    ".turbo",
    "coverage",
}
HARD_SKIP_FILES = {"package-lock.json", "pnpm-lock.yaml", "yarn.lock", "poetry.lock"}
TEST_HINTS = ("test", "tests", "__tests__")


def classify_path(path: Path) -> tuple[Category, str | None]:
    suffix = path.suffix.lower()
    path_text = path.as_posix().lower()
    name = path.name.lower()

    if suffix in BINARY_EXTENSIONS:
        return "binary", None
    if name in {"makefile", "dockerfile"}:
        return "build", name
    if suffix in CODE_EXTENSIONS:
        if any(part in TEST_HINTS for part in path.parts) or name.startswith("test_"):
            return "test", CODE_EXTENSIONS[suffix]
        return "code", CODE_EXTENSIONS[suffix]
    if suffix in DOC_EXTENSIONS:
        return "docs", DOC_EXTENSIONS[suffix]
    if suffix in CONFIG_EXTENSIONS or name in {".gitignore", ".env", "config"}:
        if ".github/workflows/" in path_text:
            return "build", CONFIG_EXTENSIONS.get(suffix, "config")
        return "config", CONFIG_EXTENSIONS.get(suffix, "config")
    if any(part in TEST_HINTS for part in path.parts):
        return "test", None
    return "docs", "text"


def should_hard_skip_dir(path: Path) -> bool:
    return path.name in HARD_SKIP_DIRS


def should_hard_skip_file(path: Path) -> bool:
    return path.name in HARD_SKIP_FILES


def is_probably_binary(path: Path, payload: bytes) -> bool:
    if path.suffix.lower() in BINARY_EXTENSIONS:
        return True
    return b"\x00" in payload
