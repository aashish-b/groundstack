from __future__ import annotations

import re
from collections import defaultdict

from .graph import build_repo_graph
from .models import (
    Citation,
    EvidenceBundle,
    EvidenceItem,
    Mode,
    PlanStep,
    ScanResult,
    ScoredFile,
    ScoredSymbol,
    TaskSpec,
    TokenBudget,
    TraversalPlan,
)
from .providers import DEFAULT_PROVIDER, ProviderAdapter

WORD_RE = re.compile(r"[A-Za-z0-9_]+")
ARCHITECTURE_TERMS = {"architecture", "design", "overview", "explain", "layout"}
TEST_TERMS = {"test", "tests", "failing", "assert", "broken"}
CI_TERMS = {"ci", "workflow", "pipeline", "github", "actions"}
CONFIG_TERMS = {"config", "yaml", "toml", "json", "settings"}
BUG_TERMS = {"bug", "fix", "error", "failure", "refresh"}


def build_traversal_plan(
    scan_result: ScanResult,
    task: str,
    *,
    mode: Mode = "high_token",
    provider: ProviderAdapter = DEFAULT_PROVIDER,
) -> TraversalPlan:
    task_spec = TaskSpec(description=task, mode=mode)
    budget = _budget_for_mode(task_spec.mode)
    graph = build_repo_graph(scan_result)
    candidate_files = _score_files(scan_result, task_spec, graph)
    candidate_symbols = _score_symbols(scan_result, candidate_files, task_spec)
    steps = _build_steps(candidate_files, candidate_symbols, provider, task_spec.mode)
    return TraversalPlan(
        repo_root=scan_result.repo_root,
        task=task_spec,
        budget=budget,
        repo_map=scan_result.nodes,
        candidate_files=candidate_files,
        candidate_symbols=candidate_symbols,
        steps=steps,
    )


def build_evidence_bundle(
    scan_result: ScanResult,
    plan: TraversalPlan,
    *,
    provider: ProviderAdapter = DEFAULT_PROVIDER,
) -> EvidenceBundle:
    doc_by_path = {document.path: document for document in scan_result.documents}
    mode = plan.task.mode
    max_files = 5 if mode == "high_token" else 3
    symbol_context = 8 if mode == "high_token" else 4
    max_symbols_per_file = 2 if mode == "high_token" else 1
    selected_files = plan.candidate_files[:max_files]
    symbols_by_path: dict[str, list[ScoredSymbol]] = defaultdict(list)
    for symbol in plan.candidate_symbols:
        if len(symbols_by_path[symbol.path]) < max_symbols_per_file:
            symbols_by_path[symbol.path].append(symbol)

    items: list[EvidenceItem] = []
    total_evidence_tokens = 0

    for file_score in selected_files:
        document = doc_by_path[file_score.path]
        chosen_symbols = symbols_by_path[file_score.path]
        if chosen_symbols:
            for symbol in chosen_symbols:
                snippet = _snippet_for_symbol(document.source_text, symbol.start_line, symbol.end_line, symbol_context)
                citations = [Citation(path=file_score.path, start_line=symbol.start_line, end_line=symbol.end_line)]
                items.append(
                    EvidenceItem(
                        path=file_score.path,
                        category=file_score.category,
                        reason="; ".join(symbol.reasons or file_score.reasons),
                        score=symbol.score,
                        citations=citations,
                        symbol_names=[symbol.name],
                        snippet=snippet,
                    )
                )
                total_evidence_tokens += provider.count_tokens(snippet)
            continue

        start_line, end_line, snippet = _fallback_snippet(document.source_text, mode)
        items.append(
            EvidenceItem(
                path=file_score.path,
                category=file_score.category,
                reason="; ".join(file_score.reasons),
                score=file_score.score,
                citations=[Citation(path=file_score.path, start_line=start_line, end_line=end_line)],
                symbol_names=[],
                snippet=snippet,
            )
        )
        total_evidence_tokens += provider.count_tokens(snippet)

    return EvidenceBundle(
        task=plan.task,
        mode=plan.task.mode,
        items=items,
        files=selected_files,
        symbols=plan.candidate_symbols,
        total_evidence_tokens=total_evidence_tokens,
    )


def _budget_for_mode(mode: Mode) -> TokenBudget:
    if mode == "low_token":
        return TokenBudget(
            mode="low_token",
            max_prompt_tokens=20_000,
            target_prompt_tokens=12_000,
            reserved_output_tokens=2_000,
        )
    return TokenBudget(
        mode="high_token",
        max_prompt_tokens=80_000,
        target_prompt_tokens=60_000,
        reserved_output_tokens=4_000,
    )


def _score_files(
    scan_result: ScanResult, task: TaskSpec, graph: dict[str, set[str]]
) -> list[ScoredFile]:
    task_terms = _terms(task.description)
    task_text = task.description.lower()
    scored: list[ScoredFile] = []
    base_scores: dict[str, float] = {}

    for file_summary, document in zip(scan_result.files, scan_result.documents, strict=True):
        path_terms = _terms(file_summary.path)
        symbol_name_terms = set().union(*(_terms(symbol.name) for symbol in file_summary.symbols))
        import_terms = _terms(" ".join(file_summary.imports))
        symbol_terms = symbol_name_terms | import_terms
        matched_terms = sorted(task_terms & (path_terms | symbol_terms | _terms(document.source_text)))
        score = float(len(task_terms & path_terms) * 3 + len(task_terms & symbol_terms) * 4 + len(matched_terms) * 0.5)
        reasons: list[str] = []
        if task_terms & path_terms:
            reasons.append("path terms match task")
        if task_terms & symbol_terms:
            reasons.append("symbol names match task")

        if TEST_TERMS & task_terms and file_summary.category == "test":
            score += 3.0
            reasons.append("test-focused task boosts test file")
        if BUG_TERMS & task_terms and file_summary.category == "code":
            score += 2.5
            reasons.append("bug-fix task boosts code file")
        if BUG_TERMS & task_terms and file_summary.category == "test" and not (TEST_TERMS & task_terms):
            score -= 1.5
            reasons.append("bug-fix task deprioritizes tests")
        if CI_TERMS & task_terms and (".github/" in file_summary.path or file_summary.category == "build"):
            score += 4.0
            reasons.append("CI/workflow terms boost build file")
        if CONFIG_TERMS & task_terms and file_summary.category == "config":
            score += 2.0
            reasons.append("config-focused task boosts config file")
        if ARCHITECTURE_TERMS & task_terms and file_summary.category in {"docs", "config"}:
            score += 2.0
            reasons.append("architecture task boosts docs/config")
        if "readme" in file_summary.path.lower() and ARCHITECTURE_TERMS & task_terms:
            score += 2.0
            reasons.append("README likely relevant for architecture request")
        if file_summary.line_count > 400 and score < 6:
            score -= 0.5
            reasons.append("large file penalty")

        if (
            score <= 0
            and any(term in task_text for term in {"bug", "fix", "error"})
            and file_summary.category == "code"
        ):
            score = 0.25
            reasons.append("baseline code candidate for bug task")

        base_scores[file_summary.path] = score
        scored.append(
            ScoredFile(
                path=file_summary.path,
                category=file_summary.category,
                summary=file_summary.summary,
                score=score,
                reasons=reasons,
                matched_terms=matched_terms,
                symbols=[symbol.name for symbol in file_summary.symbols],
                graph_links=sorted(graph.get(file_summary.path, set())),
            )
        )

    boosted_scores = dict(base_scores)
    for path, neighbors in graph.items():
        source_score = base_scores.get(path, 0.0)
        if source_score <= 0:
            continue
        for neighbor in neighbors:
            boosted_scores[neighbor] = boosted_scores.get(neighbor, 0.0) + round(source_score * 0.15, 4)

    for scored_file in scored:
        if boosted_scores[scored_file.path] > scored_file.score:
            scored_file.reasons.append("graph proximity boost")
            scored_file.score = boosted_scores[scored_file.path]

    return sorted(scored, key=lambda item: (-item.score, item.path))


def _score_symbols(
    scan_result: ScanResult,
    candidate_files: list[ScoredFile],
    task: TaskSpec,
) -> list[ScoredSymbol]:
    task_terms = _terms(task.description)
    file_scores = {file_score.path: file_score for file_score in candidate_files}
    scored_symbols: list[ScoredSymbol] = []

    for file_summary in scan_result.files:
        if file_summary.path not in file_scores:
            continue
        parent_file_score = file_scores[file_summary.path]
        for symbol in file_summary.symbols:
            symbol_terms = _terms(symbol.name) | _terms(symbol.signature) | _terms(symbol.docstring or "")
            overlap = task_terms & symbol_terms
            score = parent_file_score.score * 0.25 + len(overlap) * 4
            reasons = list(parent_file_score.reasons)
            if overlap:
                reasons.append("symbol overlap with task")
            if score <= 0:
                continue
            scored_symbols.append(
                ScoredSymbol(
                    path=symbol.path,
                    name=symbol.name,
                    kind=symbol.kind,
                    signature=symbol.signature,
                    start_line=symbol.start_line,
                    end_line=symbol.end_line,
                    score=score,
                    reasons=reasons,
                )
            )

    return sorted(scored_symbols, key=lambda item: (-item.score, item.path, item.start_line, item.name))


def _build_steps(
    candidate_files: list[ScoredFile],
    candidate_symbols: list[ScoredSymbol],
    provider: ProviderAdapter,
    mode: str,
) -> list[PlanStep]:
    max_files = 5 if mode == "high_token" else 3
    max_symbols = 8 if mode == "high_token" else 4
    steps = [
        PlanStep(
            kind="repo_map",
            target="repo",
            reason="Start from repo map before expansion",
            score=1.0,
            token_estimate=256,
        )
    ]
    for file_score in candidate_files[:max_files]:
        steps.append(
            PlanStep(
                kind="file",
                target=file_score.path,
                reason="; ".join(file_score.reasons) or "Top-ranked file",
                score=file_score.score,
                token_estimate=provider.count_tokens(file_score.summary),
            )
        )
    for symbol in candidate_symbols[:max_symbols]:
        steps.append(
            PlanStep(
                kind="symbol",
                target=f"{symbol.path}:{symbol.name}",
                reason="; ".join(symbol.reasons) or "Top-ranked symbol",
                score=symbol.score,
                token_estimate=provider.count_tokens(symbol.signature),
            )
        )
    return steps


def _snippet_for_symbol(text: str, start_line: int, end_line: int, context: int) -> str:
    lines = text.splitlines()
    start = max(start_line - context, 1)
    end = min(end_line + context, len(lines))
    numbered = [f"{index}: {lines[index - 1]}" for index in range(start, end + 1)]
    return "\n".join(numbered)


def _fallback_snippet(text: str, mode: str) -> tuple[int, int, str]:
    lines = text.splitlines()
    limit = 80 if mode == "high_token" else 40
    end = min(len(lines), limit)
    numbered = [f"{index}: {lines[index - 1]}" for index in range(1, end + 1)]
    return 1, end, "\n".join(numbered)


def _terms(text: str) -> set[str]:
    return {token.lower() for token in WORD_RE.findall(text) if len(token) >= 2}
