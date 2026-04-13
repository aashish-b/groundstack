from __future__ import annotations

from .models import CacheRecord, ContextBundle, EvidenceBundle, RenderedSection, ScanResult, TraversalPlan
from .providers import DEFAULT_PROVIDER, ProviderAdapter
from .serialization import sha256_text

RENDERER_VERSION = "groundstack-renderer-v1"


def assemble_context_bundle(
    scan_result: ScanResult,
    plan: TraversalPlan,
    evidence_bundle: EvidenceBundle,
    *,
    provider: ProviderAdapter = DEFAULT_PROVIDER,
) -> ContextBundle:
    repo_map_markdown = _render_repo_map_markdown(plan)
    sections = [
        _section("instructions", _render_instructions(), True, provider),
        _section("task", _render_task(plan), False, provider),
        _section("repo_map", repo_map_markdown, True, provider),
        _section("selected_evidence", _render_evidence(evidence_bundle, scan_result), False, provider),
        _section("constraints", _render_constraints(plan), True, provider),
        _section("output_contract", _render_output_contract(), True, provider),
    ]
    prompt = "\n\n".join(f"<{section.name}>\n{section.content}\n</{section.name}>" for section in sections)
    stable_prefix_parts: list[str] = []
    for section in sections:
        rendered = f"<{section.name}>\n{section.content}\n</{section.name}>"
        if not section.cacheable:
            break
        stable_prefix_parts.append(rendered)
    stable_prefix = "\n\n".join(stable_prefix_parts)
    variable_tail = prompt[len(stable_prefix) :].lstrip()
    citations = [citation for item in evidence_bundle.items for citation in item.citations]
    token_counts = {section.name: section.token_count for section in sections}
    cache_record = CacheRecord(
        prefix_hash=sha256_text(stable_prefix),
        renderer_version=RENDERER_VERSION,
        tokenizer_id=provider.tokenizer_id,
        cacheable_sections=[section.name for section in sections if section.cacheable],
        ttl_hint_seconds=provider.ttl_hint_seconds,
        section_hashes={section.name: section.content_hash for section in sections},
        stable_prefix_tokens=provider.count_tokens(stable_prefix),
        total_prompt_tokens=provider.count_tokens(prompt),
    )
    return ContextBundle(
        repo_root=scan_result.repo_root,
        task=plan.task,
        budget=plan.budget,
        repo_map_markdown=repo_map_markdown,
        evidence_bundle=evidence_bundle,
        rendered_sections=sections,
        citations=citations,
        token_counts=token_counts,
        stable_prefix=stable_prefix,
        variable_tail=variable_tail,
        prompt=prompt,
        cache_record=cache_record,
    )


def _section(name: str, content: str, cacheable: bool, provider: ProviderAdapter) -> RenderedSection:
    return RenderedSection(
        name=name,
        cacheable=cacheable,
        token_count=provider.count_tokens(content),
        content_hash=sha256_text(content),
        content=content,
    )


def _render_instructions() -> str:
    return "\n".join(
        [
            "## Instructions",
            "- Read the repo map before drilling into evidence.",
            "- Use only the cited evidence blocks when making claims.",
            "- Prefer grounded reasoning over speculation.",
            "- Preserve file paths and line spans in any proposed fix.",
        ]
    )


def _render_task(plan: TraversalPlan) -> str:
    lines = [
        "## Task",
        plan.task.description,
        "",
        f"- Mode: `{plan.task.mode}`",
        f"- Target prompt tokens: `{plan.budget.target_prompt_tokens}`",
        f"- Reserved output tokens: `{plan.budget.reserved_output_tokens}`",
    ]
    if plan.task.constraints:
        lines.extend(["", "## Constraints", *[f"- {constraint}" for constraint in plan.task.constraints]])
    return "\n".join(lines)


def _render_repo_map_markdown(plan: TraversalPlan) -> str:
    lines = ["## Repo Map"]
    for file_score in plan.candidate_files[:10]:
        lines.append(f"- `{file_score.path}` ({file_score.category}, score={file_score.score:.2f})")
        lines.append(f"  - {file_score.summary}")
        if file_score.symbols:
            lines.append(f"  - Symbols: {', '.join(file_score.symbols[:5])}")
        if file_score.graph_links:
            lines.append(f"  - Graph links: {', '.join(file_score.graph_links[:3])}")
        if file_score.reasons:
            lines.append(f"  - Why: {'; '.join(file_score.reasons)}")
    return "\n".join(lines)


def _render_evidence(evidence_bundle: EvidenceBundle, scan_result: ScanResult) -> str:
    language_by_path = {document.path: document.language for document in scan_result.documents}
    lines = ["## Selected Evidence"]
    for item in evidence_bundle.items:
        language = language_by_path.get(item.path) or ""
        citation = item.citations[0]
        lines.append(f"### `{item.path}`")
        lines.append(f"- Reason: {item.reason}")
        lines.append(f"- Citation: {citation.path}:{citation.start_line}-{citation.end_line}")
        if item.symbol_names:
            lines.append(f"- Symbols: {', '.join(item.symbol_names)}")
        lines.append(f"```{language}")
        lines.append(item.snippet)
        lines.append("```")
    return "\n".join(lines)


def _render_constraints(plan: TraversalPlan) -> str:
    return "\n".join(
        [
            "## Constraints",
            "- Ground all claims in cited evidence.",
            "- Prefer the top-ranked files and symbols before expanding more context.",
            f"- Stay within `{plan.budget.max_prompt_tokens}` prompt tokens.",
            "- Keep stable instructions separate from task-specific evidence for caching.",
        ]
    )


def _render_output_contract() -> str:
    return "\n".join(
        [
            "## Output Contract",
            "```json",
            "{",
            '  "summary": "string",',
            '  "key_files": ["path:line-line"],',
            '  "risks": ["string"],',
            '  "next_actions": ["string"]',
            "}",
            "```",
        ]
    )
