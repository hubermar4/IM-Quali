"""Build docs/historical_qualification_race_slots.md from the cached Coach Cox cycle pages."""
import re
from collections import defaultdict

from project_paths import CACHE_DIR, DOCS_DIR
from scrape_qualifying_races import parse_races

CACHE = CACHE_DIR / "CoachCoxQualificationPages"
OUTPUT = DOCS_DIR / "historical_qualification_race_slots.md"


def load_rows():
    rows = []
    for path in sorted(CACHE.glob("qualification_*.html")):
        cycle = re.search(r"(\d{4})", path.name).group(1)
        rows.extend(parse_races(path.read_text(encoding="utf-8"), path.name, cycle))
    return rows


def kind(name):
    if "70.3" in name:
        return "IRONMAN 70.3"
    if "World Championship" in name:
        return "World Championship"
    return "IRONMAN"


def split_text(row):
    if row["combined_qualifiers"] is not None or (
        row["male_qualifiers"] is None and row["female_qualifiers"] is None
    ):
        return ""
    return f" ({row['male_qualifiers'] or 0}M/{row['female_qualifiers'] or 0}W)"


def total(row):
    return row["total_qualifiers"] or 0


def main():
    rows = load_rows()
    cycles = sorted({r["qualification_cycle"] for r in rows})
    series = defaultdict(list)
    for row in rows:
        key = row["series_id"] or row["race_name"]
        series[key].append(row)

    def series_name(items):
        latest = max(items, key=lambda r: r["race_date"])
        return latest["race_name"]

    ordered = sorted(
        series.values(),
        key=lambda items: (kind(series_name(items)), series_name(items).lower()),
    )

    lines = [
        "# Historical qualification races and slots, 2017-2026",
        "",
        "Where athletes could qualify for the IRONMAN / IRONMAN 70.3 World "
        "Championship, and how many age-group slots each race offered. Generated "
        "by [build_race_slot_history.py](../src/build_race_slot_history.py) from the cached "
        "Coach Cox qualification-cycle pages "
        "([source data](../data/derived/coachcox_qualifiers_2017_2026.md)). "
        "Rules that apply to each cycle: "
        "[historical_qualification_rules.md](./historical_qualification_rules.md).",
        "",
        "- A race is listed under the qualification cycle in which it was held "
        "(late-season races belong to the following cycle).",
        "- Slot numbers are the totals published by Coach Cox; where men and women have "
        "separate quotas they are shown as `(M/W)`. Several editions in one cycle are "
        "joined with `+`.",
        "- Races are grouped by Coach Cox series, so renamed races (e.g. Kalmar / "
        "Sweden, Kopenhagen / Copenhagen) are one row. `—` means the race was not a "
        "qualifier in that cycle.",
        "- Slot totals include slots that were not accepted or rolled down.",
        "- The 2027 cycle is not included in the cached data (in progress); see "
        "[im_qualification_race_slots.md](./im_qualification_race_slots.md).",
        "",
        "## Summary by cycle",
        "",
        "| Cycle | Races | IRONMAN | 70.3 | World Championship | Slots | Avg slots / race |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for cycle in cycles:
        cr = [r for r in rows if r["qualification_cycle"] == cycle]
        counts = {k: sum(kind(r["race_name"]) == k for r in cr)
                  for k in ("IRONMAN", "IRONMAN 70.3", "World Championship")}
        slots = sum(total(r) for r in cr)
        lines.append(
            f"| {cycle} | {len(cr)} | {counts['IRONMAN']} | {counts['IRONMAN 70.3']} | "
            f"{counts['World Championship']} | {slots} | {slots / len(cr):.0f} |"
        )
    lines.append(
        f"| **Total** | **{len(rows)}** | | | | **{sum(total(r) for r in rows)}** | |"
    )

    lines += ["", "## Slots by race and cycle", ""]
    for group in ("IRONMAN", "IRONMAN 70.3", "World Championship"):
        group_series = [s for s in ordered if kind(series_name(s)) == group]
        if not group_series:
            continue
        title = {
            "IRONMAN": "Full-distance qualifying races",
            "IRONMAN 70.3": "IRONMAN 70.3 events listed with full-distance slots",
            "World Championship": "World Championship races that also offered slots (split championships)",
        }[group]
        lines += [
            f"### {title}",
            "",
            "| Race | " + " | ".join(cycles) + " | Editions | Total slots |",
            "|---|" + "---:|" * (len(cycles) + 2),
        ]
        for items in group_series:
            cells = []
            for cycle in cycles:
                eds = sorted(
                    (r for r in items if r["qualification_cycle"] == cycle),
                    key=lambda r: r["race_date"],
                )
                cells.append(
                    " + ".join(f"{total(r)}{split_text(r)}" for r in eds) if eds else "—"
                )
            lines.append(
                f"| {series_name(items)} | " + " | ".join(cells)
                + f" | {len(items)} | {sum(total(r) for r in items)} |"
            )
        lines.append("")

    lines += ["## Every edition", ""]
    for cycle in cycles:
        cr = sorted(
            (r for r in rows if r["qualification_cycle"] == cycle),
            key=lambda r: (r["race_date"], r["event_title"]),
        )
        lines += [
            f"### {cycle} cycle",
            "",
            "| Date | Race | Men | Women | Combined | Total | Starters |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
        for r in cr:
            def v(x):
                return "—" if x is None else str(x)
            lines.append(
                f"| {r['race_date']} | {r['event_title']} | {v(r['male_qualifiers'])} | "
                f"{v(r['female_qualifiers'])} | {v(r['combined_qualifiers'])} | "
                f"{v(r['total_qualifiers'])} | {r['competitors']} |"
            )
        lines.append("")

    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUTPUT} ({len(rows)} editions, {len(series)} races)")


if __name__ == "__main__":
    main()
