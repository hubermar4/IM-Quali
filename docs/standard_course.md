# Standard course: converting race times to a common reference

The standard course is a theoretical construct that makes race-years comparable.
A split or finish time raced on any course, in any season, under any conditions
is converted to the time the same athlete would have needed on the standard
course. It is used by the Qualification workspace ("Your time", "Race
difficulty", "Qualification targets", "Where to qualify") and by the Course
Analysis workspace.

## Definition

| Property | Full distance (IRONMAN) | Half distance (IRONMAN 70.3) |
|---|---|---|
| Swim | 3.8 km | 1.9 km |
| Bike | 180 km | 90 km |
| Run | 42.2 km | 21.1 km |
| Course profile | The average qualifying course | The average qualifying course |
| Season and conditions | Average qualifying race-year | Average qualifying race-year |
| Athlete | Age-graded with the current Kona / 70.3 Standard, first appearance | Same |

Distances are the constants `FULL_DISTANCE` and `HALF_DISTANCE` in
[build_dashboard.py](../src/build_dashboard.py). The two distances are always
modelled separately; a full-distance time is never converted with a 70.3 factor.

"Average" means the geometric mean over all qualifying race-years of that
distance: the standard course has factor 1.000 by construction, a factor of
1.05 means 5% slower than the standard course. Factors are multiplicative
because course and conditions slow slower athletes by more seconds.

Two approaches convert a raced time to the standard course. They answer the
same question with different evidence.

| | Approach A: repeat athletes | Approach B: GPX bike model |
|---|---|---|
| Idea | The same athlete is timed on several courses; the differences are the course | A reference rider is simulated over the bike GPX track |
| Splits covered | Swim, bike, run, overall | Bike only |
| Captures | Course, season, weather, water temperature, run profile | Bike terrain only |
| Needs | Results of athletes racing several race-years | One GPX track per race |
| Code | [course_difficulty.py](../src/course_difficulty.py) | [gpx_course_model.py](../src/gpx_course_model.py), [build_gpx_report.py](../src/build_gpx_report.py) |
| Role in the dashboard | **Used for standard-course conversions**; T1/T2 factors are diagnostic only | Cross-check ("Bike course check: GPX model vs. athlete data") |

## Approach A: repeat athletes (empirical)

**Idea.** An athlete's ability cancels out when the same athlete is compared with
themselves on different courses. What remains is the race-year effect.

**Model** (per split: swim, T1, bike, T2, run, overall):

```
log(age-graded time) = athlete + race-year effect + returning effect
```

1. **Matching.** Athletes are identified across race-years of the same distance
   by normalised name (accents removed, tokens sorted), gender and country
   (`identity_key`). An identity is dropped when it appears twice in the same
   race-year or when its age groups imply inconsistent birth years
   (`repeat_athlete_records`). Roughly 41,000 records remain for full distance
   and 1,600 for 70.3 (build of 2026-09-28).
2. **Age grading.** Times are multiplied by the Kona / 70.3 Standard ratio of the
   athlete's division before fitting, so ageing between appearances does not
   bias later editions. Divisions without a standard are excluded.
3. **Returning effect.** Athletes are about 1.0% faster on later appearances
   (flat after the second). Without this term, the gain is booked to later
   race-years and makes 2024-2026 look about 1.5% easier. The standard course
   is defined for an athlete's *first* appearance.
4. **Fit.** `fit_race_year_effects` uses alternating means (fixed effects). The
   race-year effects are centred to zero over the baseline race-years
   (all qualifying races), which fixes the standard course. After the first fit,
   records with residuals beyond 4 robust standard deviations (mechanicals,
   walked marathons) are trimmed and the model is refitted.
5. **Factors.** `estimate_course_factors` returns a multiplicative factor
   `exp(effect)` per race-year and split, with standard errors (typically
   0.1-0.3% per race-year) and fit diagnostics. T1/T2 factors are estimated
   where transition times are available, but are used only for Course Analysis
   diagnostics; standard-course transitions remain median-based.
6. **Course and season.** `course_and_season_effects` splits the race-year
   factor into `course x season x conditions` (log-additive, season effects
   centred over the baseline). The season effect is almost entirely bike
   (+1.7% in 2017 to -2.0% in 2026, equipment progress). The *course* factor is
   the typical factor of a course in an average season.

**Excluded race-years.** Shortened or modified courses never enter the fit:
Calella-Barcelona 2021 (swim cancelled for most), Switzerland Thun 2021 (swim
about 30% short), Vitoria-Gasteiz 2021 and Leeds 2026 (swim cancelled),
France 2019 (shortened run) and Frankfurt 2026 (shortened bike and run). See `MODIFIED_COURSES` in
[build_dashboard.py](../src/build_dashboard.py). Non-qualifying races
(Kona, Nice) are fitted but do not define the baseline.

**Conversion.** For one split, with `s` the age-group standard ratio, `f` the
race-year factor of the race raced, `r` the returning factor (1 for a first
appearance):

```
standard-course time = raw time x s / (f x r) / s_target   (per split)
```

`s_target` brings the age-graded value back to the athlete's own age group. The
dashboard averages the converted splits geometrically over an athlete's past
races (dropping outliers beyond the fit's trim limit) to get an athlete's level
per split, and sums swim + bike + run + typical transitions to a standard
course finish time (`athleteLevelRows`, `currentAbility` in
[build_dashboard.py](../src/build_dashboard.py)). Transitions are the median
over qualifying race-years, scaled by the athlete's own transition ratio.

To compare races (not people), the race-year factor `f` is used as raced; the
season-adjusted course factor shows the course alone.

**Distance deviations.** Course factors absorb real course lengths: a 176 km
bike makes a course look faster than a 180 km one. This is intended for the
conversion (the athlete really rode less), and the reason the GPX track length
is reported next to the difficulty factor.

**Strengths and limits.** Covers every split and all conditions; no physical
assumptions. Needs overlapping athletes, so isolated or new races rely on few
connections; sampling error is shown per race-year.

## Approach B: GPX bike model (physical)

**Idea.** Simulate the same reference rider over the bike track and compare with
the time over a flat route of equal length.

**Reference rider** (`Rider` in [gpx_course_model.py](../src/gpx_course_model.py)):
82 kg rider plus bike, 200 W on flat terrain, +20% power on climbs and -25% on
descents (threshold +-0.5% grade), CdA 0.25 m², rolling resistance 0.004,
drivetrain efficiency 97.5%, air density 1.225 kg/m³, no wind. The dashboard
uses 25 m resampling and 100 m elevation smoothing.

**Steps** (`simulate`):

1. Read the GPX track and resample it to equal spacing; smooth elevation while
   keeping net elevation change.
2. For every segment solve the speed at which crank power equals the target
   power for its grade (`solve_speed`, bisection).
3. Sum segment times: `t_observed`. Compute `t_flat`, the same distance at flat
   grade.
4. Course difficulty factor `CDF = t_observed / t_flat`.

CDF values of the supplied tracks range from 1.014 (Hamburg) to 1.176
(France). See [dist/gpx_track_statistics.md](../dist/gpx_track_statistics.md)
(generated by `python src/build_gpx_report.py`).

**Conversion to the standard course (proposed, not implemented).** CDF is a ratio on the supplied length, so
it measures terrain only. A raced bike split is converted by replacing the
terrain of the raced course with the terrain of the standard course and the
distance with 180 km:

```
standard bike time = raced bike time x (180 / track length) x (CDF_standard / CDF_race)
```

`CDF_standard` is the geometric mean of the CDFs of all compared qualifying
courses, the same reference the dashboard uses for its check. The first factor
fixes distance deviations of the supplied track (for example France 170.8 km,
Barcelona 175.5 km); only apply it when the track is believed complete.

**Status.** Approach B is a cross-check: the dashboard plots the CDF-based bike
difficulty against the season-adjusted bike course factor of Approach A. The
two rank flat and rolling courses alike, but the GPX model underestimates hilly
courses by about half (Leeds +7% vs. +16%, Wales +8% vs. +16%) and rates
Calella-Barcelona about 7 points slower than the athletes did. Neither model
covers wind, surface, technical sections, drafting, or the swim and run.
Earlier, a constant additive GPX correction was used; it was replaced because
course effects are multiplicative, ignore swim and run, and were invalid for
France. Use Approach B as a qualitative check, not for qualification targets.

Track caveats:

- France: the corrected 2026-09-29 track has +2,489 m and no grade
  discontinuities; used.
- Lanzarote: start and finish are 50 m apart but the finish reads 192 m against
  17 m (altimeter drift on the last 12 km); used as supplied (course factor
  1.148, 1.143 when corrected).
- GPX tracks only exist for full-distance races, not for 70.3.

## Where it is used

| Use | Approach | Code |
|---|---|---|
| Athlete level on a standard course from past results | A | `athleteLevelRows`, `currentAbility` |
| Race-year and course factors (overall, swim, bike, run); T1/T2 diagnostics | A | `load_course_factors` |
| Race targets "as raced" vs. "on a standard course" | A | `courseFactor`, `courseEffect` |
| Cross-race ranking and predicted margin | A | `renderEasiest` |
| Bike course check | B vs. A | `bike_course_correction`, `experimentalGpxChart` |

## Tests

[test_course_difficulty.py](../tests/test_course_difficulty.py) and
[test_gpx_course_model.py](../tests/test_gpx_course_model.py) cover both
approaches.

## Open points

- Approach B's distance and terrain conversion is documented here but is not
  wired into the dashboard's conversions.
- Swim and run have no physical model; their standard-course times rely on
  Approach A alone.
- The standard course profile changes slightly with each added race or season
  because it is the average of the fitted qualifying race-years.
