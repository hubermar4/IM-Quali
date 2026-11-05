# Historical IRONMAN age-group qualification rules, 2017-2027

This is the single reference for which qualification rule set applied in each
qualification cycle covered by the race data (2017-2027). It replaces the former
`legacy_qualification_rules.md`, which only described the pre-2026 era. The
current published rules are kept verbatim in
[official_qualification_rules.md](./official_qualification_rules.md).

## How to read this document

- **Qualification cycle N** is the qualifying season for the World
  Championship of year N. It starts in late August of year N-1 and ends in
  mid/late August of year N (Coach Cox windows: 2027 cycle from 22 Aug 2026;
  2026 cycle 16 Aug 2025-16 Aug 2026; 2025 cycle 17 Aug 2024-17 Aug 2025; and
  so on). A race in late August can offer slots for two consecutive cycles.
- A **race-year** belongs to the cycle in which it was held, not to the cycle
  with the same number. IRONMAN Austria 2021 (September) is a 2022-cycle race;
  IRONMAN Austria 2017 (June) is a 2017-cycle race.
- The dashboard always uses the cycle of the race-year (see
  [Dashboard mapping](#dashboard-mapping)).
- **Confidence** states how well the rule is documented:
  *official* (ironman.com), *observed* (reproduced from race data or published
  race-day allocations), *inferred* (consistent with data, no official text).

## Rule sets

| ID | Name | Cycles | Summary |
|---|---|---|---|
| **R1** | Age-group allocation, proportional | 2017-2018 (start) | Fixed slots per race; every represented age group gets 1 slot; the rest is split by each age group's share of race-day starters (largest-remainder). Slots go in finishing order within the age group; declines roll down inside the age group. |
| **R2** | Age-group allocation, D'Hondt | 2018 (during) - 2022 | Same principles as R1, but integer allocation follows the D'Hondt highest-averages method, which gives large age groups slightly more slots. |
| **R3** | Age-group allocation, gender-neutral quota, split championship | 2023 | R2 allocation per race, but the World Championship is split into a men's and a women's race (Nice / Kona). |
| **R4** | Age-group allocation, explicit gender quotas | 2024-2025 | R2 allocation applied separately to a published men's quota and women's quota per race. |
| **P1** | Performance pool, gender-split pools | 2026-2027 | Age-group winners get automatic slots (roll to 2nd, 3rd). Remaining slots form a performance pool split by male/female eligible starter representation; athletes are ranked within gender by age-graded time (Kona Standard / IRONMAN 70.3 Standard). |

R1 and R2 are the same published policy (see
[Published procedure](#published-procedure-r1-r4)); IRONMAN never published the
integer formula, so the split between them is an observation, not an official
change.

## Cycle overview

| Cycle | Qualifying window | Full-distance World Championship | Full-distance rule set | Typical slots per race | Races / slots (Coach Cox) |
|---|---|---|---|---|---|
| 2017 | 28 Aug 2016-27 Aug 2017 | Kona, Oct 2017 | R1 | 40 (30-75) | 46 / 1961 |
| 2018 | 27 Aug 2017-19 Aug 2018 | Kona, Oct 2018 | R1 -> R2 | 40 (30-80) | 46 / 1946 |
| 2019 | 26 Aug 2018-18 Aug 2019 | Kona, Oct 2019 | R2 | 40 (30-80) | 44 / 1916 |
| 2020 | 25 Aug 2019-Oct 2020 | Cancelled (COVID-19); qualifiers could defer to 2021 or 2022 | R2 | 40 (30-75) | 24 / 1006 |
| 2021 | Sep 2020-22 Aug 2021 | St George, 7 May 2022 (postponed from Kona) | R2 | 40 (25-150) | 20 / 1095 |
| 2022 | 22 Aug 2021-21 Aug 2022 | Kona, 6 Oct (women) and 8 Oct 2022 (men) | R2 | 45 (40-80) | 51 / 2492 |
| 2023 | Aug 2022-20 Aug 2023 | Nice 10 Sep (men), Kona 14 Oct (women) 2023 | R3 | 55 (40-100) | 44 / 2362 |
| 2024 | 20 Aug 2023-18 Aug 2024 | Nice (women), Kona (men) 2024 | R4 | e.g. 35 M / 40 W up to 75 M / 75 W | 35 / 2583 |
| 2025 | 17 Aug 2024-17 Aug 2025 | Nice (men), Kona (women) 2025 | R4 | 65 M / 35 W, 65 M / 20 W from Aug 2025 | 40 / 4053 |
| 2026 | 16 Aug 2025-16 Aug 2026 | Kona, Oct 2026 (men and women together) | P1 | 40 (55-60 at large races) | 41 / 1953 |
| 2027 | from 22 Aug 2026 | Kona 2027 | P1 | 45-55 | in progress |

Race and slot counts come from
[coachcox_qualifiers_2017_2026.md](../data/derived/coachcox_qualifiers_2017_2026.md).
Slot totals for the 2020-2023 cycles include slots that were not accepted
(Coach Cox reports 91-97% of the 2022 and 2023 slots as confirmed).

## Published procedure (R1-R4)

1. Each qualifying race received a fixed number of World Championship slots.
2. Only age groups represented by at least one eligible starter participated.
3. Every represented age group received a minimum of one slot.
4. The remaining slots were apportioned by each age group's share of eligible
   starters. Men and women therefore competed for slots through their own
   age-group categories, not through a cross-age ranking.
5. The allocation was based on race-day starters, not registrations or
   finishers.
6. Slots were offered in finishing order within the age group. A declined slot
   rolled down inside that age group. Cutoff estimates that assume no declines
   use the finishing time at the allocated slot rank.

Integer allocation:

- **R1**: one slot per represented age group, then the remainder by largest
  remainder. Reproduces the published Austria 2018 40-slot allocation from the
  local starter data.
- **R2**: D'Hondt. Published race-day allocations during 2018 (e.g. IRONMAN
  Texas 2018, 80 slots) match D'Hondt, not R1. IRONMAN never announced the
  change; the exact race at which it happened is unknown. *Observed.*

## Cycle details

### 2017 cycle (R1)

- World Championship: Kona 2017, single combined championship.
- Quota: combined total per race (typically 40; 75 at the largest races,
  25-30 in Asia-Pacific).
- Age-group allocation published per race by Coach Cox for Austria 2017.
- Data race-years: Austria 2017. Kona 2017 results are the championship
  itself, not a qualifier.

### 2018 cycle (R1, changing to R2 during the cycle)

- Kona 2018, combined championship, combined quota (40; 80 at the largest
  races such as Frankfurt).
- Use the race's published allocation; reconstruct only if missing.
- Data race-years: Austria 2018, France 2018, Frankfurt 2018.

### 2019 cycle (R2)

- Kona 2019, combined championship, combined quota (40; 80 at the largest
  races such as Frankfurt).
- Data race-years: Austria 2019, France 2019 (shortened run), Frankfurt 2019,
  Italy 2018, Kalmar 2019, Copenhagen 2019.

### 2020 cycle (R2, COVID-19 disruption)

- The 2020 championship was cancelled. Qualifiers could defer to 2021 or 2022
  (Wikipedia, IRONMAN announcements). Many races were also cancelled, hence
  24 listed races.
- Data race-years: Barcelona 2019, Italy 2019, Tallinn 2020.

### 2021 cycle (R2, COVID-19 disruption)

- The 2021 championship was held in St George, Utah on 7 May 2022 instead of
  Kona. Only 20 races ran in the cycle; quotas were unusually uneven (25-150).
- Data race-years: Frankfurt 2021, Copenhagen 2021, Lanzarote 2021 (100 slots).
- Official `Qualified` flags in the results are the preferred allocation.

### 2022 cycle (R2)

- Kona 2022 was raced over two days (women 6 Oct, men 8 Oct), still a
  combined quota per race (usually 45; 40 or 75-80 at some races).
- The 2021-cycle rescheduled qualifiers and 2022-cycle qualifiers shared
  several races, so 2021 and 2022 race-years mix (Austria 2021 and Austria 2022
  are both 2022-cycle races).
- Data race-years: Austria 2021/2022, Barcelona 2021, France 2021/2022,
  Frankfurt 2022, Hamburg 2021/2022, Italy 2021, Kalmar 2022, Copenhagen 2022,
  Lanzarote 2022, Portugal 2021, Tallinn 2022, Thun 2021/2022,
  Vitoria 2021/2022.

### 2023 cycle (R3)

- First split championship: Nice (men, 10 Sep 2023) and Kona (women,
  14 Oct 2023).
- Quota remained a combined number per race (55 typical; Frankfurt 100).
  Late-season races (Aug 2023) already list men-only slots for Nice.
- Data race-years: Austria 2023, Barcelona 2022, France 2023, Frankfurt 2023
  (99 published age-group slots vs 100 listed), Hamburg 2023, Italy 2022,
  Kalmar 2023, Copenhagen 2023, Lanzarote 2023, Portugal 2022, Tallinn 2023,
  Thun 2023, Vitoria 2023, Wales 2022.

### 2024 cycle (R4)

- Nice (women) and Kona (men) 2024. Each race publishes separate men's and
  women's slots (e.g. Austria 50 M / 50 W, Frankfurt 75 M / 75 W, Kalmar and
  Copenhagen 35 M / 35 W, Barcelona 25 M / 50 W).
- Data race-years: Austria 2024, Barcelona 2023, France 2024, Frankfurt 2024,
  Hamburg 2024, Italy 2023, Kalmar 2024, Copenhagen 2024, Lanzarote 2024,
  Portugal 2023, Thun 2024, Vitoria 2024, Wales 2023.
- Frankfurt, Kalmar and Copenhagen 2024 flag only the 2025-cycle women's
  slots, so their 2024-cycle allocation is reconstructed.

### 2025 cycle (R4)

- Nice (men) and Kona (women) 2025. Separate quotas, typically 65 M / 35 W;
  from Sweden and Copenhagen 2025 (16-17 Aug) 65 M / 20 W. Largest races
  reached 85 M / 65 W; some races offered women-only slots (35 W) because the
  2024 Kona men's race was already full.
- Data race-years: Austria 2025, Barcelona 2024, France 2025, Frankfurt
  2024/2025, Hamburg 2025, Italy 2024, Kalmar 2024/2025, Copenhagen 2024/2025,
  Lanzarote 2025, Leeds 2025, Portugal 2024, Tallinn 2024, Vitoria 2025,
  Wales 2024.

### 2026 cycle (P1)

- First cycle under the performance-pool system (introduced July 2025, first
  races from late August 2025). Kona 2026 is the first championship since 2022
  with men and women racing together.
- Slots are a combined number per race (40 typical; 55-60 at large races), but
  the performance pool is split by gender (see below).
- **Mid-cycle change**: The first races used one combined performance pool,
  which gave about 96% of pool slots to men. In November 2025 (effective from
  IRONMAN Arizona, with retroactive re-allocation of earlier races) IRONMAN
  split the pool by gender in proportion to eligible age-group starters and
  kept age-group-winner roll-down within gender. The dashboard applies the
  gender-split rule to the whole cycle, because the retroactive result is the
  final official outcome. *Official.*
- Age grading: Kona Standard and IRONMAN 70.3 Standard from the IRONMAN
  qualification page; the 70.3 2026-cycle table differs from the 2027 table
  in every age group (see
  [qualification_703.py](../src/qualification_703.py)).
- Data race-years: Austria 2026, Barcelona 2025, California 2025, Chattanooga
  2025, Cozumel 2025, Florida 2025, Frankfurt 2026 (shortened bike
  and run), Hamburg 2026, Italy 2025, Kalmar 2025/2026, Copenhagen 2025/2026,
  Lanzarote 2026, Leeds 2026 (swim cancelled), Portugal 2025, Tallinn 2025,
  Texas 2026, Thun 2025/2026, Vitoria 2026, Wales 2025. California and
  Chattanooga 2025 (55 each), Cozumel 2025 (100), Florida 2025 (55) and Texas
  2026 (75) come from Coach Cox; the `Qualified` flags match these totals.
  *Official.*
- California, Chattanooga, Cozumel and Florida 2022-2024 and Texas 2022-2025
  are R-era race-years; their Coach Cox cycle is unique and their `Qualified`
  flags fill the published totals, so the official allocation from the
  results is used.
- 70.3 data race-years: Zell am See 2025 (35/35), Valencia 2026 (35/35),
  Venice-Jesolo 2026, Mallorca 2026 and Kraichgau 2026 (30/30 each); official
  ironman.com 2026 qualifying-events allocations, confirmed by the `Qualified`
  flags. The 70.3 World Championship Nice 2026 (men and women in separate
  files) is the matching start list for this cycle.

### 2027 cycle (P1)

- Same system as 2026. The Kona Standard table is identical to the 2026
  table; the IRONMAN 70.3 Standard table was updated.
- Published slots: Barcelona 55, California 55, Chattanooga 55, Cozumel 100,
  Florida 55, Italy 55, Portugal 55, Tallinn 45, Wales 50; 70.3 Zell am See,
  Krakow, Tallinn, Portugal-Cascais and Porec 25 M / 25 W, Italy
  Emilia-Romagna 30 M / 30 W.
- Data race-years: California 2026, Chattanooga 2026, Italy 2026, Tallinn
  2026, Wales 2026; 70.3 Zell am See, Krakow, Tallinn, Emilia-Romagna,
  Cascais and Porec 2026 (no Coach Cox entry yet; official ironman.com
  allocations are used and match the `Qualified` flags). No 2027 championship
  start list exists yet.

## IRONMAN 70.3

### Cycle mapping and championships

Race-year to cycle mapping and published slot totals come from the Coach Cox
70.3 qualification pages (`data/cache/CoachCoxHalfQualificationPages/`,
`coachcox_703_name` in `data/reference/events.json`), complemented by the
official ironman.com 2026/2027 lists. Coach Cox lists the 2024-2027 cycles
completely; its 2022 and 2023 cycle pages are nearly empty, so race-years of
those cycles (Zell am See 2021/2022, Kraichgau 2022, Venice-Jesolo 2022/2023,
Emilia-Romagna and Poznan 2022) have no established cycle and stay
unavailable in historical mode. *Official* where listed. The supplied
Kraichgau 2023 file is excluded (`data/excluded/`): 155 of 157 athletes also
in the 2022 results appear in a younger age group, so it is an older edition.

| Cycle | Championship | Rules | Data race-years with a known cycle |
|---|---|---|---|
| 2022 | St. George, USA (Oct 2022) | R | none |
| 2023 | Lahti, Finland (Aug 2023) | R | none |
| 2024 | Taupo, New Zealand (Dec 2024) | R | Emilia-Romagna 2023 (40), Poznan 2023 (30), Zell am See 2023 (40), Venice-Jesolo 2024 (45), Kraichgau 2024 (55) |
| 2025 | Marbella, Spain (Nov 2025) | R | Belgrade 2024 (50), Emilia-Romagna 2024 (50), Poznan 2024 (40), Zell am See 2024 (50), Venice-Jesolo 2025 (50), Kraichgau 2025 (50) |
| 2026 | Nice, France (Sep 2026) | P1 | Belgrade, Emilia-Romagna, Zell am See 2025 (35/35), Poznan 2025 (30/30), Valencia 2026 (35/35), Venice-Jesolo, Mallorca, Kraichgau 2026 (30/30) |
| 2027 | Chattanooga, USA (2027) | P1 | Krakow, Tallinn, Poznan, Zell am See, Belgrade, Cascais, Porec 2026 (25/25), Emilia-Romagna 2026 (30/30) |

In every listed race-year the `Qualified` flags fill the published total, so
R-era race-years use the official allocation from the results. Each
championship's men's and women's results are separate files in one folder
per venue (`IM_703_<Venue>_WC`).

### Zell am See flags

The 70.3 World Championship has been run as two separate days for men and
women since 2021 and always with separate men's and women's quotas. Rule
evidence for the Zell am See race-years comes from the `Qualified` flags in
the results files:

| Race-year | Flagged qualifiers | Men / Women | Rule set | Source |
|---|---:|---|---|---|
| 2021 | 80 | 40 / 40 | Age-group allocation (R2) | Results flags, *observed* |
| 2022 | 80 | 40 / 40 | Age-group allocation (R2) | Results flags, *observed* |
| 2023 | 40 | 29 / 11 | Age-group allocation (R3); gender split by starters | Results flags, *observed* |
| 2024 | 50 | 38 / 12 | Age-group allocation (R4); gender split by starters | Results flags, *observed* |
| 2025 (Aug/Sep 2025, 2026 cycle) | 70 | 35 / 35 | P1, 2026-cycle 70.3 Standard | ironman.com, *official* |
| 2026 (2027 cycle) | 50 | 25 / 25 | P1, 2027-cycle 70.3 Standard | ironman.com, *official* |

For 2021-2024 the flags do not state the formula. The unequal gender split in
2023 and 2024 is consistent with a gender quota proportional to race-day
starters (*inferred*); in 2021 and 2022 the quota was equal.

## Dashboard mapping

- **Historical mode** uses the rule set of the race-year's cycle.
  - A unique supported cycle is required. If the cycle cannot be established,
    or the performance-pool standard for that cycle is unavailable, the
    historical target is unavailable; current standards are not substituted.
  - Cycles 2017-2025 (R1-R4): age-group allocation; rank athletes inside their
    age group by raw finish time; the Nth finisher is the strict no-roll-down
    cutoff.
  - Allocation source order: official `Qualified` flags when they cover 90-100%
    of the cycle's slots; then the race page's published allocation
    ([coachcox_age_group_allocations.json](../data/derived/coachcox_age_group_allocations.json));
    then a labelled reconstruction (R2 formula).
  - Cycles 2026-2027 (P1): performance-pool engine with that cycle's standard;
    a race-page age-group table must not override it.
- **Current mode** applies the latest published race allocation and standards
  to every historical field (a counterfactual).
- Match-density and 15-absence scan estimates require an actual P1 race and
  compatible same-cycle gender-pool matches. They are unavailable as
  qualification methods for R1-R4 races and unresolved cycles. The matched-slot
  cutoff is also available for race-years with a known R1-R4 cycle. Objective A
  uses that cycle's championship roster re-ranked under current rules (those
  starters qualified through age-group slots, so this is a counterfactual
  mapping, not observed pool roll-down). Objective B uses the actual raw
  age-group ranking: N is the race-year's age-group slots, and a matched
  age-group rank-1 finisher counts because R1-R4 had no separate winner route.
  In objective B's
  ranked-evidence plot only, an R1-R4 race may show a descriptive density
  boundary and five-unmatched scan in its actual age-group ranking. The
  age-group rank-1 finisher, matched or not, is shown as a gold dot at the actual rank and raw time but is
  excluded from the plot-only density/scan inputs and counts; this is not a P1
  automatic-slot route. These markers are not qualification methods or results
  and do not affect targets, rank factors, Finder chances, calibration or model
  metrics. Matching does not establish acceptance, and missing matches do not
  establish absence or declined slots.
- The matched-slot cutoff ignores unmatched championship ranks and selects the
  Nth rank with a matched result from that exact qualifying race-year, where N
  is the compatible gender performance-pool allocation (B R1-R4: the age-group
  allocation in the actual age-group ranking). A ranks the same-cycle
  roster under current rules and standards; B uses the historical ranking and
  cycle standard. Fewer than N matched ranks, or incompatible cycle, roster,
  ranking, slots, or standard, is unavailable without strict fallback. P1
  age-group winners are excluded from pool ranks and match counts and retain
  their separate automatic-slot route. This boundary is not density, scan,
  rank factor, or evidence of slot acceptance.
- The rank-factor scenario uses initial gender-pool slots for P1 or age-group
  slots for R1-R4, plus `floor(slots * factor + 0.5)` hypothetical positions.
  It does not infer a finisher beyond the available ranking; P1 keeps the
  separate automatic-winner route.
- World Championship races (Kona, Nice) are not qualifiers and are excluded
  from qualification comparisons.

## Sources

- [IRONMAN: World Championship Age Group Qualification System](https://www.ironman.com/about/age-group-qualification)
  (current performance-pool system; contrasts with the earlier size-based
  allocation).
- [IRONMAN: 2026 Qualification Update](https://www.ironman.com/about/2026-qualification-update)
  and the November 2025 announcement of gender-split pools
  ([TRI247 report](https://www.tri247.com/triathlon-news/age-group/ironman-announce-changes-november-2025-kona-qualifying-system)).
- [Coach Cox: Age Group Kona Slot Allocation (2018)](https://www.coachcox.co.uk/2018/11/23/age-group-kona-slot-allocation/)
  (D'Hondt observation).
- [Coach Cox: How Are Kona Slots Allocated?](https://www.coachcox.co.uk/2013/03/10/how-are-kona-slots-allocated/)
  and [Kona Qualification and the Roll Down](https://www.coachcox.co.uk/2013/03/06/kona-qualification-and-the-roll-down/)
  (proportional policy, one-slot minimum, in-age-group roll-down).
- [Coach Cox qualification overview](https://www.coachcox.co.uk/imstats/im/qualification/)
  (cycle windows, race and slot counts).
- [Wikipedia: Ironman World Championship](https://en.wikipedia.org/wiki/Ironman_World_Championship)
  (2020 cancellation, 2021 championship in St George on 7 May 2022, 2022 split
  days, Nice/Kona alternation from 2023).
- Local data: [coachcox_qualifiers_2017_2026.md](../data/derived/coachcox_qualifiers_2017_2026.md),
  [coachcox_age_group_allocations.json](../data/derived/coachcox_age_group_allocations.json),
  [scrape_age_group_allocations.py](../src/scrape_age_group_allocations.py),
  [code_review.md](./code_review.md).

## Open points

- The exact race where IRONMAN switched from R1 to R2 is not documented.
- 70.3 rules for 2021-2024 are inferred from result flags; no official
  per-cycle 70.3 text was found.
- Cycle windows for 2020 and 2021 overlap because of COVID-19 deferrals.

## Machine-readable data

Reference data used by the code lives in [data/reference/](../data/reference/):
`rule_sets.json` (this document's rule sets and cycles), `age_group_standards.json`
(Kona and 70.3 Standard ratios by cycle), `qualification_constants.json`,
`current_slots.json`, `events.json`, `modified_courses.json` and
`reported_cutoffs.json`. Loaded through [reference_data.py](../src/reference_data.py).
Update the JSON and this document together.
