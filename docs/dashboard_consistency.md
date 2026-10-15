# Dashboard Consistency

## Implementation

- [x] Inventory existing features and preserve all calculation/evidence modes.
- [x] One shared year selector; synchronized demographic filters local to relevant analyses.
- [x] Strict, manual-extra, reported, density and scope-aware 3-/15-absence approaches shown together.
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
| Qualification | Four steps: 1 Your time (typed or past results, strength profile), 2 Race difficulty (as raced vs. standard course, predicted time), 3 Qualification targets (slots, strict and standard-course targets, roll-down estimates and slots passed on; expandable five-approach comparison, slot what-ifs and Kona + Nice start-list evidence with local attribution), 4 Where to qualify (chance ranking; expandable approach comparison, historical target hits and cross-race plots: scatter/regression/residuals, slot pressure, percentile, inter-year uncertainty); one shared historical/current approach selector and separate pool/legacy extra places |
| Course Analysis | Overall-split course/season/conditions factors, all-cohort adjusted field and qualification targets, GPX comparison, fixed athlete examples and head-to-head raw checks; only distance, top percentage and shared years are adjustable |

## Contracts

- Displayed-year selection changes displayed rows, aggregates and comparison fits, not model training or Kona estimator evidence.
- Demographic context applies to qualification and explicitly demographic analyses, not all-athlete race statistics.
- Strict entitlement, reported acceptance, inferred cutoffs and conditional athlete attribution remain distinct.
- All five cutoff approaches are shown together; manual pool and legacy extra places are inputs for the manual approach, not method selectors.
- One shared historical-vs-current radio controls every qualification analysis; local rule-mode selectors are removed.
- Missing or incompatible race-year evidence is marked in place. Strict fallback is explicit and never silently substitutes for an inferred cutoff.
- Legacy scans use age-group ranks and three consecutive absences; performance-pool scans use gender ranks and fifteen. Labels and roll-down calculations follow the displayed ranking scope.
- Modified courses, incompatible ranking scopes, changed allocation and mismatched championship cycles cannot silently borrow inferred cutoffs.
- Legacy estimates use raw age-group rankings and cycle-compatible allocations, not 2026 standards.
- Personal results and 2026 attribution keep their existing browser storage keys; older-cycle reviews are namespaced by cycle.
- Static HTML and its sibling data script continue to work offline.