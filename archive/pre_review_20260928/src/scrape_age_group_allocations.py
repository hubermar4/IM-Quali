import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.request import Request, urlopen

from project_paths import (
    CACHE_DIR,
    DERIVED_DATA_DIR,
    RACE_HISTORY_DIR,
)
from scrape_qualifying_races import parse_races


PAGE_CACHE = CACHE_DIR / "CoachCoxQualificationPages"
DETAIL_CACHE = CACHE_DIR / "CoachCoxRaceSlotPages"
OUTPUT_FILE = DERIVED_DATA_DIR / "coachcox_age_group_allocations.json"
EVENT_NAMES = {
    "im_austria": "Ironman Austria",
    "im_france": "Ironman France",
    "im_frankfurt": "Ironman Frankfurt",
    "im_hamburg": "Ironman Hamburg",
    "im_italy": "Ironman Italy",
    "im_kalmar": "Ironman Sweden",
    "im_kopenhagen": "Ironman Copenhagen",
    "im_tallinn": "Ironman Tallinn",
}


def local_years(event_id):
    folder_name = {
        "im_austria": "IM_Austria",
        "im_france": "IM_France",
        "im_frankfurt": "IM_Frankfurt",
        "im_hamburg": "IM_Hamburg",
        "im_italy": "IM_Italy",
        "im_kalmar": "IM_Kalmar",
        "im_kopenhagen": "IM_Kopenhagen",
        "im_tallinn": "IM_Tallinn",
    }[event_id]
    return {
        match.group(1)
        for path in (RACE_HISTORY_DIR / folder_name).glob("*.csv")
        if (match := re.search(r"(20\d{2})", path.stem))
    }


def source_records():
    records = {}
    wanted = {name: event_id for event_id, name in EVENT_NAMES.items()}
    wanted_years = {event_id: local_years(event_id) for event_id in EVENT_NAMES}
    for page in sorted(PAGE_CACHE.glob("qualification_*.html")):
        cycle = re.search(r"(20\d{2})", page.stem).group(1)
        source_url = f"https://coachcox.co.uk/imstats/im/qualification/{cycle}/races/"
        for row in parse_races(page.read_text(encoding="utf-8"), source_url, cycle):
            event_id = wanted.get(row["race_name"])
            year = row["event_year"]
            if not event_id or year not in wanted_years[event_id] or not row["qualification_url"]:
                continue
            key = (event_id, year)
            existing = records.get(key)
            if existing is None or int(row["qualification_cycle"]) > int(existing["qualification_cycle"]):
                records[key] = row
    return records


def fetch_detail(race_id, url):
    cache_file = DETAIL_CACHE / f"race_{race_id}_slots.md"
    if cache_file.exists():
        return cache_file.read_text(encoding="utf-8")
    proxy_url = f"https://r.jina.ai/{url}"
    request = Request(proxy_url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=90) as response:
        text = response.read().decode("utf-8", errors="replace")
    DETAIL_CACHE.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(text, encoding="utf-8")
    return text


def parse_detail(text):
    preset_match = re.search(r"Preset Allocation:\s*(.+?)\[Slots\]", text, re.S)
    preset = " ".join(preset_match.group(1).split()) if preset_match else ""
    allocations = {}
    cutoffs = {}
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        division_match = re.search(r"\b([MF]\d{2}-\d{2})\b", cells[0])
        if not division_match or not cells[1].isdigit():
            continue
        division = division_match.group(1)
        allocations[division] = int(cells[1])
        cutoffs[division] = cells[2] or None
    if not allocations:
        raise ValueError("No age-group allocation table found")
    return {"preset": preset, "allocations": allocations, "published_cutoffs": cutoffs}


def main():
    records = source_records()
    details = {}
    unique = {row["race_id"]: row for row in records.values()}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {
            pool.submit(fetch_detail, race_id, row["qualification_url"]): race_id
            for race_id, row in unique.items()
        }
        for future in as_completed(futures):
            race_id = futures[future]
            try:
                details[race_id] = parse_detail(future.result())
                print(f"Fetched race {race_id}: {len(details[race_id]['allocations'])} age groups")
            except Exception as error:
                print(f"Skipped race {race_id}: {error}")

    output = {}
    for (event_id, year), row in sorted(records.items()):
        detail = details.get(row["race_id"])
        if detail is None:
            continue
        output.setdefault(event_id, {})[year] = {
            **detail,
            "race_id": row["race_id"],
            "qualification_cycle": row["qualification_cycle"],
            "source_url": row["qualification_url"],
        }
    OUTPUT_FILE.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Saved {sum(len(years) for years in output.values())} race-years to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()