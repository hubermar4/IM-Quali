# IRONMAN qualification analysis

Historical IRONMAN result analysis, qualification estimates, GPX bike-course
normalization, and a generated interactive dashboard.

## Layout

- `src/` - maintained Python source and embedded dashboard UI module
- `tests/` - qualification and GPX regression tests
- `data/race_history/` - race result CSV files grouped by event
- `data/gpx_tracks/` - bike-course GPX inputs
- `data/cache/` - cached Coach Cox source pages
- `data/derived/` - reproducible extracted qualification datasets
- `data/legacy/` - older Excel inputs retained for legacy analyses
- `docs/` - qualification rules and source documentation
- `dist/` - generated dashboard, data payload, reports, plots, and CSV files
- `archive/` - duplicates and superseded generated artifacts retained for safety

## Setup

```powershell
py -3 -m pip install -r requirements.txt
```

## Build

```powershell
py -3 build.py --with-tests
```

The primary output is `dist/dashboard.html`. Its large dataset is stored in
`dist/dashboard_data.js`, keeping athlete data out of the HTML while preserving
direct `file://` opening. Keep both files together.

For local HTTP serving:

```powershell
py -3 -m http.server 8000 --directory dist
```

Then open `http://localhost:8000/dashboard.html`.

Use `--legacy-plots` to regenerate the older Excel-based plots and CSV exports.

## Dashboard workspaces

The dashboard preserves all original analyses in four workspaces:

- **Race Explorer:** participation, finish-time distributions, athlete search,
  split profiles, pace/speed and filtered CSV export.
- **Compare Races:** participation, distance-specific finish/split distributions,
  age-group depth and split contributions.
- **Qualification:** race targets, Race Finder, Historical Target Hits and
  Kona Evidence, plus historical slots, cross-race targets, pool pressure,
  percentiles and regression/uncertainty diagnostics. Rankings link to race targets and their cutoff evidence,
  with a return path. Past results and strength profiles remain available
  in expandable detail; browser storage keys are unchanged.
- **Course Analysis:** course/season/conditions factors, adjusted targets,
  GPX cross-checks, repeat-athlete examples and head-to-head comparisons.

Distance, gender and age group remain synchronized, but selectors appear only
beside analyses that use them. One shared year selector works across workspaces,
with All/None/Reset controls; chart year legends are not duplicate controls. Selected
years filter displayed data, aggregates and comparison fits, not published
model training, personal-result calibration or Kona matching evidence.
Race Explorer statistics remain all-athlete statistics.

The shared qualification controls independently select actual historical or
current-scenario rules and a strict, manual, reported, density or 15-absence
cutoff. Manual pool and legacy age-group extra places remain separate. Race
targets show the strict baseline alongside the selected target. Inferred or
reported modes include only compatible covered editions by default. Uncovered
races stay visible and unranked; strict fallback is an explicit opt-in.
Changed allocations/standards, incompatible ranking scopes, different qualifying cycles
and modified courses cannot silently borrow evidence. Reported minute values
and density estimates retain approximate presentation.

The build embeds `src/dashboard_ui.js` into the HTML. No additional runtime
script, framework or server is required beyond the existing sibling data file.

## Refresh historical sources

```powershell
py -3 src/scrape_qualifying_races.py
py -3 src/scrape_age_group_allocations.py
py -3 build.py --with-tests
```

Source refreshes use cached pages unless the scraper is run with its refresh
option. Review source conflicts and missing coverage in `docs/code_review.md`.

## Qualification interpretation

- **Current mode** applies the current age-graded performance-pool system and
  the latest published race allocation to every historical field as a
  counterfactual.
- **Historical mode** uses each race-year's own qualifying cycle: slots, rules,
  and age-grading standard. Legacy age-group allocations come from the
  official results' `Qualified` flags where they cover that cycle; published
  or explicitly labeled reconstructed allocations are fallbacks.
- The performance-pool model reproduces the official qualifier lists exactly;
  the regression suite checks this for every performance-pool race-year.
- Strict cutoffs model entitlement; other cutoff modes are separate assumptions.
  Actual ceremony outcomes depend on attendance, prior qualification, and slot
  acceptance, which are not available in the result files.
- **Historical Target Hits** checks a finish time against selected race-years
  and ranks races by how often that time would have qualified. By default the
  time is treated as a time on an average course and scaled by each
  race-year's course factor.
- **Race Finder** ranks qualifying races by the modelled chance to
  qualify. Optionally add your past results (search your name or enter them
  manually): the dashboard derives your swim, bike, and run ability on an
  average course, shows strengths versus same-level athletes, and predicts
  your time split by split for every past race-year. Results are stored only
  in the browser.
- **Shared cutoff alternatives:** strict allocation (default), manual extra
  places, reported last accepted, density estimate and the 15-absence scan.
  A selected estimate replaces extra places for its matching edition.
  Historical legacy estimates use raw finish times ranked within the actual
  age group, including its winner and its recorded, published or explicitly
  reconstructed allocation. Current gender-pool estimates use the matching
  Kona-cycle standard to convert age-graded time, retaining the winner route.
  Estimates cannot cross ranking scopes, allocation changes or incompatible
  cycles. Unavailable editions are excluded unless strict fallback is enabled.
  Both methods remain unverified heuristics, not acceptance thresholds.
- **Course Analysis** shows course and race-day factors estimated from athletes
  who raced several race-years (`src/course_difficulty.py`), split into course,
  season, and conditions, with the GPX bike model as a cross-check.

## Race comparisons and Kona trace

**Compare Races** includes total finishers, DNS as a percentage of registered
athletes and DNF as a percentage of starters. Only the selected distance's
finish-time distribution is displayed. Qualification plots and historical World
Championship allocations live in **Qualification**, not Compare Races. Shared
year buttons filter plots, regression fits and aggregated summaries.

**Kona Evidence** supports available championship cycles 2017-2019 and 2022-2026,
with a cycle selector and, for legacy rules, an age-group selector. There are no
local 2020/2021 championship starter fields. The local Kona fields contain only
women in 2023/2025 and only men in 2024; the corresponding Nice fields are needed
for the other gender. Missing qualifying results or incompatible allocations
remain explicit coverage gaps. Estimates do not extend to 70.3 races.

The trace links age-group starters (including DNFs, excluding DNS and
professionals) to the selected qualifying-cycle race list, including prior-year
editions. Matching requires normalized full name, gender,
country and compatible age groups. Duplicate identities are excluded.
Unavailable race results are listed in the coverage table.

The default race/gender summary has no attributed cutoff until an athlete's slot
source is reviewed in the starter table. Each athlete can be attributed to one
matched race or marked "Other race / special entry" (including Legacy entries).
Unknown sources and other-route entries do not affect the reviewed pool depth.
Reviews are stored locally in the browser and are assumptions, not proof of
acceptance. An automatic-winner attribution does not set a performance cutoff.

Reported last-accepted age-graded times appear separately in the summary and
chart, with their sources. Austria 2026 men: 08:58, user-reported to the minute.
Hamburg 2026: men 09:03:44 and women 11:04:32, from
[tri-mag.de's 9 June 2026 report](https://tri-mag.de/szene/von-hamburg-nach-hawaii-so-schnell-musste-man-fuer-die-kona-quali-sein/).
These references do not automatically attribute athletes to races or establish
declined-slot counts. The article's gender ranks include podium qualifiers and
must not be substituted for performance-pool ranks.

Two exploratory methods are shown side by side, including for races with
reported cutoffs so their agreement can be checked. Neither replaces a reported
reference or automatically attributes a slot source.

**Density estimate:** an exploratory two-rate Bernoulli model
estimates the pool rank where Kona-starter match density drops. It requires at
least three matched pool athletes and a BIC improvement over a constant-density
model (two additional parameters). Isolated deep matches are background rather
than automatic cutoff evidence. The displayed range combines the central 90%
of normalized profile-likelihood weights with an alternative fit excluding
multi-race matches. Disjoint support ranges trigger a sensitivity warning.
This is a model support range, not a calibrated confidence interval; special
entry, unavailable races and Kona DNS can still bias it. Estimates use the same
data in all evidence modes, are rounded to minutes, never override reported
references and do not establish acceptance or declined-slot counts. Modified
courses are marked; Frankfurt 2026's times are not full-distance targets.

**15-absence estimate:** scan the ordered performance pool immediately after
the last fixed pool slot. A matched Kona starter resets the absence counter.
The first 15 consecutive unmatched athletes stop the scan; the last matched
pool athlete before that run supplies the estimate. The summary reports that
athlete's name, pool rank, age-graded time and the stopping gap's ranks. Matches
after the gap cannot extend the estimate. If no match occurs after the fixed
allocation, the last matched athlete within it is used. No preceding match,
no initial pool slots or an incomplete trailing gap leaves the cutoff unknown.
All compatible Kona-starter matches count, including multi-race candidates;
automatic age-group winners and Kona DNS do not. The `scan_pool_cutoff` helper
accepts a different `consecutive_absences` threshold; the dashboard uses 15.
Missing matches or special-entry routes can make this heuristic stop too early
or too late. Absence does not prove that a slot was not offered or was declined.
The scan is independent of the summary evidence mode, just like the density
estimate. They can disagree; agreement does not establish acceptance either.

Unverified modes retain the deepest candidate times for exploration only. Even
one local race match can belong to someone who qualified at an unavailable race
or through a special route, so it cannot establish an observed qualifying time.

Conditional skipped places are
`max(0, deepest attributed pool rank - initial pool slots)`, not a count of
people who declined. The estimate assumes the attributed slot source is correct,
age-group winners accepted and gender pools stayed fixed. Prior qualification,
automatic-slot roll-downs, reallocations and accepted slots followed by Kona DNS
can change it. Actual ceremony cutoffs require slot-acceptance evidence.
