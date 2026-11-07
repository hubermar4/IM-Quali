# IRONMAN qualification analysis

Historical IRONMAN result analysis, qualification estimates, GPX bike-course
normalization, and a generated interactive dashboard.

## Layout

- `src/` - maintained Python source; the dashboard is assembled from `dashboard_template.html`, `dashboard.css`, `dashboard_app.js` and `dashboard_ui.js`
- `tests/` - qualification and GPX regression tests
- `data/race_history/` - race result CSV files grouped by event
- `data/gpx_tracks/` - bike-course GPX inputs
- `data/cache/` - cached Coach Cox source pages
- `data/reference/` - editable reference data (slots, events, standards, rule sets, modified courses, reported cut-offs, announced race calendar)
- `data/derived/` - reproducible extracted qualification datasets
- `docs/` - qualification rules and source documentation
- `dist/` - generated dashboard, data payload, and reports

## Setup

```powershell
py -3 -m pip install -r requirements.txt
```

## Build

```powershell
py -3 build.py --with-tests
```

The primary output is `dist/dashboard.html`. Its datasets are stored separately
in `dist/dashboard_data_im.js` and `dist/dashboard_data_703.js`, keeping athlete
data out of the HTML and each generated file below GitHub's file-size limit while
preserving direct `file://` opening. Keep all three files together. The build
also creates `dist/index.html`, which redirects to the dashboard for static-site
hosts.

## GitHub Pages

The GitHub Actions workflow builds the dashboard and deploys `dist/` to GitHub
Pages on pushes to the repository's default branch, or when manually dispatched.
To enable it once, open the repository's **Settings → Pages** and set **Build
and deployment → Source** to **GitHub Actions**. The deployed site is public when
the repository and its Pages site are public; do not put private data or secrets
in the published inputs or generated artifacts.

For local HTTP serving:

```powershell
py -3 -m http.server 8000 --directory dist
```

Then open `http://localhost:8000/dashboard.html`.

## Dashboard workspaces

The dashboard preserves all original analyses in four workspaces:

- **Race Explorer:** participation, finish-time distributions, athlete search,
  split profiles, pace/speed and filtered CSV export.
- **Compare Races:** participation, distance-specific finish/split distributions,
  age-group depth and split contributions.
- **Qualification:** a guided five-step flow.
  1. *You* - shared distance, gender and age group.
  2. *Your time* - one finish time on a standard course (average qualifying
     race-year and conditions), typed or derived split by split from past
     results, with the strength profile. Every later step uses it.
  3. *Race difficulty* - each qualifying race as raced and converted to a
     standard course: course effects (overall/swim/bike/run), race-year
     factors, age-group medians and winners, and your predicted time.
  4. *Qualification targets* - for the selected race: slots per year
     (automatic + gender pool, or age-group slots), strict target as raced and
     on a standard course, reported/scan/density roll-down estimates with the
    modelled scan depth, and your predicted margin. The method comparison,
    slot what-ifs and the World Championship start-list evidence
     (Kona + Nice) are expandable sections.
  5. *Where to qualify* - the current-rules race ranking by estimated chance, including the
     target on a standard course; historical target hits and cross-race charts
     are expandable sections.
  Rankings link to race targets and their cutoff evidence, with a return
  path. Browser storage keys are unchanged.
- **Course Analysis:** course/season/conditions factors, adjusted targets,
  GPX cross-checks, repeat-athlete examples and head-to-head comparisons. Its
  only analysis inputs are distance, top-finisher percentage and the shared
  race-year selection; split analysis is fixed to overall and field strength
  uses both genders and all age groups.

Distance, gender and age group remain synchronized, but selectors appear only
beside analyses that use them. One shared year selector works across workspaces,
with All/None/Reset controls; chart year legends are not duplicate controls. Selected
years filter displayed data, aggregates and comparison fits, not published
model training, personal-result calibration or Kona matching evidence.
Race Explorer statistics remain all-athlete statistics.

Qualification Targets can use historically correct rules and data or current
performance-pool rules applied to historical results. Where to Qualify always
uses current rules. Both share a cutoff-method selector: strict allocation,
rank-based roll-down factor, matched-slot cutoff, match-density estimate, or
15-absence gender-pool scan. Reported last accepted remains separate evidence.
Density and scan require an original P1 race and compatible same-cycle matches.
The matched-slot cutoff also covers known R1-R4 race-years: current rules use
the re-ranked same-cycle roster; historical rules take the Nth matched rank in
the actual age-group ranking (N = age-group slots, a matched winner counts).
Unresolved cycles support no match-based estimate, and legacy races no strict
fallback. Targets, Race Finder and
Historical Target Hits show per-race-year evidence and mark missing or
incompatible years. Strict fallback, when enabled, is labelled as such and is
never presented as borrowed estimate evidence. Changed
allocations/standards, incompatible ranking scopes and different qualifying
cycles cannot silently borrow evidence; modified-course comparisons remain
excluded. Reported minute values and density estimates retain approximate
presentation.

**Shareable links:** the address bar's `#…` part records the current view, race,
distance, gender, age group, qualification approach, cutoff method, roll-down
factor and strict-fallback setting. **Copy link** (beside the year buttons)
copies it; opening the link restores the same analysis. Year selections and
personal results stay in the browser and are not part of the link.

The build inlines the dashboard template, CSS and JS files from `src/` into the HTML. No additional runtime
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

- **Current performance-pool mode** applies the current age-graded
  performance-pool system and latest published race allocation to every
  historical field as a counterfactual, including old age-group-era results.
- **Historical mode** uses each race-year's own qualifying cycle: slots, rules,
  and age-grading standard. Legacy age-group allocations come from the
  official results' `Qualified` flags where they cover that cycle; published
  or explicitly labeled reconstructed allocations are fallbacks.
- The performance-pool model reproduces the official qualifier lists exactly;
  the regression suite checks this for every performance-pool race-year.
- Strict allocation models entitlement. The rank factor is a hypothetical
  allocation scenario; reported cutoffs, P1 density estimates and P1 absence
  scans remain separate evidence-based approaches. Actual ceremony outcomes
  depend on attendance, prior qualification and slot acceptance, which are not
  available in the result files.
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
- **Cutoff approaches:** strict allocation, rank factor, P1 match density and
  P1 15-absence scan are compared alongside separately reported last-accepted
  evidence. For `f >= 0`, the factor targets rank
  `slots + floor(slots * f + 0.5)`; 30 slots with factors 0, 1 and 2 target
  ranks 30, 60 and 90. The default is 0, values above 2 are allowed, and a
  rank beyond available finishers has no extrapolated time. The P1 gender pool
  excludes automatic winner slots and retains the separate winner route;
  historical legacy scenarios use raw age-group ranks and their actual slots.
  The factor is not calibrated by the old time-multiplier model or its backtest.
  For actual P1 race-years, objective A uses the compatible championship
  roster re-ranked under current rules; objective B uses its historical pool,
  allocation and standard. Legacy and unknown races never supply pool-match
  estimates, even when strict fallback is enabled.
  Reported cutoffs appear only when documented for the same scope and cycle.
  Estimates cannot cross ranking scopes, allocation changes or incompatible
  cycles. Missing or incompatible editions are marked individually; strict
  fallback is explicitly labelled when enabled. Density and scan results remain
  unverified heuristics, not acceptance thresholds.
  The exploratory density boundary compares observed Kona-starter match rates
  across ranking positions with a constant-rate model, fits a two-rate breakpoint,
  requires at least three matches before it and positive BIC improvement after
  the penalty, and reports the best breakpoint with weighted 5%-95% rank/time
  support and sensitivity to single-race matches. It is not evidence of actual
  acceptance or declines. A scan cutoff requires a matched starter beyond the
  initial allocation before its absence window; Race Targets never display
  density or scan targets faster than strict allocation.
- **Course Analysis** shows course and race-day factors estimated from athletes
  who raced several race-years (`src/course_difficulty.py`), split into course,
  season, and conditions, with the GPX bike model as a cross-check.

## Race comparisons and Kona trace

**Compare Races** includes total finishers, DNS as a percentage of registered
athletes and DNF as a percentage of starters. Only the selected distance's
finish-time distribution is displayed. Qualification plots and historical World
Championship allocations live in **Qualification**, not Compare Races. Shared
year buttons filter plots, regression fits and aggregated summaries.

**World Championship evidence** (step 4) supports available championship cycles
2017-2019 and 2022-2026, with a cycle selector; legacy cycles use the shared
age group. There are no local 2020/2021 championship starter fields. In
2023-2025 the championship was split between Kona and Nice
(`data/race_history/IM_Nice_WC`: men 2023/2025, women 2024); both start lists
are combined per championship year, so both genders are covered from 2022 on.
Nice also appears as a non-qualifying race in Race Explorer and Compare Races.
Missing qualifying results or incompatible allocations remain explicit
coverage gaps. Match-based estimates do not extend to 70.3 races. Scan depth
in step 4 is the estimated rank minus allocated slots, not a count of declines.

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

Strict allocation and rank factor are available for legacy and P1 races;
P1 density and scan estimates and reported last-accepted evidence are shown
separately where compatible. A matched starter does not prove acceptance, and
an unmatched rank does not prove absence or a decline.

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

**P1 absence scan:** scan the compatible gender-pool ranking immediately after
the last fixed allocation. A matched championship starter resets the counter;
15 consecutive unmatched ranks stop the scan. The last matched athlete before
that run supplies the estimate only if that match is beyond the allocation.
No post-allocation match, no initial slots or an incomplete trailing gap leaves
the cutoff unknown. All compatible starter matches count, including multi-race
candidates; automatic age-group winners and championship DNS do not.
Missing matches or special-entry routes can make this heuristic stop too early
or too late. Absence does not prove that a slot was not offered or was declined.
When a rank and positive initial slot count exist, the dashboard also plots the
assumption-derived percentage `(estimated rank - initial slots) / estimated
rank * 100` within the matching scope. This is a model-derived roll-down rate, not an
observed decline or acceptance rate. The scan is independent of reviewed
summary attribution, just like the density estimate. They can disagree;
agreement does not establish acceptance either.

Unverified modes retain the deepest candidate times for exploration only. Even
one local race match can belong to someone who qualified at an unavailable race
or through a special route, so it cannot establish an observed qualifying time.

Conditional skipped places are
`max(0, deepest attributed pool rank - initial pool slots)`, not a count of
people who declined. The estimate assumes the attributed slot source is correct,
age-group winners accepted and gender pools stayed fixed. Prior qualification,
automatic-slot roll-downs, reallocations and accepted slots followed by Kona DNS
can change it. Actual ceremony cutoffs require slot-acceptance evidence.
