## Context

See proposal.md for motivation. The extractor already tracks imports, parser call assignments and AST facts. The checker uses line-based regular expressions. Both scripts use only the standard library.

## Goals / Non-Goals

**Goals:** Reuse existing capability and fact structures; preserve schema version and single-line report compatibility.

**Non-Goals:** General interprocedural argparse resolution, arbitrary Markdown parsing, automatic semantic conclusions, README promotion and release work.

## Decisions

- Recognize statically resolved argparse constructors using existing import information. Reuse command call/variable association for root parsers and preserve subcommand IDs. Give root capabilities deterministic source-based identifiers rather than relying on runtime program names. Avoid treating every same-named call as argparse.
- Visit previously skipped expression children exactly once while preserving existing body traversal. Prefer targeted traversal over replacing visitors in ways that could duplicate facts or change context handling.
- Extract the causal-chain field through its continuation lines up to the next field or heading. Reuse the evidence-label rule on that content. Avoid whole-finding searches, which can accidentally accept evidence from another field, and avoid a Markdown dependency.
- Extend the existing assert-based regression checks; add a small checker regression file if needed. Include negative controls rather than only successful examples.

## Risks / Trade-offs

- More facts change counts and capability links → verify distinct IDs, root/subcommand separation and existing regression behavior.
- Markdown boundary ambiguity → test indented arrows, fenced chains, subsequent fields and subsequent findings.
- Static argparse support remains bounded → document direct assignment support without claiming complete CLI coverage.
