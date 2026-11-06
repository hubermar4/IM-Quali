---
description: "Use when handling any question, code change, or analysis about current or historical IRONMAN / IRONMAN 70.3 age-group World Championship qualification: rule sets by qualification cycle, slot allocation, performance pool, age grading, roll-down, cutoffs, dashboard historical vs current mode."
applyTo: "src/qualification_*.py,src/build_dashboard.py,src/kona_trace.py,src/scrape_*.py,tests/test_qualification_rules.py,tests/test_dashboard_*.py,docs/*qualification_rules.md,data/reference/rule_sets.json,data/reference/age_group_standards.json,data/reference/qualification_constants.json,data/reference/reported_cutoffs.json,src/reference_data.py"
---

# Qualification rules

The single source of truth for qualification rules is
[docs/historical_qualification_rules.md](../../docs/historical_qualification_rules.md).
The current official text is [docs/official_qualification_rules.md](../../docs/official_qualification_rules.md).

- Every estimate belongs to either the current-rules or the historical objective; see [dual-objectives.instructions.md](./dual-objectives.instructions.md).
- For which races offered how many slots per cycle, see [qualification-race-slots.instructions.md](./qualification-race-slots.instructions.md).
- Read the historical document before answering or changing anything about qualification, for any year.
- Map every race-year to its qualification cycle first (a late-year race belongs to the next cycle, e.g. Austria 2021 is a 2022-cycle race), then apply that cycle's rule set (R1-R4 age-group allocation for 2017-2025, P1 performance pool for 2026+).
- Never apply one rule set to all years unless explicitly doing the "current rules" counterfactual.
- Keep confidence labels (official / observed / inferred) and say when an allocation is reconstructed.
- If you find new evidence or change rule handling in code, update the historical document in the same change.
