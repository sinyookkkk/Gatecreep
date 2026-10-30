# Structured Feature Discovery Specification

## Purpose

Make feature discovery traceable through scan-led model review, blind-spot inspection and explicit reconciliation, preserving evidence and unresolved scope without claiming independent verification or exhaustive semantic coverage.

## Requirements

### Requirement: Four versioned discovery artifacts
The workflow SHALL produce JSON artifacts for scan facts, model feature summary, supplemental inspection and final reconciliation, in that order. All SHALL identify the same snapshot. Model artifacts SHALL declare a supported contract version. Existing version 3 scan facts SHALL be reused without requiring a new extraction format. All outputs MUST remain outside the audited target and target code MUST NOT be executed.

#### Scenario: Snapshot mismatch
- **WHEN** any model artifact identifies a different snapshot from the scan
- **THEN** validation fails and affected analysis requires renewal

#### Scenario: Unsupported input
- **WHEN** an artifact has an unsupported version or malformed structure
- **THEN** validation returns a nonzero diagnostic rather than treating it as completed analysis

### Requirement: Evidence-based model feature summary
The model SHALL read repository evidence using scan candidates as leads and produce user-facing features with unique IDs, purpose, inputs, outputs, success criteria, preconditions, side effects, failure behavior, candidate associations and evidence. Unknown or inapplicable details SHALL carry explicit states and reasons. Many-to-many feature and entry associations SHALL be supported.

#### Scenario: Multiple actions in one tool
- **WHEN** one tool dispatches distinct public actions
- **THEN** the summary can represent multiple features linked to the same candidate with action-specific evidence

### Requirement: Explicit supplemental inspection
The model SHALL inspect documentation, configuration, dynamic registration, multi-action dispatch, non-Python paths and unmapped gates or unresolved calls applicable to scope. Supplemental JSON SHALL record each inspection category, evidence, outcome and coverage impact, including additions and corrections. Outcomes SHALL distinguish inspected-no-addition, discovered, not-applicable, not-inspected and unresolved; omitted inspection MUST NOT imply a clean result.

#### Scenario: Unresolved dynamic registration
- **WHEN** dynamic registration cannot be confirmed
- **THEN** the inspection retains an unresolved item and describes possible feature omissions

### Requirement: Complete candidate disposition and final mapping
Reconciliation SHALL dispose every scan capability candidate exactly once as public-entry, internal, test, legacy, false-positive or unresolved, with reasons and evidence or explicit missing-evidence explanations. Public entries SHALL reference final features. Every final feature SHALL cite evidence and retain source summary or supplement IDs. Reconciliation SHALL record merges, splits, conflicts and impacts of scan and supplemental gaps. Unresolved items SHALL remain visible in downstream audit scope.

#### Scenario: Internal helper
- **WHEN** a scanned function is an internal helper rather than a public feature
- **THEN** reconciliation records its disposition and basis instead of silently dropping it or inventing a user capability

#### Scenario: Missing candidate disposition
- **WHEN** a scan candidate has no disposition or duplicate dispositions
- **THEN** validation fails and feature discovery is not marked complete

#### Scenario: Documented capability without confirmed implementation
- **WHEN** documentation declares a capability whose implementation remains unknown
- **THEN** the final inventory retains its evidence and unknown status rather than asserting it exists as a reachable feature or does not exist

### Requirement: Validation and semantic boundaries
Validation SHALL check types, required fields, enumerations, unique IDs, cross-artifact references, shared snapshots, evidence references and disposition completeness. Missing and changed source evidence SHALL use existing reference validation behavior. Human-readable reports SHALL identify final feature IDs and unresolved scope from reconciliation. Successful validation MUST NOT assert semantic correctness, independent cross-validation or complete feature coverage.

#### Scenario: Structurally valid but uncertain inventory
- **WHEN** all records validate while dynamic paths remain unresolved
- **THEN** the result reports structural validity and unresolved scope separately without claiming exhaustive coverage

#### Scenario: Broken reference
- **WHEN** a feature references an unknown candidate, evidence or source feature ID
- **THEN** validation fails with the affected record identified
