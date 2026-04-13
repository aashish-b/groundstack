from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Category = Literal["code", "config", "docs", "test", "build", "binary"]
Mode = Literal["high_token", "low_token"]
NodeKind = Literal["directory", "file"]


class GroundstackModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Citation(GroundstackModel):
    path: str
    start_line: int
    end_line: int


class TokenBudget(GroundstackModel):
    mode: Mode
    max_prompt_tokens: int
    target_prompt_tokens: int
    reserved_output_tokens: int = 1024


class TaskSpec(GroundstackModel):
    description: str
    mode: Mode = "high_token"
    constraints: list[str] = Field(default_factory=list)


class DocumentBlock(GroundstackModel):
    kind: str
    title: str | None = None
    content: str
    start_line: int = 1
    end_line: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)


class CanonicalDocument(GroundstackModel):
    path: str
    category: Category
    language: str | None = None
    size_bytes: int
    line_count: int
    sha256: str
    source_text: str
    blocks: list[DocumentBlock]
    summary: str


class RepoNode(GroundstackModel):
    path: str
    kind: NodeKind
    parent: str | None = None
    children: list[str] = Field(default_factory=list)
    category: Category | None = None


class SymbolSummary(GroundstackModel):
    name: str
    kind: str
    path: str
    signature: str
    start_line: int
    end_line: int
    docstring: str | None = None
    score: float = 0.0


class FileSummary(GroundstackModel):
    path: str
    category: Category
    language: str | None = None
    size_bytes: int
    line_count: int
    summary: str
    imports: list[str] = Field(default_factory=list)
    symbols: list[SymbolSummary] = Field(default_factory=list)
    graph_links: list[str] = Field(default_factory=list)


class ScanResult(GroundstackModel):
    repo_root: str
    nodes: list[RepoNode]
    files: list[FileSummary]
    documents: list[CanonicalDocument]
    skipped_paths: list[str] = Field(default_factory=list)


class ScoredFile(GroundstackModel):
    path: str
    category: Category
    summary: str
    score: float
    reasons: list[str] = Field(default_factory=list)
    matched_terms: list[str] = Field(default_factory=list)
    symbols: list[str] = Field(default_factory=list)
    graph_links: list[str] = Field(default_factory=list)


class ScoredSymbol(GroundstackModel):
    path: str
    name: str
    kind: str
    signature: str
    start_line: int
    end_line: int
    score: float
    reasons: list[str] = Field(default_factory=list)


class PlanStep(GroundstackModel):
    kind: str
    target: str
    reason: str
    score: float
    token_estimate: int


class TraversalPlan(GroundstackModel):
    repo_root: str
    task: TaskSpec
    budget: TokenBudget
    repo_map: list[RepoNode]
    candidate_files: list[ScoredFile]
    candidate_symbols: list[ScoredSymbol]
    steps: list[PlanStep]


class EvidenceItem(GroundstackModel):
    path: str
    category: Category
    reason: str
    score: float
    citations: list[Citation]
    symbol_names: list[str]
    snippet: str


class EvidenceBundle(GroundstackModel):
    task: TaskSpec
    mode: Mode
    items: list[EvidenceItem]
    files: list[ScoredFile]
    symbols: list[ScoredSymbol]
    total_evidence_tokens: int


class RenderedSection(GroundstackModel):
    name: str
    cacheable: bool
    token_count: int
    content_hash: str
    content: str


class CacheRecord(GroundstackModel):
    prefix_hash: str
    renderer_version: str
    tokenizer_id: str
    cacheable_sections: list[str]
    ttl_hint_seconds: int | None = None
    section_hashes: dict[str, str]
    stable_prefix_tokens: int
    total_prompt_tokens: int
    deterministic: bool = True


class ContextBundle(GroundstackModel):
    repo_root: str
    task: TaskSpec
    budget: TokenBudget
    repo_map_markdown: str
    evidence_bundle: EvidenceBundle
    rendered_sections: list[RenderedSection]
    citations: list[Citation]
    token_counts: dict[str, int]
    stable_prefix: str
    variable_tail: str
    prompt: str
    cache_record: CacheRecord
