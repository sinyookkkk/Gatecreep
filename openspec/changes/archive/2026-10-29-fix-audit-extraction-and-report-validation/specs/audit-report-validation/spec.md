## Purpose

Validate evidence labels in audit report causal chains consistently across single-line and multiline formatting, without accepting labels from unrelated fields.

## ADDED Requirements

### Requirement: Multiline causal chain evidence labels
The report checker SHALL accept [静态事实] or [模型推断] anywhere within the causal-chain field, including continuation lines and fenced multiline examples. It MUST stop at the next field or finding boundary and retain rejection of causal chains without either label.

#### Scenario: Equivalent formatting
- **WHEN** otherwise valid reports contain the same labeled causal chain on one line or multiple lines
- **THEN** both reports pass validation

#### Scenario: Label in another field
- **WHEN** the causal chain lacks a label but the following field or finding contains one
- **THEN** validation reports the missing causal-chain evidence label

#### Scenario: Unlabeled chain
- **WHEN** a multiline causal chain contains no recognized evidence label
- **THEN** validation rejects it with a causal-chain diagnostic
