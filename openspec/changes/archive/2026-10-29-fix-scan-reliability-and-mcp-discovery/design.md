## Context

See proposal.md for motivation. The current extractor holds facts in memory, globally enumerates and sorts paths before exclusion, uses suffix-based tool decorator heuristics, and builds a second complete JSON representation before writing stdout. Existing standard-library visitors, import maps, capability records and coverage records can be reused.

## Goals / Non-Goals

**Goals:** Fix observed failures with bounded output buffering; expose scan scope and uncertain mappings; preserve schema 2 and read-only target handling.

**Non-Goals:** Constant-memory fact extraction, arbitrary repository size guarantees, gitignore interpretation, configurable truncation, full Python dataflow or Lua analysis.

## Decisions

### Output staging

Serialize with ensure_ascii=True and allow_nan=False into a standard-library TemporaryFile outside the target, rewind only after serialization completes, then copy in fixed chunks and flush stdout within the same error boundary. Use an external temporary directory, checking it is outside the resolved target; fail with a diagnostic if none is usable. Clean resources through context management.

This preserves the existing no-partial-JSON-on-serialization-failure contract. Direct json.dump to stdout breaks it; keeping json.dumps retains output-size memory duplication. Catch the specified exception families, including MemoryError, with a concise phase-aware diagnostic. Partial delivery on device failure is unavoidable and must be documented; do not promise atomic stdout or successful diagnostics during total resource exhaustion.

### Scan pruning

Use top-down os.walk with sorted directory and file lists. Remove existing SKIP_DIRS entries and .uv-cache, plus marker-confirmed virtual environments, before descent. Record each pruned directory once, not every descendant. Use onerror for traversal errors. Do not follow directory symlinks or Windows junctions; record skipped links and avoid reading file links that resolve outside the target. Retain deterministic relative paths. Avoid prefix guesses and broad hidden-directory exclusions.

### Provenance

Add source_role to capabilities, gates and flows once per parsed Python file using the path rules in the spec. Values are test or unknown; do not label unrecognized files production. Keep test evidence and explain in the Skill and method that product entrypoint analysis must distinguish test candidates, while tests can substantiate contracts. This additive schema-2 metadata preserves current fields.

### MCP scope

Reuse statically resolved imports to recognize mcp.types.Tool, including from mcp import types, import aliases and direct constructor imports. Resolve only literal expressions and directly assigned literal schema names; computed values stay unresolved. Preserve names, descriptions and input schemas in named agent-tool capabilities with source-based IDs, marking declaration provenance separately from implementation certainty.

Recognize call_tool/list_tools registration as dispatcher/listing roles before the generic suffix heuristic. For this bounded implementation, do not infer per-tool handlers from shared name-based dispatch: emit unresolved implementation coverage per declaration. This gives the 30 aseprite-mcp declarations visibility without asserting that all dispatcher branches apply to every tool. Preserve ordinary python-function discovery and existing @tool support.

## Risks / Trade-offs

- Temporary storage needs disk and permissions → diagnose failures and clean files; never place staging files inside the target.
- Facts and linking still use memory → document the ceiling; this change removes full output-string duplication, not all scaling limits.
- Exclusions add coverage entries even in ordinary repositories → describe them as scope exclusions, not proof of a defect.
- Path-based test detection misses custom layouts → unknown remains explicit; no default fact deletion.
- More named tools may still lack implementation mappings → keep gaps visible instead of fabricating complete coverage.

## Migration Plan

Keep schema_version 2 and all existing fields. Add optional source_role and MCP role/declaration metadata, update consumers in the Skill documentation, and rerun existing regression scripts. Validate focused real-project samples without regenerating all large scan artifacts. Rollback consists of reverting this change; no target-project migration is needed.
