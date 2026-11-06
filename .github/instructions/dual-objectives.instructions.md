---
description: "Use for ANY change, analysis or review of the dashboard, qualification estimates, Race Finder / Where to Qualify, chance-to-qualify, cut-off or target calculations. The project has two separate objectives (Current-rules prediction and Historical-correct reconstruction) that must never be mixed."
applyTo: "src/build_dashboard.py,src/dashboard_*.js,src/dashboard_*.html,src/dashboard.css,src/kona_trace.py,src/qualification_*.py,tests/test_dashboard_*.py,tests/test_qualification_rules.py,docs/standard_course.md,docs/dashboard_consistency.md,docs/race_finder.md,src/dashboard_insights.py,src/backtest.py,data/reference/cycle_calendar.json,tests/test_race_finder_insights.py"
---

# Two objectives: never mix them

The project's main goal is to find the race where the user is most likely to
qualify. It serves two distinct objectives. In code they are the
`qualificationSystem` values `"current"` and `"historical"`.

| | **A. Current rules on old results** (`"current"`) | **B. Historically correct** (`"historical"`) |
|---|---|---|
| Question | If the old race-years were run under today's rules, what would it take to qualify? | What did it actually take to qualify in each race-year? |
| Use | Predicting the user's chance at the next qualifying race | Reconstructing historical rules and comparing estimates with available evidence |
| Rule set | The current cycle only (P1, performance pool, `CURRENT_CYCLE` in `data/reference/age_group_standards.json`) | The rule set of the cycle the race-year belongs to (R1-R4 or P1, see `docs/historical_qualification_rules.md`) |
| Slots | Latest published allocation per race (`data/reference/current_slots.json`) | The slots actually offered in that race-year (Coach Cox / official `Qualified` flags) |
| Age-group standard | Current cycle table | The table of that race-year's cycle |
| Evidence for roll-down methods | Actual P1 races: compatible championship starters of the race-year's cycle re-ranked under current rules (`counterfactual_*`). Known R1-R4 race-years: the same re-ranked roster for the matched-slot cutoff only | Only for actual P1 races: the compatible real start list of that cycle (`summaries`). Known R1-R4 race-years: the same-cycle start list matched in the actual age-group ranking, for the matched-slot cutoff only |
| Output labelled | "current-pool counterfactual" | "historical rules" |

Ranked championship evidence plots are a separate descriptive view, not an added roll-down method. Whenever same-cycle roster and matching data exist, show matched starters from the corresponding World Championship for every selected race-year. A ranks all such starters under current P1 rules and the current standard, even for original R1-R4 races; for those races, show no density or absence-scan boundary and present only the A matched-slot cutoff (labelled as re-ranked starters who qualified through age-group slots) as match-based evidence. B uses the actual historical ranking; for R1-R4 show B's age-group matched-slot cutoff (a selectable method, see below) plus a descriptive density boundary and five-consecutive-unmatched gap/boundary markers in the plot only, based on actual age-group ranks and excluding the rank-1 match from density and scan inputs/counts. These legacy density/scan plot fits are not selectable methods or qualification estimates and must not affect targets, rank factors, Finder chances, calibration, or any model metric. If roster compatibility or matching evidence is missing, label it unavailable. Mark age-group first-place finishers, matched or not, as gold dots rather than assigning a performance-pool rank. P1 winners use the separate automatic-slot route and are excluded from pool rankings, density, absence-scan, and other pool metrics. In B's R1-R4 plot, show a matched actual age-group rank-1 finisher in gold at the historical rank/time and label it "Age-group rank 1", not an automatic slot; exclude that match from plot-only density/scan inputs and counts. Do not alter historical age-group allocation or infer slot acceptance. A match does not mean slot acceptance, and a non-match does not prove absence or decline.

## Rules

1. Every qualification number, chart, table or text must belong to exactly one
   objective and say which one (label, title or note). Never silently blend them.
2. Objective A is the basis of the ranking and chance in "Where to qualify". Its
   allocation and ranking must not use historical slot counts, rule sets or
   standards. The actual historical rule set is used only to determine evidence
   eligibility. Course, season and field effects of the old race-years still apply.
3. Objective B must reconstruct each race-year using its own cycle, quota,
   rule set and standard. Where it cannot be reconstructed, say "unavailable"
   instead of falling back to current rules. Strict and rank-factor scenarios
   are not proof of actual slot acceptance or declines.
4. Never apply one rule set to all years except in objective A, and then only
   the current one.
5. Changes to A's cut-off or probability logic should be checked against B and
   compatible official qualifiers or reported cut-offs. Keep the model vs.
   official check green, but do not claim historical backtests or old time-based
   calibration validate the new rank factor.
6. Shared inputs are allowed and expected: results, age grading by cycle, course
   factors (`docs/standard_course.md`), modified-course exclusions.
7. A fix or feature touching either objective must state in the commit/PR text
   which objective it affects, and add or keep a test for both when the code
   path is shared (`tests/test_dashboard_*.py`, `tests/test_qualification_rules.py`).
8. Map each race-year to its real qualifying cycle and rule set to determine
   whether its original race used P1, regardless of objective or calendar year;
   see `qualification-rules.instructions.md` and `docs/historical_qualification_rules.md`.
   If the cycle or evidence compatibility is unknown, do not infer a pool match
   model. Known R1-R4 races remain usable for historical strict, age-group
   matched-slot and rank-factor scenarios when their allocation is available.
9. The Race Finder chance model, roll-down assumptions, DNF risk, calendar filter
   and backtest are documented in `docs/race_finder.md`; keep it in sync. Keep
   selected display years separate from model-training data and do not silently
   retrain on a user's year selection.

## Cut-off methods

| Original race rules | A: current rules | B: historical rules |
|---|---|---|
| P1 performance pool | Strict, matched-slot cutoff, compatible density, absence scan, and rank factor in the current gender pool | Strict, matched-slot cutoff, compatible density, absence scan, and rank factor in the actual gender pool |
| R1-R4 age-group allocation | Strict, matched-slot cutoff (same-cycle roster re-ranked under current rules), and rank factor in the current gender pool | Strict, matched-slot cutoff (Nth matched rank in the actual age-group ranking, a matched age-group winner counts), and rank factor in the original age-group ranking |

Density and absence scan require a confirmed actual P1 race and same-cycle,
scope-compatible evidence; A re-ranks actual-pool-era matches under current
rules and B uses the historical pool, standards and slots. The matched-slot
cutoff follows the same rule for P1 races. For race-years with a known R1-R4
cycle (user decisions, November 2026), A ranks that cycle's championship
roster under current rules, allocation and standard; those starters qualified
through age-group slots, so label the boundary accordingly and never present
it as observed pool roll-down. B uses the same roster matched in the actual
raw age-group ranking with N = the race-year's age-group slots; R1-R4 had no
separate winner route, so a matched age-group rank-1 finisher counts. Never
use old-era age-group matches as density or scan evidence. Unknown or incompatible
evidence is unavailable; strict fallback requires explicit opt-in and a clear
label. Externally documented last-accepted cutoffs are separately labelled
evidence, not inference methods.

The matched-slot cutoff counts matched results only from the selected
qualifying race-year (P1, or a known R1-R4 race-year), ignores unmatched championship ranks, and takes the Nth
matched rank for N gender performance-pool slots (B R1-R4: N age-group slots in
the actual age-group ranking). A uses its current-rule
counterfactual ranking and standard; B uses the race-year's historical ranking
and standard. Fewer than N matches or any cycle, roster, ranking, allocation,
or standard mismatch is unavailable without strict fallback. Automatic P1
age-group winners have no performance-pool rank and are excluded from this
count. This is neither a density/absence/rank-factor method nor evidence of
acceptance. Race Finder always evaluates this method under objective A.

This P1-only restriction applies to selected density and scan methods and
their outputs. The sole legacy exception is B's descriptive R1-R4 ranked-evidence
plot: it may show the actual age-group-rank density boundary and five-unmatched
gap/boundary markers, excluding the age-group-rank-1 match from both inputs and
counts. These plot-only values are not targets, Finder chances, calibration,
or model metrics. A matched rank-1 finisher remains visible in gold at the
actual age-group rank/time and is labeled "Age-group rank 1"; this does not
make the finisher a P1 automatic-slot winner or change historical allocation.

The rank factor is a scenario, not historical proof: `extra = floor(slots * f +
0.5)` for `f >= 0`, and `target rank = slots + extra`. It defaults to 0 and may
exceed 2. Use initial pool slots excluding automatic winners for P1, or historical
age-group slots for R1-R4; retain the separate winner route and correct age-grade
mapping for P1. Show unavailable rather than extrapolating beyond ranked
finishers. Do not use manual extra places as an independent method or reuse the
old time-based factor or its spread. See [roll-down-approaches.instructions.md](./roll-down-approaches.instructions.md)
for rounding, examples, support checks and method limitations; its policy takes
precedence over conflicting descriptions of legacy scan or calibration behavior
in existing documentation.
