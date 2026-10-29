## ADDED Requirements

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
