# Legacy IRONMAN age-group qualification procedure

## Scope

This document describes the age-group slot system used before the performance-
pool system introduced for the 2026 qualifying cycle. It applies to historical
IRONMAN and IRONMAN 70.3 World Championship qualification estimates.

## Published procedure

1. Each qualifying race received a fixed number of World Championship slots.
2. Only age groups represented by at least one eligible starter participated in
   the allocation.
3. Every represented age group received a minimum of one slot.
4. The remaining slots were apportioned according to each age group's share of
   eligible starters. Men and women therefore competed for slots through their
   separate age-group categories rather than through a cross-age performance
   ranking.
5. The final allocation was based on race-day starters, not registrations or
   finishers.
6. Slots were offered in finishing order within the allocated age group. A
   declined slot rolled down within that age group. Historical cutoff estimates
   that assume no declines therefore use the finishing time at the allocated
   slot rank.

## Integer allocation changed over time

The public policy described proportional allocation and the one-slot minimum,
but IRONMAN did not publish a stable, complete integer-allocation formula.
Consequently, a single reconstructed formula must not be presented as exact for
all historical years.

Coach Cox documents two observed implementations:

- An earlier method first assigned one slot to every represented age group,
  then distributed the remaining slots proportionally. A largest-remainder
  implementation reproduces the published Austria 2018 40-slot allocation from
  the local starter data.
- During 2018, published race-day allocations began matching the D'Hondt
  highest-averages method. D'Hondt slightly favors larger age groups compared
  with the earlier method.

For this reason, the dashboard's historical mode should prefer the age-group
allocation published for that specific race. A reconstructed allocation should
be explicitly labeled as an estimate when no published allocation is available.

## Dashboard interpretation

The two supported modes answer different questions:

### Current performance-pool rules

- Apply the current race slot allocation to every displayed historical field.
- Give one automatic slot to each represented age-group winner.
- Split remaining full-distance performance-pool slots by eligible male/female
  starter representation.
- Rank remaining athletes within gender by current age-graded time.
- For 70.3, use the current separately published male and female quotas.

This is a counterfactual comparison: it asks what historical results would have
looked like under the current rules.

### Actual historical rules and slots

- Use the slot total or gender quotas published for that race and qualifying
  cycle.
- Use the official age-group allocation from the results' `Qualified` flags
  when the flags cover that cycle (90-100% of its slots; age groups without a
  finisher cannot be flagged). Otherwise use the race's published age-group
  allocation, and only then a labeled reconstruction.
- For races in the 2026 qualifying cycle and later, use that cycle's Kona or
  70.3 Standard and gender performance pools; a race-page age-group table must
  not override the qualification system active for that cycle.
- For earlier age-group allocation cycles, rank athletes only inside their age
  group by raw finish time.
- Display the Nth finisher as the strict no-roll-down cutoff, where N is that
  age group's allocated slot count.

This mode estimates the automatic entitlement line, not the final ceremony
result. Actual accepted qualifying times can be slower when slots roll down.

## Sources

- [IRONMAN: World Championship Age Group Qualification System](https://www.ironman.com/about/age-group-qualification)
  describes the new performance-pool system and explicitly contrasts it with
  the prior system, where slots were allocated according to age-group size.
- [Coach Cox: Age Group Kona Slot Allocation](https://www.coachcox.co.uk/2018/11/23/age-group-kona-slot-allocation/)
  documents the observed change to D'Hondt and compares it with the previous
  method.
- [Coach Cox: How Are Kona Slots Allocated?](https://www.coachcox.co.uk/2013/03/10/how-are-kona-slots-allocated/)
  records the published proportional-to-starters policy and one-slot minimum.
- [Coach Cox: Kona Qualification and the Roll Down](https://www.coachcox.co.uk/2013/03/06/kona-qualification-and-the-roll-down/)
  describes age-group-specific roll-down behavior and its effect on cutoff
  times.
- [Coach Cox historical qualifier counts](../data/derived/coachcox_qualifiers_2017_2026.md)
  records race-cycle slot totals and gender quotas used by historical mode.
- [Coach Cox exact age-group allocations](../data/derived/coachcox_age_group_allocations.json)
  caches the published race-page slot table used when its gender totals reconcile
  with the historical race-cycle source. The companion
  [scraper](../src/scrape_age_group_allocations.py) rebuilds this dataset from
  cached qualification lists and source race pages. Frankfurt 2023 is retained
  as published at 99 allocated age-group slots against 100 listed source slots;
  the dashboard displays both values.