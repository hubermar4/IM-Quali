# Race Finder: how the chance to qualify is built

Every number is labelled by objective (see
[dual-objectives](../.github/instructions/dual-objectives.instructions.md)):
**A** = current rules applied to old results, **B** = historically correct rules.

## Chance per race

1. For each past race-year of a race, predict your time on that course
   (average-course time × the race-year course factor, or split by split from
   your own results; see [standard_course.md](standard_course.md)).
2. Compare it with the time needed (below). Chance of that race-year
   `= Φ(ln(needed ÷ expected) ÷ σ)`, with σ = day-to-day residual SD of the
  repeat-athlete fit (≈3.7 %), widened by `√(1 + 1/used results)` when using
  personal results. No old time-multiplier spread is applied to the rank factor.
3. Race chance = mean over race-years, then:
   - **Evidence shrinkage:** `(n·mean + 2·all-race mean) ÷ (n + 2)`; fewer than
     three race-years is flagged "thin".
   - **DNF risk (toggle):** multiplied by `1 − DNF rate`. The rate is the pooled
     DNF share of starters over unmodified editions, shrunk toward the distance
     average with a prior of 1000 starters (`dashboard_insights.dnf_rates`).
   - **80 % range:** `±1.28 · SD(race-year chances) ÷ √n` (pooled SD when n = 1).

## Time needed

Targets and Race Finder share strict allocation, matched-slot cutoff, rank
factor, match density and the 15-absence scan. Finder always uses objective A;
Targets may use A or B.
The original race's verified qualifying cycle determines eligibility, not its
calendar year. Actual P1 races can use all five selectable approaches, subject
to evidence availability; actual R1-R4 races support strict, matched-slot and
factor. A
uses the current gender pool, allocation and standards. B uses the actual
cycle's gender pool or legacy age-group allocation and ranking. An unknown
cycle cannot support match-based methods; B also requires a verified historical
allocation.

Density and scan estimates for targets and Finder require compatible
same-cycle P1 championship matches. The matched-slot cutoff also applies to
race-years with a known R1-R4 cycle. In A (and therefore in the Finder) it
re-ranks that cycle's championship roster under current rules. Those starters
qualified through age-group slots, so the A boundary for R1-R4 years is a
counterfactual mapping, not observed pool roll-down. In B it uses the actual
raw age-group ranking: N is the race-year's age-group slots, and a matched
age-group rank-1 finisher counts because R1-R4 had no separate winner route.
For P1 the matched-slot cutoff counts
only pool ranks with a matched result from that exact qualifying race-year,
ignores unmatched World Championship ranks, and selects the Nth matched rank
for N gender performance-pool slots. A re-ranks the race-year's championship
roster under current rules; B uses its historical ranking and standard. Fewer
than N matches, or an incompatible cycle, roster, ranking, allocation, or
standard, is unavailable with no strict fallback. Separate automatic P1 age-group
winners are excluded from pool ranks and the match count. This boundary is not
an acceptance record, density breakpoint, absence scan, or rank-factor
scenario. Historical B legacy evidence plots may show a
descriptive age-group density boundary and five-unmatched scan (both exclude
the age-group winner), but those
markers are plot-only and do not affect targets, rank factors, Finder chances,
calibration or metrics. Missing P1 evidence may use a labelled strict fallback
only when explicitly enabled; legacy or unknown methods cannot use this
fallback. Reported last-accepted times
are separate external evidence. Charts and cross-year method summaries exclude
fallbacks; rankings identify fallback counts and excluded-year reasons.

The rank factor `f >= 0` is hypothetical additional declines per initial slot,
not an observed rate or a multiplier of time. Its default is 0; values above 2
are allowed. For initial slots `S`, calculate `extra = floor(S*f + 0.5)` and
target rank `S + extra`. Thus 30 slots and factors 0, 1 and 2 target ranks 30,
60 and 90. P1 uses gender-pool slots excluding automatic winners and the slower
of the winner and age-graded pool equivalent. Legacy B uses age-group slots.
There is no extrapolated time when the factor rank exceeds ranked finishers.
The scenario is neither calibrated nor validated by the old time model.

## Field and evidence

The Finder shows the latest published slots alongside median eligible
age-group starters from the selected, unmodified historical years. Total
eligible starters divided by total slots and gender eligible starters divided
by gender slots use matching scopes; gender slots are the current allocation
projected onto each historical field, not a fixed P1 age-group quota. The
age-group field-strength figure is the median across selected years of each
year's top-20% finish-time threshold divided by its overall course factor;
the number of finishers and contributing years are shown. These field figures
are descriptive, not additional inputs to the chance model.

Ranked evidence shows all selected race-years in separate panels. Pool panels
share a 1-100 rank axis, expandable to available strict, matched-slot, and
factor ranks and, for P1, density, scan and supported reported boundaries and
complete stopping gaps. Historical age-group panels scale to their own slots,
factor rank and plot-only markers (wide density support bands are clipped) and
expand to the whole age-group field.
Historical legacy panels offer strict, matched-slot (Nth matched age-group
rank, a matched winner counts) and factor target methods; their
ranked evidence plot also shows a descriptive age-group density boundary and
five-unmatched scan markers, which are not qualification results and do not
affect targets, Finder chances or model metrics. Age-group winners are gold
dots, matched or not. In a legacy panel the winner is age-group rank 1, shown
at the actual rank and raw time, excluded from those plot-only density/scan
inputs and counts (it does count in B's age-group matched-slot cutoff when
matched), and is not a P1 automatic-slot winner. In a
performance-pool panel each winner keeps the separate automatic-slot route:
its dot sits in the matched or not-matched row where its age-graded time
falls, but it holds no pool rank and never enters pool ranks, matched-slot
counts, density or scan; winners beyond the displayed axis are drawn to its
right. Compatible starter matches remain visible as evidence, not proof of
acceptance.
Each year's method table lists rank, ranks beyond the initial allocation,
finish time, age-graded time (pool panels), mapped target and basis for its
applicable approaches, including overlapping or unavailable boundaries and the
plot-only legacy markers; pool-only methods are marked not applicable for
R1-R4 or unknown cycles. The step's "time needed and roll-down" charts plot the
same per-year method rows: the mapped target time of every applicable method
and its ranks beyond the initial allocation (strict = 0), excluding strict
fallbacks and plot-only legacy markers. Ranks beyond the initial allocation are a model or
scenario depth, not a count of declines. The factor marks its
calculated rank; automatic winners remain separate. Ranks beyond the last
finisher have no extrapolated time. Reported minute-precision cutoffs do not
establish an exact rank; their reported pool time is shown. Hover, keyboard focus,
or touch reveals the rank, finishing time, available age-graded time, year,
and match status; missing compatible evidence is labelled per year. Current
ranks use the current-rules pool, never the historical pool ranking. A match does not prove
acceptance at the qualifying race; no match does not prove absence or decline.
Automatic age-group winners are a separate route from the performance pool.
70.3 championship starter matching uses the 70.3 World Championship start list
of the same cycle (St. George 2022, Lahti 2023, Taupo 2024, Marbella 2025,
Nice 2026). Race-years without a published cycle mapping (the 2022 and 2023
cycles) and 2027-cycle race-years show the evidence as unavailable. The shared year filter
changes displayed comparisons, not the underlying course fit, DNF training or
personal-result calibration.

## Calendar

`data/reference/cycle_calendar.json` holds the qualifying events already
announced for the 2027 cycle (source: ironman.com, retrieved 2026-10-31).
The "Races" filter hides dashboard races whose next edition has already been
held; races that are not yet announced stay open and show their usual month
(from past editions). Extend the JSON when new events are published, and set
`event_id` when a race exists in `data/reference/events.json`.

## Backtest (dashboard view "Backtest", `src/backtest.py`)

Historical results below describe the former time-multiplier model, not the
new rank-factor scenario (distance IRONMAN, repeat athletes):

- **Cut-off (A):** leave-one-cycle-out. Strict bias −5.7 % men / −11.2 % women,
  old time-multiplier bias −0.5 % / −0.8 %, mean absolute error roughly halved.
- **Athlete level:** leave-one-race-out error SD ≈ 6.2 % (robust 5.3 %) against
  the model's 3.7 % σ; 51 % of results fall within ±1σ (normal: 68 %).
- **Reliability:** the chance formula is overconfident at mid-range chances
  (e.g. predicted 30–40 % happened ≈ 20–26 %). Brier scores beat the
  base-rate baseline (A strict 0.022 vs 0.033, old A time model 0.053 vs 0.118,
  B 0.030 vs 0.054). These results describe the former models, not the current
  factor ranking or its probabilities. Widening σ alone did not help the old
  models: errors are heavy-tailed, not just wider.

Caveats: only finishers are scored (DNF excluded), repeat athletes are not
representative of all starters, "met the standard" is not slot acceptance, and
course factors are fitted on the same athletes (mild leakage).
