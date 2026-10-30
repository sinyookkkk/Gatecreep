## Purpose

Bind read-only audit conclusions to the actual source and contract bytes reviewed, and expose evidence boundaries across tool validation and recovery paths so historical failures are not confused with current implementations.

## ADDED Requirements

### Requirement: Actual input snapshot
The extractor SHALL record a deterministic manifest of examined source and contract files, including content SHA-256 for successfully read files and explicit skipped or failed states. Git revision SHALL be optional context and MUST NOT replace actual content identity. Analysis MUST NOT execute or modify the target.

#### Scenario: Dirty or non-Git project
- **WHEN** a project has uncommitted changes or no Git metadata
- **THEN** actual file hashes identify reviewed input without requiring a remote repository

#### Scenario: Read failure
- **WHEN** an eligible file cannot be read
- **THEN** the manifest and coverage expose the failure without claiming complete analysis

### Requirement: Evidence reference validation
Reports SHALL associate source evidence with manifest entries and line ranges. Evidence validation MUST reject absolute or escaping reference paths, files outside the target, invalid line ranges and content mismatches. Validation SHALL distinguish reference validity from semantic correctness and runtime proof.

#### Scenario: Evidence changes before delivery
- **WHEN** a referenced file changes after extraction
- **THEN** validation fails for that evidence and affected conclusions require renewed analysis

#### Scenario: Valid but insufficient citation
- **WHEN** a citation exists at the recorded snapshot but its causal interpretation is unproven
- **THEN** reference validation does not label the interpretation verified

### Requirement: Structured failure evidence
Audits SHALL record failure steps and links with evidence references and explicit static-fact, supplied-runtime-record or inference provenance. Function reachability MUST NOT be presented as proof of branch feasibility or actual agent behavior. Missing links SHALL be disclosed.

#### Scenario: Dynamic recovery path
- **WHEN** static analysis finds a rejecting validator but cannot confirm its upper handler
- **THEN** the handler connection remains inferred or unresolved rather than a confirmed end-to-end failure

### Requirement: Tool contract comparison
For tools in scope, audits SHALL compare available input schema, descriptions, implementation validation, returned continuation fields and error recovery instructions. Missing layers SHALL be recorded as coverage gaps. Legitimate validation MUST remain distinguishable from misleading recovery behavior.

#### Scenario: Invalid payload interpreted as missing permission
- **WHEN** extra fields are rejected with an authorization message and recovery requests user confirmation despite an applicable continuation rule
- **THEN** the audit distinguishes legitimate payload rejection from the misleading recovery chain and cites both sides of the conflict

#### Scenario: Historical failure and repaired implementation
- **WHEN** supplied historical calls describe behavior absent from the reviewed repaired snapshot
- **THEN** the report separates historical evidence from current findings and does not assert the old defect remains

### Requirement: Reproducible audit evaluation
Regression materials SHALL contain a minimal faulty and repaired tool workflow with synthetic call records and expected evidence boundaries. Automated checks and model semantic evaluation SHALL have separate results; missing model evaluation MUST NOT be reported as passed.

#### Scenario: Structural checks pass
- **WHEN** fixture extraction and report structure checks pass without model evaluation
- **THEN** results claim only those checks and leave semantic detection unevaluated
