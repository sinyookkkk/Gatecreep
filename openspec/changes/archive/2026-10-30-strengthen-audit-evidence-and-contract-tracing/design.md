## Context

See proposal.md for motivation. Existing scripts use Python standard library AST extraction and Markdown report checking. Existing IDs and source locations can support evidence association; they do not encode branch feasibility. This change spans extraction, model instructions and report validation.

## Goals / Non-Goals

Goals: detect evidence drift and require explicit reasoning across tool contract boundaries with minimal extensions to existing scripts.

Non-goals: execute target code, reconstruct historical worktrees automatically, prove arbitrary Python control flow, or introduce a graph database, dependency or general dataflow engine.

## Decisions

1. Extend existing facts to schema version 3 with a file manifest, rather than a separate indexing service. Hash the exact bytes used for parsing; preserve Python encoding handling. Record path, hash, line count and processing status. Git HEAD is optional background. Document and test migration from version 2 rather than silently interpreting old facts as snapshot-bound.
2. Reuse existing fact IDs. A report-adjacent JSON evidence record stores snapshot identity, citations, ordered failure steps and links with provenance; Markdown references record IDs. One companion record is simpler to validate than parsing arbitrary prose into claims. JSON stays outside the target alongside the report.
3. Extend check_report.py with explicit facts/evidence/target inputs for source verification. Reject unsafe paths and symlink escapes before reads; compare hashes and line bounds. Preserve legacy format-only invocation with an explicit output label that it did not verify source references. New Skill deliveries require evidence validation. Validation errors exit nonzero and never alter existing report artifacts.
4. Keep contract comparison in the model workflow: compare schema, description, validator, result and recovery. Add static extraction only where already supported syntax provides reliable facts. No keyword heuristic decides that authorization is excessive.
5. Add a small synthetic faulty/fixed fixture and expected evaluation checklist based on the described trading-agent failure. Do not copy user trading data or pretend synthetic logs prove the original incident. Automated checks validate extraction, citations and evidence boundaries; a separately recorded model run evaluates detection.

## Risks / Trade-offs

- Hashes detect drift but do not freeze a live repository → hash bytes actually parsed, recheck referenced files before delivery, invalidate affected claims on mismatch.
- Referenced source validity can look like semantic proof → emit separate reference, static-analysis, supplied-log and inference states; never collapse them into verified=true.
- More report fields increase authoring burden → reference existing facts and use one compact companion record, keep unresolved links explicit.
- Snapshot files may disappear → return a diagnostic and incomplete evidence state; do not substitute current files for historical bytes.

## Migration Plan

First add the workflow checklist and evaluation fixture. Then add manifest extraction and schema-version documentation. Finally integrate evidence checking and update report examples and Skill completion conditions. Run existing regression scripts plus focused new checks. Rollback is reverting the change and regenerating version-2 facts; do not reinterpret version-3 artifacts with older consumers.
