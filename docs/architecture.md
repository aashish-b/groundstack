# Architecture

Groundstack v1 is split into five deterministic layers:

1. `CanonicalDocument`: normalize text/config/docs/code files into structured blocks.
2. `TraversalPlan`: rank files and symbols under a token budget.
3. `EvidenceBundle`: select snippet windows with path-and-line provenance.
4. `ContextBundle`: render XML outer sections with Markdown inner bodies.
5. `CacheRecord`: track stable-prefix hashes and cacheability metadata.

The first proving ground is repo contexting for coding-agent tasks. The planner
is intentionally offline and deterministic so it can be tested without live
model APIs. Provider-specific token accounting is abstracted behind adapters.
