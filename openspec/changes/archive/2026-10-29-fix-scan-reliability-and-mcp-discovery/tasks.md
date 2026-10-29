## 1. Reliable bounded-buffer output

- [x] 1.1 Add minimal assert-based output regressions for lone surrogates, Unicode round-trip and serialization failure after valid content; verify the current encoding defect fails before the fix and failed serialization emits no stdout.
- [x] 1.2 Stage strict ASCII-escaped JSON in an external temporary file, then copy bounded chunks and flush; verify no complete serialized string is allocated, parsed JSON retains all facts, and temporary storage is outside the target and cleaned.
- [x] 1.3 Handle the specified extraction, serialization, temporary-storage, write and flush exceptions with phase diagnostics; verify injected OSError, UnicodeError and MemoryError produce exit 2 without traceback and do not claim partial stdout is valid.

## 2. Explicit scan scope and source roles

- [x] 2.1 Add temporary-tree regressions for .uv-cache, legacy exclusions, marker-confirmed .venv_seedream and a similarly named ordinary source directory; verify pruning failures are reproduced before implementation.
- [x] 2.2 Replace global rglob enumeration with deterministic top-down pruning and per-directory exclusion records; verify excluded descendants are never enumerated or parsed and included source remains visible.
- [x] 2.3 Record enumeration errors and skip directory links/junctions and external file links; verify with controlled traversal errors and available platform link support that external source is not read and skipped scope is explicit.
- [x] 2.4 Add test/unknown source_role to capabilities, gates and flows; verify tests/, test/, test_*.py and *_test.py retain all facts with test provenance and ordinary paths remain unknown.

## 3. MCP declaration discovery

- [x] 3.1 Add failing regressions for literal MCP Tool declarations, import aliases, directly assigned literal schemas, dynamic fields and unrelated Tool constructors; verify existing discovery omits the declarations before fixing it.
- [x] 3.2 Resolve supported MCP constructors and emit named capabilities preserving descriptions and input schemas with stable unique IDs; verify positive declarations and negative constructor controls.
- [x] 3.3 Separate MCP call_tool/list_tools registration roles from named tools and record unresolved schemas, names and per-tool implementation mappings; verify no fabricated dispatcher-to-tool gate links and existing @tool behavior remains intact.

## 4. Integration and documentation

- [x] 4.1 Update README, SKILL.md and audit-method.md for exclusions, provenance, output failure semantics and bounded MCP support; verify schema remains 2 and the documents make no complete-coverage or arbitrary-scale guarantee.
- [x] 4.2 Run all existing and new assert-based checks plus strict CLI JSON parsing; verify target contents and timestamps remain unchanged and no target code executes.
- [x] 4.3 If the local aseprite-mcp sample remains available, validate its 30 named declarations, separate dispatcher and test facts, and unresolved implementation coverage; otherwise use an equivalent small local synthetic sample and record that limitation.
- [x] 4.4 Validate an environment-contaminated small tree through the CLI without regenerating large scan files; verify exclusion coverage, bounded writes, stable IDs and deterministic repeated output, then run strict OpenSpec validation and diff checks.
