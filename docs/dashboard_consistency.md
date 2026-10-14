# Dashboard Consistency

## Implementation

- [x] Inventory existing features and preserve all calculation/evidence modes.
- [x] One shared year selector; synchronized demographic filters local to relevant analyses.
- [x] Shared strict/manual/reported/density/15-absence qualification assumptions.
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
| Qualification | Race targets, historical slots, cross-race qualification plots, scatter/regression/residuals, slot pressure, percentile, inter-year uncertainty, historical/current rules, gender-pool overrides, separate pool/legacy extra places, historical target-hit rate, modelled chance, personal results and strength profile, multi-cycle Kona evidence and local attribution |
| Course Analysis | Course/season/conditions factors, adjusted field and qualification targets, GPX comparison, athlete examples and head-to-head raw checks |

## Contracts

- Displayed-year selection changes displayed rows, aggregates and comparison fits, not model training or Kona estimator evidence.
- Demographic context applies to qualification and explicitly demographic analyses, not all-athlete race statistics.
- Strict entitlement, reported acceptance, inferred cutoffs and conditional athlete attribution remain distinct.
- Estimate rankings use covered compatible editions by default; strict fallback is explicit. Missing races remain visible.
- Modified courses, incompatible ranking scopes, changed allocation and mismatched championship cycles cannot silently borrow inferred cutoffs.
- Legacy estimates use raw age-group rankings and cycle-compatible allocations, not 2026 standards.
- Personal results and 2026 attribution keep their existing browser storage keys; older-cycle reviews are namespaced by cycle.
- Static HTML and its sibling data script continue to work offline.