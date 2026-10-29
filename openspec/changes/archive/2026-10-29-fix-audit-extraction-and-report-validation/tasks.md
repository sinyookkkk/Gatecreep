## 1. Restore omitted extraction facts

- [x] 1.1 Add assert-based regression cases for plain argparse, aliases, unrelated constructors and root/subcommand argument separation; confirm the missing behavior fails before fixing it.
- [x] 1.2 Reuse existing import resolution and command associations to extract root parser capabilities and argument metadata with distinct stable IDs.
- [x] 1.3 Add regression cases for comparisons, calls and slices inside loop/raise expressions, including raise causes; confirm failures before fixing traversal.
- [x] 1.4 Traverse missing expression children once and verify enclosing facts and capability links remain intact.

## 2. Accept multiline causal chains

- [x] 2.1 Add minimal checker regressions for single-line, indented multiline and fenced causal chains, plus unlabeled chains and labels in following fields/findings; confirm the multiline defect fails before fixing it.
- [x] 2.2 Check evidence labels across the causal-chain field only, preserving existing required fields, classifications and diagnostics.

## 3. Verify the complete change

- [x] 3.1 Run existing and new regression checks, verify CLI JSON output, unique fact IDs and extraction of Gatecreep's two argparse entry points.
- [x] 3.2 Confirm target files are never executed or modified and document the tested static support boundary without claiming full semantic coverage.
- [x] 3.3 Run strict OpenSpec validation and review the diff for scope and compatibility.
