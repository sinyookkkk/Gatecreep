## Context

See proposal.md for motivation. The extractor uses only the standard library and AST; literal() feeds multiple output fields and link_facts indexes gates by ID. No existing main specs exist.

## Goals / Non-Goals

Goals: repair shared conversion and linking boundaries, preserve factual evidence, retain a runnable check without dependencies.
Non-Goals: execute decorators, resolve framework semantics, infer excessive gates, or redesign the audit method.

## Decisions

- Normalize literal values recursively in the shared literal path. Preserve JSON-native scalars/lists/string-key dictionaries; represent sets, bytes, complex and non-string-key dictionaries with explicit type tags and JSON-safe contents, using deterministic ordering for sets. Retain tuple identity with a tagged representation. Keep the original source expression for typed representations. Avoid default=str because it hides types and cannot fix invalid dictionary keys. Handle non-finite floats explicitly to emit strict JSON.
- Serialize the entire facts object with json.dumps before stdout writes; serialization errors produce a nonzero diagnostic. This prevents serialization failures from leaking prefixes; it does not promise atomic writes on broken pipes.
- Add decorator candidate facts at definition entry with explicit owner identity. Share the existing definition traversal rather than scanning target imports. Confirm decorator presence, leave gate semantics inferred, and avoid name-based auth/cache classification. Keep tool recognition behavior intact.
- Add visit_Assert with condition/message expression and ordinary traversal of child expressions.
- Give comparison segments a deterministic segment suffix only where needed and advance the left operand through comparators. Verify all callers of literal and add_gate and linking consumers before editing.

## Risks / Trade-offs

- Typed literal records add shapes to value fields → document their format and verify ordinary scalar output remains unchanged.
- Decorators can be non-gates and class ownership is not a public function capability → retain candidate semantics and explicit coverage for unmapped facts.
- Whole-output serialization uses additional memory → acceptable for the current in-memory facts architecture.

## Migration Plan

Implement with a small standard-library regression script, run it and scan this repository through the CLI with strict JSON parsing. Update schema documentation/version if consumer review shows incompatible value assumptions. Rollback consists of reverting the extractor and accompanying checks/docs together.
