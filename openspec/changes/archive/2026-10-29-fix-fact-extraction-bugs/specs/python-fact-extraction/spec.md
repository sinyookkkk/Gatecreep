## Purpose

Provide reliable, read-only Python audit facts so downstream reviewers receive complete JSON, visible candidate gate structures, and correct capability links without executing target code or inferring gate legitimacy from syntax alone.

## ADDED Requirements

### Requirement: Complete JSON output
The extractor SHALL serialize supported literal values recursively into deterministic JSON-safe values while preserving non-JSON types and their source expressions. It MUST complete serialization before emitting stdout.

#### Scenario: Non-JSON literals
- **WHEN** input contains nested sets, tuples, bytes, complex values or dictionaries with non-string keys
- **THEN** extraction succeeds with parseable JSON, stable representations and preserved type information where JSON cannot represent the original value

#### Scenario: Serialization failure
- **WHEN** serialization fails before output
- **THEN** the command exits nonzero with a diagnostic and emits no partial JSON to stdout

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
