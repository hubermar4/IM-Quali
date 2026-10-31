---
description: "Use when handling any question, code change, or analysis about WHERE to qualify: which IRONMAN / IRONMAN 70.3 races were qualifying races, how many World Championship age-group slots each race offered per qualification cycle (men/women quotas), slot trends, race comparisons, race-slot data scraping or the race-slot history document."
applyTo: "src/build_race_slot_history.py,src/scrape_qualifying_races.py,src/scrape_age_group_allocations.py,src/build_dashboard.py,docs/historical_qualification_race_slots.md,data/derived/coachcox_*,data/reference/current_slots.json,data/reference/events.json"
---

# Qualification race slots (where to qualify)

Source of truth: [docs/historical_qualification_race_slots.md](../../docs/historical_qualification_race_slots.md)
(cycles 2017-2026; the 2027 cycle is in [docs/im_qualification_race_slots.md](../../docs/im_qualification_race_slots.md) and [docs/im703_qualification_race_slots.md](../../docs/im703_qualification_race_slots.md)).

- The file is large: search it (grep for the race name) or read only the relevant section instead of loading it whole. Sections: "Summary by cycle", "Slots by race and cycle" (one row per race, one column per cycle), "Every edition" (per-cycle list).
- Slots are listed under the qualification cycle in which the race was held, not the calendar year in the race name.
- `(M/W)` are separate quotas; `A + B` means two editions in one cycle; `—` means not a qualifier that cycle.
- Totals are Coach Cox published slots, including declined/rolled-down slots. How they were awarded depends on the cycle: see [qualification-rules.instructions.md](./qualification-rules.instructions.md).
- Do not edit the document by hand. Refresh the Coach Cox cache with `python src/scrape_qualifying_races.py --refresh`, then run `python src/build_race_slot_history.py`.
