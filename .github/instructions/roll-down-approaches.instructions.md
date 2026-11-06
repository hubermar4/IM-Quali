---
description: "Use when analyzing or changing strict qualification cut-offs, roll-down assumptions, density estimates, absence scans, manual extra places, or their display and tests. Keep current-rules and historical objectives separate."
applyTo: "src/dashboard_*.js,src/dashboard_*.html,src/kona_trace.py,src/qualification_*.py,src/build_dashboard.py,src/dashboard_insights.py,src/backtest.py,tests/test_dashboard_*.py,tests/test_qualification_rules.py,tests/test_race_finder_insights.py,docs/race_finder.md,docs/*qualification_rules.md,data/reference/reported_cutoffs.json"
---

# Roll-down and Cut-off Approaches

## Scope and evidence

- Every target belongs to exactly one objective: **A, current rules on historical results**, or **B, historically correct rules and data**. Follow [dual-objectives.instructions.md](./dual-objectives.instructions.md) and [qualification-rules.instructions.md](./qualification-rules.instructions.md).
- Determine whether the original race actually used a performance pool from its real qualifying cycle and rule set, not its calendar year or the selected hypothetical objective. If the cycle, rule set, or evidence compatibility is unknown or ambiguous, do not claim match-based methods are supported.
- For objective A, use the current rule set, standard, and allocation when ranking historical results. For an actual P1 race, re-rank compatible championship starters from its cycle under those current rules. For a race-year with a known R1-R4 cycle, the same re-ranked roster supports only the matched-slot cutoff (user decision, November 2026); never use old-era age-group matches as density or scan evidence.
- For objective B, use the race-year's actual rule set, cycle-compatible standards and slots, and, for an actual P1 race, its compatible championship starter list. For a race-year with a known R1-R4 cycle, the same-cycle championship roster supports only the age-group matched-slot cutoff in the actual age-group ranking (user decision, November 2026). Never borrow evidence from another cycle; show it as unavailable when compatibility cannot be established.
- Ranked championship evidence plots are descriptive and separate from method availability: whenever same-cycle roster and matching evidence exist, plot matched starters from the corresponding World Championship for every selected race-year. In A, rank them under current P1 rules and the current standard, including original R1-R4 races; for those legacy races, show no density or absence-scan boundary, and show the matched-slot cutoff labelled as re-ranked starters who qualified through age-group slots. In B, use the actual historical ranking; for R1-R4, show B's age-group matched-slot cutoff (a selectable method) plus a descriptive legacy density boundary and five-unmatched gap/boundary markers in the plot only, based on actual age-group ranks and excluding the rank-1 match from density and scan inputs/counts. These legacy density/scan markers are not selected methods, qualification estimates, targets, Finder chances, calibration inputs, or model metrics. Missing or incompatible roster/matching evidence is explicitly unavailable.
- Show age-group first-place finishers, matched or not, as gold dots, not as performance-pool ranks. P1 winners use the separate automatic-slot route and are excluded from performance-pool rankings, density, absence-scan, and other pool metrics. For B's R1-R4 plot-only legacy evidence, show a matched actual age-group rank-1 finisher in gold at that actual rank and time, label it "Age-group rank 1" (not an automatic slot), and exclude it from the plot's density/scan inputs and counts. Do not alter historical age-group allocation or infer slot acceptance. A match does not establish slot acceptance, and an unmatched starter does not establish absence or decline.
- Keep the labels distinct: **strict** is an allocation-based baseline; **density** and **absence scan** are model estimates from matched championship starters; the **rank-based roll-down factor** is a user-selected scenario. None proves who accepted or declined a slot.
- Slot allocation is based on eligible starters. A time cut-off is read from the relevant ranked finishers. Do not silently substitute finishers for starters when reconstructing an allocation.

## Available methods

| Original race rules | A: current rules on historical results | B: historically correct |
|---|---|---|
| P1 performance pool | Strict, matched-slot cutoff, compatible match-density, absence scan, and rank factor in the current gender pool | Strict, matched-slot cutoff, compatible match-density, absence scan, and rank factor in the actual gender pool |
| R1-R4 age-group allocation | Strict, matched-slot cutoff (same-cycle roster re-ranked under current rules), and rank factor in the current gender pool | Strict, matched-slot cutoff (Nth matched rank in the actual age-group ranking, a matched age-group winner counts), and rank factor in the original age-group ranking |
Density and absence scan require a confirmed actual P1 race and compatible same-cycle evidence. The matched-slot cutoff also applies to race-years with a known R1-R4 cycle: A uses that cycle's championship roster re-ranked under current rules; B uses the same roster matched in the actual age-group ranking. The matched-slot cutoff counts only distinct ranks with a matched result from the selected qualifying race-year, ignores unmatched championship ranks, and takes the Nth matched rank where N is that race-year's gender performance-pool slots (B R1-R4: its age-group slots, with a matched age-group winner counted). A re-ranks the same-cycle championship roster under current rules and standard; B uses the historical ranking and cycle standard. Fewer than N matches, or incompatible cycle, roster, ranking, slots, or standard, is unavailable and never uses strict fallback. P1 age-group winners have no pool rank and do not enter the match count. This method is not density, absence scan, rank factor, or evidence of acceptance. Unknown or incompatible evidence is unavailable, not evidence of a pool match model. A strict fallback must not expose density or scan as available methods for an R1-R4 race or an unconfirmed pool race.

Density and absence scan require a confirmed actual P1 race and compatible same-cycle evidence. Unknown or incompatible evidence is unavailable, not evidence of a pool match model. A strict fallback must not expose density or scan as available methods for an R1-R4 race or an unconfirmed pool race. If the original rules or cycle are unresolved, objective A can still use its current-rules strict and rank-factor scenarios; objective B requires a reliably established historical rule, ranking, and allocation. Known R1-R4 races remain usable for historical strict, age-group matched-slot, and rank-factor scenarios. An externally documented last-accepted cutoff may be displayed separately as labelled evidence, not as an inference method. This policy supersedes any conflicting descriptions of legacy match scans or time-based calibration in existing documentation.

The descriptive ranked-evidence plot is not a match-based qualification method. Its B R1-R4 legacy density boundary and five-unmatched-rank markers are visualization-only, exclude the actual age-group rank-1 match from their fit/scan inputs and counts, and must never leak into any recommendation, selected method, target, Finder chance, calibration, or model metric. Show P1 age-group winners (matched or not) as gold dots placed by age-graded time; do not assign them pool ranks or include them in pool density/absence-scan calculations. In the B legacy plot, show a matched age-group rank-1 finisher in gold at rank 1, without treating that finisher as a P1 automatic-slot winner.

## 1. Strict allocation: no roll-down

The strict cut-off assumes every initially allocated slot is accepted. It does not estimate declines or use championship-starter matching.

- For historical R1-R4 age-group allocation, use the race-year's cycle-compatible allocation and rank finishers within the specified age group. The strict target is the finisher at the allocated age-group slot rank.
- For P1, account for the age-group winner's automatic slot and the gender-specific performance pool. The target is the slower (larger) time of the age-group winner and the allocated performance-pool boundary, because either route can earn a slot. Strict allocation does not roll an unaccepted winner slot to second or third place.
- Under objective A, apply the selected current allocation and current standard to the old race results. Under objective B, use the race-year's actual rule set, slots, and standard.
- Treat strict as the no-roll-down baseline for comparisons. Do not label it as a predicted or observed acceptance cut-off.
- If the allocation exceeds the available ranked finishers, explicitly show either any finish or unavailable, as appropriate, without inventing a finisher or time.

## 2. Match-density estimate

The density estimate searches the compatible championship ranking for a breakpoint in the distribution of matched starters. It asks whether matches are sufficiently more concentrated above a candidate rank than below it.

- For a selectable density estimate, use only starters matched to an actual P1 qualifying race-year, ranked in its compatible gender pool and cycle. For A, re-rank those matches under current rules; for B, use the historical pool and its cycle's standards and slots. Do not expose legacy age-group density as a qualification estimate; the B R1-R4 plot-only boundary described above is descriptive, excludes age-group rank 1 from its inputs/counts, and is unavailable to all qualification calculations.
- The current implementation requires a positive initial allocation, at least four ranked pool positions, at least three matched ranks, and at least three matches above a candidate breakpoint. It selects a candidate by likelihood and accepts it only when the BIC improvement is positive. Preserve these support checks when changing the estimator.
- Show the estimated rank/time as exploratory, with its supported interval, match count, and sensitivity to the single-match subset where available.
- The estimate is not an observed acceptance boundary or a count of declined slots. Sparse or missing matches may reflect incomplete matching or coverage.
- Do not let a density estimate imply a faster target than strict allocation. If evidence is insufficient or incompatible, return unavailable; strict fallback is allowed only when explicitly enabled and must be labelled as a strict fallback.

## 3. Absence scan

The scan walks down the compatible championship ranking after the initial allocation. A matched starter resets the consecutive-absence counter. The scan stops at the first qualifying run of unmatched ranks and returns the last matched starter before that run.

- For a selectable absence-scan estimate, use **15 consecutive unmatched ranks** in the compatible gender performance-pool ranking. Do not expose a legacy age-group scan as a qualification estimate. The B R1-R4 plot-only five-unmatched marker is descriptive, uses actual age-group ranks, excludes rank 1 from scan inputs/counts, and is unavailable to qualification calculations.
- The scan must begin after the initial allocation and must be supported by a matched starter beyond the strict boundary. If the pool ends before the absence criterion is met, or no post-allocation match exists before it, provide no scan cut-off.
- Keep the estimate at or beyond the strict boundary. Do not turn the absence gap into a confirmed number of declines.
- The displayed roll-down percentage, when calculated from the last matched rank and initial slots, is a **model-derived assumption**, not an observed decline rate. Explain that unmatched starters may be absent, unrecognized, or missing from the source data.
- If evidence is insufficient or incompatible, return unavailable; strict fallback is allowed only when explicitly enabled and must be labelled as a strict fallback. Never present fallback as scan evidence.

## 4. Rank-based roll-down factor
## 4. Matched-slot cutoff

- Under B, offer this selected method for race-years verified to have used the P1 performance pool and for race-years with a known R1-R4 cycle. For R1-R4, use the actual age-group ranking and slots: N is the race-year's age-group slots, and a matched age-group rank-1 finisher counts as a matched rank because R1-R4 had no separate winner route (user decision, November 2026). The B legacy density boundary and five-unmatched markers stay visualization-only and keep excluding rank 1. Under A, also offer it for race-years with a known R1-R4 cycle, using that cycle's championship roster re-ranked under current rules, allocation and standard; state that those starters qualified through age-group slots, so the boundary is a counterfactual mapping, not observed pool roll-down. Unknown cycles remain unavailable.
- Require the same-cycle compatible World Championship roster and matching evidence, the objective's compatible ranking cycle and standard, and an exact match between the objective's slot count (performance-pool or, for B R1-R4, age-group) and the evidence pool's slots. Never borrow another championship cycle or use age-group-rank matches as pool matches.
- For P1, let N be the gender performance-pool slots, excluding separate automatic age-group-winner places. Count each championship pool rank once when that rank has a matched finisher from this exact qualifying race-year; ignore unmatched ranks. The boundary is the Nth matched rank, not rank N. If fewer than N ranks match, or the ranking evidence lacks its time/age-grade, return unavailable without a strict fallback or extrapolation.
- Under A, rank the same-cycle roster using current rules, allocation, and standard. Under B, use the actual historical pool ranking, allocation, and standard for P1, or the actual raw age-group ranking and slots for R1-R4. Keep these rankings separate even when the roster and qualifying race-year are the same.
- Show both the selected championship rank and the finish time. For P1, map its age-graded time through the applicable target-event standard and the same slower-of-winner-or-pool-equivalent route as other P1 targets; for B R1-R4, the raw age-group finish time is the target.
- This is a matched-slot boundary, not a match-density breakpoint, absence scan, rank-factor scenario, observed acceptance cutoff, count of declines, or proof that any athlete accepted a slot. P1 age-group winners remain in their separate automatic route, with no pool rank or contribution to the matched count. B R1-R4 rank-one matches count only in B's age-group matched-slot cutoff and never enter a pool method, density, or scan.

## 5. Rank-based roll-down factor

The factor is a what-if assumption, not championship evidence or a historical acceptance boundary. It applies to both objectives in the ranking specified above, including historical R1-R4 age groups.

- Let `f >= 0` be extra declined/offered positions per initially allocated qualifying slot. Calculate `extra = floor(slots * f + 0.5)` (nearest whole integer, halves rounded upward) and `target rank = slots + extra`.
- Use initial gender performance-pool slots excluding automatic age-group-winner slots for P1, or the historical age-group allocation for R1-R4. Default `f` to 0; allow 0 and values above 2. For 30 slots, `f = 0` targets rank 30, `f = 1` rank 60, and `f = 2` rank 90.
- Display the assumption, rounding, target rank, and corresponding time consistently. If that rank exceeds the available ranking, show it as unavailable; never extrapolate a finisher.
- For P1, retain the separate automatic age-group-winner route and map the ranked pool boundary using the objective's correct age-grade standard. An unavailable pool rank must not become an invented pool threshold.
- The factor is not a probability, a percentage of elapsed time, or a guaranteed count of observed declines. Do not add its extra positions to strict, density, absence-scan, or reported cutoffs.
- Retire manual extra places as an independent cutoff method and time-based prior calibration; the rank factor replaces them. Do not automatically reuse old gender-specific time multipliers or their calibration spread, or imply that the new factor has been calibrated or backtested by the old time-based model.

## Keep separate from these approaches

- **Reported last accepted** is externally reported evidence. Preserve its source, precision, and verification status; do not describe it as a density or absence estimate.
- Historical backtests and old time-spread results describe their original models only; they do not validate or calibrate this new rank factor.

## Validation and documentation

- Keep the dashboard labels and explanations consistent with this document and [docs/race_finder.md](../../docs/race_finder.md). Update both when approach semantics change.
- Test the four objective/original-rule combinations, cycle transitions and ambiguity, strict targets, matched-slot Nth-match selection and fewer-than-N unavailability, A/B ranking separation, rank-one winner exclusion from pool methods and inclusion in B's R1-R4 matched-slot count, rank-factor rounding and examples, unavailable ranks, age-group-winner routes, density support/rejection, the pool absence threshold and stopping conditions, incompatible evidence, and explicit strict fallback.
- When code paths are shared between objectives, retain tests that verify both current-rules counterfactual and historically correct behavior. Check historical estimates against compatible official or reported evidence where available.
