# Code and data review

## Data update 2026-09-28: seven new full-distance races

Added IRONMAN Calella-Barcelona, Lanzarote, Leeds, Portugal-Cascais,
Switzerland Thun, Vitoria-Gasteiz, and Wales, plus earlier years for Kalmar
(2019), Copenhagen (2019, 2021), and Tallinn (2020, 2021).

- Current allocations from ironman.com: Calella-Barcelona 55, Portugal-Cascais
  55, and Wales 50 (2027 cycle); Lanzarote, Leeds, Switzerland, and
  Vitoria-Gasteiz 40 (2026 cycle). Wales 2026 (2027 cycle, 50 slots) is not in
  the cached Coach Cox pages and is sourced from ironman.com.
- Every legacy race-year of the new races uses the official `Qualified` flags;
  every performance-pool race-year reproduces the official qualifier list
  exactly.
- Modified courses, detected from top-20 splits and excluded from cross-race
  comparisons and course factors: Calella-Barcelona 2021 (swim cancelled for
  most athletes), Switzerland Thun 2021 (swim about 30% short),
  Vitoria-Gasteiz 2021 and Leeds 2026 (swim cancelled).
- New GPX tracks with elevation are used for Barcelona, Copenhagen, Leeds,
  Thun, Vitoria-Gasteiz, and Wales. Corrected tracks for France, Lanzarote,
  and Portugal-Cascais were supplied on 2026-09-29 and are used as well.
- A few rows have no division (Kalmar, Copenhagen, Leeds, Tallinn, Wales 2026)
  and are excluded; the warning now lists them as `missing`.

## Review 2026-09-28b: empirical course factors

The Experimental tab previously subtracted one GPX-derived constant per race.
That is additive (course effects are multiplicative and larger for slower
athletes), ignores swim, run, and race-day conditions, and is invalid for
France. It is replaced by `src/course_difficulty.py`:

- Athletes are matched across race-years of the same distance by normalised
  name, gender, and country. Keys that appear twice in one race-year or whose
  age groups imply inconsistent birth years are dropped. About 41,000 records
  for 140.6 and 1,600 for 70.3 remain.
- Model per split: log(age-graded time) = athlete + race-year + returning
  athlete. Fitted by alternating means, refitted after trimming residuals
  beyond 4 robust standard deviations. Race-year effects average zero over
  qualifying race-years; sampling error is about 0.1-0.3% per race-year.
- The returning-athlete term matters: athletes are about 1.0% faster on later
  appearances (flat after the second). Without it, the gain was booked to
  later race-years and made 2024-2026 look about 1.5% easier.
- Race-year factors are split into course x season x conditions. The season
  effect is almost entirely bike (+1.7% in 2017 to -2.0% in 2026, consistent
  with equipment progress; swim and run show no trend), so per-race medians
  would flatter races with only recent editions (Copenhagen, Kalmar, Tallinn).
- Season-adjusted overall course effects (16 full-distance races, build of
  2026-09-28): Copenhagen -6.4%, Hamburg -5.2%, Kalmar -4.8%, Calella-Barcelona
  -4.0%, Italy -4.0%, Tallinn -3.5%, Vitoria-Gasteiz -1.7%, Austria +0.4%,
  Frankfurt +0.6%, Portugal-Cascais +1.2%, Switzerland Thun +4.1%, Kona +4.4%,
  France +6.5%, Leeds +7.6% (one race-year), Wales +9.8%, Lanzarote +11.3%.
- The GPX model ranks flat and rolling bike courses like the athlete data but
  underestimates hilly ones by about half (Leeds +7% vs. +16%, Wales +8% vs.
  +16% relative to the compared-course mean) and rates Calella-Barcelona 7
  points slower than the athletes did. Use it as a qualitative check only.
- IRONMAN Frankfurt's bike has been about 5% faster since 2024 even after the
  season effect; this shows as race-day conditions, not a new course.
- Age-grading uses the current standard. Shortened race-years get no factor.
  70.3 has one race, so its factors compare Zell am See editions only.

**Can I Qualify?** defaults to treating the entered time as a time on an
average course and multiplies it by each race-year's factor; the ranking adds
"Needed on an average course" (time needed / factor), which is the fairest
cross-race difficulty comparison.

## Review 2026-09-28: validation against official results

The result CSVs contain IRONMAN's own `Qualifier Time` (age-graded time),
`Gender Qualifier Rank`, and `Qualified` flags. The flags mark the strict
official slot entitlement (top-k per age group in legacy years; age-group
winners plus the top-N pool places in performance-pool years). They are now
the ground truth for every rule check.

Verified:

- Full-distance pool split (allocation minus automatic slots of age-group
  winners who finished, split by eligible age-group starters) reproduces the
  official qualifier list exactly in all 10 performance-pool race-years
  (IRONMAN Italy 2025 rules out the "represented starters" variant).
- Official age-graded time is `floor(finish x standard)`. The Kona Standard is
  identical in the 2026 and 2027 cycles.
- Regression tests now assert exact agreement with the official flags and
  official qualifier times.

Fixed:

- IRONMAN 70.3 Zell am See 2025 used the 2027-cycle 70.3 Standard. The
  2026-cycle table differs in every age group and changed one male qualifier;
  historical mode now uses each race-year's own cycle standard.
- Zell am See 2026 was labelled 2026 cycle with 35/35 slots; it is a 2027-cycle
  race with 25/25 slots. Tallinn 2026 (2027 cycle, 45 slots) had no source.
- Current-mode allocations updated to the latest published cycle: Italy 55
  and Tallinn 45 (2027 cycle), Zell am See 25/25 (2027 cycle).
- Slot sources merged overlapping cycles with `max()`, which could combine
  numbers from different championships. One real cycle row is now selected;
  the others are listed as "also offered".
- Coach Cox age-group tables disagree with the official flags for several
  race-years (up to 18 slots for IRONMAN Frankfurt 2023 and 16 for IRONMAN
  France 2023). Legacy years now use the official flag counts whenever they
  cover the selected cycle; Coach Cox tables and reconstruction are fallbacks.
  Zell am See 2021-2024 gained historical data from the flags.
- IRONMAN Kona 2022 was raced over two days with one file per day; only the
  men's file was loaded. Both files are now combined.
- Kona is not a qualifying event but was shown with a fabricated 40-slot
  estimate and appeared in qualification comparisons. It is now excluded.
- The raw finish-time target ignored the age-group winner route. Time needed
  is now the slower of the winner's time and the pool equivalent, which
  matters for older age groups.
- Shortened race-years (IRONMAN France 2019, IRONMAN Frankfurt 2026) are
  flagged in tables and excluded from all cross-race comparisons.
- Athlete names were inserted into the page without HTML escaping.
- Pool construction was duplicated between the engine and the dashboard; the
  dashboard now uses the engine output.

Added: the **Can I Qualify?** tab (race-year check for any finish time,
ease-of-qualification ranking, share-of-race-years curve, qualifiers per 100
starters by age group).

Open points:

- IRONMAN Austria 2026 F75-79 has one official qualifier time implying 0.6165
  against the published 0.6150; the published value is kept.
- Frankfurt, Kalmar, and Copenhagen 2024 flag only the 2025-cycle women's
  slots, so their 2024-cycle allocation remains reconstructed.
- Exact .5 gender-split roundings are resolved half-up; no official example
  distinguishes this from other conventions.

## Review 2026-09-24

## Correctness fixes completed

- Performance-pool gender allocation now uses only canonical eligible
  age-group starters. Professional, handcycle, PC/ID, guide, special-team, and
  unknown divisions no longer influence the male/female slot split.
- Exactly one automatic slot is awarded per represented age group, even if
  source data contains duplicate rank-1 rows.
- Women in age groups with an official TBD standard still count as starters and
  can receive the automatic winner slot; they are excluded only from the
  age-graded performance pool.
- Full-distance calculations now reject impossible cases where automatic slots
  exceed the race allocation.
- Full-dataset tests verify current slot conservation, historical source-total
  reconciliation, and sufficient performance-pool depth.
- Compare-race means contain only canonical age-group finishers. France 2019
  is excluded from fitted comparisons because that edition used a shortened
  course.

## Qualification rules and limitations

The implemented rule paths match the available source material:

- Pre-performance-pool races use published age-group allocations where a
  complete table exists; otherwise the dashboard labels the proportional
  reconstruction explicitly.
- Races in the 2026 qualification cycle use automatic age-group winner slots,
  starter-representation gender pools, and Kona/70.3 age grading.
- Historical cutoffs are estimates. The result files do not record ceremony
  attendance, declined slots, prior qualification, or the final accepting
  athlete. Selected roll-down counts are scenarios, not observed outcomes.
- F80-84 and F85-89 performance-pool standards remain TBD in the official
  source. No ratio is invented.

### Overlapping source-cycle records

The cached source lists contain different allocations for the same physical
race in overlapping qualification cycles:

- Frankfurt 2024: 2024-cycle 75 M / 75 F; 2025-cycle 35 F
- Kalmar 2024: 2024-cycle 35 M / 35 F; 2025-cycle 35 F
- Kalmar 2025: 2025-cycle 65 M / 20 F; 2026-cycle 40 combined
- Copenhagen 2024: 2024-cycle 35 M / 35 F; 2025-cycle 35 F
- Copenhagen 2025: 2025-cycle 65 M / 20 F; 2026-cycle 40 combined

The dashboard preserves the existing selected-cycle logic and exposes source
cycles/links in its data. These cases should be resolved from authoritative
race-specific allocation records before claiming final accepted qualifiers.

### Historical data gaps

- Tallinn 2026 has results but no local historical slot source.
- Kona is a championship, not a qualifying race, so historical qualification
  rows are intentionally unavailable.
- Some exact Coach Cox pages expose only one gender. These race-years use an
  explicitly labeled reconstruction instead of presenting partial data as
  exact.

## HTML and frontend review

Completed:

- The 30 MB athlete payload was removed from the HTML and written to
  `dist/dashboard_data.js`. `dist/dashboard.html` is now about 100 KiB and
  still works when opened directly, provided both files stay together.
- Tooltips are clamped inside chart panels.
- Split summary wording now states that standard deviation is measured in time,
  not transformed pace/speed units.
- Slot-control fallback no longer throws when no valid event is selected.

Remaining opportunities:

- The data payload is still about 30 MB and is parsed eagerly. The next major
  improvement is one data file per event with lazy `fetch()` loading. That
  requires serving `dist/` over HTTP because browsers commonly block local
  `file://` fetches.
- Density charts recalculate kernel estimates and replace complete SVG trees.
  Cache unchanged charts or precompute densities if interaction becomes slow.
- Athlete search and split summaries scan all active-event records on every
  input event. Debouncing search and caching selected years would help with
  larger datasets.
- The generated frontend remains a large Python string. Extracting CSS and JS
  templates would improve maintainability but is a larger refactor with no
  immediate analytical benefit.

## Additional plots implemented

The Compare Races tab now includes:

1. **Slot pressure:** qualifying slots per 100 eligible starters, with
  rule-aware gender or age-group scope.
2. **Relative cutoff depth:** selected-age-group cutoff percentile within the
  same race field.
3. **Age-group depth:** split-complete selected-age-group finisher counts by
  race-year.
4. **Split contribution:** mean athlete-level swim, transition, bike, and run
  shares by race.
5. **Qualification uncertainty:** median cutoff with interquartile range and
  min/max whiskers across years.

The mean-finish-versus-qualification legend is interactive; visible traces
alone determine the global fit and residual chart.

Still useful: a dedicated data-quality chart for unsupported divisions,
zero/corrupt splits, and missing historical sources by race-year.

## GPX model caveat

The GPX model is now only a bike cross-check in the Experimental tab; course
normalisation uses the empirical factors described at the top.

- France: the corrected track (2026-09-29) has +2,489 m and no grade
  discontinuities (the old one had +3,406 m and >25% jumps); it is included.
- Lanzarote: start and finish are 50 m apart, but the finish reads 192 m
  against 17 m at the start. Repeated road sections between km 22 and 161
  agree within about 5 m; the error builds up over the last 12 km (altimeter
  drift on the descent to Puerto del Carmen). Copying the outbound elevations
  onto the return changes the course factor only from 1.148 to 1.143, so the
  file is used as supplied.
