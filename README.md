# Groundstack

Groundstack is a deterministic repo-contexting toolkit for coding agents.

V1 focuses on one problem: given a repository and a task, produce a grounded
`ContextBundle` that is better than naive repo dumping. It does that by:

- scanning repos with `.gitignore` awareness
- extracting symbols and imports from Python and JS/TS
- ranking files and symbols deterministically
- assembling XML-segmented, Markdown-centered prompt bundles
- emitting citations, token budgets, and cache metadata

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Quickstart

```bash
groundstack scan tests/fixtures/python_service
groundstack map tests/fixtures/python_service
groundstack plan tests/fixtures/python_service --task "Fix the auth token refresh bug"
groundstack bundle tests/fixtures/python_service --task "Fix the auth token refresh bug"
groundstack dump tests/fixtures/python_service --task "Fix the auth token refresh bug"
```

## Commands

- `scan <repo>`: normalize repo files into `CanonicalDocument` records
- `map <repo>`: emit repo tree, file summaries, symbols, and graph hints
- `plan <repo> --task ...`: compute a deterministic `TraversalPlan`
- `bundle <repo> --task ...`: emit a full `ContextBundle` as JSON
- `dump <repo> --task ...`: print the final model-ready prompt payload

## Development

```bash
ruff check .
mypy src
pytest -q
```

## Scope

Groundstack v1 is intentionally narrow:

- In scope: repos, code/config/docs files, deterministic traversal, prompt assembly
- Out of scope: PDF/Office/image parsing, semantic caching, remote model calls, agent runtimes
