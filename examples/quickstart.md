# Quickstart Example

Use the fixture repos during early development:

```bash
groundstack bundle tests/fixtures/python_service --task "Fix the auth token refresh bug"
groundstack dump tests/fixtures/mixed_repo --task "Explain the CI workflow and config layout"
```

The JSON bundle contains:

- `TraversalPlan`
- selected `EvidenceBundle`
- rendered prompt sections
- token counts
- stable-prefix hashes for future provider caching
