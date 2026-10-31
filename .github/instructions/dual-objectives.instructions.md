---
description: "Use for ANY change, analysis or review of the dashboard, qualification estimates, Race Finder / Where to Qualify, chance-to-qualify, cut-off or target calculations. The project has two separate objectives (Current-rules prediction and Historical-correct reconstruction) that must never be mixed."
applyTo: "src/build_dashboard.py,src/dashboard_*.js,src/dashboard_*.html,src/dashboard.css,src/kona_trace.py,src/qualification_*.py,tests/test_dashboard_*.py,tests/test_qualification_rules.py,docs/standard_course.md,docs/dashboard_consistency.md"
---

# Two objectives: never mix them

The project's main goal is to find the race where the user is most likely to
qualify. It serves two distinct objectives. In code they are the
`qualificationSystem` values `"current"` and `"historical"`.

| | **A. Current rules on old results** (`"current"`) | **B. Historically correct** (`"historical"`) |
|---|---|---|
| Question | If the old race-years were run under today's rules, what would it take to qualify? | What did it actually take to qualify in each race-year? |
| Use | Predicting the user's chance at the next qualifying race | Checking, calibrating and validating the model against reality |
| Rule set | The current cycle only (P1, performance pool, `CURRENT_CYCLE` in `data/reference/age_group_standards.json`) | The rule set of the cycle the race-year belongs to (R1-R4 or P1, see `docs/historical_qualification_rules.md`) |
| Slots | Latest published allocation per race (`data/reference/current_slots.json`) | The slots actually offered in that race-year (Coach Cox / official `Qualified` flags) |
| Age-group standard | Current cycle table | The table of that race-year's cycle |
| Evidence for roll-down | Kona/Nice start list of the race-year's cycle re-ranked under current rules (`counterfactual_*`) | The real start list of that cycle (`summaries`) |
| Output labelled | "current-pool counterfactual" | "historical rules" |

## Rules

1. Every qualification number, chart, table or text must belong to exactly one
   objective and say which one (label, title or note). Never silently blend them.
2. Objective A is the basis of the ranking and chance in "Where to qualify". It
   must not use historical slot counts, historical rule sets or historical
   standards. Course, season and field effects of the old race-years still apply.
3. Objective B must reproduce what happened: use each race-year's own cycle,
   quota, rule set and standard. Where it cannot be reconstructed, say
   "unavailable" instead of falling back to current rules.
4. Never apply one rule set to all years except in objective A, and then only
   the current one.
5. Objective B is the validation of objective A: changes to A's cut-off or
   probability logic should be checked against B (official qualifiers, reported
   cut-offs). Keep the model vs. official check green.
6. Shared inputs are allowed and expected: results, age grading by cycle, course
   factors (`docs/standard_course.md`), modified-course exclusions.
7. A fix or feature touching either objective must state in the commit/PR text
   which objective it affects, and add or keep a test for both when the code
   path is shared (`tests/test_dashboard_*.py`, `tests/test_qualification_rules.py`).
8. Mapping each race-year to its cycle is required for B first; see
   `qualification-rules.instructions.md` and `docs/historical_qualification_rules.md`.
