# Dashboard Consistency

## Implementation

- [x] Inventory existing features and preserve all calculation/evidence modes.
- [x] One shared year selector; synchronized demographic filters local to relevant analyses.
- [x] Strict, rank factor, P1 density and P1 15-absence scan share a selector; reported cutoffs remain separate evidence.
- [x] Four workspaces with connected race, target and evidence drill-downs.
- [x] Offline, keyboard, empty-state and responsive verification.

Verified with the full 52-test build gate and 25 focused dashboard regressions.
The generated offline page was checked at desktop and mobile widths, including
all nine views with no years selected, cross-view year persistence, synchronized
filters, distance-specific personal-result inputs, keyboard focus, and the
ranking-to-target-to-evidence return path.
The follow-up correction checked selected-distance distributions, non-interactive
year legends, qualification-only chart placement, historical raw-time targets,
cycle-specific evidence links, missing-gender warnings and mobile filter sizing.

## Feature Preservation

| Workspace | Preserved surfaces |
| --- | --- |
| Race Explorer | Athlete search, time range, split statistics, profiles, pace/speed, CSV export, overall distributions and top cutoffs, participation/DNS/DNF and completion rates |
| Compare Races | Participation/DNS/DNF, distance-specific finish/split distributions, age-group depth and split contribution |
| Qualification | Five steps: 1 You (shared distance, gender and age group), 2 Your time (typed or past results, strength profile), 3 Race difficulty (as raced vs. standard course), 4 Qualification targets (race selector, current or historical targets and ranked evidence), 5 Where to qualify (current-rules recommendations, field size and strength, expandable evidence and comparison charts); one shared cutoff method and rank factor |
| Course Analysis | Course/season/conditions factors by split, all-cohort adjusted field and qualification targets, GPX comparison, fixed athlete examples and head-to-head raw checks; distance, plot-local top percentage and race-year split are adjustable. Race comparison includes a standard-course reference, minute equivalents and expandable year factors. |

## Contracts

- Displayed-year selection changes displayed rows, aggregates and comparison fits, not model training or Kona estimator evidence.
- Demographic context applies to qualification and explicitly demographic analyses, not all-athlete race statistics.
- Strict entitlement, reported acceptance, inferred cutoffs and conditional athlete attribution remain distinct.
- The selected method controls targets, Finder what-if estimates, rankings, detail and graphs. The rank factor is independent of other methods. Reported last-accepted cutoffs remain separate evidence.
- The historical/current selector controls Targets; Finder always uses current rules, regardless of that selection. The rank factor is not calibrated by the old time model.
- Missing or incompatible race-year evidence is marked in place. Strict fallback is explicit and only applies to supported P1 estimates, never legacy or unknown rules.
- Only original P1 races support density and 15-absence gender-pool estimates as qualification methods. The matched-slot cutoff also covers race-years with a known R1-R4 cycle: A re-ranks that cycle's championship roster under current rules (starters who qualified through age-group slots; not observed pool roll-down); B takes the Nth matched rank in the actual age-group ranking (N = age-group slots), counting a matched age-group winner. Historical B legacy evidence plots also show descriptive age-group density and five-unmatched scan markers; these are plot-only and do not affect targets, rank factor, Finder chance, calibration or metrics. Matches are not evidence of absence or acceptance.
- Modified courses, incompatible ranking scopes, changed allocation and mismatched championship cycles cannot silently borrow inferred cutoffs.
- Historical legacy scenarios use raw age-group rankings and cycle-compatible allocations, not 2026 standards.
- Historical targets without a unique known cycle or supported performance-pool standard are unavailable, not reconstructed using current rules.
- Ranked evidence shows same-cycle matched starters from the corresponding World Championship in a separate panel for every selected race-year. A ranks matches under current P1 rules and standards, including legacy races without density or scan boundaries (their matched-slot cutoff is shown). Age-group winners of the objective's allocation appear as gold dots whether matched or not (A takes winner matches from the counterfactual trace); in performance-pool panels each dot sits in the matched or not-matched row where its age-graded time falls, with no performance-pool rank, and never enters pool ranks, matched-slot counts, density or scan. B uses the actual historical ranking, shows its age-group matched-slot cutoff for legacy years and adds plot-only density/five-unmatched markers. The legacy age-group rank-1 finisher appears as a gold dot at the actual rank/time, matched or not, is excluded from those plot-only density/scan inputs and counts (a matched winner counts in the matched-slot cutoff), and is not a P1 automatic-slot winner. These legacy markers are not qualification results and do not affect targets, Finder chances, calibration or metrics. Pool panels share a 1-100 rank axis; B age-group panels scale to their own slots and markers. Each panel has a method table with rank, ranks beyond the initial allocation, times, mapped target and basis for every applicable method; pool-only methods are marked not applicable for R1-R4 or unknown cycles. The step's time-needed and roll-down charts plot the same method rows per objective. Axes name the actual plotted age group or gender performance pool. Missing or incompatible roster evidence is labelled unavailable. Point and winner details are available on hover, focus and touch.
- Personal results and 2026 attribution keep their existing browser storage keys; older-cycle reviews are namespaced by cycle.
- Static HTML and its sibling data script continue to work offline.