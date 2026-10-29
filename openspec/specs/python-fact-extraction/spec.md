# Python Fact Extraction Specification

## Purpose

Provide reliable, read-only Python audit facts so downstream reviewers receive complete JSON, visible candidate gate structures, and correct capability links without executing target code or inferring gate legitimacy from syntax alone.

## Requirements

### Requirement: Complete JSON output
The extractor SHALL serialize supported literal values recursively into deterministic JSON-safe values while preserving non-JSON types and their source expressions. It MUST complete serialization before emitting stdout. Output MUST preserve Unicode values including lone surrogates through JSON escaping, without allocating a complete serialized output string in memory. Extraction, serialization and output failures caused by OSError, UnicodeError, ValueError, TypeError or MemoryError SHALL produce a concise stderr diagnostic and exit status 2 when diagnostic output is available. No facts SHALL be silently truncated.

#### Scenario: Non-JSON literals
- **WHEN** input contains nested sets, tuples, bytes, complex values or dictionaries with non-string keys
- **THEN** extraction succeeds with parseable JSON, stable representations and preserved type information where JSON cannot represent the original value

#### Scenario: Serialization failure
- **WHEN** serialization fails before output
- **THEN** the command exits nonzero with a diagnostic and emits no partial JSON to stdout

#### Scenario: Lone surrogate in facts
- **WHEN** a valid Python comparison contains a lone surrogate string literal
- **THEN** output is UTF-8 encodable strict JSON and decoding preserves the original literal value

#### Scenario: Output or resource failure
- **WHEN** a supported failure occurs while extracting, serializing, writing or flushing output
- **THEN** the command exits 2 with a diagnostic rather than an uncaught traceback, and consumers treat any partially written stdout as invalid

#### Scenario: Temporary serialization storage
- **WHEN** output serialization requires temporary storage
- **THEN** that storage is outside the target project and cleaned on success or failure

### Requirement: Decorator candidates
The extractor SHALL record every function and class decorator with source, full expression and owning definition, including private, nested and asynchronous definitions. It MUST distinguish confirmed syntax from inferred gate semantics and retain existing tool capability discovery.

#### Scenario: Decorated definitions
- **WHEN** definitions use authentication, cache, unknown or tool decorators, with or without arguments
- **THEN** every decorator is visible as a candidate without asserting its behavior or legitimacy from its name

### Requirement: Assertion facts
The extractor SHALL record assert conditions, optional messages, source and owning function without classifying assertions as excessive.

#### Scenario: Assertions with and without messages
- **WHEN** a function contains either form of assert
- **THEN** each assertion is represented and linked to its discovered capability when applicable

### Requirement: Distinct chained comparisons
The extractor SHALL give each comparison segment a unique stable identifier and its actual adjacent operands, preserving every segment through capability linking.

#### Scenario: Three operand comparison
- **WHEN** a public function contains a < b < c
- **THEN** two distinct comparison facts describe a < b and b < c and both remain linked to the capability

### Requirement: Plain argparse entry points
The extractor SHALL record directly assigned argparse.ArgumentParser instances, including imported aliases, as CLI capabilities and attach their directly declared arguments with options, required, default, choices and action metadata. It MUST preserve existing subcommand extraction and distinguish unrelated same-named constructors.

#### Scenario: Parser without subcommands
- **WHEN** a parser declares a positional path and --limit with default 10 and choices [5, 10, 20]
- **THEN** a CLI capability contains both arguments and preserves the default and choices

#### Scenario: Existing subcommands
- **WHEN** a root parser has subcommands with their own arguments
- **THEN** root and subcommand arguments remain attached to their respective capabilities with distinct identifiers

#### Scenario: Unrelated constructor
- **WHEN** a non-argparse object is constructed using the name ArgumentParser
- **THEN** its name alone does not establish a confirmed argparse capability

### Requirement: Facts inside loop and raise expressions
The extractor SHALL traverse for iterables, while tests, raise exceptions and raise causes using the existing fact rules, retaining the enclosing loop or raise facts without duplicate traversal. Facts MUST NOT assert gate legitimacy.

#### Scenario: Loop expressions
- **WHEN** a for iterable contains a bounded slice and a while test contains a comparison and function call
- **THEN** the slice, comparison and call facts are extracted along with the loop facts

#### Scenario: Raise expressions
- **WHEN** a raise exception or cause contains calls or comparisons
- **THEN** those nested facts are extracted along with the raise fact

### Requirement: Pruned scan scope with visible exclusions
The extractor SHALL prune existing excluded directories, .uv-cache and directories containing pyvenv.cfg before descending into them. It SHALL emit one excluded-directory coverage record per pruned directory with its relative path and reason, and record directory enumeration errors. Traversal MUST be deterministic and MUST NOT follow directory links outside the target root. It MUST NOT skip ordinary source merely because its name starts with .venv.

#### Scenario: Custom virtual environment
- **WHEN** .venv_seedream contains pyvenv.cfg and installed Python packages
- **THEN** no nested package files are parsed and one exclusion record identifies the environment directory

#### Scenario: Cache and legacy exclusions
- **WHEN** a target includes .uv-cache, .venv or node_modules
- **THEN** their descendants are not enumerated and the exclusions are visible in coverage

#### Scenario: Ordinary source and unreadable directory
- **WHEN** a similarly named source directory lacks an environment marker or an included directory cannot be enumerated
- **THEN** the source directory remains eligible and the enumeration failure is recorded instead of implying complete coverage

### Requirement: Test source provenance
The extractor SHALL retain test facts and mark capabilities, gates and flows with source_role test for paths containing tests or test directories or basenames matching test_*.py or *_test.py. Other Python facts SHALL use source_role unknown, without asserting they are production code. Source role is a path heuristic, not a semantic conclusion; original source locations MUST remain intact.

#### Scenario: Test assertions
- **WHEN** tests/test_server.py contains assertions and comparisons
- **THEN** those facts remain present with test provenance and are not classified as excessive gates

#### Scenario: Non-test path
- **WHEN** server.py contains a public function
- **THEN** its facts have unknown provenance rather than a confirmed production classification

### Requirement: MCP declarations and dispatch boundaries
The extractor SHALL discover literal tool names, descriptions and input schemas from statically resolved mcp.types.Tool constructors, including import aliases and directly assigned literal schema values. It SHALL distinguish MCP call_tool and list_tools registration functions from individually declared tools. Unknown names, unresolved schemas or unconfirmed implementation mappings SHALL produce explicit coverage records. Unrelated constructors named Tool MUST NOT establish confirmed MCP declarations.

#### Scenario: Declarative tools
- **WHEN** a list-tools handler returns two literal Tool declarations and a separate call-tool handler dispatches requests
- **THEN** two named agent-tool capabilities preserve their declared inputs and the dispatcher is not reported as a third named tool

#### Scenario: Unresolved dispatch
- **WHEN** a declared tool's per-tool implementation cannot be statically confirmed
- **THEN** the declaration remains visible with an unresolved mapping coverage record and no invented confirmed implementation link

#### Scenario: Aliases and unrelated constructors
- **WHEN** MCP types are imported under aliases alongside an unrelated Tool constructor
- **THEN** MCP aliases are recognized while the unrelated constructor is not classified as an MCP declaration

#### Scenario: Dynamic declaration
- **WHEN** a recognized MCP Tool call uses a computed name or schema
- **THEN** a coverage record identifies the unresolved declaration component without claiming the dynamic value is confirmed
