import json
import re
from pathlib import Path

import pandas as pd
import qualification_full
import qualification_703 as qualification_half
from course_difficulty import course_and_season_effects, estimate_course_factors
from gpx_course_model import Rider, read_gpx, simulate
from kona_trace import build_kona_trace
from project_paths import (
  COACHCOX_ALLOCATION_FILE,
  CACHE_DIR,
  DIST_DIR,
  GPX_TRACK_DIR,
  RACE_HISTORY_DIR,
  ensure_output_directories,
)
from scrape_qualifying_races import parse_races as parse_coachcox_races

from split_time_analysis import (
    SPLIT_COLUMNS,
    parse_duration,
)


OUTPUT_FILE = DIST_DIR / "dashboard.html"
DATA_FILE = DIST_DIR / "dashboard_data.js"
INDEX_FILE = DIST_DIR / "index.html"
COACHCOX_CACHE_DIR = CACHE_DIR / "CoachCoxQualificationPages"
FULL_DISTANCE = {"swim": 3800, "bike": 180, "run": 42.2}
HALF_DISTANCE = {"swim": 1900, "bike": 90, "run": 21.1}
YEAR_PATTERN = re.compile(r"(20\d{2})")
PRO_DIVISIONS = {"MPRO", "FPRO"}
HALF_DISTANCE_PATTERN = re.compile(r"70\.?3|703", re.IGNORECASE)
DEFAULT_TOTAL_SLOTS = 40
DEFAULT_SLOTS_PER_GENDER = 25
KONA_SLOTS_2026_URL = "https://www.ironman.com/races/im-world-championship-kona/qualifying-events-2026"
KONA_SLOTS_2027_URL = "https://www.ironman.com/races/im-world-championship-kona/qualifying-events-2027"
WC703_SLOTS_2026_URL = "https://www.ironman.com/races/im703-world-championship-2026/qualifying-events-2026"
WC703_SLOTS_2027_URL = "https://www.ironman.com/races/im703-world-championship-2027/qualifying-events-2027"
# Latest published allocation per race and its qualifying cycle; current mode
# applies it to every historical field.
RACE_SLOTS_IM = {
  "im_austria": (40, "2026"),
  "im_barcelona": (55, "2027"),
  "im_france": (40, "2026"),
  "im_frankfurt": (60, "2026"),
  "im_hamburg": (60, "2026"),
  "im_italy": (55, "2027"),
  "im_kalmar": (40, "2026"),
  "im_kopenhagen": (40, "2026"),
  "im_lanzarote": (40, "2026"),
  "im_leeds": (40, "2026"),
  "im_portugal": (55, "2027"),
  "im_tallinn": (45, "2027"),
  "im_thun": (40, "2026"),
  "im_vitoria": (40, "2026"),
  "im_wales": (50, "2027"),
}
RACE_SLOTS_703 = {
  "im_703_zellamsee": ({"male": 25, "female": 25}, "2027"),
}
# World Championship races are not qualifying events for the age-group system.
NON_QUALIFYING_EVENTS = {"im_kona", "im_nice_wc"}
# Championship editions held in Nice (2023/2025 men, 2024 women); their start
# lists complement the local Kona files of the same championship year.
NICE_CHAMPIONSHIP_EVENT = "im_nice_wc"
# Race-years whose course was shortened; excluded from cross-race comparisons.
MODIFIED_COURSES = {
  ("im_barcelona", "2021"): "swim cancelled for most athletes",
  ("im_france", "2019"): "shortened run",
  ("im_frankfurt", "2026"): "shortened bike and run",
  ("im_leeds", "2026"): "swim cancelled",
  ("im_thun", "2021"): "shortened swim",
  ("im_vitoria", "2021"): "swim cancelled",
}
# Official ironman.com allocations for race-years missing from the Coach Cox lists.
OFFICIAL_SLOT_SOURCES = {
  ("im_tallinn", "2026"): {
    "method": "performance", "male": None, "female": None, "combined": 45,
    "total": 45, "cycles": ["2027"], "source_url": KONA_SLOTS_2027_URL,
  },
  ("im_wales", "2026"): {
    "method": "performance", "male": None, "female": None, "combined": 50,
    "total": 50, "cycles": ["2027"], "source_url": KONA_SLOTS_2027_URL,
  },
  ("im_703_zellamsee", "2025"): {
    "method": "performance", "male": 35, "female": 35, "combined": None,
    "total": 70, "cycles": ["2026"], "source_url": WC703_SLOTS_2026_URL,
  },
  ("im_703_zellamsee", "2026"): {
    "method": "performance", "male": 25, "female": 25, "combined": None,
    "total": 50, "cycles": ["2027"], "source_url": WC703_SLOTS_2027_URL,
  },
}
COACHCOX_EVENT_NAMES = {
  "im_austria": "Ironman Austria",
  "im_barcelona": "Ironman Barcelona",
  "im_france": "Ironman France",
  "im_frankfurt": "Ironman Frankfurt",
  "im_hamburg": "Ironman Hamburg",
  "im_italy": "Ironman Italy",
  "im_kalmar": "Ironman Sweden",
  "im_kopenhagen": "Ironman Copenhagen",
  "im_lanzarote": "Ironman Lanzarote",
  "im_leeds": "Ironman Leeds",
  "im_portugal": "Ironman Portugal - Cascais",
  "im_tallinn": "Ironman Tallinn",
  "im_thun": "Ironman Switzerland",
  "im_vitoria": "Ironman Vitoria-Gasteiz",
  "im_wales": "Ironman Wales",
}
EVENT_DISPLAY_NAMES = {
  "im_barcelona": "IRONMAN Calella-Barcelona",
  "im_kalmar": "IRONMAN Kalmar",
  "im_kopenhagen": "IRONMAN Copenhagen",
  "im_nice_wc": "IRONMAN World Championship Nice",
  "im_portugal": "IRONMAN Portugal-Cascais",
  "im_tallinn": "IRONMAN Tallinn",
  "im_thun": "IRONMAN Switzerland Thun",
  "im_vitoria": "IRONMAN Vitoria-Gasteiz",
}
GPX_EVENT_FILES = {
  "im_austria": "austria.gpx",
  "im_barcelona": "barcelona.gpx",
  "im_france": "france.gpx",
  "im_hamburg": "hamburg.gpx",
  "im_italy": "italy.gpx",
  "im_kalmar": "kalmar.gpx",
  "im_kopenhagen": "copenhagen.gpx",
  "im_lanzarote": "lanzarote.gpx",
  "im_leeds": "leeds.gpx",
  "im_portugal": "portugal.gpx",
  "im_tallinn": "tallinn.gpx",
  "im_thun": "thun.gpx",
  "im_vitoria": "vitoria.gpx",
  "im_wales": "wales.gpx",
}
LEGACY_RANK_OFFSETS = (1, 2, 5)


def finishers_only(frame):
    """Keep only rows with an official 'FIN' result, dropping DNS/DNF/DQ/NC."""
    if "Finish" not in frame.columns:
        return frame
    return frame.loc[frame["Finish"].astype(str).str.strip().str.upper().eq("FIN")]


def read_results(csv_files):
    """Read one race-year; editions split across race days have one file per day."""
    key = tuple(csv_files)
    if key not in _RESULTS_CACHE:
        frames = [pd.read_csv(path) for path in csv_files]
        _RESULTS_CACHE[key] = (
            frames[0] if len(frames) == 1 else pd.concat(frames, ignore_index=True)
        )
    return _RESULTS_CACHE[key].copy()


_RESULTS_CACHE = {}


def discover_events():
    """Build one dashboard event per race-history subfolder, with the CSV files per year."""
    events = {}
    for folder in sorted(RACE_HISTORY_DIR.iterdir()):
        if not folder.is_dir():
            continue
        year_files = {}
        for csv_file in sorted(folder.glob("*.csv")):
            match = YEAR_PATTERN.search(csv_file.stem)
            if match:
                year_files.setdefault(match.group(1), []).append(csv_file)
        if not year_files:
            continue

        event_id = folder.name.lower()
        display_name = EVENT_DISPLAY_NAMES.get(
          event_id,
          folder.name.replace("IM_", "IRONMAN ").replace("_", " "),
        )
        group = "703" if HALF_DISTANCE_PATTERN.search(folder.name) else "im"
        qualifying = event_id not in NON_QUALIFYING_EVENTS
        if group == "703":
            slots, slot_cycle = RACE_SLOTS_703.get(
                event_id,
                ({"male": DEFAULT_SLOTS_PER_GENDER, "female": DEFAULT_SLOTS_PER_GENDER}, None),
            )
            note = (
                f"Current rules: {slots['male']} men / {slots['female']} women "
                f"({slot_cycle or 'unsourced'} qualifying-cycle allocation) and the "
                f"{qualification_half.CURRENT_CYCLE}-cycle IRONMAN 70.3 Standard; "
                "strict estimate: all age-group winners accept, no roll-down."
            )
        else:
            slots, slot_cycle = RACE_SLOTS_IM.get(event_id, (DEFAULT_TOTAL_SLOTS, None))
            note = (
                f"Current rules: {slots} total slots ({slot_cycle or 'unsourced'} "
                "qualifying-cycle allocation); performance-pool slots split by eligible "
                f"age-group starter representation; {qualification_full.CURRENT_CYCLE}-cycle "
                "Kona Standard; strict estimate: all age-group winners accept, no roll-down."
            )
        if not qualifying:
            note = "World Championship race: not a qualifying event, so no qualification estimate is shown."
        events[event_id] = {
            "name": display_name,
            "subtitle": display_name,
            "years": dict(sorted(year_files.items())),
            "distances": HALF_DISTANCE if group == "703" else FULL_DISTANCE,
            "default_from": "04:30:00" if group == "703" else "09:00:00",
            "default_to": "05:00:00" if group == "703" else "09:30:00",
            "group": group,
            "qualifying": qualifying,
            "qualification_slots": slots,
            "qualification_slot_cycle": slot_cycle,
            "qualification_note": note,
            "modified_courses": {
              year: description
              for (course_event, year), description in MODIFIED_COURSES.items()
              if course_event == event_id
            },
        }
    return events


EVENTS = discover_events()
QUALIFICATION_MODULES = {
    event_id: (qualification_half if event["group"] == "703" else qualification_full)
    for event_id, event in EVENTS.items()
}


def load_historical_slot_sources():
  matches = {}
  wanted_names = {name: event_id for event_id, name in COACHCOX_EVENT_NAMES.items()}
  for cache_file in sorted(COACHCOX_CACHE_DIR.glob("qualification_*.html")):
    cycle_match = YEAR_PATTERN.search(cache_file.stem)
    if not cycle_match:
      continue
    cycle = cycle_match.group(1)
    source_url = f"https://coachcox.co.uk/imstats/im/qualification/{cycle}/races/"
    rows = parse_coachcox_races(
      cache_file.read_text(encoding="utf-8"), source_url, cycle
    )
    for row in rows:
      event_id = wanted_names.get(row["race_name"])
      if event_id:
        matches.setdefault((event_id, row["event_year"]), []).append(row)

  def row_total(row):
    if row["male_qualifiers"] is not None or row["female_qualifiers"] is not None:
      return (row["male_qualifiers"] or 0) + (row["female_qualifiers"] or 0)
    return row["combined_qualifiers"] or 0

  def row_label(row):
    if row["male_qualifiers"] is not None or row["female_qualifiers"] is not None:
      parts = [
        f"{row[key]} {label}"
        for key, label in (("male_qualifiers", "M"), ("female_qualifiers", "F"))
        if row[key] is not None
      ]
      return f"{row['qualification_cycle']} cycle: {' / '.join(parts)}"
    return f"{row['qualification_cycle']} cycle: {row['combined_qualifiers']} total"

  sources = {}
  for key, rows in matches.items():
    performance_rows = [
      row for row in rows if int(row["qualification_cycle"]) >= 2026
    ]
    # One real cycle allocation: the performance-pool cycle if present,
    # otherwise the complete (largest) allocation, earliest cycle on ties.
    selected = max(
      performance_rows or rows,
      key=lambda row: (row_total(row), -int(row["qualification_cycle"])),
    )
    male_slots = selected["male_qualifiers"]
    female_slots = selected["female_qualifiers"]
    combined_slots = selected["combined_qualifiers"]
    sources[key] = {
      "method": "performance" if performance_rows else "legacy",
      "male": male_slots,
      "female": female_slots,
      "combined": combined_slots,
      "total": row_total(selected),
      "cycles": [str(selected["qualification_cycle"])],
      "source_url": selected["qualification_url"] or selected["source_url"],
      "other_cycles": [row_label(row) for row in rows if row is not selected],
    }

  for key, source in OFFICIAL_SLOT_SOURCES.items():
    sources[key] = {**source, "other_cycles": []}
  return sources


HISTORICAL_SLOT_SOURCES = load_historical_slot_sources()


def load_exact_age_group_allocations():
  if not COACHCOX_ALLOCATION_FILE.exists():
    return {}
  return json.loads(COACHCOX_ALLOCATION_FILE.read_text(encoding="utf-8"))


EXACT_AGE_GROUP_ALLOCATIONS = load_exact_age_group_allocations()


def prepare_eligible_age_group_rows(frame, module):
  frame = frame.dropna(how="all").copy()
  gender_column = "Gender" if "Gender" in frame.columns else "gender"
  required = {gender_column, "Division", "Overall Time"}
  if frame.empty or not required.issubset(frame.columns):
    return pd.DataFrame()

  frame["gender_normalized"] = (
    frame[gender_column].astype(str).str.strip().str.title()
  )
  frame["Division"] = frame["Division"].astype(str).str.strip().str.upper()
  frame = frame[
    frame["gender_normalized"].isin(("Male", "Female"))
    & ~frame["Division"].isin(module.NON_AGE_GROUP_DIVISIONS)
    & frame["Division"].str.match(r"^[MF]\d{2}-\d{2}$", na=False)
    & frame["Division"].str[0].eq(frame["gender_normalized"].str[0])
  ].copy()
  if "Finish" in frame.columns:
    frame["finish_status"] = frame["Finish"].astype(str).str.strip().str.upper()
  else:
    frame["finish_status"] = "FIN"
  frame["finish_td"] = frame["Overall Time"].map(module.parse_time)
  return frame


def allocate_proportional_slots(starter_counts, total_slots):
  represented = {division: int(count) for division, count in starter_counts.items() if count > 0}
  if not represented or not total_slots:
    return {}
  if total_slots < len(represented):
    return {
      division: int(index < total_slots)
      for index, division in enumerate(
        sorted(represented, key=lambda item: (-represented[item], item))
      )
    }

  allocations = {division: 1 for division in represented}
  remaining = total_slots - len(represented)
  total_starters = sum(represented.values())
  quotas = {
    division: remaining * count / total_starters
    for division, count in represented.items()
  }
  extras = {division: int(quota) for division, quota in quotas.items()}
  for division in sorted(
    represented,
    key=lambda item: (
      quotas[item] - extras[item], represented[item], item
    ),
    reverse=True,
  )[: remaining - sum(extras.values())]:
    extras[division] += 1
  return {
    division: allocations[division] + extras[division]
    for division in represented
  }


def allocate_historical_slots(starter_counts, source):
  if source["male"] is not None or source["female"] is not None:
    allocations = {}
    for prefix, key in (("M", "male"), ("F", "female")):
      gender_counts = {
        division: count
        for division, count in starter_counts.items()
        if division.startswith(prefix)
      }
      allocations.update(
        allocate_proportional_slots(gender_counts, source[key] or 0)
      )
    return allocations
  return allocate_proportional_slots(starter_counts, source["combined"])


def exact_historical_allocation(event_id, year, source):
  detail = EXACT_AGE_GROUP_ALLOCATIONS.get(event_id, {}).get(year)
  if not detail:
    return None
  allocations = {
    division: int(slots)
    for division, slots in detail.get("allocations", {}).items()
    if int(slots) > 0
  }
  male_slots = sum(
    slots for division, slots in allocations.items() if division.startswith("M")
  )
  female_slots = sum(
    slots for division, slots in allocations.items() if division.startswith("F")
  )
  if source["male"] is not None or source["female"] is not None:
    if male_slots != (source["male"] or 0) or female_slots != (source["female"] or 0):
      return None
  else:
    expected = source["combined"] or 0
    if not male_slots or not female_slots or abs(male_slots + female_slots - expected) > 1:
      return None
  return allocations, detail


def cutoff_at_rank(values, rank):
  index = rank - 1
  return values[index] if 0 <= index < len(values) else None


def official_flag_counts(frame):
  """Per-division qualifiers flagged in the official results (finishers only)."""
  if "Qualified" not in frame.columns:
    return {}
  flagged = frame[
    frame["finish_status"].eq("FIN")
    & pd.to_numeric(frame["Qualified"], errors="coerce").eq(1)
  ]
  return {
    division: int(count)
    for division, count in flagged.groupby("Division").size().items()
  }


def gender_totals(allocations):
  male = sum(slots for division, slots in allocations.items() if division.startswith("M"))
  female = sum(slots for division, slots in allocations.items() if division.startswith("F"))
  return male, female


def official_flags_cover_source(counts, source):
  """Flags belong to the selected cycle when they fill 90-100% of its slots.

  Slots of represented age groups without a finisher cannot be flagged, and
  results of races with overlapping cycles flag only one championship.
  """
  if not counts:
    return False
  male, female = gender_totals(counts)
  if source["male"] is not None or source["female"] is not None:
    checks = ((male, source["male"] or 0), (female, source["female"] or 0))
  else:
    checks = ((male + female, source["combined"] or 0),)
  return all(0.9 * expected <= flagged <= expected for flagged, expected in checks)


def official_flag_source(counts):
  total = sum(counts.values())
  return {
    "method": "legacy", "male": None, "female": None, "combined": total,
    "total": total, "cycles": [], "source_url": None, "other_cycles": [],
    "from_official_flags": True,
  }


def pool_payload(result):
  return {
    **{
      gender: [
        {"division": division, "age_graded": round(seconds, 4)}
        for division, seconds in result["pools"][gender]
      ]
      for gender in ("male", "female")
    },
    "automatic": result["automatic_divisions"],
    "winners": {
      division: round(seconds) for division, seconds in result["winner_times"].items()
    },
  }


def gender_performance_slots(result, gender, is_half):
  if is_half:
    return result["male_performance_slots" if gender == "Male" else "female_performance_slots"]
  return result["male_slots" if gender == "Male" else "female_slots"]


def gender_standard_cutoff(result, gender, is_half):
  if is_half:
    return result["male_cutoff_td" if gender == "Male" else "female_cutoff_td"]
  return result["male_cut_td" if gender == "Male" else "female_cut_td"]


def load_historical_qualification_data(event_id, event):
  module = QUALIFICATION_MODULES[event_id]
  is_half = event["group"] == "703"
  rows = []
  pools = {}
  unavailable_years = []
  official_years = []
  if not event["qualifying"]:
    return {
      "targets": rows, "pools": pools, "rank_offsets": list(LEGACY_RANK_OFFSETS),
      "unavailable_years": list(event["years"]), "official_years": official_years,
    }
  for year, csv_files in event["years"].items():
    raw = read_results(csv_files)
    frame = prepare_eligible_age_group_rows(raw, module)
    if frame.empty:
      unavailable_years.append(year)
      continue
    flag_counts = official_flag_counts(frame)
    source = HISTORICAL_SLOT_SOURCES.get((event_id, year))
    if source is None and flag_counts and int(year) <= 2024:
      source = official_flag_source(flag_counts)
    if source is None:
      unavailable_years.append(year)
      continue
    official_complete = official_flags_cover_source(flag_counts, source)
    if official_complete:
      official_years.append(year)
    starters = frame[~frame["finish_status"].eq("DNS")]
    starter_counts = starters.groupby("Division").size().to_dict()
    finishers = frame[
      frame["finish_status"].eq("FIN")
      & frame["finish_td"].notna()
      & frame["finish_td"].gt(pd.Timedelta(0))
    ]

    if source["method"] == "legacy":
      exact = exact_historical_allocation(event_id, year, source)
      allocation_detail = None
      if official_complete:
        allocations = flag_counts
        method = "Official age-group allocation (results)"
      elif exact is not None:
        allocations, allocation_detail = exact
        method = "Coach Cox age-group allocation"
      else:
        allocations = allocate_historical_slots(starter_counts, source)
        method = "Reconstructed age-group allocation"
      allocated_total = sum(allocations.values())
      for division, slots in allocations.items():
        times = sorted(
          value.total_seconds()
          for value in finishers.loc[
            finishers["Division"].eq(division), "finish_td"
          ]
        )
        gender = "Male" if division.startswith("M") else "Female"
        rows.append({
          "year": year,
          "gender": gender,
          "division": division,
          "method": method,
          "slot_scope": "age group",
          "slots": slots,
          "starters": starter_counts.get(division, 0),
          "finishers": len(times),
          "cutoff": cutoff_at_rank(times, slots),
          "winner": times[0] if times else None,
          "times": times,
          "official_qualifiers": flag_counts.get(division, 0) if official_complete else None,
          "ranks": {
            str(offset): cutoff_at_rank(times, slots + offset)
            for offset in LEGACY_RANK_OFFSETS
          },
          "source": {
            **source,
            "allocation_source_url": (
              allocation_detail["source_url"]
              if allocation_detail is not None
              else None
            ),
            "allocation_cycle": (
              allocation_detail["qualification_cycle"]
              if allocation_detail is not None
              else None
            ),
            "published_allocation_total": allocated_total,
          },
        })
      continue

    cycle = source["cycles"][0] if source["cycles"] else module.CURRENT_CYCLE
    cycle = cycle if cycle in module.STANDARDS else module.CURRENT_CYCLE
    try:
      if is_half:
        result = module.process_dataframe(
          year, raw.copy(), male_slots=source["male"],
          female_slots=source["female"], cycle=cycle,
        )
      else:
        result = module.process_dataframe(
          year, raw.copy(), total_slots=source["total"], cycle=cycle
        )
    except (KeyError, ValueError):
      unavailable_years.append(year)
      continue
    if not result:
      unavailable_years.append(year)
      continue
    pools[year] = pool_payload(result)
    method = (
      f"{cycle}-cycle IRONMAN 70.3 Standard performance pool"
      if is_half
      else f"{cycle}-cycle Kona Standard performance pool"
    )
    for target in module.build_target_rows([result]):
      gender = target["Gender"]
      division = target["Division"]
      performance_slots = gender_performance_slots(result, gender, is_half)
      automatic_slots = result[
        "male_auto" if gender == "Male" else "female_auto"
      ]
      finish_time = module.parse_time(target["Finish at or below"])
      rows.append({
        "year": year,
        "gender": gender,
        "division": division,
        "method": method,
        "standard_cycle": cycle,
        "ratio": target.get("70.3 ratio", target.get("Kona ratio")),
        "slot_scope": "gender",
        "slots": performance_slots + automatic_slots,
        "performance_slots": performance_slots,
        "automatic_slots": automatic_slots,
        "automatic_slot": int(division in result["winner_times"]),
        "starters": starter_counts.get(division, 0),
        "finishers": int(finishers["Division"].eq(division).sum()),
        "winner": result["winner_times"].get(division),
        "standard_cutoff": duration_seconds(
          gender_standard_cutoff(result, gender, is_half)
        ),
        "cutoff": duration_seconds(finish_time),
        "official_qualifiers": flag_counts.get(division, 0) if official_complete else None,
        "official_check": result["official_check"][gender.lower()],
        "times": [],
        "ranks": {},
        "source": source,
      })
  return {
    "targets": rows,
    "pools": pools,
    "rank_offsets": list(LEGACY_RANK_OFFSETS),
    "unavailable_years": unavailable_years,
    "official_years": official_years,
  }


def load_event_data(event):
    columns = [
        "Bib",
        "Name",
        "Country",
        "Division",
        "Overall Time",
        *SPLIT_COLUMNS.values(),
    ]
    records = []

    for year, csv_files in event["years"].items():
        frame = read_results(csv_files)
        missing = set(columns) - set(frame.columns)
        if missing:
            continue

        gender_column = "Gender" if "Gender" in frame.columns else "gender"
        if gender_column not in frame.columns:
            continue
        if "Finish" in frame.columns:
            frame = frame.loc[frame["Finish"].eq("FIN")]
        selected_columns = [*columns, gender_column]
        frame = frame[selected_columns].copy()
        duration_columns = ["Overall Time", *SPLIT_COLUMNS.values()]
        for column in duration_columns:
            frame[column] = frame[column].map(parse_duration)
        frame = frame.dropna(subset=["Overall Time", *SPLIT_COLUMNS.values()])
        # Some source rows are marked FIN but have corrupted/missing splits (e.g. 00:00:00);
        # exclude those since a real finisher can't have zero swim/bike/run/overall time.
        zero = pd.Timedelta(0)
        frame = frame.loc[
            (frame["Overall Time"] > zero)
            & (frame[SPLIT_COLUMNS["Swim"]] > zero)
            & (frame[SPLIT_COLUMNS["Bike"]] > zero)
            & (frame[SPLIT_COLUMNS["Run"]] > zero)
        ]

        for row in frame.itertuples(index=False, name=None):
            values = dict(zip(selected_columns, row))
            records.append(
                {
                    "year": year,
                    "bib": str(values["Bib"]),
                    "name": str(values["Name"]),
                    "country": str(values["Country"]),
                    "gender": str(values[gender_column]),
                    "division": str(values["Division"]),
                    "overall": round(values["Overall Time"].total_seconds()),
                    "swim": round(values["Swim Time"].total_seconds()),
                    "t1": round(values["Transition 1 Time"].total_seconds()),
                    "bike": round(values["Bike Time"].total_seconds()),
                    "t2": round(values["Transition 2 Time"].total_seconds()),
                    "run": round(values["Run Time"].total_seconds()),
                }
            )
    return records


def load_overall_data(event):
    yearly_times = {}
    pro_times = {}
    for year, csv_files in event["years"].items():
        frame = read_results(csv_files)
        if "Overall Time" not in frame.columns:
            continue
        frame = finishers_only(frame)
        if frame.empty:
            continue

        division = (
            frame["Division"].astype(str).str.strip().str.upper()
            if "Division" in frame.columns
            else pd.Series("", index=frame.index)
        )
        gender_column = "Gender" if "Gender" in frame.columns else "gender"
        gender = (
            frame[gender_column].astype(str).str.strip().str.title()
            if gender_column in frame.columns
            else pd.Series("", index=frame.index)
        )
        pro_mask = division.isin(PRO_DIVISIONS)
        age_group_mask = division.str.match(r"^[MF]\d{2}-\d{2}$", na=False)

        age_group_durations = frame.loc[
          age_group_mask, "Overall Time"
        ].map(parse_duration).dropna()
        age_group_durations = age_group_durations[age_group_durations > pd.Timedelta(0)]
        if not age_group_durations.empty:
            yearly_times[year] = sorted(
                round(value.total_seconds()) for value in age_group_durations
            )

        pro_durations = frame.loc[pro_mask, "Overall Time"].map(parse_duration)
        pro_durations = pro_durations[pro_durations > pd.Timedelta(0)]
        pro_times[year] = {
            "male": sorted(
                round(value.total_seconds())
                for value in pro_durations[gender.loc[pro_mask].eq("Male")].dropna()
            ),
            "female": sorted(
                round(value.total_seconds())
                for value in pro_durations[gender.loc[pro_mask].eq("Female")].dropna()
            ),
        }
    return yearly_times, pro_times


def load_race_statistics(event):
    stats = []
    for year, csv_files in event["years"].items():
        frame = read_results(csv_files).dropna(how="all")
        if "Finish" not in frame.columns:
            continue

        finish = frame["Finish"].astype(str).str.strip().str.upper()
        gender_column = "Gender" if "Gender" in frame.columns else "gender"
        gender = (
            frame[gender_column].astype(str).str.strip().str.title()
            if gender_column in frame.columns
            else pd.Series("", index=frame.index)
        )
        division = (
            frame["Division"].astype(str).str.strip().str.upper()
            if "Division" in frame.columns
            else pd.Series("", index=frame.index)
        )

        fin_mask = finish.eq("FIN")
        registered = len(frame)
        dns = int(finish.eq("DNS").sum())
        dnf = int(finish.eq("DNF").sum())
        dq = int(finish.eq("DQ").sum())
        finishers = int(fin_mask.sum())
        starters = registered - dns
        pro_mask = division.isin(PRO_DIVISIONS)

        durations = frame.loc[fin_mask, "Overall Time"].map(parse_duration).dropna() if "Overall Time" in frame.columns else pd.Series(dtype="timedelta64[ns]")
        durations = durations[durations > pd.Timedelta(0)]

        stats.append({
            "year": year,
            "registered": registered,
            "starters": starters,
            "finishers": finishers,
            "dns": dns,
            "dnf": dnf,
            "dq": dq,
            "male_finishers": int((fin_mask & gender.eq("Male")).sum()),
            "female_finishers": int((fin_mask & gender.eq("Female")).sum()),
            "pro_finishers": int((fin_mask & pro_mask).sum()),
            "age_group_finishers": int((fin_mask & ~pro_mask).sum()),
            "completion_rate": (finishers / starters) if starters else None,
            "avg_finish": durations.mean().total_seconds() if not durations.empty else None,
            "median_finish": durations.median().total_seconds() if not durations.empty else None,
        })
    return stats


def duration_seconds(value):
  return None if value is None else value.total_seconds()


def load_division_statistics(event_id, event):
  """Eligible age-group starters, finishers, winner and median time per race-year."""
  module = QUALIFICATION_MODULES[event_id]
  statistics = {}
  for year, csv_files in event["years"].items():
    frame = prepare_eligible_age_group_rows(read_results(csv_files), module)
    if frame.empty:
      continue
    starters = frame[~frame["finish_status"].eq("DNS")].groupby("Division").size()
    finishers = frame[
      frame["finish_status"].eq("FIN")
      & frame["finish_td"].notna()
      & frame["finish_td"].gt(pd.Timedelta(0))
    ]
    times = finishers.groupby("Division")["finish_td"]
    winners = times.min()
    medians = times.median()
    counts = times.size()
    statistics[year] = {
      division: {
        "starters": int(starters.get(division, 0)),
        "finishers": int(counts.get(division, 0)),
        "winner": round(winners[division].total_seconds()) if division in winners else None,
        "median": round(medians[division].total_seconds()) if division in medians else None,
      }
      for division in sorted(set(starters.index) | set(counts.index))
    }
  return statistics


def load_qualification_data(event_id, event):
    module = QUALIFICATION_MODULES[event_id]
    is_half = event["group"] == "703"
    empty = {
      "summaries": [], "targets": [], "pools": {}, "ratios": {},
      "standard_cycle": module.CURRENT_CYCLE, "rank_offsets": [],
      "show_female_ranks": is_half,
    }
    if not event["qualifying"]:
        return empty
    results = []
    for year, csv_files in event["years"].items():
        frame = read_results(csv_files)
        try:
            if is_half:
                slots = event["qualification_slots"]
                result = module.process_dataframe(
                    year, frame, male_slots=slots["male"], female_slots=slots["female"]
                )
            else:
                result = module.process_dataframe(
                    year, frame, total_slots=event["qualification_slots"]
                )
        except (KeyError, ValueError):
            continue
        if result:
            results.append(result)

    summaries = []
    if is_half:
        rank_offsets = (10, 20, 25)
        for result in results:
            summaries.append({
                "year": str(result["year"]),
                "male_finishers": result["male_finishers"],
                "female_finishers": result["female_finishers"],
                "male_starters": result["male_starters"],
                "female_starters": result["female_starters"],
                "male_auto": result["male_auto"],
                "female_auto": result["female_auto"],
                "male_perf": result["male_performance_slots"],
                "female_perf": result["female_performance_slots"],
                "male_cutoff": duration_seconds(result["male_cutoff_td"]),
                "female_cutoff": duration_seconds(result["female_cutoff_td"]),
                "ranks": {
                    str(offset): {
                        "male": duration_seconds(result[f"male_rank_{offset}_td"]),
                        "female": duration_seconds(result[f"female_rank_{offset}_td"]),
                    }
                    for offset in rank_offsets
                },
            })
    else:
        rank_offsets = (15, 30)
        for result in results:
            summaries.append({
                "year": str(result["year"]),
                "male_finishers": result["male_finishers"],
                "female_finishers": result["female_finishers"],
                "male_starters": result["male_starters"],
                "female_starters": result["female_starters"],
                "male_auto": result["male_auto"],
                "female_auto": result["female_auto"],
                "male_perf": result["male_slots"],
                "female_perf": result["female_slots"],
                "male_cutoff": duration_seconds(result["male_cut_td"]),
                "female_cutoff": duration_seconds(result["female_cut_td"]),
                "ranks": {
                    "15": {
                        "male": duration_seconds(
                            module.parse_time(result["male_cut_15"])
                            if result["male_cut_15"] else None
                        ),
                        "female": None,
                    },
                    "30": {
                        "male": duration_seconds(
                            module.parse_time(result["male_cut_30"])
                            if result["male_cut_30"] else None
                        ),
                        "female": None,
                    },
                },
            })

    target_rows = module.build_target_rows(results)
    targets = []
    for row in target_rows:
        ratio = row.get("70.3 ratio", row.get("Kona ratio"))
        targets.append({
            "year": str(row["Year"]),
            "gender": row["Gender"],
            "division": row["Division"],
            "ratio": ratio,
            "age_graded_cutoff": row["Age-graded cutoff"],
            "finish_target": row["Finish at or below"],
        })
    men, women = module.STANDARDS[module.CURRENT_CYCLE]
    return {
      "summaries": summaries,
      "targets": targets,
      "pools": {str(result["year"]): pool_payload(result) for result in results},
      "ratios": {**men, **women},
      "standard_cycle": module.CURRENT_CYCLE,
      "rank_offsets": list(rank_offsets),
      "show_female_ranks": is_half,
    }


def load_course_factors(datasets):
  """Race-year factors plus course, season and returning-athlete effects per distance."""
  factors = {event_id: {} for event_id in datasets}
  models = {}
  for group, module in (("im", qualification_full), ("703", qualification_half)):
    frames, baseline = [], set()
    for event_id, dataset in datasets.items():
      records = pd.DataFrame(dataset["records"])
      if dataset["group"] != group or records.empty:
        continue
      records["division"] = records["division"].str.strip().str.upper()
      records = records[
        ~records["year"].isin(dataset["modified_courses"])
        & records["division"].str.match(r"^[MF]\d{2}-\d{2}$", na=False)
        & records["division"].str[0].eq(records["gender"].str[0])
      ].copy()
      records["race_year"] = event_id + ":" + records["year"]
      records["year"] = records["year"].astype(int)
      frames.append(records)
      if dataset["qualifying"]:
        baseline.update(records["race_year"])
    if not frames:
      continue
    combined = pd.concat(frames, ignore_index=True)
    estimates, fit = estimate_course_factors(combined, baseline, module.get_ratio)
    for label, entry in estimates.items():
      event_id, year = label.split(":")
      factors[event_id][year] = entry
    course, season = (
      course_and_season_effects(estimates, baseline)
      if len({label.split(":")[0] for label in estimates}) > 1
      else ({}, {})
    )
    standards = {
      division: module.get_ratio(gender, division)
      for gender, division in combined[["gender", "division"]].drop_duplicates().itertuples(index=False)
    }
    models[group] = {
      "returning": {split: values["returning"] for split, values in fit.items()},
      "fit": fit,
      "course": course,
      "season": season,
      "standards": {
        division: ratio for division, ratio in sorted(standards.items()) if ratio is not None
      },
      "cycle": module.CURRENT_CYCLE,
    }
  return factors, models


def current_pool_counterfactual_calendar(calendar, events, event_names):
  """A cycle's own qualifying race-years, re-allocated with each race's latest slots.

  Kona starters only reveal the roll-down of the race-years that qualified for
  that championship, so current-rule estimates for e.g. Austria 2017 must use
  the Kona 2017 start list, ranked under the current rules and allocation.
  """
  name_to_event = {name: event_id for event_id, name in event_names.items()}
  rows = []
  for race in calendar:
    event = events.get(name_to_event.get(race["race_name"]), {})
    total_slots = event.get("qualification_slots")
    if event.get("group") != "im" or not event.get("qualifying", True):
      continue
    if not isinstance(total_slots, int) or total_slots <= 0:
      continue
    rows.append({**race, "total_qualifiers": total_slots})
  return rows


def championship_start_list(kona_files, nice_files):
  """One championship year's field: Kona plus, in split years, the Nice race."""
  frames = [read_results(kona_files).assign(Venue="Kona")]
  if nice_files:
    frames.append(read_results(nice_files).assign(Venue="Nice"))
  return pd.concat(frames, ignore_index=True)


def load_dashboard_data():
  rider = Rider()
  bike_course_corrections = {}
  for event_id, filename in GPX_EVENT_FILES.items():
    path = GPX_TRACK_DIR / filename
    if not path.exists():
      continue
    result = simulate(read_gpx(path), rider, 25.0, 100.0)
    bike_course_corrections[event_id] = {
      "source": filename,
      "reference_time": result["t_observed_s"],
      "flat_time": result["t_flat_s"],
      "correction": result["t_observed_s"] - result["t_flat_s"],
      "course_difficulty_factor": result["course_difficulty_factor"],
    }
  datasets = {}
  for event_id, event in EVENTS.items():
      datasets[event_id] = {
          key: value
          for key, value in event.items()
          if key != "years"
      }
      datasets[event_id]["records"] = load_event_data(event)
      datasets[event_id]["overall"], datasets[event_id]["pro_times"] = load_overall_data(event)
      datasets[event_id]["statistics"] = load_race_statistics(event)
      datasets[event_id]["qualification"] = load_qualification_data(
          event_id, event
      )
      datasets[event_id]["historical_qualification"] = (
        load_historical_qualification_data(event_id, event)
      )
      datasets[event_id]["division_stats"] = load_division_statistics(event_id, event)
      datasets[event_id]["bike_course_correction"] = (
        bike_course_corrections.get(event_id)
      )
      summaries = datasets[event_id]["qualification"]["summaries"]
      if summaries:
          latest = summaries[-1]
          datasets[event_id]["default_slots"] = {
              "male": latest["male_perf"],
              "female": latest["female_perf"],
          }
      else:
          datasets[event_id]["default_slots"] = {"male": 0, "female": 0}
  kona = EVENTS.get("im_kona", {})
  historical_targets = {}
  for event_id, dataset in datasets.items():
    for target in dataset["historical_qualification"]["targets"]:
      historical_targets.setdefault((event_id, target["year"]), []).append(target)
  traces = {}
  for cycle, csv_files in kona.get("years", {}).items():
    calendar_file = COACHCOX_CACHE_DIR / f"qualification_{cycle}.html"
    calendar = parse_coachcox_races(
      calendar_file.read_text(encoding="utf-8"),
      f"https://coachcox.co.uk/imstats/im/qualification/{cycle}/races/", cycle,
    ) if calendar_file.exists() else []
    kona_results = championship_start_list(csv_files, EVENTS.get(NICE_CHAMPIONSHIP_EVENT, {}).get("years", {}).get(cycle, []))
    traces[cycle] = build_kona_trace(
      kona_results, calendar, EVENTS,
      read_results, COACHCOX_EVENT_NAMES, year=cycle, historical_targets=historical_targets,
    )
    counterfactual_trace = build_kona_trace(
      kona_results, current_pool_counterfactual_calendar(calendar, EVENTS, COACHCOX_EVENT_NAMES),
      EVENTS, read_results, COACHCOX_EVENT_NAMES, year=cycle,
      historical_targets=historical_targets, ranking_cycle=qualification_full.CURRENT_CYCLE,
    )
    traces[cycle]["counterfactual_summaries"] = [
      {key: value for key, value in row.items() if key != "manual_pool_times"}
      for row in counterfactual_trace["summaries"]["all"]
    ]
    traces[cycle]["counterfactual_standards"] = counterfactual_trace["standards"]
    traces[cycle]["counterfactual_standard_cycle"] = counterfactual_trace["standard_cycle"]
  if "im_kona" in datasets:
    datasets["im_kona"]["kona_traces"] = traces
    datasets["im_kona"]["kona_trace"] = traces.get("2026")
    datasets["im_kona"]["kona_trace_cycles"] = [
      {"year": str(cycle), "available": str(cycle) in traces}
      for cycle in range(2017, 2027)
    ]
  factors, models = load_course_factors(datasets)
  for event_id, dataset in datasets.items():
      model = models.get(dataset["group"], {})
      dataset["course_factors"] = factors[event_id]
      dataset["course_model"] = {
          "course": model.get("course", {}).get(event_id),
          "season": model.get("season", {}),
          "returning": model.get("returning"),
          "fit": model.get("fit"),
          "standards": model.get("standards", {}),
          "cycle": model.get("cycle"),
      }
  return datasets


def build_html(datasets):
    dashboard_ui = Path(__file__).with_name("dashboard_ui.js").read_text(encoding="utf-8")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>IRONMAN Split Explorer</title>
  <style>
    :root {{
      --ink: #15231e; --muted: #65716c; --paper: #f1f3ef; --panel: #ffffff;
      --line: #d5ddd8; --line-strong: #aebcb5; --accent: #00796b;
      --accent-soft: #dcece7; --header: #183a31; --swim: #287da1;
      --t1: #e9b949; --bike: #189b74; --t2: #ee8147; --run: #d94b4b;
    }}
    * {{ box-sizing: border-box; }}
    html {{ background: var(--paper); }}
    body {{ margin: 0; color: var(--ink); background: var(--paper); font-family: "Aptos", "Segoe UI", sans-serif; line-height: 1.4; }}
    header {{ color: white; background-color: var(--header); background-image: linear-gradient(90deg, rgba(255,255,255,.035) 1px, transparent 1px), linear-gradient(rgba(255,255,255,.025) 1px, transparent 1px); background-size: 28px 28px; border-bottom: 4px solid #e4b84d; }}
    .header-inner {{ width: min(100% - 64px, 1480px); margin: auto; padding: 30px 0 25px; }}
    h1 {{ margin: 0; font-family: Georgia, "Times New Roman", serif; font-size: clamp(27px, 3vw, 42px); font-weight: 500; letter-spacing: 0; line-height: 1.12; }}
    .subtitle {{ margin: 8px 0 0; color: #c9d9d3; font-size: 14px; }}
    main {{ padding: 0 32px 48px; max-width: 1544px; margin: auto; }}
    .controls {{ display: flex; flex-wrap: wrap; align-items: end; gap: 16px; padding: 16px; margin: 0 0 22px; background: var(--panel); border: 1px solid var(--line); border-radius: 4px; }}
    label {{ display: grid; gap: 6px; color: var(--muted); font-size: 11px; font-weight: 700; text-transform: uppercase; }}
    #easiestDeclines:disabled {{ opacity: 0.5; }}
    .duration-input, input[type=search], input[type=number], select {{ height: 39px; border: 1px solid var(--line-strong); border-radius: 3px; background: var(--panel); padding: 8px 10px; font: 14px "Aptos", "Segoe UI", sans-serif; color: var(--ink); transition: border-color .15s, box-shadow .15s; }}
    .duration-input:focus, input[type=search]:focus, input[type=number]:focus, select:focus {{ border-color: var(--accent); box-shadow: 0 0 0 3px rgba(0,121,107,.12); outline: 0; }}
    .duration-input {{ width: 112px; font-variant-numeric: tabular-nums; }}
    .duration-input:invalid {{ border-color: var(--run); outline-color: var(--run); }}
    input[type=search] {{ width: 230px; }}
    input[type=checkbox] {{ width: 15px; height: 15px; accent-color: var(--accent); }}
    .years {{ display: flex; flex-wrap: wrap; gap: 7px; padding: 0; }}
    .years label {{ display: flex; flex-direction: row; align-items: center; gap: 5px; padding: 8px 9px; border: 1px solid var(--line); border-radius: 3px; background: #f8faf8; color: var(--ink); text-transform: none; font-size: 12px; font-weight: 600; }}
    .controls .years input[type=checkbox] {{ width: 15px; flex: 0 0 15px; }}
    #comparePanel fieldset {{ min-inline-size: 0; margin-top: 18px; }}
    button {{ min-height: 39px; border: 0; border-radius: 3px; background: var(--accent); color: white; padding: 9px 15px; cursor: pointer; font: 700 12px "Aptos", "Segoe UI", sans-serif; transition: background .15s, transform .15s; }}
    button:hover {{ background: #00665a; }}
    button:active {{ transform: translateY(1px); }}
    button:focus-visible {{ outline: 3px solid rgba(228,184,77,.55); outline-offset: 2px; }}
    .event-control {{ display: flex; align-items: end; justify-content: space-between; padding: 14px 16px; margin-top: -1px; background: #e5ebe7; border: 1px solid var(--line); border-top: 0; }}
    .event-control[hidden] {{ display: none; }}
    .event-control label {{ width: min(100%, 360px); }}
    .tabs {{ display: flex; gap: 4px; margin: 0 0 24px; padding: 8px 0 0; border-bottom: 1px solid var(--line-strong); overflow-x: auto; }}
    .tab-button {{ flex: 0 0 auto; min-height: 43px; color: var(--muted); background: transparent; border: 1px solid transparent; border-bottom: 3px solid transparent; border-radius: 3px 3px 0 0; padding: 10px 18px; font-size: 13px; }}
    .tab-button:hover {{ color: var(--ink); background: #e6ebe7; }}
    .tab-button.active {{ color: var(--ink); background: var(--panel); border-color: var(--line); border-bottom-color: var(--accent); }}
    .tab-panel {{ display: none; }}
    .tab-panel.active {{ display: block; }}
    .metrics {{ display: grid; grid-template-columns: repeat(3, minmax(140px, 1fr)); gap: 12px; margin-bottom: 28px; }}
    .metric {{ position: relative; overflow: hidden; background: var(--panel); border: 1px solid var(--line); border-radius: 4px; padding: 15px 18px 16px; }}
    .metric::before {{ content: ""; position: absolute; inset: 0 auto 0 0; width: 4px; background: var(--accent); }}
    .metric:nth-child(2)::before {{ background: #e4b84d; }} .metric:nth-child(3)::before {{ background: #d66b47; }}
    .metric span {{ display: block; color: var(--muted); font-size: 10px; font-weight: 800; text-transform: uppercase; }}
    .metric strong {{ display: block; margin-top: 5px; font-family: Georgia, "Times New Roman", serif; font-size: 26px; font-weight: 500; font-variant-numeric: tabular-nums; }}
    section {{ margin-top: 30px; }}
    h2 {{ margin: 0 0 11px; font-family: Georgia, "Times New Roman", serif; font-size: 19px; font-weight: 500; line-height: 1.25; }}
    .table-wrap {{ overflow: auto; border: 1px solid var(--line); border-radius: 4px; background: var(--panel); box-shadow: 0 1px 2px rgba(21,35,30,.04); max-height: 620px; scrollbar-color: var(--line-strong) transparent; }}
    table {{ width: 100%; border-collapse: separate; border-spacing: 0; white-space: nowrap; font-size: 13px; font-variant-numeric: tabular-nums; }}
    th {{ position: sticky; top: 0; z-index: 3; padding: 11px 12px; text-align: left; color: #33453e; background: #e5ece8; border-bottom: 1px solid var(--line-strong); font-size: 10px; font-weight: 800; text-transform: uppercase; }}
    td {{ padding: 10px 12px; border-bottom: 1px solid #e6ebe7; }}
    tbody tr:nth-child(even) td {{ background: #f8faf8; }}
    tbody tr:hover td {{ background: #eaf3ef; }}
    tbody tr:last-child td {{ border-bottom: 0; }}
    th:first-child {{ left: 0; z-index: 4; }}
    td:first-child {{ position: sticky; left: 0; z-index: 1; background: var(--panel); font-weight: 650; }}
    tbody tr:nth-child(even) td:first-child {{ background: #f8faf8; }}
    tbody tr:hover td:first-child {{ background: #eaf3ef; }}
    .summary td:first-child {{ font-weight: 700; }}
    .split-bar {{ display: flex; width: 230px; height: 11px; overflow: hidden; border-radius: 2px; background: #e8ece9; }}
    .split-bar span {{ height: 100%; min-width: 0; }}
    .swim {{ background: var(--swim); }} .t1 {{ background: var(--t1); }} .bike {{ background: var(--bike); }}
    .t2 {{ background: var(--t2); }} .run {{ background: var(--run); }}
    .legend {{ display: flex; flex-wrap: wrap; gap: 14px; color: var(--muted); font-size: 11px; font-weight: 650; margin: -2px 0 10px; }}
    .legend i {{ display: inline-block; width: 9px; height: 9px; margin-right: 5px; border-radius: 1px; }}
    .empty {{ padding: 36px; text-align: center; color: var(--muted); }}
    .note {{ color: var(--muted); font-size: 12px; margin: 9px 0 0; }}
    #qualificationPanel > .note {{ margin: 0 0 18px; padding: 11px 13px; color: #365048; background: var(--accent-soft); border-left: 3px solid var(--accent); }}
    .chart-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; margin-top: 28px; }}
    .chart-panel {{ position: relative; min-width: 0; padding: 16px; background: var(--panel); border: 1px solid var(--line); border-radius: 4px; box-shadow: 0 1px 2px rgba(21,35,30,.04); }}
    .chart-panel.wide {{ grid-column: 1 / -1; }}
    .chart-panel h2 {{ margin-bottom: 4px; }}
    .chart-heading {{ display: flex; align-items: end; justify-content: space-between; gap: 18px; margin-bottom: 4px; }}
    .chart-heading h2 {{ margin: 0; }}
    .chart-controls {{ display: flex; flex: 0 0 auto; align-items: end; gap: 10px; }}
    .chart-controls label {{ gap: 3px; }}
    .chart-controls select {{ height: 34px; min-width: 108px; padding-block: 5px; }}
    [hidden] {{ display: none !important; }}
    svg.chart {{ display: block; width: 100%; min-height: 300px; background: var(--panel); }}
    .chart text {{ font: 11px "Aptos", "Segoe UI", sans-serif; fill: var(--muted); }}
    .chart .axis {{ stroke: #9ba5a2; stroke-width: 1; }}
    .chart .grid {{ stroke: #e3e8e5; stroke-width: 1; }}
    .chart .corner-label {{ font-size: 12px; font-weight: 800; text-transform: uppercase; }}
    .chart .easy-label {{ fill: #00796b; }}
    .chart .hard-label {{ fill: #b74545; }}
    .chart .data-point {{ cursor: crosshair; stroke: var(--panel); stroke-width: 2; transition: r .12s, stroke-width .12s; }}
    .chart .data-point:hover, .chart .data-point:focus {{ r: 6; stroke: var(--ink); stroke-width: 2; outline: none; }}
    .chart .trace-toggle {{ cursor: pointer; }}
    .chart .trace-toggle:focus {{ outline: none; }}
    .chart .trace-toggle[aria-pressed="false"] {{ opacity: .35; }}
    .chart-tooltip {{ position: absolute; z-index: 8; display: none; pointer-events: none; min-width: 125px; max-width: min(320px, calc(100% - 8px)); padding: 8px 10px; color: white; background: rgba(21,35,30,.96); border-radius: 3px; box-shadow: 0 4px 14px rgba(21,35,30,.2); font-size: 12px; line-height: 1.35; }}
    .chart-tooltip strong {{ display: block; color: #f2cc66; font-size: 11px; }}
    .chart-subtitle {{ margin: 20px 0 0; font-size: 13px; font-weight: 800; color: var(--ink); }}
    .method {{ padding: 14px 18px; background: var(--panel); border: 1px solid var(--line); border-radius: 4px; font-size: 13px; line-height: 1.55; }}
    .method summary {{ cursor: pointer; font-weight: 800; }}
    .method ol {{ margin: 12px 0 0; padding-left: 22px; }}
    .method li {{ margin-bottom: 10px; }}
    .formula {{ margin: 6px 0; padding: 7px 12px; background: #f3f6f4; border-left: 3px solid var(--accent); font-family: Georgia, "Times New Roman", serif; font-size: 15px; }}
    tr.athlete-row td {{ background: #e5ece8 !important; white-space: normal; }}
    td.outlier {{ color: #b74545; }}
    .chance {{ display: inline-block; width: 86px; height: 9px; margin-right: 8px; overflow: hidden; vertical-align: middle; background: #e8ece9; border-radius: 2px; }}
    .chance span {{ display: block; height: 100%; background: var(--accent); }}
    .small-button {{ min-height: 28px; padding: 4px 10px; }}
    .strength {{ color: #00796b; font-weight: 700; }}
    .weakness {{ color: #b74545; font-weight: 700; }}
    @media (max-width: 700px) {{
      .header-inner {{ width: auto; padding: 22px 16px 20px; }}
      main {{ padding: 0 16px 36px; }}
      .event-control {{ margin-inline: -16px; padding-inline: 16px; }}
      .event-control label {{ width: 100%; }}
      .tabs {{ margin-inline: -16px; padding-left: 12px; padding-right: 12px; }}
      .tab-button {{ padding-inline: 13px; }}
      .controls {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); padding: 13px; }}
      .controls label, .controls > div, .controls input, .controls select {{ width: 100%; }}
      .controls > label:nth-child(3), .controls > div, .controls > button {{ grid-column: 1 / -1; }}
      .controls > .cutoff-control {{ grid-column: 1 / -1; }}
      .years {{ display: grid; grid-template-columns: repeat(3, 1fr); }}
      .years label {{ justify-content: center; }}
      .metrics {{ grid-template-columns: 1fr; gap: 8px; }}
      .metric {{ padding-block: 12px; }}
      section {{ margin-top: 25px; }}
      h2 {{ font-size: 18px; }}
      .chart-heading {{ align-items: stretch; flex-direction: column; }}
      .chart-controls {{ width: 100%; }}
      .chart-controls label {{ flex: 1 1 0; }}
      .chart-controls select {{ width: 100%; min-width: 0; }}
      svg.chart {{ min-height: 260px; }}
    }}
    @media (max-width: 900px) {{ .chart-grid {{ grid-template-columns: 1fr; }} .chart-panel.wide {{ grid-column: auto; }} }}
  </style>
</head>
<body>
  <header>
    <div class="header-inner">
      <h1 id="eventTitle">IRONMAN Split Explorer</h1>
      <p id="eventSubtitle" class="subtitle"></p>
    </div>
  </header>
  <main>
    <div class="event-control">
      <label>Event <select id="eventSelect"></select></label>
    </div>
    <nav class="tabs" aria-label="Dashboard views" role="tablist">
      <button class="tab-button active" data-tab="splits" role="tab" aria-selected="true" aria-controls="splitsPanel">Split Explorer</button>
      <button class="tab-button" data-tab="qualification" role="tab" aria-selected="false" aria-controls="qualificationPanel">Qualification</button>
      <button class="tab-button" data-tab="odds" role="tab" aria-selected="false" aria-controls="oddsPanel">Can I Qualify?</button>
      <button class="tab-button" data-tab="easiest" role="tab" aria-selected="false" aria-controls="easiestPanel">Where to Qualify</button>
      <button class="tab-button" data-tab="overall" role="tab" aria-selected="false" aria-controls="overallPanel">Overall Times</button>
      <button class="tab-button" data-tab="statistics" role="tab" aria-selected="false" aria-controls="statisticsPanel">Race Statistics</button>
      <button class="tab-button" data-tab="compare" role="tab" aria-selected="false" aria-controls="comparePanel">Compare Races</button>
      <button class="tab-button" data-tab="kona" role="tab" aria-selected="false" aria-controls="konaPanel">Kona Trace</button>
      <button class="tab-button" data-tab="experimental" role="tab" aria-selected="false" aria-controls="experimentalPanel">Experimental</button>
    </nav>

    <div id="splitsPanel" class="tab-panel active">
      <div class="controls">
        <label>From (HH:MM:SS) <input id="fromTime" class="duration-input" type="text" inputmode="numeric" pattern="[0-9]+:[0-5][0-9]:[0-5][0-9]" value="04:25:00" aria-label="Minimum finishing time"></label>
        <label>To (HH:MM:SS) <input id="toTime" class="duration-input" type="text" inputmode="numeric" pattern="[0-9]+:[0-5][0-9]:[0-5][0-9]" value="04:30:00" aria-label="Maximum finishing time"></label>
        <label>Find athlete <input id="search" type="search" placeholder="Name, country, division"></label>
        <div><label>Years</label><div id="years" class="years"></div></div>
        <button id="download">Export filtered CSV ↓</button>
      </div>

      <div class="metrics">
        <div class="metric"><span>Finishers</span><strong id="finisherCount">0</strong></div>
        <div class="metric"><span>Selected range</span><strong id="rangeLabel">—</strong></div>
        <div class="metric"><span>Median finish</span><strong id="medianFinish">—</strong></div>
      </div>

      <section>
        <h2>Split-time summary</h2>
        <div class="table-wrap" style="max-height:none">
          <table class="summary"><thead><tr><th>Split</th><th>Average time (pace / speed) ± time σ</th><th>Minimum time (pace / speed)</th><th>Maximum time (pace / speed)</th></tr></thead><tbody id="summaryBody"></tbody></table>
        </div>
        <p id="distanceNote" class="note"></p>
      </section>

      <section>
        <h2>Matching finishers</h2>
        <div class="legend"><span><i class="swim"></i>Swim</span><span><i class="t1"></i>T1</span><span><i class="bike"></i>Bike</span><span><i class="t2"></i>T2</span><span><i class="run"></i>Run</span></div>
        <div class="table-wrap">
          <table><thead><tr><th>Year</th><th>Athlete</th><th>Division</th><th>Overall</th><th>Split profile</th><th>Swim</th><th>T1</th><th>Bike</th><th>T2</th><th>Run</th></tr></thead><tbody id="finishersBody"></tbody></table>
        </div>
      </section>
    </div>

    <div id="qualificationPanel" class="tab-panel">
      <p id="qualificationNote" class="note"></p>
      <div id="qualificationContent">
      <div class="metrics">
        <div class="metric"><span id="qualificationSlotsLabel">Official slot allocation</span><strong id="qualificationSlotsMetric">—</strong></div>
        <div class="metric"><span id="qualificationSelectedTotalLabel">Selected total (auto + performance pool)</span><strong id="qualificationSelectedTotalMetric">—</strong></div>
        <div class="metric"><span id="qualificationCheckLabel">Model vs. official qualifiers</span><strong id="qualificationCheckMetric">—</strong></div>
      </div>
      <div class="controls">
        <label>Gender <select id="qualificationGender"><option value="Male">Men</option><option value="Female">Women</option></select></label>
        <label>Displayed age group <select id="qualificationAgeGroup"></select></label>
        <label>Performance-pool declines (X) <input id="qualificationDeclines" type="number" min="0" step="1" value="0"></label>
        <label class="historical-rule-only">Age-group declines (Y) <input id="qualificationLegacyDeclines" type="number" min="0" step="1" value="0"></label>
        <label class="current-rule-only">Male age-group winners (auto) <input id="maleAutoSlots" type="number" readonly tabindex="-1"></label>
        <label class="current-rule-only">Female age-group winners (auto) <input id="femaleAutoSlots" type="number" readonly tabindex="-1"></label>
        <label class="current-rule-only">Male performance-pool slots <input id="maleSlots" type="number" min="0" step="1"></label>
        <label class="current-rule-only">Female performance-pool slots <input id="femaleSlots" type="number" min="0" step="1"></label>
        <button id="resetSlots" class="current-rule-only" type="button">Reset defaults</button>
      </div>
      <section>
        <h2 id="qualificationTableTitle">Qualification estimate by year</h2>
        <div class="table-wrap" style="max-height:none">
          <table><thead id="qualificationHead"></thead><tbody id="qualificationBody"></tbody></table>
        </div>
      </section>
      <div class="chart-grid">
        <div class="chart-panel wide"><h2 id="qualificationChartTitle">Qualification cutoff trends</h2><svg id="qualificationChart" class="chart" viewBox="0 0 1000 330"></svg></div>
        <div class="chart-panel wide"><h2 id="ageGroupTargetChartTitle">Time needed to qualify by age group</h2><p class="note">Finish at or below this raw time to qualify: by winning the age group or, in performance-pool years, by making the gender pool (whichever is slower). Gaps mean the age group had no finisher or no slot data.</p><svg id="ageGroupTargetChart" class="chart" viewBox="0 0 1000 350"></svg></div>
      </div>
      </div>
    </div>

    <div id="oddsPanel" class="tab-panel">
      <p class="note">Checks a finish time against every qualifying race-year in the dataset. With the average-course basis, your time is converted to each race-year's course and conditions using the factors from the Experimental tab, so a 10:00 athlete is expected to need longer in Nice than in Copenhagen. A time qualifies when it is at or below the time needed: the age-group winner's time or the performance-pool equivalent in performance-pool years, and the last allocated age-group slot in legacy years. Inserting your result is assumed not to change the slot split. Shortened race-years are excluded.</p>
      <div class="controls">
        <label>Distance <select id="oddsDistance"><option value="im">IRONMAN 140.6</option><option value="703">IRONMAN 70.3</option></select></label>
        <label>Gender <select id="oddsGender"><option value="Male">Men</option><option value="Female">Women</option></select></label>
        <label>Age group <select id="oddsAgeGroup"></select></label>
        <label>Your finish time (HH:MM:SS) <input id="oddsTime" class="duration-input" type="text" inputmode="numeric" pattern="[0-9]+:[0-5][0-9]:[0-5][0-9]" value="10:00:00" aria-label="Your finish time"></label>
        <label>Time basis <select id="oddsTimeBasis"><option value="average">Average course (adjusted per race-year)</option><option value="raw">Same time at every race</option></select></label>
        <label>Extra roll-down places <input id="oddsDeclines" type="number" min="0" step="1" value="0"></label>
      </div>
      <div class="metrics">
        <div class="metric"><span>Race-years where your time qualifies</span><strong id="oddsQualifiedMetric">—</strong></div>
        <div class="metric"><span>Easiest race for this age group</span><strong id="oddsBestMetric">—</strong></div>
        <div class="metric"><span id="oddsMedianNeededLabel">Time that qualified in half of race-years</span><strong id="oddsMedianNeededMetric">—</strong></div>
      </div>
      <section>
        <h2 id="oddsRankingTitle">Ease-of-qualification ranking</h2>
        <div class="table-wrap" style="max-height:none">
          <table><thead id="oddsRankingHead"></thead><tbody id="oddsRankingBody"></tbody></table>
        </div>
        <p id="oddsRankingNote" class="note"></p>
      </section>
      <div class="chart-grid">
        <div class="chart-panel wide">
          <h2>Share of race-years in which a finish time qualifies</h2>
          <p class="note">Each line is one race. A point at 75% means that finish time was fast enough in three of every four race-years; the dashed line marks your time. With the average-course basis the x-axis is time on an average course.</p>
          <svg id="oddsProbabilityChart" class="chart" viewBox="0 0 1000 420"></svg>
        </div>
        <div class="chart-panel wide">
          <h2 id="oddsRateTitle">Qualifiers per 100 starters by age group</h2>
          <p class="note">Median across race-years of age-group qualifiers divided by eligible age-group starters. Current mode uses projected no-decline qualifiers; historical mode uses the official allocation where the results flag it.</p>
          <svg id="oddsRateChart" class="chart" viewBox="0 0 1000 380"></svg>
        </div>
      </div>
      <section>
        <h2>Race-year detail</h2>
        <div class="table-wrap">
          <table><thead id="oddsDetailHead"></thead><tbody id="oddsDetailBody"></tbody></table>
        </div>
      </section>
    </div>

    <div id="easiestPanel" class="tab-panel">
      <p class="note">Ranks every qualifying race by your chance to qualify. For each past race-year the dashboard predicts your time on that course and in that year's conditions, compares it with the time needed in your age group (slots, rules, and field of that race-year), and turns the gap into a probability. Add your past results for a split-by-split prediction that rewards courses matching your strengths; without results, enter a finish time on an average course.</p>
      <div class="controls">
        <label>Distance <select id="easiestDistance"><option value="im">IRONMAN 140.6</option><option value="703">IRONMAN 70.3</option></select></label>
        <label>Gender <select id="easiestGender"><option value="Male">Men</option><option value="Female">Women</option></select></label>
        <label>Age group at your next race <select id="easiestAgeGroup"></select></label>
        <label>Finish time on an average course <input id="easiestTime" class="duration-input" type="text" inputmode="numeric" pattern="[0-9]+:[0-5][0-9]:[0-5][0-9]" value="10:30:00" aria-label="Finish time on an average course"></label>
        <label>Extra roll-down places <input id="easiestDeclines" type="number" min="0" step="1" value="0"></label>
      </div>
      <section>
        <h2>Your past results (optional)</h2>
        <p class="note">Search your name in the results database and click Add, or enter a result manually. Your results stay in this browser only.</p>
        <div class="controls">
          <label>Find my results <input id="easiestSearch" type="search" placeholder="Your name"></label>
        </div>
        <div class="table-wrap" style="max-height:280px">
          <table><thead id="easiestSearchHead"></thead><tbody id="easiestSearchBody"></tbody></table>
        </div>
        <div class="controls" style="margin-top:14px">
          <label>Race <select id="easiestManualRace"></select></label>
          <label>Year <select id="easiestManualYear"></select></label>
          <label>Age group then <select id="easiestManualAgeGroup"></select></label>
          <label>Swim <input id="easiestManualSwim" class="duration-input" type="text" placeholder="01:10:00"></label>
          <label>T1 <input id="easiestManualT1" class="duration-input" type="text" placeholder="00:05:00"></label>
          <label>Bike <input id="easiestManualBike" class="duration-input" type="text" placeholder="05:30:00"></label>
          <label>T2 <input id="easiestManualT2" class="duration-input" type="text" placeholder="00:04:00"></label>
          <label>Run <input id="easiestManualRun" class="duration-input" type="text" placeholder="03:45:00"></label>
          <button id="easiestManualAdd" type="button">Add result</button>
        </div>
        <p id="easiestManualNote" class="note"></p>
        <div class="table-wrap" style="max-height:none">
          <table><thead id="easiestResultsHead"></thead><tbody id="easiestResultsBody"></tbody></table>
        </div>
        <p id="easiestResultsNote" class="note"></p>
      </section>
      <section>
        <h2 id="easiestProfileTitle">Your strength profile</h2>
        <div class="table-wrap" style="max-height:none">
          <table><thead id="easiestProfileHead"></thead><tbody id="easiestProfileBody"></tbody></table>
        </div>
        <p id="easiestProfileNote" class="note"></p>
      </section>
      <div class="metrics" style="margin-top:28px">
        <div class="metric"><span>Best race for you</span><strong id="easiestBestMetric">—</strong></div>
        <div class="metric"><span>Estimated chance there</span><strong id="easiestChanceMetric">—</strong></div>
        <div class="metric"><span>Your finish time on an average course</span><strong id="easiestAbilityMetric">—</strong></div>
      </div>
      <section>
        <h2 id="easiestRankingTitle">Where you qualify most easily</h2>
        <div class="table-wrap" style="max-height:none">
          <table><thead id="easiestRankingHead"></thead><tbody id="easiestRankingBody"></tbody></table>
        </div>
        <p id="easiestRankingNote" class="note"></p>
      </section>
      <div class="chart-grid">
        <div class="chart-panel wide">
          <h2>Your margin in every past race-year</h2>
          <p class="note">Time needed minus your expected time. Points above zero meet the selected target, not proof of slot acceptance. Races are ordered by estimated chance; race-years where any finish met the target are not drawn.</p>
          <svg id="easiestMarginChart" class="chart" viewBox="0 0 1000 420"></svg>
        </div>
      </div>
      <section>
        <div class="chart-heading">
          <h2>Race-year detail</h2>
          <div class="chart-controls"><label>Race <select id="easiestDetailRace"></select></label></div>
        </div>
        <div class="table-wrap" style="max-height:none">
          <table><thead id="easiestDetailHead"></thead><tbody id="easiestDetailBody"></tbody></table>
        </div>
      </section>
      <section>
        <h2>How the ranking is calculated</h2>
        <details class="method">
          <summary>Formulas and assumptions</summary>
          <ol>
            <li><strong>Your ability per split on an average course.</strong> <span class="formula">a<sub>s</sub> = geometric mean over your results of t<sub>s</sub> × A(age group then) ÷ A(age group next race) ÷ f<sub>s</sub>(race-year)</span> for s = swim, bike, run. f<sub>s</sub> are the split factors from the Experimental tab; A is the age-grading standard, so results from a younger age group are slowed down to your next age group. Transitions: your T1 + T2 relative to that race-year's median, averaged over your results.</li>
            <li><strong>Expected time at race-year r.</strong> <span class="formula">T<sub>r</sub> = a<sub>swim</sub>·f<sub>swim</sub>(r) + a<sub>bike</sub>·f<sub>bike</sub>(r) + a<sub>run</sub>·f<sub>run</sub>(r) + transition ratio × median T1+T2(r)</span>. A strong cyclist loses less time than the field on a hard bike course, so hilly courses rank higher for them. Without results: T<sub>r</sub> = your average-course time × f<sub>overall</sub>(r).</li>
            <li><strong>Time needed N<sub>r</sub></strong> in your age group: the slower of the age-group winner and the performance-pool equivalent, or the last allocated age-group slot in legacy years. Manual extra places extend the pool or legacy age-group allocation separately. Reported, density and absence-scan modes use only compatible scope and cycle evidence; legacy scans rank raw age-group times with three consecutive absences, while gender-pool scans use fifteen. Extra places are not added to evidence estimates. Uncovered editions are excluded unless strict fallback is explicitly enabled. Changed allocation, modified course or a different cycle cannot silently borrow a cutoff.</li>
            <li><strong>Chance in race-year r.</strong> <span class="formula">p<sub>r</sub> = Φ( ln(N<sub>r</sub> ÷ T<sub>r</sub>) ÷ σ )</span>. Φ is the standard normal distribution; σ is how much one athlete's result varies from race to race after course and conditions are removed (the residual SD of the course model), widened by √(1 + 1/n) when your ability comes from n results.</li>
            <li><strong>Chance at a race</strong> = average of p<sub>r</sub> over its past race-years; every race-year is one equally likely scenario for field strength, slots, and weather. Races with few race-years are less certain.</li>
            <li><strong>Course fit</strong> = your expected time ÷ the expected time of same-level athletes (median splits of your age group at your average-course level) on this course, relative to an average course. Negative means the course suits your profile.</li>
          </ol>
          <p class="note">Pool estimates are unverified Kona-starter matching heuristics, not observed acceptance or predicted future cutoffs. They apply only to covered full-distance editions, not all historical years or 70.3 races. Not modelled: ceremony attendance, prior qualification, future changes in field size or allocation, and whether your results were your first IRONMAN (about 1% slower).</p>
        </details>
      </section>
    </div>

    <div id="overallPanel" class="tab-panel">
      <section>
        <h2>Overall finishing-time statistics</h2>
        <p class="note">Age-group metrics exclude professional (MPRO/FPRO) athletes; pro columns show their fastest times separately.</p>
        <div class="table-wrap" style="max-height:none">
          <table><thead><tr><th>Year</th><th>Finishers</th><th>Mean</th><th>Median</th><th>Top 20% cutoff</th><th>Top 100 cutoff</th><th>Top 50 cutoff</th><th>Top 20 cutoff</th><th>Top 10 Pro (M)</th><th>Top 10 Pro (F)</th></tr></thead><tbody id="overallBody"></tbody></table>
        </div>
      </section>
      <div class="chart-grid">
        <div class="chart-panel wide">
          <h2>Finishing-time density by year</h2>
          <p class="note">Each row is a normalized density on the same time axis; the dot marks the median. Density height compares distribution shape, not finisher count.</p>
          <svg id="densityChart" class="chart" viewBox="0 0 1000 500"></svg>
        </div>
        <div class="chart-panel"><h2>Mean and median</h2><svg id="averageChart" class="chart" viewBox="0 0 600 330"></svg></div>
        <div class="chart-panel"><h2>Top finisher cutoffs</h2><svg id="cutoffChart" class="chart" viewBox="0 0 600 330"></svg></div>
      </div>
    </div>

    <div id="statisticsPanel" class="tab-panel">
      <section>
        <h2>Race statistics by year</h2>
        <p class="note">Starters exclude no-shows (DNS). Completion rate is finishers divided by starters.</p>
        <div class="table-wrap" style="max-height:none">
          <table><thead><tr><th>Year</th><th>Registered</th><th>Starters</th><th>Finishers</th><th>DNS</th><th>DNF</th><th>DQ</th><th>Completion</th><th>Male finishers</th><th>Female finishers</th><th>% Male</th><th>% Female</th><th>Pro finishers</th><th>Avg finish</th><th>Median finish</th></tr></thead><tbody id="statisticsBody"></tbody></table>
        </div>
      </section>
      <div class="chart-grid">
        <div class="chart-panel wide"><h2>Finishers, DNS and DNF by year</h2><svg id="statusChart" class="chart" viewBox="0 0 1000 330"></svg></div>
        <div class="chart-panel"><h2>Male vs. female finishers</h2><svg id="genderChart" class="chart" viewBox="0 0 600 330"></svg></div>
        <div class="chart-panel"><h2>Completion rate</h2><svg id="completionChart" class="chart" viewBox="0 0 600 330"></svg></div>
      </div>
    </div>

    <div id="comparePanel" class="tab-panel">
      <p class="note">Races are grouped by distance: full-distance IRONMAN (Kona-qualifying) events are compared with each other, and 70.3 events are compared separately. Shortened or modified race-years are left out of cross-race comparisons: <span class="modified-course-list"></span>.</p>
      <fieldset class="controls">
        <legend>Visible years</legend>
        <div id="compareYears" class="years"></div>
      </fieldset>
      <div class="chart-grid">
        <div class="chart-panel wide">
          <div class="chart-heading">
            <h2>Field size and historical slots</h2>
            <div class="chart-controls">
              <label>Distance <select id="compareStatisticsDistance"><option value="im">IRONMAN 140.6</option><option value="703">IRONMAN 70.3</option></select></label>
            </div>
          </div>
          <p class="note">Finishers include professionals. Slot totals are the race-year's historical World Championship allocation, not the current-rule projection; unavailable allocations are omitted.</p>
          <h2>Total finishers</h2>
          <svg id="compareFinishers" class="chart" viewBox="0 0 1000 360"></svg>
          <h2>DNS rate (% of registered athletes)</h2>
          <svg id="compareDnsRatio" class="chart" viewBox="0 0 1000 360"></svg>
          <h2>DNF rate (% of starters)</h2>
          <svg id="compareDnfRatio" class="chart" viewBox="0 0 1000 360"></svg>
          <h2>Total World Championship slots</h2>
          <svg id="compareTotalSlots" class="chart" viewBox="0 0 1000 360"></svg>
        </div>
        <div class="chart-panel wide">
          <h2>IRONMAN (140.6) finish-time distribution</h2>
          <p class="note">Age-group finishers only (pros excluded); each point is one year's mean finish time for that race.</p>
          <svg id="compareImDistribution" class="chart" viewBox="0 0 1000 360"></svg>
        </div>
        <div class="chart-panel wide">
          <h2>70.3 finish-time distribution</h2>
          <p class="note">Age-group finishers only (pros excluded); each point is one year's mean finish time for that race.</p>
          <svg id="compare703Distribution" class="chart" viewBox="0 0 1000 360"></svg>
        </div>
        <div class="chart-panel wide">
          <div class="chart-heading">
            <h2>Split-time distribution by race</h2>
            <div class="chart-controls">
              <label>Distance <select id="compareSplitDistance"><option value="im">IRONMAN 140.6</option><option value="703">IRONMAN 70.3</option></select></label>
            </div>
          </div>
          <p class="note">Same view as the finish-time distribution, one chart per leg: age-group finishers only (pros excluded); each point is one year's mean split time for that race. Transitions exclude zero-duration placeholders. Hover a point for pace or speed, median, and athlete count. Raw times: course length, course profile, and conditions are all included.</p>
          <h3 class="chart-subtitle">Swim</h3>
          <svg id="compareSplitSwim" class="chart" viewBox="0 0 1000 340"></svg>
          <h3 class="chart-subtitle">T1</h3>
          <svg id="compareSplitT1" class="chart" viewBox="0 0 1000 340"></svg>
          <h3 class="chart-subtitle">Bike</h3>
          <svg id="compareSplitBike" class="chart" viewBox="0 0 1000 340"></svg>
          <h3 class="chart-subtitle">T2</h3>
          <svg id="compareSplitT2" class="chart" viewBox="0 0 1000 340"></svg>
          <h3 class="chart-subtitle">Run</h3>
          <svg id="compareSplitRun" class="chart" viewBox="0 0 1000 340"></svg>
        </div>
      </div>
      <div class="chart-grid">
        <div class="chart-panel wide">
          <div class="chart-heading">
            <h2>IRONMAN World Championship — raw qualifying time by race</h2>
            <div class="chart-controls">
              <label>Age group <select id="compareImAgeGroup"></select></label>
              <label>Gender <select id="compareImGender"><option value="Male">Men</option><option value="Female">Women</option></select></label>
            </div>
          </div>
          <p class="note">Qualifying races only, using each race's slot allocation for the selected system. Each point is one race-year's raw time needed (age-group win or performance pool, whichever is slower; last allocated slot in legacy years). Strict estimate: all age-group winners accept, no roll-down. Shortened race-years are excluded.</p>
          <svg id="compareImQualification" class="chart" viewBox="0 0 1000 360"></svg>
        </div>
        <div class="chart-panel wide">
          <div class="chart-heading">
            <h2>70.3 World Championship — raw qualifying time by race</h2>
            <div class="chart-controls">
              <label>Age group <select id="compare703AgeGroup"></select></label>
              <label>Gender <select id="compare703Gender"><option value="Male">Men</option><option value="Female">Women</option></select></label>
            </div>
          </div>
          <p class="note">Uses each race's 70.3 World Championship slot allocation for the selected system. Each point is one race-year's raw time needed (age-group win or performance pool, whichever is slower; last allocated slot in legacy years). Strict estimate: all age-group winners accept, no roll-down.</p>
          <svg id="compare703Qualification" class="chart" viewBox="0 0 1000 360"></svg>
        </div>
      </div>
      <div class="chart-grid">
        <div class="chart-panel wide">
          <div class="chart-heading">
            <h2>Mean finish time vs. raw qualifying time</h2>
            <div class="chart-controls">
              <label>Distance <select id="compareScatterDistance"><option value="im">IRONMAN 140.6</option><option value="703">IRONMAN 70.3</option></select></label>
              <label>Age group <select id="compareScatterAgeGroup"></select></label>
              <label>Gender <select id="compareScatterGender"><option value="Male">Men</option><option value="Female">Women</option></select></label>
            </div>
          </div>
          <p class="note">Each point is one race-year using age-group finishers only. Click or focus a race name in the legend to hide or show its trace; the global fit and residual chart update to use visible races only. Colored lines are per-race fits. Kona and shortened or modified race-years are excluded: <span class="modified-course-list"></span>.</p>
          <svg id="compareMeanQualification" class="chart" viewBox="0 0 1000 430"></svg>
        </div>
        <div class="chart-panel wide">
          <h2>Qualification-time difference from global fit</h2>
          <p class="note">Uses the same selected race-years as the plot above. Positive means a later, easier cutoff than the global fit predicts; negative means an earlier, harder cutoff.</p>
          <svg id="compareQualificationResidual" class="chart" viewBox="0 0 1000 390"></svg>
        </div>
      </div>
      <div class="chart-grid">
        <div class="chart-panel wide">
          <h2>Slot pressure per 100 eligible starters</h2>
          <p class="note">Uses the distance, system, age-group, and gender selected above. Performance-pool years use gender-wide slots and starters; legacy years use the selected age group's slots and starters. Higher values indicate more slot availability.</p>
          <svg id="compareSlotPressure" class="chart" viewBox="0 0 1000 390"></svg>
        </div>
        <div class="chart-panel wide">
          <h2>Qualifying cutoff percentile within the selected age group</h2>
          <p class="note">Percentage of split-complete finishers in the selected gender and age group at or faster than the estimated cutoff. Lower values indicate a more selective cutoff.</p>
          <svg id="compareCutoffPercentile" class="chart" viewBox="0 0 1000 390"></svg>
        </div>
        <div class="chart-panel wide">
          <h2>Selected age-group depth</h2>
          <p class="note">Number of split-complete finishers in the selected gender and age group for each race-year.</p>
          <svg id="compareAgeGroupDepth" class="chart" viewBox="0 0 1000 390"></svg>
        </div>
        <div class="chart-panel wide">
          <h2>Mean split contribution by race</h2>
          <p class="note">Across all available years for the selected gender and age group. Segment shares are calculated from swim, transitions, bike, and run times and normalized to 100%.</p>
          <svg id="compareSplitContribution" class="chart" viewBox="0 0 1000 430"></svg>
        </div>
        <div class="chart-panel wide">
          <h2>Qualification cutoff uncertainty across years</h2>
          <p class="note">Median raw cutoff with interquartile range and minimum/maximum whiskers for the selected system, gender, and age group. Wider ranges mean less stable historical qualification targets.</p>
          <svg id="compareQualificationUncertainty" class="chart" viewBox="0 0 1000 430"></svg>
        </div>
      </div>
    </div>

    <div id="konaPanel" class="tab-panel">
      <h2>Kona 2026 starters and qualifying results</h2>
      <p class="note">Age-group starters include Kona FIN, DNF, DQ and NC results, but exclude DNS and professionals. Matches use normalized full name, gender, country and compatible age groups. A matching finish is a possible qualifying result, not proof that the slot was accepted at that race.</p>
      <div class="controls" style="margin-top:18px">
        <label>Championship cycle <select id="konaCycle"><option value="2026">2026</option></select></label>
        <label>Gender <select id="konaGender"><option value="Male">Men</option><option value="Female">Women</option></select></label>
        <label hidden>Age group <select id="konaAgeGroup"><option value="30-34">30-34</option></select></label>
        <label>Summary evidence <select id="konaEvidence"><option value="reviewed">Reviewed sources</option><option value="single">Unverified: single</option><option value="all">Unverified: all</option></select></label>
        <label>Qualifying race <select id="konaRace"><option value="">All available races</option></select></label>
      </div>
      <div class="metrics">
        <div class="metric"><span>Championship age-group starters</span><strong id="konaStarterCount">0</strong></div>
        <div class="metric"><span>Matched to qualifying results</span><strong id="konaMatchedCount">0</strong></div>
        <div class="metric"><span>No match in available results</span><strong id="konaUnmatchedCount">0</strong></div>
      </div>
      <p id="konaCoverageNote" class="note"></p>
      <section>
        <h2>Pool cutoffs and conditional skipped places</h2>
        <p class="note">Two exploratory estimates are shown separately. The density estimate detects a drop in Kona matches; its minute-rounded range combines model support and match-selection sensitivity, not a confidence interval. The absence scan reports the last matched athlete before the first consecutive unmatched run after the fixed allocation: three within legacy age-group rankings, fifteen within gender performance pools. Missing matches, other qualifying races and special-entry routes can bias both methods. Neither proves acceptance or counts declined slots. Frankfurt 2026 uses a modified course, not a comparable full-distance finish time.</p>
        <p class="note">Reported last-accepted pool times are source-labeled references, separate from athlete matches. A time reported to the minute does not establish an exact pool rank. A match-based cutoff is unknown until a slot source is attributed. A single local finish does not establish that source: athletes may qualify elsewhere or enter through Legacy or another special route. Reviewed attributions are assumptions, not verified acceptances. Unverified modes show candidate maxima, not qualifying cutoffs. Skipped places = max(0, deepest attributed pool rank minus initial pool slots); prior qualification, automatic-slot roll-downs, reallocations and Kona DNS mean this is not a count of people who declined.</p>
        <div class="table-wrap" style="max-height:none">
          <table><thead><tr><th>Qualifying race</th><th>Year</th><th>Total slots</th><th>Initial pool slots</th><th>Matched starters</th><th>Attributed starters</th><th>Selected pool rank</th><th>Strict cutoff</th><th>Manual extra-place target</th><th>Reported last accepted</th><th>Density estimate</th><th>Absence scan</th><th>Modelled roll-down (%)</th><th>Selected time</th><th>Conditional skipped places</th><th>Selected starter</th></tr></thead><tbody id="konaSummaryBody"></tbody></table>
        </div>
      </section>
      <div class="chart-grid">
        <div class="chart-panel wide">
          <h2>Strict, reported and match-based cutoff times</h2>
          <svg id="konaCutoffChart" class="chart" viewBox="0 0 1000 420"></svg>
        </div>
        <div class="chart-panel wide">
          <h2>Conditional skipped places by qualifying race</h2>
          <svg id="konaSkippedChart" class="chart" viewBox="0 0 1000 380"></svg>
        </div>
        <div class="chart-panel wide">
          <h2>Absence-scan roll-down assumption</h2>
          <p class="note">The scan uses 3 consecutive absences within a legacy age group and 15 within a gender performance pool. This model-derived rate is an assumption, not an observed count or rate of declined slots.</p>
          <svg id="konaRollDownChart" class="chart" viewBox="0 0 1000 380"></svg>
        </div>
      </div>
      <section>
        <h2>Starter-to-result matches</h2>
        <div class="controls">
          <label>Find athlete <input id="konaSearch" type="search" placeholder="Name, country or age group"></label>
          <label>Match status <select id="konaMatchStatus"><option value="all">All starters</option><option value="matched">With a result match</option><option value="unmatched">Without a result match</option></select></label>
        </div>
        <p id="konaMatchNote" class="note"></p>
        <div class="table-wrap">
          <table><thead><tr><th>Championship starter</th><th>Country</th><th>Championship age group</th><th>Championship status</th><th>Possible qualifying race</th><th>Year</th><th>Race age group</th><th>Finish time</th><th>Pool rank</th><th>Age-graded time</th><th>Initial entitlement</th><th>Candidate races</th><th>Slot source (review)</th></tr></thead><tbody id="konaMatchesBody"></tbody></table>
        </div>
      </section>
      <section>
        <details class="method">
          <summary>2026-cycle race coverage</summary>
          <div class="table-wrap"><table><thead><tr><th>Qualifying race</th><th>Year</th><th>Date</th><th>Local results</th></tr></thead><tbody id="konaCoverageBody"></tbody></table></div>
        </details>
      </section>
    </div>

    <div id="experimentalPanel" class="tab-panel">
      <p class="note">Course and race-day conditions are estimated from athletes who finished several race-years of the same distance: each athlete is compared only with themselves, so ability cancels out. +5% means the same athlete was 5% slower than in the average qualifying race-year. Times are age-graded with the current Kona or 70.3 Standard first so that ageing between races does not make later years look harder, and the model removes the typical gain of returning athletes over their first appearance (<span id="experimentalReturningNote">—</span>). Shortened race-years are excluded. 70.3 factors compare Zell am See editions with each other only.</p>
      <div class="controls">
        <label>Distance <select id="experimentalDistance"><option value="im">IRONMAN 140.6</option><option value="703">IRONMAN 70.3</option></select></label>
        <label>Top finishers (%) <input id="experimentalPercentile" type="number" min="0.1" max="100" step="0.1" value="20"></label>
      </div>
      <section>
        <h2>How the factors are calculated</h2>
        <details class="method" open>
          <summary>Method, formulas, and fit statistics for the selected distance</summary>
          <ol>
            <li><strong>Match athletes across race-years.</strong> Identity = name tokens (accents removed, lower case, sorted, so "Anna Berg" = "BERG, Anna") + gender + country. An identity is dropped if it appears twice in one race-year (two different people), if its age groups imply inconsistent birth years, or if it has fewer than two race-years. Pros, results without an age group, and shortened or modified race-years are left out.</li>
            <li><strong>Age-grade.</strong> <span class="formula">t′ = t × A(gender, age group)</span> with A from the <span id="experimentalStandardName">—</span>, so ageing from M40-44 to M45-49 between two races is not mistaken for a harder course.</li>
            <li><strong>Fit, for each split separately:</strong>
              <div class="formula">ln t′<sub>i,r</sub> = a<sub>i</sub> + c<sub>r</sub> + b · R<sub>i,r</sub> + ε<sub>i,r</sub></div>
              a<sub>i</sub> = ability of athlete i; c<sub>r</sub> = effect of race-year r; R<sub>i,r</sub> = 1 if this is not the athlete's first race in the data, else 0; b = returning-athlete effect; ε = everything else. Least squares, solved by alternating means until nothing changes: a<sub>i</sub> = mean of (ln t′ − c<sub>r</sub> − b·R) over athlete i's races; c<sub>r</sub> = mean of (ln t′ − a<sub>i</sub> − b·R) over race-year r's athletes; b = mean of (ln t′ − a<sub>i</sub> − c<sub>r</sub>) over returning results. Because every athlete is compared only with themselves, ability cancels out.</li>
            <li><strong>Remove outliers and refit.</strong> Results with |ε| above 4 × 1.4826 × median |ε| (a robust 4-σ limit: mechanicals, walked marathons, wrong matches) are dropped.</li>
            <li><strong>Normalise.</strong> c<sub>r</sub> is shifted to average 0 over qualifying race-years. Race-year factor <span class="formula">f<sub>r</sub> = e<sup>c<sub>r</sub></sup></span>; f = 1.05 is shown as +5%.</li>
            <li><strong>Split into course, season, and conditions.</strong> <span class="formula">ln f<sub>race,year</sub> = C<sub>race</sub> + S<sub>year</sub> + conditions</span>, fitted the same way over all race-years; seasons average 0 over qualifying race-years.</li>
            <li><strong>Use.</strong> Course-adjusted time = t ÷ f<sub>r</sub>. A time T on an average course is expected to be T × f<sub>r</sub> at race-year r.</li>
          </ol>
          <div class="table-wrap" style="max-height:none">
            <table><thead><tr><th>Split</th><th>Matched athletes</th><th>Results used</th><th>Outliers removed</th><th title="Results further than this from the athlete's own level are dropped.">Outlier limit</th><th title="Typical deviation of a single result from ability × race-year factor.">Residual SD</th><th title="Returning results relative to the athlete's first appearance.">Returning effect b</th></tr></thead><tbody id="experimentalFitBody"></tbody></table>
          </div>
        </details>
      </section>
      <section>
        <h2>Course and conditions by race</h2>
        <div class="table-wrap" style="max-height:none">
          <table><thead id="experimentalFactorHead"></thead><tbody id="experimentalFactorBody"></tbody></table>
        </div>
        <p id="experimentalFactorNote" class="note"></p>
      </section>
      <section>
        <div class="chart-heading">
          <h2 id="experimentalBreakdownTitle">Factor breakdown by race-year</h2>
        </div>
        <div class="table-wrap" style="max-height:none">
          <table><thead id="experimentalBreakdownHead"></thead><tbody id="experimentalBreakdownBody"></tbody></table>
        </div>
        <p id="experimentalBreakdownNote" class="note"></p>
      </section>
      <div class="chart-grid">
        <div class="chart-panel wide">
          <h2 id="experimentalFactorTitle">Race-year difficulty</h2>
          <p class="note">Each point is one race-year relative to the average qualifying race-year: course, season and race-day conditions combined. Points above zero were slower for the same athletes. This is the factor used for course-adjusted times.</p>
          <svg id="experimentalFactorChart" class="chart" viewBox="0 0 1000 400"></svg>
        </div>
        <div class="chart-panel wide">
          <h2>Season effect across all races</h2>
          <p class="note">Common year-to-year change for the same athletes after removing each course's own difficulty. It captures whatever made a whole season faster or slower, for example equipment progress on the bike.</p>
          <svg id="experimentalSeasonChart" class="chart" viewBox="0 0 1000 340"></svg>
        </div>
        <div class="chart-panel wide">
          <h2 id="experimentalFieldTitle">Course-adjusted all-cohort field strength</h2>
          <p class="note">Top-percentage cutoff across both genders and all age groups, divided by the race-year's overall factor. Lower means a stronger field.</p>
          <svg id="experimentalFieldChart" class="chart" viewBox="0 0 1000 400"></svg>
        </div>
        <div class="chart-panel wide">
          <div class="chart-heading">
            <h2 id="experimentalNeededTitle">Course-adjusted time needed to qualify</h2>
          </div>
          <p class="note">Median qualification target across available genders and age groups, divided by the race-year's overall factor. Uses the selected qualification system and shared race-year filter.</p>
          <svg id="experimentalNeededChart" class="chart" viewBox="0 0 1000 400"></svg>
        </div>
        <div class="chart-panel wide">
          <h2>Bike course check: GPX model vs. athlete data</h2>
          <p class="note">Bike difficulty relative to the mean of the compared courses. The GPX model uses one track per race and a 200 W reference rider; the athlete data is the season-adjusted bike course effect over all race-years. The model gets the order of courses mostly right but compresses the differences: it rides faster than a typical age-grouper, and it ignores road surface, wind, corners, and drafting. Noisy elevation also inflates flat coastal courses. The Lanzarote track ends about 175 m above its start (altimeter drift on the final descent), which changes its factor by about 0.4%.</p>
          <svg id="experimentalGpxChart" class="chart" viewBox="0 0 1000 380"></svg>
        </div>
      </div>
      <section>
        <h2>Worked example: athletes who raced several race-years</h2>
        <div class="table-wrap">
          <table><thead id="experimentalAthleteHead"></thead><tbody id="experimentalAthleteBody"></tbody></table>
        </div>
        <p id="experimentalAthleteNote" class="note"></p>
      </section>
      <section>
        <div class="chart-heading">
          <h2>Raw-data check: athletes who raced both courses</h2>
        </div>
        <div class="metrics">
          <div class="metric"><span>Athletes who raced both</span><strong id="experimentalPairCount">—</strong></div>
          <div class="metric"><span>Same athletes at B vs. A (data)</span><strong id="experimentalPairObserved">—</strong></div>
          <div class="metric"><span>Model factors for the same race-years</span><strong id="experimentalPairModel">—</strong></div>
        </div>
        <div class="table-wrap">
          <table><thead id="experimentalPairHead"></thead><tbody id="experimentalPairBody"></tbody></table>
        </div>
        <p id="experimentalPairNote" class="note"></p>
      </section>
    </div>
  </main>

  <script src="dashboard_data.js"></script>
  <script>
    const DATASETS = window.DASHBOARD_DATA;
    const splits = [
      ["Swim", "swim"], ["T1", "t1"], ["Bike", "bike"], ["T2", "t2"], ["Run", "run"]
    ];
    const eventSelect = document.getElementById("eventSelect");
    const fromInput = document.getElementById("fromTime");
    const toInput = document.getElementById("toTime");
    const searchInput = document.getElementById("search");
    const yearsElement = document.getElementById("years");
    const qualificationAgeGroup = document.getElementById("qualificationAgeGroup");
    const qualificationGender = document.getElementById("qualificationGender");
    const qualificationDeclines = document.getElementById("qualificationDeclines");
    const qualificationLegacyDeclines = document.getElementById("qualificationLegacyDeclines");
    const experimentalPercentile = document.getElementById("experimentalPercentile");
    const maleAutoSlots = document.getElementById("maleAutoSlots");
    const femaleAutoSlots = document.getElementById("femaleAutoSlots");
    const maleSlots = document.getElementById("maleSlots");
    const femaleSlots = document.getElementById("femaleSlots");
    const oddsDistance = document.getElementById("oddsDistance");
    const oddsGender = document.getElementById("oddsGender");
    const oddsAgeGroup = document.getElementById("oddsAgeGroup");
    const oddsTime = document.getElementById("oddsTime");
    const oddsDeclines = document.getElementById("oddsDeclines");
    const oddsTimeBasis = document.getElementById("oddsTimeBasis");
    const experimentalDistance = document.getElementById("experimentalDistance");
    const compareSplitDistance = document.getElementById("compareSplitDistance");
    const splitStatsCache = new Map();
    const athleteIndexCache = new Map();
    const genderTimeCache = new Map();
    const slotAllocations = {{}};
    const hiddenMeanQualificationRaces = new Set();
    const selectedAgeGroupRecordCache = new Map();
    let activeTab = "splits";
    let qualificationSystem = "current";
    function dataset() {{ return DATASETS[eventSelect.value]; }}
    function escapeHtml(value) {{
      return String(value ?? "").replace(/[&<>"']/g, character => ({{ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }})[character]);
    }}
    function isModifiedCourse(eventId, year) {{
      return Boolean(DATASETS[eventId]?.modified_courses?.[year]);
    }}
    function yearCell(eventId, year) {{
      const modification = DATASETS[eventId]?.modified_courses?.[year];
      return modification ? `<span title="${{escapeHtml(modification)}}">${{year}} ⚠</span>` : year;
    }}
    function isQualifyingEvent(eventId) {{
      return DATASETS[eventId]?.qualifying !== false;
    }}
    function courseFactor(eventId, year, split = "overall") {{
      const value = DATASETS[eventId]?.course_factors?.[year]?.[split];
      return Number.isFinite(value) ? value : null;
    }}

    function parseTime(value) {{
      if (!/^\\d+:[0-5]\\d:[0-5]\\d$/.test(value.trim())) return NaN;
      const parts = value.split(":").map(Number);
      return parts[0] * 3600 + parts[1] * 60 + parts[2];
    }}
    function duration(seconds) {{
      if (!Number.isFinite(seconds)) return "—";
      const rounded = Math.round(seconds);
      const hours = Math.floor(rounded / 3600);
      const minutes = Math.floor((rounded % 3600) / 60);
      const secs = rounded % 60;
      return `${{String(hours).padStart(2, "0")}}:${{String(minutes).padStart(2, "0")}}:${{String(secs).padStart(2, "0")}}`;
    }}
    function qualificationDuration(seconds) {{
      return Number.isFinite(seconds) ? duration(Math.floor(seconds)) : "—";
    }}
    function pace(seconds) {{
      const rounded = Math.round(seconds);
      return `${{Math.floor(rounded / 60)}}:${{String(rounded % 60).padStart(2, "0")}}`;
    }}
    function metric(split, seconds, distances = dataset().distances) {{
      if (split === "swim") return `${{pace(seconds / (distances.swim / 100))}}/100 m`;
      if (split === "bike") return `${{(distances.bike / (seconds / 3600)).toFixed(1)}} km/h`;
      if (split === "run") return `${{pace(seconds / distances.run)}}/km`;
      return "";
    }}
    function withMetric(split, seconds) {{
      const value = metric(split, seconds);
      return value ? `${{duration(seconds)}} (${{value}})` : duration(seconds);
    }}
    function selectedYears() {{
      return new Set(compareYears.filter(compareYearVisible));
    }}
    function filteredData() {{
      const lower = parseTime(fromInput.value);
      const upper = parseTime(toInput.value);
      const query = searchInput.value.trim().toLowerCase();
      const activeYears = selectedYears();
      return dataset().records.filter(row => row.overall >= lower && row.overall <= upper && activeYears.has(row.year))
        .filter(row => !query || `${{row.name}} ${{row.country}} ${{row.division}} ${{row.bib}}`.toLowerCase().includes(query))
        .sort((a, b) => a.overall - b.overall || a.name.localeCompare(b.name));
    }}
    function summaryRows(rows) {{
      if (!rows.length) return `<tr><td colspan="4" class="empty">No finishers in this range.</td></tr>`;
      return splits.map(([label, key]) => {{
        const values = rows.map(row => row[key]).filter(value => value > 0);
        if (!values.length) return `<tr><td>${{label}}</td><td colspan="3">No recorded values</td></tr>`;
        const average = values.reduce((sum, value) => sum + value, 0) / values.length;
        const sigma = Math.sqrt(values.reduce((sum, value) => sum + (value - average) ** 2, 0) / values.length);
        const averageMetric = metric(key, average);
        const averageText = averageMetric ? `${{duration(average)}} (${{averageMetric}})` : duration(average);
        return `<tr><td>${{label}}</td><td>${{averageText}} ± ${{duration(sigma)}}</td><td>${{withMetric(key, Math.min(...values))}}</td><td>${{withMetric(key, Math.max(...values))}}</td></tr>`;
      }}).join("");
    }}
    function finisherRows(rows) {{
      if (!rows.length) return `<tr><td colspan="10" class="empty">Adjust the range or year filters to find finishers.</td></tr>`;
      return rows.map(row => {{
        const bars = splits.map(([, key]) => `<span class="${{key}}" style="width:${{100 * row[key] / row.overall}}%"></span>`).join("");
        return `<tr><td>${{row.year}}</td><td><strong>${{escapeHtml(row.name)}}</strong><br><small>${{escapeHtml(row.country)}} · #${{escapeHtml(row.bib)}}</small></td><td>${{escapeHtml(row.division)}}</td><td>${{duration(row.overall)}}</td><td><div class="split-bar">${{bars}}</div></td><td>${{withMetric("swim", row.swim)}}</td><td>${{duration(row.t1)}}</td><td>${{withMetric("bike", row.bike)}}</td><td>${{duration(row.t2)}}</td><td>${{withMetric("run", row.run)}}</td></tr>`;
      }}).join("");
    }}
    function median(values) {{
      const middle = Math.floor(values.length / 2);
      return values.length % 2 ? values[middle] : (values[middle - 1] + values[middle]) / 2;
    }}
    function attachPointTooltips(svg) {{
      const panel = svg.closest(".chart-panel");
      let tooltip = panel.querySelector(".chart-tooltip");
      if (!tooltip) {{
        tooltip = document.createElement("div");
        tooltip.className = "chart-tooltip";
        tooltip.setAttribute("role", "tooltip");
        panel.appendChild(tooltip);
      }}
      const show = (point, clientX, clientY) => {{
        tooltip.innerHTML = `<strong>${{point.dataset.series}}</strong>${{point.dataset.year}} · ${{point.dataset.value}}`;
        const panelBox = panel.getBoundingClientRect();
        tooltip.style.display = "block";
        const gap = 12;
        const padding = 4;
        let left = clientX - panelBox.left - tooltip.offsetWidth / 2;
        let top = clientY - panelBox.top - tooltip.offsetHeight - gap;
        left = Math.max(padding, Math.min(left, panelBox.width - tooltip.offsetWidth - padding));
        if (top < padding) top = clientY - panelBox.top + gap;
        tooltip.style.left = `${{left}}px`;
        tooltip.style.top = `${{top}}px`;
      }};
      svg.querySelectorAll(".data-point").forEach(point => {{
        point.addEventListener("pointerenter", event => show(point, event.clientX, event.clientY));
        point.addEventListener("pointermove", event => show(point, event.clientX, event.clientY));
        point.addEventListener("pointerleave", () => tooltip.style.display = "none");
        point.addEventListener("focus", () => {{
          const box = point.getBoundingClientRect();
          show(point, box.left + box.width / 2, box.top);
        }});
        point.addEventListener("blur", () => tooltip.style.display = "none");
      }});
    }}
    function lineChart(elementId, labels, series, formatValue = null, options = {{}}) {{
      if (labels.every(label => compareYears.includes(label))) {{
        const indices = labels.map((label, index) => compareYearVisible(label) ? index : -1).filter(index => index >= 0);
        labels = indices.map(index => labels[index]);
        series = series.map(item => ({{ ...item, values: indices.map(index => item.values[index]) }}));
      }} else {{
        series = series.filter(item => !compareYears.includes(item.label) || compareYearVisible(item.label));
      }}
      const svg = document.getElementById(elementId);
      const width = svg.viewBox.baseVal.width;
      const height = svg.viewBox.baseVal.height;
      const legendColumnWidth = 285;
      const legendColumns = Math.max(1, Math.floor((width - 92) / legendColumnWidth));
      const legendRows = Math.ceil(series.length / legendColumns);
      const margin = {{ left: 68, right: 24, top: 16 + legendRows * 22, bottom: 48 }};
      const values = series.flatMap(item => item.values.filter(Number.isFinite));
      if (!values.length) {{ svg.innerHTML = `<text x="20" y="40">No data available</text>`; return; }}
      const format = formatValue || (elementId === "qualificationChart" ? qualificationDuration : duration);
      const tickFormat = formatValue ? (value => format(value)) : (value => format(value).slice(0, 5));
      let minimum = Math.min(...values), maximum = Math.max(...values);
      if (options.zeroBaseline) {{
        minimum = 0;
        maximum += Math.max(maximum * 0.08, formatValue ? 1 : 60);
      }} else {{
        const padding = Math.max((maximum - minimum) * 0.12, formatValue ? 1 : 60);
        minimum -= padding; maximum += padding;
      }}
      const x = index => margin.left + index * (width - margin.left - margin.right) / Math.max(labels.length - 1, 1);
      const y = value => margin.top + (maximum - value) * (height - margin.top - margin.bottom) / (maximum - minimum);
      let markup = "";
      for (let tick = 0; tick <= 4; tick++) {{
        const value = minimum + (maximum - minimum) * tick / 4;
        const yPosition = y(value);
        markup += `<line class="grid" x1="${{margin.left}}" y1="${{yPosition}}" x2="${{width - margin.right}}" y2="${{yPosition}}"/><text x="${{margin.left - 8}}" y="${{yPosition + 4}}" text-anchor="end">${{tickFormat(value)}}</text>`;
      }}
      labels.forEach((label, index) => markup += `<text x="${{x(index)}}" y="${{height - 18}}" text-anchor="middle">${{label}}</text>`);
      markup += `<line class="axis" x1="${{margin.left}}" y1="${{margin.top}}" x2="${{margin.left}}" y2="${{height - margin.bottom}}"/><line class="axis" x1="${{margin.left}}" y1="${{height - margin.bottom}}" x2="${{width - margin.right}}" y2="${{height - margin.bottom}}"/>`;
      series.forEach((item, seriesIndex) => {{
        const points = item.values.map((value, index) => Number.isFinite(value) ? `${{x(index)}},${{y(value)}}` : null).filter(Boolean).join(" ");
        markup += `<polyline points="${{points}}" fill="none" stroke="${{item.color}}" stroke-width="2.2"/>`;
        item.values.forEach((value, index) => {{
          if (Number.isFinite(value)) {{
            const valueText = format(value);
            const accessibleLabel = `${{item.label}}, ${{labels[index]}}, ${{valueText}}`;
            markup += `<circle class="data-point" cx="${{x(index)}}" cy="${{y(value)}}" r="4" fill="${{item.color}}" tabindex="0" role="img" aria-label="${{accessibleLabel}}" data-series="${{item.label}}" data-year="${{labels[index]}}" data-value="${{valueText}}"><title>${{accessibleLabel}}</title></circle>`;
          }}
        }});
        const legendColumn = seriesIndex % legendColumns;
        const legendRow = Math.floor(seriesIndex / legendColumns);
        const legendX = margin.left + legendColumn * legendColumnWidth;
        const legendY = 15 + legendRow * 22;
        markup += `<line x1="${{legendX}}" y1="${{legendY}}" x2="${{legendX + 18}}" y2="${{legendY}}" stroke="${{item.color}}" stroke-width="3"/><text x="${{legendX + 23}}" y="${{legendY + 4}}">${{item.label}}</text>`;
      }});
      svg.innerHTML = markup;
      attachPointTooltips(svg);
    }}
    function densityChart(yearlyTimes) {{
      const svg = document.getElementById("densityChart");
      const width = 1000;
      const entries = Object.entries(yearlyTimes).filter(([year, values]) => compareYearVisible(year) && values.length);
      const allValues = entries.flatMap(([, values]) => values).sort((left, right) => left - right);
      if (!allValues.length) {{ svg.innerHTML = `<text x="20" y="40">No data available</text>`; return; }}

      const percentile = (values, fraction) => values[Math.min(values.length - 1, Math.floor((values.length - 1) * fraction))];
      const minimum = percentile(allValues, 0.01);
      const maximum = percentile(allValues, 0.99);
      const range = Math.max(maximum - minimum, 1);
      const bandwidth = Math.max(300, Math.min(1200, range / 30));
      const sampleCount = 180;
      const rowHeight = 58;
      const margin = {{ left: 88, right: 26, top: 18, bottom: 52 }};
      const height = margin.top + entries.length * rowHeight + margin.bottom;
      const plotBottom = height - margin.bottom;
      const x = value => margin.left + (value - minimum) * (width - margin.left - margin.right) / range;
      const colors = ["#006d77", "#e76f51", "#277da1", "#7a6f3d", "#8f5d8c", "#2a9d8f", "#bc4749"];
      svg.setAttribute("viewBox", `0 0 ${{width}} ${{height}}`);

      let markup = "";
      for (let tick = 0; tick <= 6; tick++) {{
        const value = minimum + range * tick / 6;
        const xPosition = x(value);
        markup += `<line class="grid" x1="${{xPosition}}" y1="${{margin.top}}" x2="${{xPosition}}" y2="${{plotBottom}}"/><text x="${{xPosition}}" y="${{height - 20}}" text-anchor="middle">${{duration(value).slice(0, 5)}}</text>`;
      }}

      entries.forEach(([year, values], seriesIndex) => {{
        const color = compareYearColor(year);
        const baseline = margin.top + (seriesIndex + 1) * rowHeight - 10;
        const density = Array.from({{ length: sampleCount }}, (_, index) => {{
          const value = minimum + range * index / (sampleCount - 1);
          const total = values.reduce((sum, observation) => {{
            const distance = (value - observation) / bandwidth;
            return sum + Math.exp(-0.5 * distance * distance);
          }}, 0);
          return {{ value, density: total / values.length }};
        }});
        const peak = Math.max(...density.map(point => point.density));
        const ridgeHeight = rowHeight - 18;
        const points = density.map(point => `${{x(point.value)}},${{baseline - ridgeHeight * point.density / peak}}`).join(" L ");
        const medianValue = median(values);
        const medianX = x(medianValue);
        const medianText = duration(medianValue).slice(0, 5);
        const accessibleLabel = `${{year}} median, ${{medianText}}`;
        markup += `<line class="grid" x1="${{margin.left}}" y1="${{baseline}}" x2="${{width - margin.right}}" y2="${{baseline}}"/>`;
        markup += `<path d="M ${{x(minimum)}},${{baseline}} L ${{points}} L ${{x(maximum)}},${{baseline}} Z" fill="${{color}}" fill-opacity="0.22" stroke="${{color}}" stroke-width="2"/>`;
        markup += `<text x="${{margin.left - 12}}" y="${{baseline - 12}}" text-anchor="end" font-weight="700">${{year}}</text><text x="${{margin.left - 12}}" y="${{baseline + 4}}" text-anchor="end">n=${{values.length.toLocaleString()}}</text>`;
        markup += `<line x1="${{medianX}}" y1="${{baseline - ridgeHeight}}" x2="${{medianX}}" y2="${{baseline}}" stroke="${{color}}" stroke-dasharray="3 3"/><circle class="data-point" cx="${{medianX}}" cy="${{baseline}}" r="4.5" fill="${{color}}" tabindex="0" role="img" aria-label="${{accessibleLabel}}" data-series="Median finish" data-year="${{year}}" data-value="${{medianText}}"><title>${{accessibleLabel}}</title></circle>`;
      }});
      markup += `<line class="axis" x1="${{margin.left}}" y1="${{plotBottom}}" x2="${{width - margin.right}}" y2="${{plotBottom}}"/><text x="${{(margin.left + width - margin.right) / 2}}" y="${{height - 3}}" text-anchor="middle">Finish time (HH:MM)</text>`;
      svg.innerHTML = markup;
      attachPointTooltips(svg);
    }}
    function qualificationAgeGroups() {{
      const targets = qualificationSystem === "historical"
        ? dataset().historical_qualification.targets
        : dataset().qualification.targets;
      const male = new Set(targets.filter(row => row.gender === "Male").map(row => row.division.slice(1)));
      const female = new Set(targets.filter(row => row.gender === "Female").map(row => row.division.slice(1)));
      return [...male].filter(ageGroup => female.has(ageGroup)).sort((left, right) => Number(left.split("-")[0]) - Number(right.split("-")[0]));
    }}
    function divisionFor(gender, ageGroup) {{
      return `${{gender === "Male" ? "M" : "F"}}${{ageGroup}}`;
    }}
    function poolThreshold(pool, places) {{
      if (!Number.isFinite(places) || places <= 0) return -Infinity;
      return places > pool.length ? Infinity : pool[places - 1].age_graded;
    }}
    // Raw finish time needed in one race-year: the last allocated age-group slot
    // (legacy) or the slower of the age-group winner and the pool equivalent.
    function strictQualificationStandard(eventId, year, gender, ageGroup, system, options = {{}}) {{
      const ds = DATASETS[eventId];
      if (!ds || ds.qualifying === false) return null;
      const extraPlaces = options.extraPlaces || 0;
      const division = divisionFor(gender, ageGroup);
      const genderKey = gender.toLowerCase();
      const stats = ds.division_stats?.[year]?.[division];
      const base = {{
        eventId, year, division,
        starters: stats?.starters ?? 0,
        finishers: stats?.finishers ?? 0,
        median: stats?.median ?? null,
      }};
      const performance = (yearPool, performanceSlots, ratio, method, extra) => {{
        const pool = yearPool?.[genderKey] || [];
        const ageGraded = poolThreshold(pool, performanceSlots + extraPlaces);
        const poolEquivalent = Number.isFinite(ratio) ? ageGraded / ratio : null;
        const winner = yearPool?.winners?.[division] ?? null;
        return {{
          ...base, ...extra, method, scope: "gender", ratio: ratio ?? null,
          performanceSlots, ageGraded, poolEquivalent, winner,
          needed: winner === null ? Infinity : Math.max(winner, poolEquivalent ?? -Infinity),
          qualifiers: (yearPool?.automatic?.[genderKey]?.includes(division) ? 1 : 0)
            + pool.slice(0, performanceSlots).filter(entry => entry.division === division).length,
        }};
      }};
      if (system === "historical") {{
        const historical = ds.historical_qualification;
        const rows = historical.targets.filter(row => row.year === year);
        if (!rows.length) return null;
        const target = rows.find(row => row.division === division);
        if (!target) {{
          // No slot row: nobody finished in this age group, so a finisher would take its slot.
          return {{
            ...base, method: rows[0].method, scope: rows[0].slot_scope, source: rows[0].source,
            needed: Infinity, winner: null, poolEquivalent: null, ageGraded: null, qualifiers: 0,
          }};
        }}
        if (target.slot_scope === "age group") {{
          const places = target.slots + extraPlaces;
          return {{
            ...base, method: target.method, scope: "age group", source: target.source,
            slots: target.slots, winner: target.winner, poolEquivalent: null, ageGraded: null,
            needed: places <= 0 ? -Infinity : places > target.times.length ? Infinity : target.times[places - 1],
            qualifiers: target.slots, official: target.official_qualifiers,
          }};
        }}
        return performance(
          historical.pools[year], target.performance_slots, target.ratio, target.method,
          {{ source: target.source, official: target.official_qualifiers, check: target.official_check, automaticSlots: target.automatic_slots }},
        );
      }}
      const summary = ds.qualification.summaries.find(row => row.year === year);
      if (!summary) return null;
      const performanceSlots = Number.isFinite(options.performanceSlots)
        ? options.performanceSlots
        : slotAllocations[eventId]?.[genderKey] ?? summary[`${{genderKey}}_perf`];
      return performance(
        ds.qualification.pools[year], performanceSlots, ds.qualification.ratios[division],
        `${{ds.qualification.standard_cycle}}-cycle rules, current allocation`,
        {{ automaticSlots: summary[`${{genderKey}}_auto`] }},
      );
    }}
    function qualifyingResult(standard, time) {{
      if (!standard || !Number.isFinite(time)) return null;
      if (time > standard.needed) return {{ qualifies: false, via: "not qualified" }};
      if (standard.scope === "age group") return {{ qualifies: true, via: "age-group slot" }};
      if (standard.winner === null || time <= standard.winner) return {{ qualifies: true, via: "age-group win" }};
      return {{ qualifies: true, via: "performance pool" }};
    }}
    function neededText(seconds) {{
      if (seconds === Infinity) return "any finish";
      if (seconds === -Infinity) return "no slot";
      return qualificationDuration(seconds);
    }}
    // Which route sets the strict raw target: the legacy age-group slot, the
    // age-group winner (automatic slot) or the gender performance pool.
    function targetRouteText(standard) {{
      if (!standard) return "";
      if (standard.needed === Infinity) return standard.scope === "age group" ? "fewer finishers than slots" : "no AG finisher";
      if (standard.needed === -Infinity) return "no slot";
      if (standard.scope === "age group") return `AG place ${{standard.slots}}`;
      return standard.winner !== null && standard.needed === standard.winner ? "set by AG winner" : "set by gender pool";
    }}
    function qualifierRateText(standard) {{
      if (!standard || !(standard.finishers > 0) || !Number.isFinite(standard.qualifiers)) return "—";
      const qualifiers = Math.min(standard.qualifiers, standard.finishers);
      return `${{qualifiers}} / ${{standard.finishers}} (${{(100 * qualifiers / standard.finishers).toFixed(1)}}%)`;
    }}
    // Seconds the raw target moves when the ranking rolls down by `places` more slots.
    function rollDownSensitivityText(base, deeper) {{
      if (!base || !deeper || !Number.isFinite(base.needed) || !Number.isFinite(deeper.needed)) return "—";
      return signedDuration(Math.max(0, deeper.needed - base.needed));
    }}
    function currentRatio(gender) {{
      return dataset().qualification.ratios?.[divisionFor(gender, qualificationAgeGroup.value)];
    }}
    function hasSlotOverride() {{
      return Object.prototype.hasOwnProperty.call(slotAllocations, eventSelect.value);
    }}
    function displayAllocation() {{
      return slotAllocations[eventSelect.value]
        || dataset()?.default_slots
        || {{ male: 0, female: 0 }};
    }}
    function poolEntry(year, gender, performanceSlots, rejections = 0) {{
      const pool = dataset().qualification.pools[year]?.[gender.toLowerCase()] || [];
      const index = performanceSlots + rejections - 1;
      return index >= 0 && index < pool.length ? pool[index] : null;
    }}
    function poolCutoff(year, gender, performanceSlots, rejections = 0) {{
      const entry = poolEntry(year, gender, performanceSlots, rejections);
      return typeof entry === "number" ? entry : entry?.age_graded ?? null;
    }}
    function dynamicQualificationSummaries() {{
      const rawSummaries = dataset().qualification.summaries;
      if (!hasSlotOverride()) {{
        // No manual override: show the exact historical per-year values (matches Compare Races).
        return rawSummaries;
      }}
      const allocations = slotAllocations[eventSelect.value];
      const offsets = dataset().qualification.rank_offsets;
      return rawSummaries.map(row => {{
        const malePerformance = Math.max(0, allocations.male);
        const femalePerformance = Math.max(0, allocations.female);
        return {{
          ...row,
          male_perf: malePerformance,
          female_perf: femalePerformance,
          male_cutoff: poolCutoff(row.year, "male", malePerformance),
          female_cutoff: poolCutoff(row.year, "female", femalePerformance),
          ranks: Object.fromEntries(offsets.map(offset => [String(offset), {{
            male: poolCutoff(row.year, "male", malePerformance, offset),
            female: poolCutoff(row.year, "female", femalePerformance, offset),
          }}])),
        }};
      }});
    }}
    function syncSlotControls() {{
      const summaries = dataset().qualification.summaries;
      const allocation = displayAllocation();
      const latest = summaries[summaries.length - 1] || {{ male_auto: 0, female_auto: 0 }};
      maleSlots.min = 0;
      femaleSlots.min = 0;
      maleSlots.value = allocation.male;
      femaleSlots.value = allocation.female;
      maleAutoSlots.value = latest.male_auto;
      femaleAutoSlots.value = latest.female_auto;
      const officialSlots = dataset().qualification_slots;
      const officialTotal = typeof officialSlots === "object" ? officialSlots.male + officialSlots.female : officialSlots;
      const selectedTotal = Number(latest.male_auto) + Number(latest.female_auto) + Number(allocation.male) + Number(allocation.female);
      const mode = hasSlotOverride() ? "what-if override" : `historical, ${{latest.year}}`;
      document.getElementById("qualificationSelectedTotalMetric").textContent = `${{selectedTotal}} (official: ${{officialTotal}}; ${{mode}})`;
    }}
    function updateSlotAllocation() {{
      const previous = displayAllocation();
      slotAllocations[eventSelect.value] = {{
        male: Math.max(0, Math.round(Number.isFinite(Number(maleSlots.value)) ? Number(maleSlots.value) : previous.male)),
        female: Math.max(0, Math.round(Number.isFinite(Number(femaleSlots.value)) ? Number(femaleSlots.value) : previous.female)),
      }};
      syncSlotControls();
      renderSharedViews();
    }}
    function renderAgeGroupNeededChart(years, gender, standardFor) {{
      const ageGroups = qualificationAgeGroups();
      const series = years.map(year => ({{
        label: year,
        color: compareYearColor(year),
        values: ageGroups.map(ageGroup => {{
          const needed = standardFor(year, ageGroup)?.needed;
          return Number.isFinite(needed) ? needed : null;
        }}),
      }}));
      document.getElementById("ageGroupTargetChartTitle").textContent = `${{gender === "Male" ? "Male" : "Female"}} time needed to qualify by age group`;
      lineChart("ageGroupTargetChart", ageGroups, series);
    }}
    function populateQualificationAgeGroups() {{
      const ageGroups = qualificationAgeGroups();
      const previousAgeGroup = qualificationAgeGroup.value;
      qualificationAgeGroup.innerHTML = ageGroups.map(ageGroup => `<option value="${{ageGroup}}">${{ageGroup}}</option>`).join("");
      qualificationAgeGroup.value = ageGroups.includes(previousAgeGroup) ? previousAgeGroup : (ageGroups.includes("30-34") ? "30-34" : ageGroups[0]);
    }}
    function modelCheckSummary() {{
      const checks = new Map();
      dataset().historical_qualification.targets.forEach(row => {{
        if (row.official_check && Number.isFinite(row.official_qualifiers)) checks.set(`${{row.year}}|${{row.gender}}`, row.official_check);
      }});
      if (!checks.size) return "No performance-pool years with official flags";
      const official = [...checks.values()].reduce((sum, check) => sum + check.official, 0);
      const matched = [...checks.values()].reduce((sum, check) => sum + check.matched, 0);
      const years = new Set([...checks.keys()].map(key => key.split("|")[0])).size;
      return `${{(100 * matched / Math.max(official, 1)).toFixed(1)}}% (${{matched}}/${{official}} in ${{years}} pool year${{years === 1 ? "" : "s"}})`;
    }}
    function renderCurrentQualification() {{
      const slots = dataset().qualification_slots;
      const slotCycle = dataset().qualification_slot_cycle;
      document.querySelectorAll(".current-rule-only").forEach(element => element.hidden = false);
      document.querySelectorAll(".historical-rule-only").forEach(element => element.hidden = true);
      document.getElementById("qualificationSlotsLabel").textContent = "Latest published allocation";
      document.getElementById("qualificationSelectedTotalLabel").textContent = "Selected total (auto + performance pool)";
      document.getElementById("qualificationSlotsMetric").textContent = (typeof slots === "object"
        ? `${{slots.male}} M / ${{slots.female}} F`
        : `${{slots}} total`) + (slotCycle ? ` (${{slotCycle}} cycle)` : "");
      document.getElementById("qualificationCheckMetric").textContent = modelCheckSummary();
      syncSlotControls();
      const summaries = dynamicQualificationSummaries().filter(row => compareYearVisible(row.year));
      populateQualificationAgeGroups();
      const ageGroup = qualificationAgeGroup.value;
      const gender = qualificationGender.value;
      const genderKey = gender.toLowerCase();
      const prefix = gender === "Male" ? "M" : "F";
      const ratio = currentRatio(gender);
      const declines = Math.max(0, Math.round(Number(qualificationDeclines.value) || 0));
      const standardName = dataset().group === "703" ? "70.3 Standard" : "Kona Standard";
      const standardFor = (row, rowGender, rowAgeGroup, extraPlaces = 0) => strictQualificationStandard(
        eventSelect.value, row.year, rowGender, rowAgeGroup, "current",
        {{ extraPlaces, performanceSlots: row[`${{rowGender.toLowerCase()}}_perf`] }},
      );
      document.getElementById("qualificationHead").innerHTML = `<tr><th>Year</th><th>${{prefix}} finishers</th><th>M / F total slots</th><th title="Projected no-decline qualifiers: automatic winner slot plus performance-pool places.">M / F ${{ageGroup}} qualifiers</th><th>${{prefix}} auto</th><th>${{prefix}} performance pool</th><th title="Age-graded time of the last performance-pool qualifier.">${{standardName}} cutoff</th><th title="Pool cutoff converted to a raw ${{prefix}}${{ageGroup}} finish time.">${{prefix}}${{ageGroup}} pool equivalent</th><th>${{prefix}}${{ageGroup}} winner</th>      <th title="Slower of the age-group winner and the pool equivalent.">${{prefix}}${{ageGroup}} time needed</th><th title="Time needed when ${{declines}} pool qualifiers decline.">Time needed (+${{declines}} declines)</th><th title="Strict ${{prefix}}${{ageGroup}} qualifiers (winner slot + pool places) per ${{prefix}}${{ageGroup}} finisher.">${{prefix}}${{ageGroup}} qualifiers / finishers</th><th title="How much slower the raw ${{prefix}}${{ageGroup}} target becomes if the gender pool rolls down 5 more places: a measure of how much declines matter in that race-year.">Roll-down sensitivity (+5 pool places)</th></tr>`;
      document.getElementById("qualificationBody").innerHTML = summaries.map(row => {{
        const standard = standardFor(row, gender, ageGroup);
        const rolled = standardFor(row, gender, ageGroup, declines);
              const deeper = standardFor(row, gender, ageGroup, 5);
              const totalSlots = `${{row.male_auto + row.male_perf}} / ${{row.female_auto + row.female_perf}}`;
              const ageGroupSlots = `${{standardFor(row, "Male", ageGroup)?.qualifiers ?? "—"}} / ${{standardFor(row, "Female", ageGroup)?.qualifiers ?? "—"}}`;
              return `<tr><td>${{yearCell(eventSelect.value, row.year)}}</td><td>${{row[`${{genderKey}}_finishers`]}}</td><td>${{totalSlots}}</td><td>${{ageGroupSlots}}</td><td>${{row[`${{genderKey}}_auto`]}}</td><td>${{row[`${{genderKey}}_perf`]}}</td><td>${{qualificationDuration(standard?.ageGraded)}}</td><td>${{qualificationDuration(standard?.poolEquivalent)}}</td><td>${{qualificationDuration(standard?.winner)}}</td><td><strong>${{neededText(standard?.needed)}}</strong><br><small>${{targetRouteText(standard)}}</small></td><td>${{neededText(rolled?.needed)}}</td><td>${{qualifierRateText(standard)}}</td><td>${{rollDownSensitivityText(standard, deeper)}}</td></tr>`;
            }}).join("");
      const ratioText = Number.isFinite(ratio) ? `ratio ${{Number(ratio).toFixed(4)}}` : "standard TBD";
      const overrideText = hasSlotOverride()
        ? " What-if override: the selected male and female performance-pool slots apply to every year."
        : " Current rules and the latest race allocation are applied to every historical field.";
      document.getElementById("qualificationNote").textContent = `${{dataset().qualification_note}} The ${{standardName}} cutoff is age-graded; pool equivalent and time-needed columns are raw ${{prefix}}${{ageGroup}} finish times (${{ratioText}}).${{overrideText}}`;
      document.getElementById("qualificationTableTitle").textContent = `Qualification estimate by year · ${{prefix}}${{ageGroup}}`;
      document.getElementById("qualificationChartTitle").textContent = `Time needed to qualify · ${{prefix}}${{ageGroup}}`;
      const years = summaries.map(row => row.year);
      const finite = value => Number.isFinite(value) ? value : null;
      const series = [
        {{ label: `${{prefix}}${{ageGroup}} time needed`, color: "#277da1", values: summaries.map(row => finite(standardFor(row, gender, ageGroup)?.needed)) }},
        {{ label: `${{prefix}}${{ageGroup}} +${{declines}} declines`, color: "#e76f51", values: summaries.map(row => finite(standardFor(row, gender, ageGroup, declines)?.needed)) }},
        {{ label: "Selected cutoff target", color: "#2a9d8f", values: summaries.map(row => finite(qualificationStandard(eventSelect.value, row.year, gender, ageGroup, "current")?.needed)) }},
      ];
      lineChart("qualificationChart", years, series);
      const summaryByYear = Object.fromEntries(summaries.map(row => [row.year, row]));
      renderAgeGroupNeededChart(years, gender, (year, rowAgeGroup) => qualificationStandard(eventSelect.value, year, gender, rowAgeGroup, "current"));
    }}
    function historicalGenderSlots(year, gender) {{
      const rows = dataset().historical_qualification.targets.filter(row =>
        row.year === year && row.gender === gender
      );
      if (!rows.length) return null;
      return rows[0].slot_scope === "gender"
        ? rows[0].slots
        : rows.reduce((sum, row) => sum + row.slots, 0);
    }}
    function historicalSourceLabel(source) {{
      if (!source) return "—";
      if (source.from_official_flags) return `${{source.total}} (official results)`;
      if (Number.isFinite(source.male) || Number.isFinite(source.female)) {{
        return `${{source.male ?? "—"}} M / ${{source.female ?? "—"}} F`;
      }}
      return Number.isFinite(source.total) ? `${{source.total}} total` : "—";
    }}
    function historicalSourceHtml(source) {{
      const label = historicalSourceLabel(source);
      const cycle = source?.cycles?.length ? ` · ${{source.cycles.join(", ")}} cycle` : "";
      const others = source?.other_cycles?.length ? ` Also offered: ${{source.other_cycles.join("; ")}}.` : "";
      const title = `Slot source${{cycle}}.${{others}}`;
      const url = source?.allocation_source_url || source?.source_url;
      const text = `${{escapeHtml(label)}}${{escapeHtml(cycle)}}${{others ? " *" : ""}}`;
      return url
        ? `<a href="${{escapeHtml(url)}}" target="_blank" rel="noreferrer" title="${{escapeHtml(title)}}">${{text}}</a>`
        : `<span title="${{escapeHtml(title)}}">${{text}}</span>`;
    }}
    function officialCheckHtml(year) {{
      const qualification = dataset().historical_qualification;
      const rows = qualification.targets.filter(row => row.year === year);
      if (!rows.length) return "—";
      if (rows[0].slot_scope === "age group") {{
        return qualification.official_years.includes(year)
          ? `<span title="Age-group slot counts taken from the official results' Qualified flags.">Official allocation</span>`
          : `<span title="The results flag another qualifying cycle, so the allocation is reconstructed.">No flags for cycle</span>`;
      }}
      const parts = ["Male", "Female"].map(gender => {{
        const check = rows.find(row => row.gender === gender)?.official_check;
        if (!check) return null;
        const exact = check.matched === check.official && check.predicted === check.official;
        return `${{exact ? "✓" : "✗"}} ${{check.matched}}/${{check.official}} ${{gender[0]}}`;
      }}).filter(Boolean);
      return parts.length ? `<span title="Model qualifiers matching the official results' Qualified flags.">${{parts.join(" · ")}}</span>` : "No official flags";
    }}
    function renderHistoricalQualification() {{
      const qualification = dataset().historical_qualification;
      document.querySelectorAll(".current-rule-only").forEach(element => element.hidden = true);
      document.querySelectorAll(".historical-rule-only").forEach(element => element.hidden = false);
      document.getElementById("qualificationSlotsLabel").textContent = "Historical slot allocation";
      document.getElementById("qualificationSelectedTotalLabel").textContent = "Latest sourced race total";
      document.getElementById("qualificationCheckMetric").textContent = modelCheckSummary();
      populateQualificationAgeGroups();
      const ageGroup = qualificationAgeGroup.value;
      const gender = qualificationGender.value;
      const prefix = gender === "Male" ? "M" : "F";
      const poolDeclines = Math.max(0, Math.round(Number(qualificationDeclines.value) || 0));
      const ageGroupDeclines = Math.max(0, Math.round(Number(qualificationLegacyDeclines.value) || 0));
      const years = [...new Set(qualification.targets.map(row => row.year))].sort().filter(compareYearVisible);
      const latestTarget = [...qualification.targets].sort((left, right) => left.year.localeCompare(right.year)).at(-1);
      document.getElementById("qualificationSlotsMetric").textContent = "Varies by race-year";
      document.getElementById("qualificationSelectedTotalMetric").textContent = latestTarget
        ? `${{historicalSourceLabel(latestTarget.source)}} (${{latestTarget.year}})`
        : "Unavailable";
      const standardFor = (year, rowGender, rowAgeGroup, rolled = false) => {{
        const standard = strictQualificationStandard(eventSelect.value, year, rowGender, rowAgeGroup, "historical");
        if (!rolled || !standard) return standard;
        const extraPlaces = standard.scope === "age group" ? ageGroupDeclines : poolDeclines;
        return strictQualificationStandard(eventSelect.value, year, rowGender, rowAgeGroup, "historical", {{ extraPlaces }});
      }};

      const standardName = dataset().group === "703" ? "70.3 Standard" : "Kona Standard";
      document.getElementById("qualificationHead").innerHTML = `<tr><th>Year</th><th>Method</th><th>Source slots</th><th>M / F total slots</th><th title="Allocated age-group slots in legacy years; projected no-decline qualifiers in performance-pool years.">M / F ${{ageGroup}} slots</th><th title="Performance-pool years only: age-graded time of the last pool qualifier.">${{standardName}} cutoff</th><th title="Performance-pool years only: pool cutoff converted to a raw ${{prefix}}${{ageGroup}} time.">${{prefix}}${{ageGroup}} pool equivalent</th><th>${{prefix}}${{ageGroup}} winner</th><th title="Legacy years: finish time of the last allocated ${{prefix}}${{ageGroup}} slot. Performance-pool years: slower of the winner and the pool equivalent.">${{prefix}}${{ageGroup}} time needed</th><th title="After X=${{poolDeclines}} pool declines (performance-pool years) or Y=${{ageGroupDeclines}} age-group declines (legacy years).">      Time needed (X=${{poolDeclines}} / Y=${{ageGroupDeclines}})</th><th title="Strict ${{prefix}}${{ageGroup}} slots or qualifiers per ${{prefix}}${{ageGroup}} finisher.">${{prefix}}${{ageGroup}} qualifiers / finishers</th><th title="How much slower the raw target becomes after one more ${{prefix}}${{ageGroup}} place (legacy years) or five more gender-pool places (performance-pool years).">Roll-down sensitivity</th><th>Official results check</th></tr>`;
      document.getElementById("qualificationBody").innerHTML = years.map(year => {{
        const standard = standardFor(year, gender, ageGroup);
        const rolled = standardFor(year, gender, ageGroup, true);
              const deeperPlaces = standard?.scope === "age group" ? 1 : 5;
              const deeper = standard && strictQualificationStandard(eventSelect.value, year, gender, ageGroup, "historical", {{ extraPlaces: deeperPlaces }});
              const male = standardFor(year, "Male", ageGroup);
              const female = standardFor(year, "Female", ageGroup);
              const source = standard?.source || male?.source || female?.source;
              const method = standard?.method || male?.method || female?.method || "Unavailable";
              const totalSlots = `${{historicalGenderSlots(year, "Male") ?? "—"}} / ${{historicalGenderSlots(year, "Female") ?? "—"}}`;
              const ageGroupSlots = `${{male?.qualifiers ?? "—"}} / ${{female?.qualifiers ?? "—"}}`;
              const sensitivity = deeper ? `${{rollDownSensitivityText(standard, deeper)}}<br><small>+${{deeperPlaces}} ${{standard.scope === "age group" ? "AG place" : "pool places"}}</small>` : "—";
              return `<tr><td>${{yearCell(eventSelect.value, year)}}</td><td>${{escapeHtml(method)}}</td><td>${{historicalSourceHtml(source)}}</td><td>${{totalSlots}}</td><td>${{ageGroupSlots}}</td><td>${{qualificationDuration(standard?.ageGraded)}}</td><td>${{qualificationDuration(standard?.poolEquivalent)}}</td><td>${{qualificationDuration(standard?.winner)}}</td><td><strong>${{neededText(standard?.needed)}}</strong><br><small>${{targetRouteText(standard)}}</small></td><td>${{neededText(rolled?.needed)}}</td><td>${{qualifierRateText(standard)}}</td><td>${{sensitivity}}</td><td>${{officialCheckHtml(year)}}</td></tr>`;
            }}).join("");
      const unavailable = qualification.unavailable_years.length
        ? ` Historical slot data is unavailable for: ${{qualification.unavailable_years.join(", ")}}.`
        : "";
      document.getElementById("qualificationNote").textContent = `Historical mode uses each race-year's own qualifying cycle: its slot allocation, rules, and age-grading standard. Legacy years use the official age-group allocation from the results' Qualified flags when they cover the selected cycle, otherwise a published or reconstructed allocation. X=${{poolDeclines}} moves down the gender pool in performance-pool years; Y=${{ageGroupDeclines}} moves down within ${{prefix}}${{ageGroup}} in legacy years. In the 2026 cycle IRONMAN switched to gender-split pools in November 2025 and applied the split retroactively to earlier races. A * marks race-years that also offered slots for another championship.${{unavailable}}`;
      document.getElementById("qualificationTableTitle").textContent = `Historical qualification by year · ${{prefix}}${{ageGroup}}`;
      document.getElementById("qualificationChartTitle").textContent = `Historical time needed and roll-down · ${{prefix}}${{ageGroup}}`;
      const finite = value => Number.isFinite(value) ? value : null;
      const series = [
        {{ label: `${{prefix}}${{ageGroup}} time needed`, color: "#277da1", values: years.map(year => finite(standardFor(year, gender, ageGroup)?.needed)) }},
        {{ label: `${{prefix}}${{ageGroup}} roll-down (X=${{poolDeclines}} pool / Y=${{ageGroupDeclines}} AG)`, color: "#e76f51", values: years.map(year => finite(standardFor(year, gender, ageGroup, true)?.needed)) }},
        {{ label: "Selected cutoff target", color: "#2a9d8f", values: years.map(year => finite(qualificationStandard(eventSelect.value, year, gender, ageGroup, "historical")?.needed)) }},
      ];
      lineChart("qualificationChart", years, series);
      renderAgeGroupNeededChart(years, gender, (year, rowAgeGroup) => qualificationStandard(eventSelect.value, year, gender, rowAgeGroup, "historical"));
    }}
    function renderQualification() {{
      const qualifying = isQualifyingEvent(eventSelect.value);
      document.getElementById("qualificationContent").hidden = !qualifying;
      if (!qualifying) {{
        document.getElementById("qualificationNote").textContent = dataset().qualification_note;
        return;
      }}
      if (qualificationSystem === "historical") renderHistoricalQualification();
      else renderCurrentQualification();
    }}
    function overallStats() {{
      const proTimes = dataset().pro_times || {{}};
      return Object.entries(dataset().overall).filter(([year]) => compareYearVisible(year)).map(([year, values]) => {{
        const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
        const pro = proTimes[year] || {{ male: [], female: [] }};
        return {{
          year, finishers: values.length, mean, median: median(values),
          top20pct: values[Math.ceil(values.length * 0.2) - 1],
          top100: values[Math.min(99, values.length - 1)],
          top50: values[Math.min(49, values.length - 1)],
          top20: values[Math.min(19, values.length - 1)],
          top10ProMale: pro.male.length >= 10 ? pro.male[9] : null,
          top10ProFemale: pro.female.length >= 10 ? pro.female[9] : null,
        }};
      }});
    }}
    function renderOverall() {{
      const stats = overallStats();
      document.getElementById("overallBody").innerHTML = stats.map(row => `<tr><td>${{yearCell(eventSelect.value, row.year)}}</td><td>${{row.finishers.toLocaleString()}}</td><td>${{duration(row.mean)}}</td><td>${{duration(row.median)}}</td><td>${{duration(row.top20pct)}}</td><td>${{duration(row.top100)}}</td><td>${{duration(row.top50)}}</td><td>${{duration(row.top20)}}</td><td>${{duration(row.top10ProMale)}}</td><td>${{duration(row.top10ProFemale)}}</td></tr>`).join("");
      const years = stats.map(row => row.year);
      lineChart("averageChart", years, [
        {{ label: "Mean", color: "#006d77", values: stats.map(row => row.mean) }},
        {{ label: "Median", color: "#e76f51", values: stats.map(row => row.median) }},
      ]);
      lineChart("cutoffChart", years, [
        {{ label: "Top 20%", color: "#006d77", values: stats.map(row => row.top20pct) }},
        {{ label: "Top 100", color: "#e76f51", values: stats.map(row => row.top100) }},
        {{ label: "Top 50", color: "#8f5d8c", values: stats.map(row => row.top50) }},
        {{ label: "Top 20", color: "#43aa8b", values: stats.map(row => row.top20) }},
      ]);
      densityChart(dataset().overall);
    }}
    function renderStatistics() {{
      const rows = (dataset().statistics || []).filter(row => compareYearVisible(row.year));
      const percent = value => Number.isFinite(value) ? `${{value.toFixed(1)}}%` : "—";
      document.getElementById("statisticsBody").innerHTML = rows.map(row => {{
        const completion = Number.isFinite(row.completion_rate) ? percent(row.completion_rate * 100) : "—";
        const pctMale = row.finishers ? percent(100 * row.male_finishers / row.finishers) : "—";
        const pctFemale = row.finishers ? percent(100 * row.female_finishers / row.finishers) : "—";
        return `<tr><td>${{yearCell(eventSelect.value, row.year)}}</td><td>${{row.registered.toLocaleString()}}</td><td>${{row.starters.toLocaleString()}}</td><td>${{row.finishers.toLocaleString()}}</td><td>${{row.dns.toLocaleString()}}</td><td>${{row.dnf.toLocaleString()}}</td><td>${{row.dq.toLocaleString()}}</td><td>${{completion}}</td><td>${{row.male_finishers.toLocaleString()}}</td><td>${{row.female_finishers.toLocaleString()}}</td><td>${{pctMale}}</td><td>${{pctFemale}}</td><td>${{row.pro_finishers.toLocaleString()}}</td><td>${{duration(row.avg_finish)}}</td><td>${{duration(row.median_finish)}}</td></tr>`;
      }}).join("");
      const years = rows.map(row => row.year);
      const countFormat = value => Number.isFinite(value) ? Math.round(value).toLocaleString() : "—";
      lineChart("statusChart", years, [
        {{ label: "Finishers", color: "#006d77", values: rows.map(row => row.finishers) }},
        {{ label: "DNS", color: "#e4b84d", values: rows.map(row => row.dns) }},
        {{ label: "DNF", color: "#d94b4b", values: rows.map(row => row.dnf) }},
      ], countFormat, {{ zeroBaseline: true }});
      lineChart("genderChart", years, [
        {{ label: "Male finishers", color: "#277da1", values: rows.map(row => row.male_finishers) }},
        {{ label: "Female finishers", color: "#e76f51", values: rows.map(row => row.female_finishers) }},
      ], countFormat, {{ zeroBaseline: true }});
      lineChart("completionChart", years, [
        {{
          label: "Finishers / (finishers + DNF)",
          color: "#43aa8b",
          values: rows.map(row => row.finishers + row.dnf ? 100 * row.finishers / (row.finishers + row.dnf) : null),
        }},
        {{
          label: "Finishers / (finishers + DNF + DNS)",
          color: "#277da1",
          values: rows.map(row => row.finishers + row.dnf + row.dns ? 100 * row.finishers / (row.finishers + row.dnf + row.dns) : null),
        }},
      ], percent);
    }}
    function updateTitle() {{
      const labels = {{ splits: "Split Explorer", qualification: "Qualification", odds: "Can I Qualify?", easiest: "Where Can I Qualify Most Easily?", overall: "Overall Times", statistics: "Race Statistics", compare: "Compare Races", kona: "Kona Qualification Trace", experimental: "Experimental", qtime: "Your time", qdifficulty: "Race difficulty" }};
      const aggregateView = ["compare", "experimental", "odds", "easiest", "kona", "qtime", "qdifficulty"].includes(activeTab);
      document.querySelector(".event-control").hidden = aggregateView;
      document.getElementById("eventTitle").textContent = aggregateView ? labels[activeTab] : `${{dataset().name}} · ${{labels[activeTab]}}`;
    }}
    function raceGroups() {{
      const groups = {{}};
      for (const [id, event] of Object.entries(DATASETS)) {{
        const key = event.group || "im";
        if (!groups[key]) groups[key] = [];
        groups[key].push(id);
      }}
      return groups;
    }}
    const compareColors = ["#006d77", "#e76f51", "#277da1", "#7a6f3d", "#8f5d8c", "#2a9d8f", "#bc4749", "#d18b25", "#577590", "#6a994e", "#9c6644", "#c9184a", "#4361ee", "#606c38", "#b5838d", "#023e8a", "#f4a261", "#5f0f40"];
    const compareYears = [...new Set(Object.values(DATASETS).flatMap(event => [
      ...Object.keys(event.overall), ...event.statistics.map(row => row.year),
    ]))].sort();
    const hiddenCompareYears = new Set();
    function compareYearVisible(year) {{
      return !hiddenCompareYears.has(year);
    }}
    function toggleCompareYear(year) {{
      if (hiddenCompareYears.has(year)) hiddenCompareYears.delete(year);
      else hiddenCompareYears.add(year);
      renderSharedViews();
    }}
    function renderCompareYears() {{
      document.getElementById("compareYears").innerHTML = compareYears.map(year =>
        `<label><input type="checkbox" value="${{year}}" ${{compareYearVisible(year) ? "checked" : ""}}>${{year}}</label>`
      ).join("");
    }}
    function compareYearColor(year) {{
      return compareColors[compareYears.indexOf(year) % compareColors.length];
    }}
    function yearSeries(eventIds, valueForYear) {{
      const years = [...new Set(eventIds.flatMap(id => [
        ...Object.keys(DATASETS[id].overall), ...DATASETS[id].statistics.map(row => row.year),
      ]))].sort();
      return years.map(year => ({{
        label: year,
        color: compareYearColor(year),
        values: eventIds.map(id => {{
          const result = valueForYear(id, year);
          const value = typeof result === "object" && result !== null ? result.value : result;
          const detail = typeof result === "object" && result !== null ? result.detail : null;
          return Number.isFinite(value) ? [{{ year, value, detail }}] : [];
        }}),
      }}));
    }}
    function categoryPointChart(elementId, categories, series, options = {{}}) {{
      const svg = document.getElementById(elementId);
      const comparison = true;
      if (comparison) series = series.map(item => ({{
        ...item,
        values: item.values.map(entries => entries.filter(entry => compareYearVisible(entry.year))),
      }}));
      const width = svg.viewBox.baseVal.width, height = svg.viewBox.baseVal.height;
      const legendColumnWidth = 160;
      const legendColumns = Math.max(1, Math.floor((width - 92) / legendColumnWidth));
      const legendRows = Math.ceil(series.length / legendColumns);
      const margin = {{ left: options.yAxisLabel ? 104 : 84, right: 24, top: 16 + legendRows * 22, bottom: 86 }};
      const values = series.flatMap(item => item.values.flat().map(entry => entry.value).filter(Number.isFinite));
      const hasData = categories.length && values.length;
      if (!hasData && !comparison) {{ svg.innerHTML = `<text x="20" y="40">No data available</text>`; return; }}
      let minimum = hasData ? Math.min(...values) : 0, maximum = hasData ? Math.max(...values) : 1;
      if (options.includeZero) {{ minimum = Math.min(minimum, 0); maximum = Math.max(maximum, 0); }}
      if (Number.isFinite(options.minimum)) minimum = options.minimum;
      if (Number.isFinite(options.maximum)) maximum = options.maximum;
      if (options.zeroBasedNice) {{
        minimum = 0;
        const rawStep = Math.max(maximum / 4, Number.EPSILON);
        const magnitude = 10 ** Math.floor(Math.log10(rawStep));
        const normalized = rawStep / magnitude;
        const niceNormalized = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10;
        const step = niceNormalized * magnitude;
        maximum = step * 4;
        if (Number.isFinite(options.maximumCap)) {{
          maximum = Math.min(maximum, options.maximumCap);
        }}
      }} else if (!Number.isFinite(options.minimum) || !Number.isFinite(options.maximum)) {{
        const minimumPadding = Number.isFinite(options.minimumPadding) ? options.minimumPadding : 300;
        const padding = Math.max((maximum - minimum) * 0.18, minimumPadding);
        if (!Number.isFinite(options.minimum)) minimum -= padding;
        if (!Number.isFinite(options.maximum)) maximum += padding;
      }}
      if (options.nonnegative) minimum = Math.max(0, minimum);
      if (maximum <= minimum) maximum = minimum + 1;
      const groupWidth = (width - margin.left - margin.right) / Math.max(categories.length, 1);
      const clusterWidth = Math.min(groupWidth * 0.42, Math.max(0, (series.length - 1) * 7));
      const pointSpacing = series.length > 1 ? clusterWidth / (series.length - 1) : 0;
      const y = value => margin.top + (maximum - value) * (height - margin.top - margin.bottom) / (maximum - minimum);
      let markup = "";
      for (let tick = 0; tick <= 4; tick++) {{
        const value = minimum + (maximum - minimum) * tick / 4;
        const yPosition = y(value);
        const tickText = options.formatTick ? options.formatTick(value) : duration(value).slice(0, 5);
        markup += `<line class="grid" x1="${{margin.left}}" y1="${{yPosition}}" x2="${{width - margin.right}}" y2="${{yPosition}}"/><text x="${{margin.left - 8}}" y="${{yPosition + 4}}" text-anchor="end">${{tickText}}</text>`;
      }}
      if (options.includeZero) {{
        markup += `<line x1="${{margin.left}}" y1="${{y(0)}}" x2="${{width - margin.right}}" y2="${{y(0)}}" stroke="#6f7b76" stroke-width="1.5" stroke-dasharray="5 4"/>`;
      }}
      categories.forEach((category, categoryIndex) => {{
        const labelX = margin.left + categoryIndex * groupWidth + groupWidth / 2;
        const labelY = height - 66;
        markup += `<text x="${{labelX}}" y="${{labelY}}" text-anchor="end" transform="rotate(-30 ${{labelX}} ${{labelY}})">${{category}}</text>`;
        series.forEach((item, seriesIndex) => {{
          const cx = labelX + (seriesIndex - (series.length - 1) / 2) * pointSpacing;
          const yearValues = item.values[categoryIndex] || [];
          yearValues.forEach(({{ year, value, detail }}) => {{
            if (!Number.isFinite(value)) return;
            const formattedValue = options.formatValue ? options.formatValue(value) : duration(value);
            const valueText = detail ? `${{formattedValue}} · ${{detail}}` : formattedValue;
            const accessibleLabel = `${{item.label}}, ${{category}}, ${{year}}: ${{valueText}}`;
            markup += `<circle class="data-point" cx="${{cx}}" cy="${{y(value)}}" r="5" fill="${{item.color}}" tabindex="0" role="img" aria-label="${{accessibleLabel}}" data-series="${{category}}" data-year="${{year}}" data-value="${{valueText}}"><title>${{accessibleLabel}}</title></circle>`;
          }});
        }});
      }});
      markup += `<line class="axis" x1="${{margin.left}}" y1="${{margin.top}}" x2="${{margin.left}}" y2="${{height - margin.bottom}}"/><line class="axis" x1="${{margin.left}}" y1="${{height - margin.bottom}}" x2="${{width - margin.right}}" y2="${{height - margin.bottom}}"/>`;
      if (options.yAxisLabel) {{
        const axisMiddle = (margin.top + height - margin.bottom) / 2;
        markup += `<text x="18" y="${{axisMiddle}}" text-anchor="middle" transform="rotate(-90 18 ${{axisMiddle}})">${{options.yAxisLabel}}</text>`;
      }}
      series.forEach((item, seriesIndex) => {{
        const legendColumn = seriesIndex % legendColumns;
        const legendRow = Math.floor(seriesIndex / legendColumns);
        const legendX = margin.left + legendColumn * legendColumnWidth;
        const legendY = 15 + legendRow * 22;
        markup += `<circle cx="${{legendX + 6}}" cy="${{legendY - 5}}" r="5" fill="${{item.color}}"/><text x="${{legendX + 19}}" y="${{legendY}}">${{item.label}}</text>`;
      }});
      if (!hasData) markup += `<text x="${{margin.left + 12}}" y="${{margin.top + 30}}">No data for visible years</text>`;
      svg.innerHTML = markup;
      attachPointTooltips(svg);
    }}
    function raceComparisonStatistic(eventId, year, metric) {{
      const event = DATASETS[eventId];
      if (isModifiedCourse(eventId, year)) return null;
      if (metric === "slots") {{
        if (!isQualifyingEvent(eventId)) return null;
        const target = event.historical_qualification.targets.find(row => row.year === year);
        const total = target?.source?.total;
        return Number.isFinite(total) ? {{ value: total, detail: "Historical World Championship allocation" }} : null;
      }}
      const row = event.statistics.find(entry => entry.year === year);
      if (!row) return null;
      if (metric === "finishers") return {{ value: row.finishers, detail: "All official finishers, including pros" }};
      const denominator = metric === "dns" ? row.registered : row.starters;
      return denominator > 0 ? {{
        value: 100 * row[metric] / denominator,
        detail: `${{row[metric].toLocaleString()}} / ${{denominator.toLocaleString()}} ${{metric === "dns" ? "registered athletes" : "starters"}}`,
      }} : null;
    }}
    function renderRaceStatisticsCompare() {{
      const eventIds = raceGroups()[document.getElementById("compareStatisticsDistance").value] || [];
      [
        ["compareFinishers", "finishers", "Total finishers"],
        ["compareDnsRatio", "dns", "DNS / registered (%)"],
        ["compareDnfRatio", "dnf", "DNF / starters (%)"],
        ["compareTotalSlots", "slots", "Historical slots"],
      ].forEach(([elementId, metric, yAxisLabel]) => {{
        const ids = metric === "slots" ? eventIds.filter(isQualifyingEvent) : eventIds;
        const ratio = metric === "dns" || metric === "dnf";
        categoryPointChart(
          elementId,
          ids.map(id => DATASETS[id].name),
          yearSeries(ids, (id, year) => raceComparisonStatistic(id, year, metric)),
          {{
            zeroBasedNice: true,
            maximumCap: ratio ? 100 : undefined,
            formatValue: value => ratio ? `${{value.toFixed(1)}}%` : Math.round(value).toLocaleString(),
            formatTick: value => ratio ? `${{value.toFixed(1)}}%` : Math.round(value).toLocaleString(),
            yAxisLabel,
          }},
        );
      }});
    }}
    const konaReviewStorageKey = "kona-2026-slot-source-reviews-v1";
    let konaReviews = {{}};
    let konaReviewStorageAvailable = true;
    try {{
      const stored = JSON.parse(localStorage.getItem(konaReviewStorageKey) || "{{}}");
      if (stored && typeof stored === "object" && !Array.isArray(stored)) konaReviews = stored;
    }} catch {{ konaReviewStorageAvailable = false; }}
    function konaReviewKey(starter) {{
      const identity = [starter.bib, starter.name, starter.country, starter.gender];
      return JSON.stringify(starter.cycle && starter.cycle !== "2026" ? [starter.cycle, ...identity] : identity);
    }}
    function reviewedKonaSummary(pool, starters) {{
      const attributed = starters.flatMap(starter => {{
        const selected = konaReviews[konaReviewKey(starter)];
        const entry = starter.matches.find(row => `${{row.event_id}}|${{row.year}}` === selected && row.event_id === pool.event_id && row.year === pool.year && (!pool.division || row.division === pool.division));
        return entry ? [{{starter, entry}}] : [];
      }});
      const ranked = attributed.filter(row => Number.isFinite(row.entry.pool_rank));
      const deepest = ranked.reduce((best, row) => !best || row.entry.pool_rank > best.entry.pool_rank ? row : best, null);
      return {{...pool, attributed_starters: attributed.length,
        deepest_rank: deepest?.entry.pool_rank ?? null,
        observed_cutoff: deepest?.entry.age_graded ?? null,
        deepest_name: deepest?.starter.name ?? null,
        estimated_skipped_slots: deepest && pool.pool_slots > 0 ? Math.max(0, deepest.entry.pool_rank - pool.pool_slots) : null,
      }};
    }}
    function reportedKonaCutoffCell(row) {{
      if (!Number.isFinite(row.reported_cutoff)) return "—";
      const duration = qualificationDuration(row.reported_cutoff);
      const time = row.reported_cutoff_precision === "minute" ? duration.slice(0, 5) : duration;
      const source = row.reported_cutoff_url
        ? `<a href="${{escapeHtml(row.reported_cutoff_url)}}" target="_blank" rel="noopener noreferrer">${{escapeHtml(row.reported_cutoff_source)}}</a>`
        : "User report";
      return `<span title="${{escapeHtml(row.reported_cutoff_source)}}">${{time}}</span><br><small>${{source}}</small>`;
    }}
    function estimatedKonaCutoffCell(row) {{
      const estimate = row.cutoff_estimate;
      if (!Number.isFinite(estimate?.time)) return `—<br><small>${{escapeHtml(estimate?.reason || "Unavailable")}}</small>`;
      const minute = (seconds, rounding) => qualificationDuration(rounding(seconds / 60) * 60).slice(0, 5);
      const range = `${{minute(estimate.low_time, Math.floor)}} to ${{minute(estimate.high_time, Math.ceil)}}`;
      const sensitivity = estimate.sensitive ? "Sensitive to match selection" : !Number.isFinite(estimate.single_match_time) ? "Single-match subset unsupported" : "Exploratory";
      const rankScope = row.slot_scope === "age group" ? "age-group rank" : "gender-pool rank";
      return `<span title="Exploratory match-density boundary, not actual acceptance; ${{rankScope}} ${{estimate.rank}}; ${{estimate.matched_pool_starters}} ranked matches; BIC improvement ${{estimate.bic_gain}}">~${{minute(estimate.time, Math.round)}}</span><br><small>Range ${{range}}<br>${{sensitivity}}</small>`;
    }}
    function scannedKonaCutoffCell(row) {{
      const scan = row.cutoff_scan;
      if (!Number.isFinite(scan?.time)) return `—<br><small>${{escapeHtml(scan?.reason || "Unavailable")}}</small>`;
      if (scan.rank <= row.pool_slots || Number.isFinite(row.strict_cutoff) && scan.time < Math.floor(row.strict_cutoff)) {{
        return `—<br><small>Scan did not clear the strict allocation boundary</small>`;
      }}
      const rankScope = row.slot_scope === "age group" ? "age-group rank" : "gender-pool rank";
      return `<span title="Unverified estimate; scan starts at ${{rankScope}} ${{row.pool_slots + 1}}">${{qualificationDuration(scan.time)}}</span><br><small>${{escapeHtml(scan.athlete)}}<br>${{rankScope}} ${{scan.rank}}<br>${{scan.consecutive_absences}} absences: ranks ${{scan.gap_start_rank}} to ${{scan.gap_end_rank}}</small>`;
    }}
    function manualKonaCutoff(row, trace) {{
      const extraPlaces = trace.slot_scope === "age group"
        ? qualificationAssumptions.legacyExtraPlaces : qualificationAssumptions.extraPlaces;
      const rank = row.pool_slots + extraPlaces;
      const time = row.manual_pool_times?.[rank - 1];
      if (!Number.isFinite(time) || rank <= 0) return `—<br><small>No ranked finisher at slot ${{rank}}</small>`;
      const rankScope = trace.slot_scope === "age group" ? "age-group rank" : "gender-pool rank";
      return `<strong>${{qualificationDuration(time)}}</strong><br><small>${{extraPlaces}} extra place${{extraPlaces === 1 ? "" : "s"}} · ${{rankScope}} ${{rank}}</small>`;
    }}
    function championshipVenues(trace) {{
      return ["Male", "Female"].map(gender => {{
        const venues = trace?.venues?.[gender] || [...new Set((trace?.starters || []).filter(row => row.gender === gender).map(row => row.venue || "Kona"))];
        return venues.length ? `${{gender === "Male" ? "men" : "women"}}: ${{venues.join(" + ")}}` : null;
      }}).filter(Boolean).join(", ");
    }}
    function selectedKonaTrace() {{
      return DATASETS.im_kona?.kona_traces?.[document.getElementById("konaCycle").value] || DATASETS.im_kona?.kona_trace;
    }}
    function renderKonaTrace() {{
      const trace = selectedKonaTrace();
      if (!trace) {{
        document.getElementById("konaCoverageNote").textContent = "Kona 2026 trace data is unavailable.";
        return;
      }}
      const gender = document.getElementById("konaGender").value;
      const legacy = trace.slot_scope === "age group";
      const ageGroupControl = document.getElementById("konaAgeGroup");
      ageGroupControl.closest("label").hidden = !legacy;
      const ageGroups = [...new Set(trace.summaries.all.filter(row => row.gender === gender && row.division).map(row => row.division.slice(1)))].sort();
      if (legacy && ageGroups.length) populateAgeGroupSelect(ageGroupControl, ageGroups);
      const division = `${{gender === "Male" ? "M" : "F"}}${{ageGroupControl.value}}`;
      document.querySelector("#konaPanel > h2").textContent = `World Championship ${{trace.year}} starters and qualifying results (${{championshipVenues(trace)}})`;
      const summaryHeaders = document.querySelectorAll("#konaSummaryBody").length ? document.querySelector("#konaSummaryBody").closest("table").querySelectorAll("th") : [];
      summaryHeaders[3].textContent = legacy ? "Initial age-group slots" : "Initial gender pool";
      summaryHeaders[6].textContent = legacy ? "Selected age-group rank" : "Selected pool rank";
      summaryHeaders[7].textContent = legacy ? "Strict raw cutoff" : "Strict age-graded cutoff";
      summaryHeaders[10].textContent = "Match-density boundary";
      summaryHeaders[11].textContent = legacy ? "3-absence age-group scan" : "15-absence gender-pool scan";
      summaryHeaders[13].textContent = legacy ? "Selected raw time" : "Selected age-graded time";
      document.querySelector("#konaMatchesBody").closest("table").querySelectorAll("th")[8].textContent = legacy ? "Age-group rank" : "Pool rank";
      document.querySelector("#konaMatchesBody").closest("table").querySelectorAll("th")[9].textContent = legacy ? "Raw ranked time" : "Age-graded time";
      const evidence = document.getElementById("konaEvidence").value;
      const selectedRace = document.getElementById("konaRace").value;
      const raceKey = row => `${{row.event_id}}|${{row.year}}`;
      const starters = trace.starters.filter(row => row.gender === gender);
      const matched = starters.filter(row => row.matches.length);
      document.getElementById("konaStarterCount").textContent = starters.length.toLocaleString();
      document.getElementById("konaMatchedCount").textContent = matched.length.toLocaleString();
      document.getElementById("konaUnmatchedCount").textContent = (starters.length - matched.length).toLocaleString();
      const multiple = matched.filter(row => row.matches.length > 1).length;
      const availableGenders = [...new Set(trace.starters.map(row => row.gender))];
      document.getElementById("konaCoverageNote").textContent = `${{trace.covered_races.length}} of ${{trace.covered_races.length + trace.missing_races.length}} qualifying race editions have usable local results and allocations. Local championship field: ${{championshipVenues(trace) || "unavailable"}}. ${{availableGenders.includes(gender) ? "" : "The selected gender's championship starter field is missing. "}}${{legacy ? "Historical estimates rank raw times within the selected age group; they do not use current age-grading standards. " : ""}}${{multiple}} matched ${{gender === "Male" ? "men" : "women"}} have multiple candidate races; ${{trace.ambiguous_identities}} ambiguous identities were excluded from matching. One observed race does not exclude qualifying elsewhere. Shortened races are included here because their slots still count.`;
      const unverified = evidence !== "reviewed";
      const rows = trace.summaries[unverified ? evidence : "all"].filter(row => compareYearVisible(row.year) && row.gender === gender && (!legacy || row.division === division) && (!selectedRace || raceKey(row) === selectedRace)).map(row => unverified ? {{...row,
        attributed_starters: null, deepest_rank: row.candidate_deepest_rank,
        observed_cutoff: row.candidate_cutoff, deepest_name: row.candidate_deepest_name,
        estimated_skipped_slots: row.candidate_skipped_slots,
      }} : reviewedKonaSummary(row, starters)).map(row => ({{
        ...row,
        manual_pool_times: trace.summaries.all.find(pool => pool.event_id === row.event_id && pool.year === row.year
          && pool.gender === row.gender && pool.division === row.division)?.manual_pool_times,
      }}));
      const count = value => Number.isFinite(value) ? value.toLocaleString() : "—";
      document.getElementById("konaSummaryBody").innerHTML = rows.map(row => `<tr><td>${{escapeHtml(row.name)}}${{isModifiedCourse(row.event_id, row.year) ? " (modified course)" : ""}}</td><td>${{row.year}}</td><td>${{row.total_slots}}</td><td>${{row.pool_slots}}</td><td>${{row.matched_starters}}</td><td>${{count(row.attributed_starters)}}</td><td>${{count(row.deepest_rank)}}</td><td>${{qualificationDuration(row.strict_cutoff)}}</td><td>${{manualKonaCutoff(row, trace)}}</td><td>${{reportedKonaCutoffCell(row)}}</td><td>${{estimatedKonaCutoffCell(row)}}</td><td>${{scannedKonaCutoffCell(row)}}</td><td>${{Number.isFinite(row.cutoff_scan?.modeled_roll_down_percent) ? `${{row.cutoff_scan.modeled_roll_down_percent.toFixed(1)}}%<br><small>model-derived assumption</small>` : "—"}}</td><td>${{qualificationDuration(row.observed_cutoff)}}${{unverified ? " (unverified maximum)" : ""}}</td><td>${{count(row.estimated_skipped_slots)}}${{unverified ? " (unverified)" : ""}}</td><td>${{escapeHtml(row.deepest_name || "—")}}</td></tr>`).join("") || `<tr><td colspan="16">No qualifying race data available</td></tr>`;
      rows.forEach((row, index) => {{
        if (row.allocation_method) document.getElementById("konaSummaryBody").rows[index].cells[3].innerHTML += `<br><small>${{escapeHtml(row.allocation_method)}}</small>`;
      }});
      const categories = rows.map(row => `${{escapeHtml(row.name)}} ${{row.year}}`);
      rows.forEach(row => {{ row.estimated_cutoff = row.cutoff_estimate?.time; row.scanned_cutoff = row.cutoff_scan?.time; }});
      const timeSeries = [
        [legacy ? "Strict age-group cutoff" : "Strict pool cutoff", "strict_cutoff", "#006d77"],
        ["Manual extra-place target", "manual_extra_cutoff", "#e76f51"],
        ["Reported last accepted", "reported_cutoff", "#495057"],
        ["Match-density boundary (exploratory)", "estimated_cutoff", "#b08900"],
        [`${{legacy ? "3-absence age-group" : "15-absence gender-pool"}} scan (unverified)`, "scanned_cutoff", "#277da1"],
        [unverified ? "Unverified candidate maximum" : "Reviewed attribution (conditional)", "observed_cutoff", "#e76f51"],
      ].map(([label, key, color]) => ({{
        label, color,
        values: rows.map(row => {{
          if (key === "manual_extra_cutoff") {{
            const extraPlaces = legacy ? qualificationAssumptions.legacyExtraPlaces : qualificationAssumptions.extraPlaces;
            const rank = row.pool_slots + extraPlaces;
            const manualTime = row.manual_pool_times?.[rank - 1];
            return Number.isFinite(manualTime) ? [{{ year: row.year, value: manualTime,
              detail: `${{extraPlaces}} manual extra place${{extraPlaces === 1 ? "" : "s"}}; ${{legacy ? "age-group" : "gender-pool"}} rank ${{rank}}; allocation scenario, not observed acceptance` }}] : [];
          }}
          return Number.isFinite(row[key]) ? [{{
          year: row.year, value: row[key],
          detail: key === "estimated_cutoff" ? escapeHtml(`Exploratory match-density estimate; support range ${{qualificationDuration(row.cutoff_estimate.low_time)}} to ${{qualificationDuration(row.cutoff_estimate.high_time)}}; ${{row.cutoff_estimate.sensitive ? "sensitive to match selection" : "not verified acceptance"}}`) : key === "scanned_cutoff" ? escapeHtml(`${{row.cutoff_scan.athlete}}; ${{legacy ? "age-group" : "gender-pool"}} rank ${{row.cutoff_scan.rank}}; ${{row.cutoff_scan.consecutive_absences}} consecutive absences at ranks ${{row.cutoff_scan.gap_start_rank}} to ${{row.cutoff_scan.gap_end_rank}}; not verified acceptance`) : key === "reported_cutoff" ? escapeHtml(`${{row.reported_cutoff_source}}; reported to the ${{row.reported_cutoff_precision}}${{row.reported_cutoff_athlete ? `; ${{row.reported_cutoff_athlete}}` : ""}}`) : key === "observed_cutoff" ? escapeHtml(`${{row.deepest_name}} · ${{legacy ? "age-group" : "gender-pool"}} rank ${{row.deepest_rank}}`) : `${{row.pool_slots}} initial ${{legacy ? "age-group" : "gender-pool"}} slots`,
          }}] : [];
        }}),
      }}));
      categoryPointChart("konaCutoffChart", categories, timeSeries, {{yAxisLabel: legacy ? "Age-group raw time (HH:MM)" : "Age-graded time (HH:MM)"}});
      categoryPointChart("konaRollDownChart", categories, [{{
        label: `${{legacy ? "3-absence age-group" : "15-absence gender-pool"}} scan · model-derived assumption`, color: "#277da1",
        values: rows.map(row => Number.isFinite(row.cutoff_scan?.modeled_roll_down_percent) ? [{{
          year: row.year, value: row.cutoff_scan.modeled_roll_down_percent,
          detail: `(${{row.cutoff_scan.rank}} estimated ${{legacy ? "age-group" : "gender-pool"}} rank − ${{row.pool_slots}} initial ${{legacy ? "age-group" : "pool"}} slots) ÷ ${{row.cutoff_scan.rank}} × 100; model-derived, not observed declines`,
        }}] : []),
      }}], {{includeZero: true, formatValue: value => `${{value.toFixed(1)}}%`, formatTick: value => `${{value.toFixed(0)}}%`, yAxisLabel: "Model-derived roll-down assumption (%)"}});
      categoryPointChart("konaSkippedChart", categories, [{{
        label: unverified ? "Unverified skipped-place scenario" : "Conditional skipped places", color: "#277da1",
        values: rows.map(row => Number.isFinite(row.estimated_skipped_slots) ? [{{
          year: row.year, value: row.estimated_skipped_slots,
          detail: `${{legacy ? "Age-group" : "Gender-pool"}} rank ${{row.deepest_rank}} minus ${{row.pool_slots}} initial slots; conditional estimate`,
        }}] : []),
      }}], {{zeroBasedNice: true, formatValue: count, formatTick: value => Math.round(value).toString(), yAxisLabel: "Conditional skipped places"}});
      const query = document.getElementById("konaSearch").value.trim().toLocaleLowerCase();
      const status = document.getElementById("konaMatchStatus").value;
      let displayed = 0;
      document.getElementById("konaMatchesBody").innerHTML = starters.flatMap(starter => {{
        if (status === "matched" && !starter.matches.length || status === "unmatched" && starter.matches.length) return [];
        if (query && !`${{starter.name}} ${{starter.country}} ${{starter.division}}`.toLocaleLowerCase().includes(query)) return [];
        const candidates = starter.matches.length ? starter.matches : [null];
        const entries = candidates.filter(entry => (!entry || compareYearVisible(entry.year)) && (!selectedRace || entry && raceKey(entry) === selectedRace));
        if (entries.length) displayed++;
        const reviewKey = konaReviewKey(starter);
        const selectedSource = konaReviews[reviewKey] || "";
        const reviewOptions = [["", "Unknown"], ["other", "Other race / special entry"], ...starter.matches.map(match => [raceKey(match), `${{match.name}} ${{match.year}}`])];
        const review = `<select data-kona-review="${{escapeHtml(reviewKey)}}" aria-label="Slot source for ${{escapeHtml(starter.name)}}">${{reviewOptions.map(([value, label]) => `<option value="${{escapeHtml(value)}}"${{value === selectedSource ? " selected" : ""}}>${{escapeHtml(label)}}</option>`).join("")}}</select>`;
        return entries.map(entry => `<tr><td>${{escapeHtml(starter.name)}}<br><small>#${{escapeHtml(starter.bib)}}</small></td><td>${{escapeHtml(starter.country)}}</td><td>${{escapeHtml(starter.division)}}</td><td>${{escapeHtml(starter.status)}}</td><td>${{escapeHtml(entry?.name || "No match in available races")}}</td><td>${{entry?.year || "—"}}</td><td>${{escapeHtml(entry?.division || "—")}}</td><td>${{qualificationDuration(entry?.finish_time)}}</td><td>${{count(entry?.pool_rank)}}</td><td>${{qualificationDuration(entry?.age_graded)}}</td><td>${{escapeHtml(entry?.initial_slot || "—")}}</td><td>${{starter.matches.length}}</td><td>${{review}}</td></tr>`);
      }}).join("") || `<tr><td colspan="13">No starters match these filters</td></tr>`;
      document.getElementById("konaMatchNote").textContent = `${{displayed.toLocaleString()}} starters shown. Slot-source reviews are ${{konaReviewStorageAvailable ? "saved in this browser" : "kept for this page session only"}}. Unknown and other-route athletes do not contribute to the reviewed cutoff. No match does not mean a slot was declined.`;
    }}
    function initializeKonaTrace() {{
      const cycleControl = document.getElementById("konaCycle");
      const previousCycle = cycleControl.value;
      const cycles = DATASETS.im_kona?.kona_trace_cycles || [{{year: "2026", available: true}}];
      cycleControl.innerHTML = cycles.slice().reverse().map(row => `<option value="${{row.year}}" ${{row.available ? "" : "disabled"}}>${{row.year}}${{row.available ? "" : " (no local starter field)"}}</option>`).join("");
      cycleControl.value = previousCycle || "2026";
      const trace = selectedKonaTrace();
      if (trace) {{
        document.getElementById("konaRace").innerHTML = `<option value="">All available races</option>` + trace.covered_races.map(row => `<option value="${{row.event_id}}|${{row.year}}">${{escapeHtml(row.name)}} ${{row.year}}</option>`).join("");
        document.getElementById("konaCoverageBody").innerHTML = [
          ...trace.covered_races.map(row => ({{...row, available: true}})),
          ...trace.missing_races.map(row => ({{...row, available: false}})),
        ].sort((left, right) => left.date.localeCompare(right.date)).map(row => `<tr><td>${{escapeHtml(row.name)}}</td><td>${{row.year}}</td><td>${{row.date || "—"}}</td><td>${{row.available ? "Available" : escapeHtml(row.reason || "Missing results")}}</td></tr>`).join("");
      }}
      renderKonaTrace();
    }}
    function quantile(sortedValues, fraction) {{
      if (!sortedValues.length) return null;
      const position = (sortedValues.length - 1) * fraction;
      const lower = Math.floor(position), upper = Math.ceil(position);
      if (lower === upper) return sortedValues[lower];
      return sortedValues[lower] + (sortedValues[upper] - sortedValues[lower]) * (position - lower);
    }}
    function stackedPercentageChart(elementId, categories, rows) {{
      const svg = document.getElementById(elementId);
      const width = svg.viewBox.baseVal.width, height = svg.viewBox.baseVal.height;
      const margin = {{ left: 72, right: 24, top: 50, bottom: 90 }};
      const plotHeight = height - margin.top - margin.bottom;
      const groupWidth = (width - margin.left - margin.right) / Math.max(categories.length, 1);
      const barWidth = Math.min(64, groupWidth * 0.62);
      const splitDefinitions = [
        ["Swim", "swim", "#287da1"], ["T1", "t1", "#e9b949"],
        ["Bike", "bike", "#189b74"], ["T2", "t2", "#ee8147"],
        ["Run", "run", "#d94b4b"],
      ];
      if (!categories.length) {{ svg.innerHTML = `<text x="20" y="40">No data available</text>`; return; }}
      const y = value => margin.top + (100 - value) * plotHeight / 100;
      let markup = "";
      for (let tick = 0; tick <= 4; tick++) {{
        const value = tick * 25, yPosition = y(value);
        markup += `<line class="grid" x1="${{margin.left}}" y1="${{yPosition}}" x2="${{width - margin.right}}" y2="${{yPosition}}"/><text x="${{margin.left - 8}}" y="${{yPosition + 4}}" text-anchor="end">${{value}}%</text>`;
      }}
      categories.forEach((category, categoryIndex) => {{
        const center = margin.left + categoryIndex * groupWidth + groupWidth / 2;
        let cumulative = 0;
        splitDefinitions.forEach(([label, key, color]) => {{
          const value = rows[categoryIndex]?.values?.[key] || 0;
          const top = cumulative + value;
          const segmentHeight = Math.max(0, y(cumulative) - y(top));
          const accessibleLabel = `${{category}}, ${{label}}: ${{value.toFixed(1)}}%`;
          markup += `<rect class="data-point" x="${{center - barWidth / 2}}" y="${{y(top)}}" width="${{barWidth}}" height="${{segmentHeight}}" fill="${{color}}" tabindex="0" role="img" aria-label="${{accessibleLabel}}" data-series="${{category}}" data-year="${{rows[categoryIndex]?.count || 0}} finishers" data-value="${{label}} ${{value.toFixed(1)}}%"><title>${{accessibleLabel}}</title></rect>`;
          cumulative = top;
        }});
        const labelY = height - 66;
        markup += `<text x="${{center}}" y="${{labelY}}" text-anchor="end" transform="rotate(-30 ${{center}} ${{labelY}})">${{category}}</text>`;
      }});
      markup += `<line class="axis" x1="${{margin.left}}" y1="${{margin.top}}" x2="${{margin.left}}" y2="${{height - margin.bottom}}"/><line class="axis" x1="${{margin.left}}" y1="${{height - margin.bottom}}" x2="${{width - margin.right}}" y2="${{height - margin.bottom}}"/>`;
      splitDefinitions.forEach(([label, , color], index) => {{
        const legendX = margin.left + index * 130;
        markup += `<rect x="${{legendX}}" y="16" width="12" height="12" fill="${{color}}"/><text x="${{legendX + 18}}" y="27">${{label}}</text>`;
      }});
      svg.innerHTML = markup;
      attachPointTooltips(svg);
    }}
    function rangeCategoryChart(elementId, categories, ranges) {{
      const svg = document.getElementById(elementId);
      const width = svg.viewBox.baseVal.width, height = svg.viewBox.baseVal.height;
      const validValues = ranges.flatMap(row => row ? [row.minimum, row.q1, row.median, row.q3, row.maximum] : []).filter(Number.isFinite);
      if (!categories.length || !validValues.length) {{ svg.innerHTML = `<text x="20" y="40">No data available</text>`; return; }}
      const margin = {{ left: 92, right: 24, top: 28, bottom: 90 }};
      let minimum = Math.min(...validValues), maximum = Math.max(...validValues);
      const padding = Math.max((maximum - minimum) * 0.18, 180);
      minimum -= padding; maximum += padding;
      const groupWidth = (width - margin.left - margin.right) / categories.length;
      const boxWidth = Math.min(48, groupWidth * 0.5);
      const y = value => margin.top + (maximum - value) * (height - margin.top - margin.bottom) / (maximum - minimum);
      let markup = "";
      for (let tick = 0; tick <= 4; tick++) {{
        const value = minimum + (maximum - minimum) * tick / 4;
        const yPosition = y(value);
        markup += `<line class="grid" x1="${{margin.left}}" y1="${{yPosition}}" x2="${{width - margin.right}}" y2="${{yPosition}}"/><text x="${{margin.left - 8}}" y="${{yPosition + 4}}" text-anchor="end">${{duration(value).slice(0, 5)}}</text>`;
      }}
      categories.forEach((category, index) => {{
        const row = ranges[index];
        const center = margin.left + index * groupWidth + groupWidth / 2;
        if (row) {{
          markup += `<line x1="${{center}}" y1="${{y(row.maximum)}}" x2="${{center}}" y2="${{y(row.minimum)}}" stroke="#65716c" stroke-width="2"/>`;
          markup += `<line x1="${{center - boxWidth / 3}}" y1="${{y(row.maximum)}}" x2="${{center + boxWidth / 3}}" y2="${{y(row.maximum)}}" stroke="#65716c" stroke-width="2"/><line x1="${{center - boxWidth / 3}}" y1="${{y(row.minimum)}}" x2="${{center + boxWidth / 3}}" y2="${{y(row.minimum)}}" stroke="#65716c" stroke-width="2"/>`;
          markup += `<rect x="${{center - boxWidth / 2}}" y="${{y(row.q3)}}" width="${{boxWidth}}" height="${{Math.max(1, y(row.q1) - y(row.q3))}}" fill="#dcece7" stroke="#00796b"/>`;
          const detail = `Median ${{duration(row.median)}} · IQR ${{duration(row.q1)}}–${{duration(row.q3)}} · range ${{duration(row.minimum)}}–${{duration(row.maximum)}} · n=${{row.count}}`;
          markup += `<circle class="data-point" cx="${{center}}" cy="${{y(row.median)}}" r="5" fill="#00796b" tabindex="0" role="img" aria-label="${{category}}: ${{detail}}" data-series="${{category}}" data-year="${{row.count}} years" data-value="${{detail}}"><title>${{category}}: ${{detail}}</title></circle>`;
        }}
        const labelY = height - 66;
        markup += `<text x="${{center}}" y="${{labelY}}" text-anchor="end" transform="rotate(-30 ${{center}} ${{labelY}})">${{category}}</text>`;
      }});
      markup += `<line class="axis" x1="${{margin.left}}" y1="${{margin.top}}" x2="${{margin.left}}" y2="${{height - margin.bottom}}"/><line class="axis" x1="${{margin.left}}" y1="${{height - margin.bottom}}" x2="${{width - margin.right}}" y2="${{height - margin.bottom}}"/>`;
      svg.innerHTML = markup;
      attachPointTooltips(svg);
    }}
    function renderDistributionCompare(elementId, eventIds) {{
      const categories = eventIds.map(id => DATASETS[id].name);
      const series = yearSeries(eventIds, (id, year) => {{
        if (isModifiedCourse(id, year)) return null;
        const values = DATASETS[id].overall[year] || [];
        return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
      }});
      categoryPointChart(elementId, categories, series);
    }}
    function ageGroupSplitStats(eventId) {{
      if (!splitStatsCache.has(eventId)) {{
        const byYear = {{}};
        DATASETS[eventId].records.forEach(row => {{
          if (!/^[MF]\\d{{2}}-\\d{{2}}$/.test(String(row.division).trim().toUpperCase())) return;
          if (!byYear[row.year]) byYear[row.year] = Object.fromEntries(splits.map(([, key]) => [key, []]));
          splits.forEach(([, key]) => {{ if (row[key] > 0) byYear[row.year][key].push(row[key]); }});
        }});
        const stats = {{}};
        Object.entries(byYear).forEach(([year, values]) => {{
          stats[year] = Object.fromEntries(Object.entries(values).map(([key, times]) => {{
            times.sort((left, right) => left - right);
            return [key, times.length ? {{
              mean: times.reduce((sum, value) => sum + value, 0) / times.length,
              median: quantile(times, 0.5),
              count: times.length,
            }} : null];
          }}));
        }});
        splitStatsCache.set(eventId, stats);
      }}
      return splitStatsCache.get(eventId);
    }}
    function renderSplitDistributions() {{
      const eventIds = raceGroups()[compareSplitDistance.value] || [];
      const categories = eventIds.map(id => DATASETS[id].name);
      splits.forEach(([label, key]) => {{
        const transition = key === "t1" || key === "t2";
        categoryPointChart(
          `compareSplit${{label}}`,
          categories,
          yearSeries(eventIds, (id, year) => {{
            const stats = isModifiedCourse(id, year) ? null : ageGroupSplitStats(id)[year]?.[key];
            if (!stats) return null;
            const speed = metric(key, stats.mean, DATASETS[id].distances);
            return {{
              value: stats.mean,
              detail: `${{speed ? `${{speed}} · ` : ""}}median ${{duration(stats.median)}} · n=${{stats.count.toLocaleString()}}`,
            }};
          }}),
          {{
            formatTick: value => transition ? duration(value).slice(3) : duration(value).slice(0, 5),
            minimumPadding: transition ? 20 : 120,
            yAxisLabel: `Mean ${{label}} (${{transition ? "MM:SS" : "HH:MM"}})`,
          }},
        );
      }});
    }}
    function signedPercent(factor) {{
      if (!Number.isFinite(factor)) return "—";
      const value = 100 * (factor - 1);
      return `${{value > 0.05 ? "+" : value < -0.05 ? "−" : ""}}${{Math.abs(value).toFixed(1)}}%`;
    }}
    function geometricMean(values) {{
      return Math.exp(values.reduce((sum, value) => sum + Math.log(value), 0) / values.length);
    }}
    function ageGroupTimesByYear(eventId, gender) {{
      const key = `${{eventId}}|${{gender}}`;
      if (!genderTimeCache.has(key)) {{
        const byYear = {{}};
        DATASETS[eventId].records.forEach(row => {{
          if (gender && row.gender !== gender || !/^[MF]\\d{{2}}-\\d{{2}}$/.test(row.division)) return;
          if (!byYear[row.year]) byYear[row.year] = [];
          byYear[row.year].push(row.overall);
        }});
        Object.values(byYear).forEach(values => values.sort((left, right) => left - right));
        genderTimeCache.set(key, byYear);
      }}
      return genderTimeCache.get(key);
    }}
    function courseEffect(eventId, split) {{
      const modelled = DATASETS[eventId].course_model?.course?.[split];
      if (Number.isFinite(modelled)) return modelled;
      const values = Object.values(DATASETS[eventId].course_factors || {{}})
        .map(entry => entry[split])
        .filter(Number.isFinite)
        .sort((left, right) => left - right);
      return values.length ? quantile(values, 0.5) : null;
    }}
    function conditionsFactor(eventId, year) {{
      const model = DATASETS[eventId].course_model;
      const entry = DATASETS[eventId].course_factors?.[year];
      const course = model?.course?.overall;
      const season = model?.season?.[year]?.overall;
      return entry && Number.isFinite(course) && Number.isFinite(season) ? entry.overall / (course * season) : null;
    }}
    function experimentalContext() {{
      const group = experimentalDistance.value;
      const eventIds = (raceGroups()[group] || []).filter(id => Object.keys(DATASETS[id].course_factors || {{}}).length);
      const model = eventIds.length ? DATASETS[eventIds[0]].course_model || {{}} : {{}};
      return {{ group, split: "overall", eventIds, model }};
    }}
    function fillRaceSelect(select, eventIds, preferred) {{
      const previous = select.value;
      select.innerHTML = eventIds.map(id => `<option value="${{id}}">${{escapeHtml(DATASETS[id].name)}}</option>`).join("");
      select.value = eventIds.includes(previous) ? previous : eventIds.includes(preferred) ? preferred : (eventIds[0] || "");
    }}
    function factorText(factor) {{
      return Number.isFinite(factor) ? `${{factor.toFixed(3)}} (${{signedPercent(factor)}})` : "—";
    }}
    function splitLabel(split) {{
      return split[0].toUpperCase() + split.slice(1);
    }}
    // Mirrors identity_key and repeat_athlete_records in src/course_difficulty.py.
    function identityKey(name, gender, country) {{
      const ascii = String(name).normalize("NFKD").replace(/[^\\x00-\\x7F]/g, "").toLowerCase();
      const tokens = ascii.replace(/[^a-z ]/g, " ").split(" ").filter(Boolean).sort();
      return tokens.length ? `${{tokens.join(" ")}}|${{gender}}|${{country}}` : null;
    }}
    function repeatAthleteIndex(group) {{
      if (athleteIndexCache.has(group)) return athleteIndexCache.get(group);
      const byKey = new Map();
      (raceGroups()[group] || []).forEach(eventId => {{
        DATASETS[eventId].records.forEach(row => {{
          if (isModifiedCourse(eventId, row.year)) return;
          const division = String(row.division).trim().toUpperCase();
          const match = /^[MF](\\d{{2}})-\\d{{2}}$/.exec(division);
          if (!match || division[0] !== String(row.gender)[0]) return;
          const key = identityKey(row.name, row.gender, row.country);
          if (!key) return;
          if (!byKey.has(key)) byKey.set(key, []);
          byKey.get(key).push({{ eventId, year: row.year, raceYear: `${{eventId}}:${{row.year}}`, division, lowerAge: Number(match[1]), row }});
        }});
      }});
      const athletes = [];
      byKey.forEach((entries, key) => {{
        const raceYears = new Set(entries.map(entry => entry.raceYear));
        if (raceYears.size < 2 || raceYears.size !== entries.length) return;
        const birthMin = Math.max(...entries.map(entry => Number(entry.year) - entry.lowerAge - 4));
        const birthMax = Math.min(...entries.map(entry => Number(entry.year) - entry.lowerAge));
        if (birthMin > birthMax) return;
        entries.sort((left, right) => Number(left.year) - Number(right.year) || (left.raceYear < right.raceYear ? -1 : left.raceYear > right.raceYear ? 1 : 0));
        entries.forEach((entry, index) => {{ entry.returning = index > 0; }});
        athletes.push({{ key, nameKey: key.split("|")[0], entries }});
      }});
      athleteIndexCache.set(group, athletes);
      return athletes;
    }}
    function athleteLevelRows(athlete, split, model) {{
      const returningFactor = model.returning?.[split] ?? 1;
      const limit = model.fit?.[split]?.trim_limit ?? Infinity;
      const rows = athlete.entries.map(entry => {{
        const raw = entry.row[split];
        const standard = model.standards?.[entry.division];
        const factor = courseFactor(entry.eventId, entry.year, split);
        if (!(raw > 0) || !Number.isFinite(standard) || !factor) return {{ entry, raw, standard, factor, usable: false }};
        const graded = raw * standard;
        const returning = entry.returning ? returningFactor : 1;
        return {{ entry, raw, standard, factor, graded, returning, normalised: graded / (factor * returning), usable: true }};
      }});
      const geometric = items => Math.exp(items.reduce((sum, row) => sum + Math.log(row.normalised), 0) / items.length);
      const usable = rows.filter(row => row.usable);
      let level = usable.length ? geometric(usable) : NaN;
      usable.forEach(row => {{ row.outlier = Math.abs(Math.log(row.normalised / level)) > limit; }});
      const kept = usable.filter(row => !row.outlier);
      if (kept.length && kept.length < usable.length) level = geometric(kept);
      usable.forEach(row => {{
        row.predicted = level * row.factor * row.returning / row.standard;
        row.residual = row.raw / row.predicted;
      }});
      return {{ rows, level, used: kept.length }};
    }}
    function renderFitTable() {{
      const {{ group, model }} = experimentalContext();
      const fit = model.fit || {{}};
      document.getElementById("experimentalStandardName").textContent = `${{model.cycle || "current"}}-cycle ${{group === "im" ? "Kona" : "IRONMAN 70.3"}} Standard`;
      document.getElementById("experimentalFitBody").innerHTML = ["swim", "bike", "run", "overall"].map(key => {{
        const row = fit[key];
        if (!row) return "";
        const share = 100 * row.trimmed / (row.records + row.trimmed);
        return `<tr><td>${{splitLabel(key)}}</td><td>${{row.athletes.toLocaleString()}}</td><td>${{row.records.toLocaleString()}}</td><td>${{row.trimmed.toLocaleString()}} (${{share.toFixed(1)}}%)</td><td>±${{(100 * row.trim_limit).toFixed(1)}}%</td><td>${{(100 * row.residual_sd).toFixed(1)}}%</td><td>${{factorText(row.returning)}}</td></tr>`;
      }}).join("") || `<tr><td colspan="7" class="empty">No fit statistics available.</td></tr>`;
    }}
    function renderBreakdown() {{
      const {{ eventIds, split, model }} = experimentalContext();
      const eventId = eventIds.includes("im_austria") ? "im_austria" : eventIds[0];
      const body = document.getElementById("experimentalBreakdownBody");
      document.getElementById("experimentalBreakdownTitle").textContent = `Factor breakdown by race-year · ${{split}}`;
      document.getElementById("experimentalBreakdownHead").innerHTML = `<tr><th>Year</th><th>Repeat athletes (overall)</th><th>Race-year factor f</th><th title="Standard error from the spread of the athletes' residuals.">± SE</th><th>Course C</th><th>Season S</th><th>Conditions = f ÷ (C × S)</th></tr>`;
      if (!eventId) {{ body.innerHTML = `<tr><td colspan="7" class="empty">No course factors available.</td></tr>`; return; }}
      const course = DATASETS[eventId].course_model?.course?.[split];
      const years = [...new Set([...Object.keys(DATASETS[eventId].overall), ...Object.keys(DATASETS[eventId].course_factors)])].sort().filter(compareYearVisible);
      let example = null;
      body.innerHTML = years.map(year => {{
        const entry = DATASETS[eventId].course_factors[year];
        if (!entry) {{
          const reason = DATASETS[eventId].modified_courses?.[year] || "no repeat athletes";
          return `<tr><td>${{yearCell(eventId, year)}}</td><td colspan="6">Not estimated: ${{escapeHtml(reason)}}</td></tr>`;
        }}
        const factor = entry[split];
        const season = model.season?.[year]?.[split];
        const conditions = Number.isFinite(course) && Number.isFinite(season) ? factor / (course * season) : null;
        if (conditions !== null) example = {{ year, factor, season, conditions }};
        const se = entry.se?.[split];
        return `<tr><td>${{yearCell(eventId, year)}}</td><td>${{entry.repeat_athletes.toLocaleString()}}</td><td><strong>${{factorText(factor)}}</strong></td><td>${{Number.isFinite(se) ? `±${{(100 * se).toFixed(1)}}%` : "—"}}</td><td>${{factorText(course)}}</td><td>${{factorText(season)}}</td><td>${{factorText(conditions)}}</td></tr>`;
      }}).join("");
      document.getElementById("experimentalBreakdownNote").textContent = example
        ? `Every row multiplies back: ${{example.year}}: f = ${{course.toFixed(3)}} × ${{example.season.toFixed(3)}} × ${{example.conditions.toFixed(3)}} = ${{example.factor.toFixed(3)}}. Course C is the geometric mean of f ÷ S over this race's race-years, so its conditions multiply to 1. Season S is shared by all races in that year.`
        : "With a single race of this distance, course and season cannot be separated; f is the only factor.";
    }}
    function renderAthleteExplorer() {{
      if (activeTab !== "experimental") return;
      const {{ group, split, model }} = experimentalContext();
      const athletes = repeatAthleteIndex(group);
      const selected = [...athletes]
        .filter(athlete => athlete.entries.some(entry => compareYearVisible(entry.year)))
        .sort((left, right) => right.entries.length - left.entries.length || left.nameKey.localeCompare(right.nameKey))
        .slice(0, 3);
      const b = model.returning?.[split];
      document.getElementById("experimentalAthleteHead").innerHTML = `<tr><th>Race</th><th>Year</th><th>Age group</th><th>Raw ${{split}} t</th><th>Age standard A</th><th>t′ = t × A</th><th>Race-year factor f</th><th>Returning b</th><th title="Should be nearly equal within one athlete if the factors are right.">t′ ÷ (f × b)</th><th>Expected = e<sup>a</sup> × f × b ÷ A</th><th>Actual ÷ expected</th></tr>`;
      document.getElementById("experimentalAthleteBody").innerHTML = selected.map(athlete => {{
        const {{ rows, level, used }} = athleteLevelRows(athlete, split, model);
        const first = athlete.entries.at(-1).row;
        const header = `<tr class="athlete-row"><td colspan="11"><strong>${{escapeHtml(first.name)}}</strong> · ${{escapeHtml(first.country)}} · ${{escapeHtml(first.gender)}} · ${{athlete.entries.length}} race-years · ability e<sup>a</sup> = <strong>${{duration(level)}}</strong> (age-graded ${{split}} on an average course, geometric mean of ${{used}} results)</td></tr>`;
        return header + rows.filter(row => compareYearVisible(row.entry.year)).map(row => {{
          const entry = row.entry;
          if (!row.usable) return `<tr><td>${{escapeHtml(DATASETS[entry.eventId].name)}}</td><td>${{yearCell(entry.eventId, entry.year)}}</td><td>${{escapeHtml(entry.division)}}</td><td>${{duration(row.raw)}}</td><td colspan="7">Not used: no age standard or race-year factor</td></tr>`;
          const residual = row.outlier ? ` class="outlier" title="Beyond the outlier limit; not used for e^a."` : "";
          return `<tr><td>${{escapeHtml(DATASETS[entry.eventId].name)}}</td><td>${{yearCell(entry.eventId, entry.year)}}</td><td>${{escapeHtml(entry.division)}}</td><td>${{duration(row.raw)}}</td><td>${{row.standard.toFixed(4)}}</td><td>${{duration(row.graded)}}</td><td>${{row.factor.toFixed(3)}}</td><td>${{entry.returning ? row.returning.toFixed(3) : "1 (first)"}}</td><td><strong>${{duration(row.normalised)}}</strong></td><td>${{duration(row.predicted)}}</td><td${{residual}}>${{signedPercent(row.residual)}}${{row.outlier ? " (outlier)" : ""}}</td></tr>`;
        }}).join("");
      }}).join("") || `<tr><td colspan="11" class="empty">No matched athlete found. Only athletes with at least two usable race-years of this distance are included.</td></tr>`;
      const shown = `the ${{selected.length}} athletes with the most race-years`;
      document.getElementById("experimentalAthleteNote").textContent = `${{athletes.length.toLocaleString()}} matched athletes for this distance; showing ${{shown}}. Read each block left to right: raw time × age standard A = age-graded t′; dividing by the race-year factor f (and by b = ${{Number.isFinite(b) ? b.toFixed(3) : "1"}} for returning results) gives t′ ÷ (f × b). If the factors are right, this column is nearly the same in every row of one athlete; its geometric mean is the athlete's ability e^a. Expected = e^a × f × b ÷ A is the raw time the model predicts; the last column is what the model cannot explain (pacing, a bad day, weather at that athlete's time of day). Values are recomputed in the browser from the published factors.`;
    }}
    function renderHeadToHead() {{
      if (activeTab !== "experimental") return;
      const {{ group, split, eventIds, model }} = experimentalContext();
      const raceA = eventIds.includes("im_hamburg") ? "im_hamburg" : eventIds[0];
      const raceB = eventIds.includes("im_austria") ? "im_austria" : eventIds.find(id => id !== raceA);
      const body = document.getElementById("experimentalPairBody");
      const metricsText = (count, observed, modelled) => {{
        document.getElementById("experimentalPairCount").textContent = count;
        document.getElementById("experimentalPairObserved").textContent = observed;
        document.getElementById("experimentalPairModel").textContent = modelled;
      }};
      document.getElementById("experimentalPairHead").innerHTML = `<tr><th>Athlete</th><th>Course A results (raw ${{split}})</th><th>Course B results (raw ${{split}})</th><th>Data: age-graded B ÷ A</th><th>Model: f<sub>B</sub>·b ÷ f<sub>A</sub>·b</th></tr>`;
      if (!raceA || !raceB || raceA === raceB) {{
        metricsText("—", "—", "—");
        body.innerHTML = `<tr><td colspan="5" class="empty">${{eventIds.length < 2 ? "Needs at least two races of this distance." : "Select two different courses."}}</td></tr>`;
        document.getElementById("experimentalPairNote").textContent = "";
        return;
      }}
      const returningFactor = model.returning?.[split] ?? 1;
      const usable = entry => compareYearVisible(entry.year) && entry.row[split] > 0 && Number.isFinite(model.standards?.[entry.division]) && courseFactor(entry.eventId, entry.year, split);
      const meanLog = (entries, value) => entries.reduce((sum, entry) => sum + Math.log(value(entry)), 0) / entries.length;
      const graded = entry => entry.row[split] * model.standards[entry.division];
      const expected = entry => courseFactor(entry.eventId, entry.year, split) * (entry.returning ? returningFactor : 1);
      const pairs = repeatAthleteIndex(group).flatMap(athlete => {{
        const atA = athlete.entries.filter(entry => entry.eventId === raceA && usable(entry));
        const atB = athlete.entries.filter(entry => entry.eventId === raceB && usable(entry));
        if (!atA.length || !atB.length) return [];
        return [{{
          athlete, atA, atB,
          observed: Math.exp(meanLog(atB, graded) - meanLog(atA, graded)),
          modelled: Math.exp(meanLog(atB, expected) - meanLog(atA, expected)),
        }}];
      }});
      if (!pairs.length) {{
        metricsText("0", "—", "—");
        body.innerHTML = `<tr><td colspan="5" class="empty">No athlete raced both courses.</td></tr>`;
        document.getElementById("experimentalPairNote").textContent = "";
        return;
      }}
      const geometric = values => Math.exp(values.reduce((sum, value) => sum + Math.log(value), 0) / values.length);
      const observed = pairs.map(pair => pair.observed).sort((left, right) => left - right);
      metricsText(
        pairs.length.toLocaleString(),
        `${{signedPercent(geometric(observed))}} (median ${{signedPercent(quantile(observed, 0.5))}})`,
        signedPercent(geometric(pairs.map(pair => pair.modelled))),
      );
      const results = entries => entries.map(entry => `${{entry.year}}: ${{duration(entry.row[split])}}`).join(", ");
      const rows = [...pairs].sort((left, right) => left.athlete.nameKey.localeCompare(right.athlete.nameKey));
      body.innerHTML = rows.slice(0, 300).map(pair => `<tr><td>${{escapeHtml(pair.athlete.entries.at(-1).row.name)}}</td><td>${{results(pair.atA)}}</td><td>${{results(pair.atB)}}</td><td>${{signedPercent(pair.observed)}}</td><td>${{signedPercent(pair.modelled)}}</td></tr>`).join("");
      const nameA = DATASETS[raceA].name, nameB = DATASETS[raceB].name;
      document.getElementById("experimentalPairNote").textContent = `${{rows.length > 300 ? `First 300 of ${{rows.length.toLocaleString()}} athletes, sorted by name. ` : ""}}Each row is one athlete: the geometric mean of their age-graded ${{split}} times at ${{nameB}} divided by that at ${{nameA}}. The model column uses the published race-year factors and returning effect for exactly the same race-years. Both averages should agree; they differ slightly because the model also learns from athletes who raced other courses and removes outliers, while this check uses only athletes who did both.`;
    }}
    function renderExperimentalDetails() {{
      renderFitTable();
      renderBreakdown();
      renderAthleteExplorer();
      renderHeadToHead();
    }}
    function renderExperimental() {{
      const group = experimentalDistance.value;
      const split = "overall";
      const percentFormat = value => `${{value > 0.05 ? "+" : value < -0.05 ? "−" : ""}}${{Math.abs(value).toFixed(1)}}%`;
      const eventIds = (raceGroups()[group] || []).filter(id => Object.keys(DATASETS[id].course_factors || {{}}).length);
      const categories = eventIds.map(id => DATASETS[id].name);
      const model = eventIds.length ? DATASETS[eventIds[0]].course_model || {{}} : {{}};
      const modelled = eventIds.some(id => Number.isFinite(DATASETS[id].course_model?.course?.overall));
      const returning = model.returning?.overall;
      document.getElementById("experimentalReturningNote").textContent = Number.isFinite(returning)
        ? `${{group === "im" ? "140.6" : "70.3"}}: ${{Math.abs(100 * (returning - 1)).toFixed(1)}}% ${{returning < 1 ? "faster" : "slower"}} overall`
        : "not estimated";

      const splitKeys = ["swim", "bike", "run", "overall"];
      const rows = eventIds.map(id => {{
        const years = Object.keys(DATASETS[id].course_factors).filter(compareYearVisible);
        const conditions = years.map(year => conditionsFactor(id, year)).filter(Number.isFinite);
        const spread = conditions.length ? conditions : years.map(year => DATASETS[id].course_factors[year].overall);
        return {{
          id,
          years: years.length,
          effects: Object.fromEntries(splitKeys.map(key => [key, courseEffect(id, key)])),
          minimum: Math.min(...spread),
          maximum: Math.max(...spread),
          athletes: lowerMedian(years.map(year => DATASETS[id].course_factors[year].repeat_athletes)),
        }};
      }}).filter(row => row.years).sort((left, right) => left.effects.overall - right.effects.overall);
      const rangeHeader = modelled
        ? `<th title="Deviation of single race-years from course × season: heat, wind, non-wetsuit swims, course changes.">Race-day conditions</th>`
        : `<th title="Fastest and slowest race-year, overall.">Overall range</th>`;
      document.getElementById("experimentalFactorHead").innerHTML = `<tr><th>Race</th><th>Race-years</th><th>Swim</th><th>Bike</th><th>Run</th><th>Overall</th>${{rangeHeader}}<th title="Median number of matched athletes per race-year.">Repeat athletes / year</th></tr>`;
      document.getElementById("experimentalFactorBody").innerHTML = rows.length ? rows.map(row => `<tr><td>${{escapeHtml(DATASETS[row.id].name)}}${{isQualifyingEvent(row.id) ? "" : " (World Championship)"}}</td><td>${{row.years}}</td>${{splitKeys.map(key => `<td>${{key === "overall" ? "<strong>" : ""}}${{signedPercent(row.effects[key])}}${{key === "overall" ? "</strong>" : ""}}</td>`).join("")}}<td>${{row.years > 1 ? `${{signedPercent(row.minimum)}} to ${{signedPercent(row.maximum)}}` : "single race-year"}}</td><td>${{Number(row.athletes).toLocaleString()}}</td></tr>`).join("")
        : `<tr><td colspan="8" class="empty">No course factors available.</td></tr>`;
      document.getElementById("experimentalFactorNote").textContent = modelled
        ? "Split columns are season-adjusted course effects: the typical factor of each course in an average season, so races with only recent editions are not flattered by faster recent seasons. Race-day conditions show how far single race-years deviated from course × season. Sampling error is about ±0.1–0.3% per race-year."
        : "Median across race-years. With a single race of this distance, course and season effects cannot be separated. Sampling error is about ±0.5% per race-year.";
      renderExperimentalDetails();

      const seasonModel = model.season || {{}};
      const seasons = Object.keys(seasonModel).sort();
      if (seasons.length) {{
        lineChart(
          "experimentalSeasonChart",
          seasons,
          splitKeys.map((key, index) => ({{
            label: key[0].toUpperCase() + key.slice(1),
            color: ["#277da1", "#e76f51", "#2a9d8f", "#1d3557"][index],
            values: seasons.map(year => 100 * (seasonModel[year][key] - 1)),
          }})),
          percentFormat,
        );
      }} else {{
        document.getElementById("experimentalSeasonChart").innerHTML = `<text x="20" y="40">Season effects need at least two races of this distance</text>`;
      }}

      document.getElementById("experimentalFactorTitle").textContent = `Race-year difficulty · ${{split}}`;
      categoryPointChart(
        "experimentalFactorChart",
        categories,
        yearSeries(eventIds, (id, year) => {{
          const entry = DATASETS[id].course_factors[year];
          if (!entry || !Number.isFinite(entry[split])) return null;
          const se = entry.se?.[split];
          return {{
            value: 100 * (entry[split] - 1),
            detail: `×${{entry[split].toFixed(3)}}${{Number.isFinite(se) ? ` ± ${{(100 * se).toFixed(1)}}%` : ""}} · ${{entry.repeat_athletes.toLocaleString()}} repeat athletes`,
          }};
        }}),
        {{ includeZero: true, formatValue: percentFormat, formatTick: percentFormat, minimumPadding: 1, yAxisLabel: `${{split}} vs. average race-year` }},
      );

      const percentage = Math.min(100, Math.max(0.1, Number(experimentalPercentile.value) || 20));
      const percentageLabel = Number.isInteger(percentage) ? percentage.toFixed(0) : percentage.toFixed(1);
      document.getElementById("experimentalFieldTitle").textContent = `Course-adjusted all-cohort field strength · top ${{percentageLabel}}%`;
      categoryPointChart(
        "experimentalFieldChart",
        categories,
        yearSeries(eventIds, (id, year) => {{
          const factor = courseFactor(id, year);
          const values = ageGroupTimesByYear(id)[year] || [];
          if (!factor || !values.length) return null;
          const rank = Math.max(1, Math.ceil(values.length * percentage / 100));
          const cutoff = values[rank - 1];
          return {{
            value: cutoff / factor,
            detail: `raw ${{duration(cutoff)}} · course ${{signedPercent(factor)}} · rank ${{rank}}/${{values.length}}`,
          }};
        }}),
        {{ yAxisLabel: `Average-course top-${{percentageLabel}}% cutoff (HH:MM)` }},
      );

      const qualifyingIds = eventIds.filter(isQualifyingEvent);
      const neededByEvent = Object.fromEntries(qualifyingIds.map(id => [id, {{}}]));
      qualifyingIds.forEach(id => qualificationYears(id, qualificationSystem).forEach(year => {{
        const values = ["Male", "Female"].flatMap(rowGender => compareAgeGroups([id]).map(ageGroup =>
          qualificationStandard(id, year, rowGender, ageGroup, qualificationSystem)?.needed
        )).filter(Number.isFinite);
        if (values.length) neededByEvent[id][year] = {{
          value: quantile(values.sort((left, right) => left - right), 0.5),
          detail: `Median across ${{values.length}} available gender/age-group targets`,
        }};
      }}));
      const neededIds = qualifyingIds.filter(id => Object.keys(neededByEvent[id]).some(year => courseFactor(id, year)));
      document.getElementById("experimentalNeededTitle").textContent = "Course-adjusted median target across all divisions";
      categoryPointChart(
        "experimentalNeededChart",
        neededIds.map(id => DATASETS[id].name),
        yearSeries(neededIds, (id, year) => {{
          const entry = neededByEvent[id][year];
          const factor = courseFactor(id, year);
          if (!entry || !factor) return null;
          return {{
            value: entry.value / factor,
            detail: `race time needed ${{duration(entry.value)}} · course ${{signedPercent(factor)}}`,
          }};
        }}),
        {{ yAxisLabel: "Average-course time needed (HH:MM)" }},
      );

      const gpxIds = group === "im"
        ? eventIds.filter(id => Number.isFinite(DATASETS[id].bike_course_correction?.course_difficulty_factor) && Number.isFinite(courseEffect(id, "bike")))
        : [];
      if (gpxIds.length < 2) {{
        document.getElementById("experimentalGpxChart").innerHTML = `<text x="20" y="40">GPX tracks are only available for IRONMAN 140.6 races</text>`;
        return;
      }}
      const gpxFactor = id => DATASETS[id].bike_course_correction.course_difficulty_factor;
      const gpxReference = geometricMean(gpxIds.map(gpxFactor));
      const dataReference = geometricMean(gpxIds.map(id => courseEffect(id, "bike")));
      categoryPointChart(
        "experimentalGpxChart",
        gpxIds.map(id => DATASETS[id].name),
        [
          {{
            label: "GPX reference-rider model",
            color: "#277da1",
            values: gpxIds.map(id => [{{
              year: "GPX model",
              value: 100 * (gpxFactor(id) / gpxReference - 1),
              detail: `course difficulty factor ${{gpxFactor(id).toFixed(4)}} · ${{escapeHtml(DATASETS[id].bike_course_correction.source)}}`,
            }}]),
          }},
          {{
            label: "Repeat-athlete data (bike course effect)",
            color: "#e76f51",
            values: gpxIds.map(id => [{{
              year: "Athlete data",
              value: 100 * (courseEffect(id, "bike") / dataReference - 1),
              detail: `season-adjusted bike course factor ×${{courseEffect(id, "bike").toFixed(3)}}`,
            }}]),
          }},
        ],
        {{ includeZero: true, formatValue: percentFormat, formatTick: percentFormat, minimumPadding: 1, yAxisLabel: "Bike vs. mean of compared courses" }},
      );
    }}
    function compareAgeGroups(eventIds) {{
      const male = new Set(), female = new Set();
      eventIds.filter(isQualifyingEvent).forEach(id => {{
        const targets = qualificationSystem === "historical"
          ? DATASETS[id].historical_qualification.targets
          : DATASETS[id].qualification.targets;
        targets.forEach(row => {{
          if (row.gender === "Male") male.add(row.division.slice(1));
          if (row.gender === "Female") female.add(row.division.slice(1));
        }});
      }});
      return [...male].filter(ageGroup => female.has(ageGroup)).sort((left, right) => Number(left.split("-")[0]) - Number(right.split("-")[0]));
    }}
    function qualificationYears(eventId, system) {{
      if (!isQualifyingEvent(eventId)) return [];
      const ds = DATASETS[eventId];
      const years = system === "historical"
        ? ds.historical_qualification.targets.map(row => row.year)
        : ds.qualification.summaries.map(row => row.year);
      return [...new Set(years)].sort().filter(compareYearVisible);
    }}
    function raceQualificationYearlyValues(eventId, gender, ageGroup, system = qualificationSystem) {{
      return qualificationYears(eventId, system)
        .filter(year => !isModifiedCourse(eventId, year))
        .map(year => {{
          const standard = qualificationStandard(eventId, year, gender, ageGroup, system);
          if (!standard || !Number.isFinite(standard.needed)) return null;
          const slots = standard.scope === "age group"
            ? `${{standard.slots}} age-group slots`
            : `${{standard.performanceSlots}} pool + ${{standard.automaticSlots}} automatic ${{gender === "Male" ? "men's" : "women's"}} slots`;
          const setBy = standard.scope === "age group"
            ? "last allocated slot"
            : standard.needed === standard.winner ? "age-group winner" : "pool equivalent";
          return {{
            year,
            value: standard.needed,
            detail: `${{standard.method}} · ${{standard.cutoffSource}} · ${{slots}} · ${{standard.starters}} starters · set by ${{setBy}}`,
            standard,
          }};
        }})
        .filter(Boolean);
    }}
    function renderQualificationCompareGroup(elementId, eventIds, ageGroup, gender) {{
      const availableEventIds = eventIds.filter(id => raceQualificationYearlyValues(id, gender, ageGroup).length);
      const categories = availableEventIds.map(id => DATASETS[id].name);
      const valuesByEvent = Object.fromEntries(availableEventIds.map(id => [id, Object.fromEntries(
        raceQualificationYearlyValues(id, gender, ageGroup).map(entry => [entry.year, entry])
      )]));
      const series = yearSeries(availableEventIds, (id, year) => valuesByEvent[id][year]);
      categoryPointChart(elementId, categories, series);
    }}
    function selectedAgeGroupRecords(eventId, year, gender, ageGroup) {{
      const cacheKey = `${{eventId}}|${{gender}}|${{ageGroup}}`;
      if (!selectedAgeGroupRecordCache.has(cacheKey)) {{
        const division = `${{gender === "Male" ? "M" : "F"}}${{ageGroup}}`;
        const byYear = {{}};
        DATASETS[eventId].records.forEach(row => {{
          if (row.gender !== gender || row.division !== division) return;
          if (!byYear[row.year]) byYear[row.year] = [];
          byYear[row.year].push(row);
        }});
        selectedAgeGroupRecordCache.set(cacheKey, byYear);
      }}
      return selectedAgeGroupRecordCache.get(cacheKey)[year] || [];
    }}
    function slotPressureForYear(eventId, year, gender, ageGroup) {{
      const dataset = DATASETS[eventId];
      if (qualificationSystem === "historical") {{
        const division = `${{gender === "Male" ? "M" : "F"}}${{ageGroup}}`;
        const target = dataset.historical_qualification.targets.find(row =>
          row.year === year && row.gender === gender && row.division === division
        );
        if (!target) return null;
        if (target.slot_scope === "age group") {{
          return target.starters > 0 ? {{
            value: 100 * target.slots / target.starters,
            detail: `${{target.slots}} slots / ${{target.starters}} ${{division}} starters`,
          }} : null;
        }}
        const summary = dataset.qualification.summaries.find(row => row.year === year);
        const starters = summary?.[`${{gender.toLowerCase()}}_starters`];
        return starters > 0 ? {{
          value: 100 * target.slots / starters,
          detail: `${{target.slots}} gender slots / ${{starters}} eligible starters`,
        }} : null;
      }}
      const summary = dataset.qualification.summaries.find(row => row.year === year);
      if (!summary) return null;
      const key = gender.toLowerCase();
      const slots = summary[`${{key}}_auto`] + (slotAllocations[eventId]?.[key] ?? summary[`${{key}}_perf`]);
      const starters = summary[`${{key}}_starters`];
      return starters > 0 ? {{
        value: 100 * slots / starters,
        detail: `${{slots}} gender slots / ${{starters}} eligible starters`,
      }} : null;
    }}
    function renderAdditionalCompare(eventIds, ageGroup, gender) {{
      const qualificationByEvent = Object.fromEntries(eventIds.map(eventId => [
        eventId,
        Object.fromEntries(
          raceQualificationYearlyValues(eventId, gender, ageGroup).map(row => [row.year, row])
        ),
      ]));

      const pressureEventIds = eventIds.filter(eventId =>
        Object.keys(DATASETS[eventId].overall).some(year =>
          Number.isFinite(slotPressureForYear(eventId, year, gender, ageGroup)?.value)
        )
      );
      categoryPointChart(
        "compareSlotPressure",
        pressureEventIds.map(eventId => DATASETS[eventId].name),
        yearSeries(pressureEventIds, (eventId, year) =>
          slotPressureForYear(eventId, year, gender, ageGroup)
        ),
        {{
          formatValue: value => `${{value.toFixed(2)}} slots / 100`,
          formatTick: value => value.toFixed(1),
          yAxisLabel: "Slots per 100 eligible starters",
          nonnegative: true,
          zeroBasedNice: true,
        }},
      );

      const percentileEventIds = eventIds.filter(eventId =>
        Object.keys(qualificationByEvent[eventId]).some(year =>
          selectedAgeGroupRecords(eventId, year, gender, ageGroup).length
        )
      );
      categoryPointChart(
        "compareCutoffPercentile",
        percentileEventIds.map(eventId => DATASETS[eventId].name),
        yearSeries(percentileEventIds, (eventId, year) => {{
          const cutoff = qualificationByEvent[eventId][year]?.value;
          const records = selectedAgeGroupRecords(eventId, year, gender, ageGroup);
          if (!Number.isFinite(cutoff) || !records.length) return null;
          const qualified = records.filter(row => row.overall <= cutoff).length;
          return {{
            value: 100 * qualified / records.length,
            detail: `${{qualified}} of ${{records.length}} finishers at or faster than ${{duration(cutoff)}}`,
          }};
        }}),
        {{
          formatValue: value => `${{value.toFixed(1)}}%`,
          formatTick: value => `${{Number.isInteger(value) ? value.toFixed(0) : value.toFixed(1)}}%`,
          yAxisLabel: "Cutoff percentile within selected age group",
          zeroBasedNice: true,
          maximumCap: 100,
        }},
      );
      renderQualificationUncertainty(eventIds, ageGroup, gender);
    }}
    function renderFieldCompare(eventIds, ageGroup, gender) {{
      const depthEventIds = eventIds.filter(eventId =>
        Object.keys(DATASETS[eventId].overall).some(year =>
          selectedAgeGroupRecords(eventId, year, gender, ageGroup).length
        )
      );
      categoryPointChart(
        "compareAgeGroupDepth",
        depthEventIds.map(eventId => DATASETS[eventId].name),
        yearSeries(depthEventIds, (eventId, year) => {{
          const count = selectedAgeGroupRecords(eventId, year, gender, ageGroup).length;
          return count ? {{ value: count, detail: `${{count}} split-complete finishers` }} : null;
        }}),
        {{
          formatValue: value => `${{Math.round(value)}} finishers`,
          formatTick: value => Math.round(value).toString(),
          yAxisLabel: "Selected age-group finishers",
          nonnegative: true,
        }},
      );

      const splitRows = [];
      const splitEventIds = [];
      eventIds.forEach(eventId => {{
        const division = `${{gender === "Male" ? "M" : "F"}}${{ageGroup}}`;
        const rows = Object.keys(DATASETS[eventId].overall).flatMap(year =>
          !compareYearVisible(year) || isModifiedCourse(eventId, year)
            ? []
            : selectedAgeGroupRecords(eventId, year, gender, ageGroup)
        );
        if (!rows.length) return;
        const percentageSums = Object.fromEntries(
          splits.map(([, key]) => [key, 0])
        );
        rows.forEach(row => {{
          const total = splits.reduce((sum, [, key]) => sum + row[key], 0);
          splits.forEach(([, key]) => {{
            percentageSums[key] += 100 * row[key] / total;
          }});
        }});
        splitEventIds.push(eventId);
        splitRows.push({{
          count: rows.length,
          values: Object.fromEntries(
            Object.entries(percentageSums).map(([key, value]) => [key, value / rows.length])
          ),
        }});
      }});
      stackedPercentageChart(
        "compareSplitContribution",
        splitEventIds.map(eventId => DATASETS[eventId].name),
        splitRows,
      );
    }}
    function renderQualificationUncertainty(eventIds, ageGroup, gender) {{
      const uncertaintyEventIds = eventIds.filter(eventId =>
        raceQualificationYearlyValues(eventId, gender, ageGroup).some(row =>
          compareYearVisible(row.year) && !excludeMeanQualificationRaceYear(eventId, row.year)
        )
      );
      const ranges = uncertaintyEventIds.map(eventId => {{
        const values = raceQualificationYearlyValues(eventId, gender, ageGroup)
          .filter(row => compareYearVisible(row.year) && !excludeMeanQualificationRaceYear(eventId, row.year))
          .map(row => row.value)
          .filter(Number.isFinite)
          .sort((left, right) => left - right);
        return values.length ? {{
          minimum: values[0],
          q1: quantile(values, 0.25),
          median: quantile(values, 0.5),
          q3: quantile(values, 0.75),
          maximum: values.at(-1),
          count: values.length,
        }} : null;
      }});
      rangeCategoryChart(
        "compareQualificationUncertainty",
        uncertaintyEventIds.map(eventId => DATASETS[eventId].name),
        ranges,
      );
    }}
    function meanFinishForYear(eventId, year) {{
      const values = DATASETS[eventId].overall[year] || [];
      return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
    }}
    function lowerMedian(values) {{
      const sorted = values.filter(value => !Number.isNaN(value)).sort((left, right) => left - right);
      return sorted.length ? sorted[Math.floor((sorted.length - 1) / 2)] : null;
    }}
    function byNumberDescending(left, right) {{
      if (left === right) return 0;
      return left > right ? -1 : 1;
    }}
    function raceColor(eventId) {{
      return compareColors[Object.keys(DATASETS).indexOf(eventId) % compareColors.length];
    }}
    function oddsEventIds() {{
      return (raceGroups()[oddsDistance.value] || []).filter(isQualifyingEvent);
    }}
    function stepShareChart(elementId, series, markerTime) {{
      const svg = document.getElementById(elementId);
      const width = svg.viewBox.baseVal.width, height = svg.viewBox.baseVal.height;
      series = series.filter(item => item.thresholds.length);
      const finite = series.flatMap(item => item.thresholds.filter(Number.isFinite));
      if (!series.length || (!finite.length && !Number.isFinite(markerTime))) {{
        svg.innerHTML = `<text x="20" y="40">No data available</text>`;
        return;
      }}
      const legendColumnWidth = 190;
      const legendColumns = Math.max(1, Math.floor((width - 112) / legendColumnWidth));
      const legendRows = Math.ceil(series.length / legendColumns);
      const margin = {{ left: 72, right: 28, top: 20 + legendRows * 22, bottom: 52 }};
      const anchors = Number.isFinite(markerTime) ? [...finite, markerTime] : finite;
      let minimum = Math.min(...anchors), maximum = Math.max(...anchors);
      const padding = Math.max((maximum - minimum) * 0.08, 600);
      minimum -= padding; maximum += padding;
      const x = value => margin.left + (value - minimum) * (width - margin.left - margin.right) / (maximum - minimum);
      const y = value => margin.top + (100 - value) * (height - margin.top - margin.bottom) / 100;
      const shareAt = (thresholds, time) => 100 * thresholds.filter(value => value >= time).length / thresholds.length;
      let markup = "";
      for (let tick = 0; tick <= 4; tick++) {{
        const value = tick * 25;
        markup += `<line class="grid" x1="${{margin.left}}" y1="${{y(value)}}" x2="${{width - margin.right}}" y2="${{y(value)}}"/><text x="${{margin.left - 8}}" y="${{y(value) + 4}}" text-anchor="end">${{value}}%</text>`;
      }}
      for (let tick = 0; tick <= 6; tick++) {{
        const value = minimum + (maximum - minimum) * tick / 6;
        markup += `<line class="grid" x1="${{x(value)}}" y1="${{margin.top}}" x2="${{x(value)}}" y2="${{height - margin.bottom}}"/><text x="${{x(value)}}" y="${{height - 30}}" text-anchor="middle">${{duration(value).slice(0, 5)}}</text>`;
      }}
      markup += `<line class="axis" x1="${{margin.left}}" y1="${{margin.top}}" x2="${{margin.left}}" y2="${{height - margin.bottom}}"/><line class="axis" x1="${{margin.left}}" y1="${{height - margin.bottom}}" x2="${{width - margin.right}}" y2="${{height - margin.bottom}}"/>`;
      markup += `<text x="${{(margin.left + width - margin.right) / 2}}" y="${{height - 8}}" text-anchor="middle">Finish time (HH:MM)</text>`;
      if (Number.isFinite(markerTime)) {{
        markup += `<line x1="${{x(markerTime)}}" y1="${{margin.top}}" x2="${{x(markerTime)}}" y2="${{height - margin.bottom}}" stroke="#15231e" stroke-width="2" stroke-dasharray="6 5"/>`;
      }}
      series.forEach((item, seriesIndex) => {{
        const steps = [...new Set(item.thresholds.filter(value => Number.isFinite(value) && value > minimum && value < maximum))].sort((left, right) => left - right);
        let path = `M ${{x(minimum)}} ${{y(shareAt(item.thresholds, minimum))}}`;
        steps.forEach(value => {{
          path += ` H ${{x(value)}} V ${{y(shareAt(item.thresholds, value + 0.5))}}`;
        }});
        path += ` H ${{x(maximum)}}`;
        markup += `<path d="${{path}}" fill="none" stroke="${{item.color}}" stroke-width="2.4"/>`;
        if (Number.isFinite(markerTime)) {{
          const share = shareAt(item.thresholds, markerTime);
          const valueText = `${{share.toFixed(0)}}% of ${{item.thresholds.length}} race-years at ${{duration(markerTime)}}`;
          markup += `<circle class="data-point" cx="${{x(markerTime)}}" cy="${{y(share)}}" r="5" fill="${{item.color}}" tabindex="0" role="img" aria-label="${{escapeHtml(item.label)}}: ${{valueText}}" data-series="${{escapeHtml(item.label)}}" data-year="Your time" data-value="${{valueText}}"><title>${{escapeHtml(item.label)}}: ${{valueText}}</title></circle>`;
        }}
        const legendX = margin.left + (seriesIndex % legendColumns) * legendColumnWidth;
        const legendY = 15 + Math.floor(seriesIndex / legendColumns) * 22;
        markup += `<line x1="${{legendX}}" y1="${{legendY - 4}}" x2="${{legendX + 18}}" y2="${{legendY - 4}}" stroke="${{item.color}}" stroke-width="3"/><text x="${{legendX + 24}}" y="${{legendY}}">${{escapeHtml(item.label)}}</text>`;
      }});
      svg.innerHTML = markup;
      attachPointTooltips(svg);
    }}
    function renderOdds() {{
      const eventIds = oddsEventIds();
      populateAgeGroupSelect(oddsAgeGroup, compareAgeGroups(eventIds));
      const ageGroup = oddsAgeGroup.value;
      const gender = oddsGender.value;
      const division = divisionFor(gender, ageGroup);
      const time = currentAbility(oddsDistance.value, division).averageTime;
      if (Number.isFinite(time)) oddsTime.value = duration(time);
      oddsTimeBasis.value = "average";
      const averageBasis = oddsTimeBasis.value === "average";
      const system = qualificationSystem;
      const marginText = seconds => seconds === Infinity ? "any finish" : seconds === -Infinity ? "no slot" : signedDuration(seconds);
      const percentText = factor => Number.isFinite(factor) ? `${{factor >= 1 ? "+" : "−"}}${{Math.abs(100 * (factor - 1)).toFixed(1)}}%` : "—";
      let skipped = 0;
      const races = eventIds.map(eventId => {{
        const entries = qualificationYears(eventId, system)
          .filter(year => !isModifiedCourse(eventId, year))
          .map(year => {{
            const standard = qualificationStandard(eventId, year, gender, ageGroup, system, {{ cutoffMode: "strict" }});
            if (!standard) return null;
            const course = courseFactor(eventId, year);
            if (averageBasis && course === null) {{
              skipped += 1;
              return null;
            }}
            const factor = averageBasis ? course : 1;
            const expected = Number.isFinite(time) ? time * factor : NaN;
            return {{
              standard, course, expected,
              adjustedNeeded: standard.needed / factor,
              neutralNeeded: course === null ? null : standard.needed / course,
              result: qualifyingResult(standard, expected),
            }};
          }})
          .filter(Boolean);
        const standards = entries.map(entry => entry.standard);
        const rates = standards.filter(standard => standard.starters > 0).map(standard => 100 * standard.qualifiers / standard.starters);
        const relative = standards
          .filter(standard => Number.isFinite(standard.needed) && Number.isFinite(standard.median) && standard.median > 0)
          .map(standard => 100 * (standard.needed / standard.median - 1));
        return {{
          eventId,
          entries,
          qualified: entries.filter(entry => entry.result?.qualifies).length,
          count: entries.length,
          medianNeeded: lowerMedian(standards.map(standard => standard.needed)),
          medianNeutral: lowerMedian(entries.map(entry => entry.neutralNeeded).filter(value => value !== null)),
          minimumNeeded: Math.min(...standards.map(standard => standard.needed)),
          maximumNeeded: Math.max(...standards.map(standard => standard.needed)),
          medianMargin: Number.isFinite(time) ? lowerMedian(entries.map(entry => entry.standard.needed - entry.expected)) : null,
          medianRate: rates.length ? quantile([...rates].sort((left, right) => left - right), 0.5) : null,
          medianRelative: relative.length ? quantile([...relative].sort((left, right) => left - right), 0.5) : null,
        }};
      }}).filter(race => race.count);
      races.sort((left, right) =>
        byNumberDescending(left.qualified / left.count, right.qualified / right.count)
        || byNumberDescending(left.medianMargin ?? 0, right.medianMargin ?? 0)
      );
      const systemLabel = system === "historical" ? "actual historical rules and slots" : "current rules and latest allocations";
      document.getElementById("oddsRankingTitle").textContent = `Ease-of-qualification ranking · ${{division}} · ${{systemLabel}}`;
      document.getElementById("oddsRankingHead").innerHTML = `<tr><th>Race</th><th>Race-years</th><th>Your time qualifies</th><th title="Lower median across race-years, in race time.">Median time needed</th><th title="Time needed divided by each race-year's overall course factor: comparable across races.">Needed on an average course</th><th>Fastest – slowest time needed</th><th title="Time needed minus your expected race time; positive means you were inside the cutoff.">Median margin</th><th title="Time needed relative to the median ${{division}} finisher of that race-year.">Needed vs. ${{division}} median</th><th title="Age-group qualifiers per 100 eligible age-group starters.">Qualifiers / 100 starters</th></tr>`;
      document.getElementById("oddsRankingBody").innerHTML = races.length ? races.map(race => {{
        const share = 100 * race.qualified / race.count;
        return `<tr><td>${{escapeHtml(DATASETS[race.eventId].name)}}</td><td>${{race.count}}</td><td><strong>${{race.qualified}} / ${{race.count}}</strong> (${{share.toFixed(0)}}%)</td><td>${{neededText(race.medianNeeded)}}</td><td><strong>${{neededText(race.medianNeutral)}}</strong></td><td>${{neededText(race.minimumNeeded)}} – ${{neededText(race.maximumNeeded)}}</td><td>${{Number.isFinite(time) ? marginText(race.medianMargin) : "—"}}</td><td>${{Number.isFinite(race.medianRelative) ? `${{race.medianRelative.toFixed(1)}}%` : "—"}}</td><td>${{Number.isFinite(race.medianRate) ? race.medianRate.toFixed(1) : "—"}}</td></tr>`;
      }}).join("") : `<tr><td colspan="9" class="empty">No qualifying race-years for this selection.</td></tr>`;
      const totalYears = races.reduce((sum, race) => sum + race.count, 0);
      const totalQualified = races.reduce((sum, race) => sum + race.qualified, 0);
      document.getElementById("oddsQualifiedMetric").textContent = totalYears && Number.isFinite(time)
        ? `${{totalQualified}} / ${{totalYears}} (${{(100 * totalQualified / totalYears).toFixed(0)}}%)`
        : "—";
      const easiest = [...races].filter(race => Number.isFinite(race.medianRate)).sort((left, right) => byNumberDescending(left.medianRate, right.medianRate))[0];
      document.getElementById("oddsBestMetric").textContent = easiest
        ? `${{DATASETS[easiest.eventId].name.replace("IRONMAN ", "")}} · ${{easiest.medianRate.toFixed(1)}} / 100`
        : "—";
      const allNeeded = races.flatMap(race => race.entries.map(entry => entry.adjustedNeeded)).sort(byNumberDescending);
      const halfNeeded = allNeeded.length ? allNeeded[Math.ceil(allNeeded.length / 2) - 1] : null;
      document.getElementById("oddsMedianNeededLabel").textContent = averageBasis
        ? "Average-course time that qualified in half of race-years"
        : "Time that qualified in half of race-years";
      document.getElementById("oddsMedianNeededMetric").textContent = neededText(halfNeeded);
      const basisText = averageBasis
        ? `${{Number.isFinite(time) ? duration(time) : "The entered time"}} is treated as your time on an average course and multiplied by each race-year's overall course factor.`
        : "The entered time is compared unchanged with every race-year.";
      const skippedText = skipped ? ` ${{skipped}} race-year${{skipped === 1 ? "" : "s"}} without a course factor are left out.` : "";
      document.getElementById("oddsRankingNote").textContent = `${{basisText}}${{skippedText}} Ranked by the share of race-years in which you qualify, then by median margin. "Needed on an average course" removes course and race-day conditions, so it is the fairest comparison of how hard each race is to qualify at; higher is easier. "Needed vs. median" compares the time needed with that race-year's median ${{division}} finish. Ranked on strict allocation. Strict entitlement model: declines and ceremony attendance are not observed in the results.`;
      stepShareChart(
        "oddsProbabilityChart",
        races.map(race => ({{
          label: DATASETS[race.eventId].name,
          color: raceColor(race.eventId),
          thresholds: race.entries.map(entry => entry.adjustedNeeded),
        }})),
        time,
      );
      const ageGroups = compareAgeGroups(eventIds);
      document.getElementById("oddsRateTitle").textContent = `${{gender === "Male" ? "Men" : "Women"}}: qualifiers per 100 starters by age group`;
      lineChart(
        "oddsRateChart",
        ageGroups,
        eventIds.map(eventId => ({{
          label: DATASETS[eventId].name,
          color: raceColor(eventId),
          values: ageGroups.map(rowAgeGroup => {{
            const rates = qualificationYears(eventId, system)
              .map(year => strictQualificationStandard(eventId, year, gender, rowAgeGroup, system))
              .filter(standard => standard && standard.starters > 0)
              .map(standard => 100 * standard.qualifiers / standard.starters)
              .sort((left, right) => left - right);
            return rates.length ? quantile(rates, 0.5) : null;
          }}),
        }})).filter(item => item.values.some(Number.isFinite)),
        value => Number.isFinite(value) ? value.toFixed(1) : "—",
        {{ zeroBaseline: true }},
      );
      document.getElementById("oddsDetailHead").innerHTML = `<tr><th>Race</th><th>Year</th><th>Method</th><th>${{division}} starters</th><th>${{division}} qualifiers</th><th>${{division}} winner</th><th>Pool equivalent</th><th>Time needed</th><th title="Overall course and conditions factor of the race-year.">Course factor</th><th>Your expected time</th><th>Your margin</th><th>Result</th></tr>`;
      document.getElementById("oddsDetailBody").innerHTML = races.flatMap(race => race.entries.map(entry => {{
        const standard = entry.standard;
        const result = entry.result;
        const label = result ? (result.qualifies ? `✓ target met: ${{result.via}}` : "✗ target not met") : "—";
        return `<tr><td>${{escapeHtml(DATASETS[race.eventId].name)}}</td><td>${{standard.year}}</td><td>${{escapeHtml(standard.method)}}<br>${{qualificationEvidenceLink(standard)}}</td><td>${{standard.starters}}</td><td>${{standard.qualifiers}}</td><td>${{qualificationDuration(standard.winner)}}</td><td>${{qualificationDuration(standard.poolEquivalent)}}</td><td><strong>${{assumptionTime(standard)}}</strong><br><small>Strict: ${{assumptionTime(standard, true)}}</small></td><td>${{percentText(entry.course)}}</td><td>${{qualificationDuration(entry.expected)}}</td><td>${{Number.isFinite(time) ? marginText(standard.needed - entry.expected) : "—"}}</td><td>${{label}}</td></tr>`;
      }})).join("") || `<tr><td colspan="12" class="empty">No qualifying race-years for this selection.</td></tr>`;
    }}
    const SWIM_BIKE_RUN = ["swim", "bike", "run"];
    const MY_RESULTS_KEY = "ironmanDashboard.myResults";
    const easiestDistance = document.getElementById("easiestDistance");
    const easiestGender = document.getElementById("easiestGender");
    const easiestAgeGroup = document.getElementById("easiestAgeGroup");
    const easiestTime = document.getElementById("easiestTime");
    const easiestDeclines = document.getElementById("easiestDeclines");
    const easiestSearch = document.getElementById("easiestSearch");
    const easiestManualRace = document.getElementById("easiestManualRace");
    const easiestManualYear = document.getElementById("easiestManualYear");
    const easiestManualAgeGroup = document.getElementById("easiestManualAgeGroup");
    const easiestDetailRace = document.getElementById("easiestDetailRace");
    const peerCache = new Map();
    const nameSearchCache = new Map();
    let easiestSearchMatches = [];
    let easiestTypedTime = "10:30:00";
    let myResults = loadMyResults();
    function loadMyResults() {{
      try {{
        const stored = JSON.parse(localStorage.getItem(MY_RESULTS_KEY) || "[]");
        return Array.isArray(stored) ? stored.filter(result => DATASETS[result?.eventId]) : [];
      }} catch {{
        return [];
      }}
    }}
    function saveMyResults() {{
      try {{
        localStorage.setItem(MY_RESULTS_KEY, JSON.stringify(myResults));
      }} catch {{
        // Storage can be unavailable (private mode); results then last for this visit only.
      }}
    }}
    function normalCdf(z) {{
      // Abramowitz & Stegun 26.2.17, absolute error below 7.5e-8.
      const t = 1 / (1 + 0.2316419 * Math.abs(z));
      const density = Math.exp(-z * z / 2) / Math.sqrt(2 * Math.PI);
      const tail = density * t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))));
      return z >= 0 ? 1 - tail : tail;
    }}
    function transitionMedian(eventId, year) {{
      const stats = ageGroupSplitStats(eventId)[year];
      return stats?.t1 && stats?.t2 ? stats.t1.median + stats.t2.median : null;
    }}
    function groupModel(group) {{
      const first = (raceGroups()[group] || [])[0];
      return first ? DATASETS[first].course_model || {{}} : {{}};
    }}
    function typicalTransitions(group) {{
      const values = (raceGroups()[group] || []).filter(isQualifyingEvent)
        .flatMap(id => Object.keys(DATASETS[id].course_factors || {{}}).map(year => transitionMedian(id, year)))
        .filter(Number.isFinite)
        .sort((left, right) => left - right);
      return values.length ? quantile(values, 0.5) : 0;
    }}
    function easiestProfile(group, division) {{
      const model = groupModel(group);
      const target = model.standards?.[division];
      const rows = myResults
        .map((result, index) => ({{ result, index }}))
        .filter(({{ result }}) => DATASETS[result.eventId]?.group === group)
        .map(({{ result, index }}) => {{
          const then = model.standards?.[result.division];
          const factors = Object.fromEntries(SWIM_BIKE_RUN.map(split => [split, courseFactor(result.eventId, result.year, split)]));
          let problem = null;
          if (result.division[0] !== division[0]) problem = "different gender from the selection";
          else if (!Number.isFinite(then) || !Number.isFinite(target)) problem = "no age-grading standard for this age group";
          else if (!SWIM_BIKE_RUN.every(split => factors[split])) problem = "no course factor for this race-year (shortened, modified, or too few repeat athletes)";
          else if (!SWIM_BIKE_RUN.every(split => result[split] > 0)) problem = "swim, bike, and run times are needed";
          const ageAdjustment = problem ? null : then / target;
          const adjusted = problem ? null : Object.fromEntries(SWIM_BIKE_RUN.map(split => [split, result[split] * ageAdjustment / factors[split]]));
          const median = transitionMedian(result.eventId, result.year);
          const transitionRatio = !problem && result.t1 > 0 && result.t2 > 0 && median ? (result.t1 + result.t2) / median : null;
          return {{ result, index, factors, ageAdjustment, adjusted, transitionRatio, problem }};
        }});
      const used = rows.filter(row => !row.problem);
      const ratios = used.map(row => row.transitionRatio).filter(Number.isFinite);
      return {{
        rows,
        used: used.length,
        splits: used.length ? Object.fromEntries(SWIM_BIKE_RUN.map(split => [split, geometricMean(used.map(row => row.adjusted[split]))])) : null,
        transitionRatio: ratios.length ? geometricMean(ratios) : 1,
      }};
    }}
    function divisionRecords(group, division) {{
      const key = `${{group}}|${{division}}`;
      if (!peerCache.has(key)) {{
        const rows = [];
        (raceGroups()[group] || []).filter(isQualifyingEvent).forEach(eventId => {{
          DATASETS[eventId].records.forEach(row => {{
            if (String(row.division).trim().toUpperCase() !== division) return;
            const overall = courseFactor(eventId, row.year);
            const factors = SWIM_BIKE_RUN.map(split => courseFactor(eventId, row.year, split));
            if (!overall || factors.some(factor => !factor)) return;
            rows.push({{ overall: row.overall / overall, swim: row.swim / factors[0], bike: row.bike / factors[1], run: row.run / factors[2] }});
          }});
        }});
        const sorted = Object.fromEntries(["overall", ...SWIM_BIKE_RUN].map(split => [split, rows.map(row => row[split]).sort((left, right) => left - right)]));
        peerCache.set(key, {{ rows, sorted }});
      }}
      return peerCache.get(key);
    }}
    function shareFaster(sorted, value) {{
      let low = 0, high = sorted.length;
      while (low < high) {{
        const middle = (low + high) >> 1;
        if (sorted[middle] < value) low = middle + 1; else high = middle;
      }}
      return sorted.length ? low / sorted.length : null;
    }}
    function sameLevelPeers(data, averageTime) {{
      for (const width of [0.03, 0.06, 0.1]) {{
        const peers = data.rows.filter(row => Math.abs(row.overall / averageTime - 1) <= width);
        if (peers.length >= 30 || width === 0.1) {{
          const splitsMedian = peers.length
            ? Object.fromEntries(SWIM_BIKE_RUN.map(split => [split, quantile(peers.map(row => row[split]).sort((left, right) => left - right), 0.5)]))
            : null;
          return {{ width, count: peers.length, splits: splitsMedian }};
        }}
      }}
    }}
    function predictRaceYear(eventId, year, splitAbility, transitionRatio, averageTime) {{
      if (!splitAbility) {{
        const factor = courseFactor(eventId, year);
        return factor ? {{ total: averageTime * factor }} : null;
      }}
      const factors = SWIM_BIKE_RUN.map(split => courseFactor(eventId, year, split));
      const transitions = transitionMedian(eventId, year);
      if (factors.some(factor => !factor) || !Number.isFinite(transitions)) return null;
      const parts = Object.fromEntries(SWIM_BIKE_RUN.map((split, index) => [split, splitAbility[split] * factors[index]]));
      parts.transitions = transitionRatio * transitions;
      return {{ ...parts, total: parts.swim + parts.bike + parts.run + parts.transitions }};
    }}
    function slotText(eventId) {{
      const slots = DATASETS[eventId].qualification_slots;
      return typeof slots === "object" ? `${{slots.male}} M / ${{slots.female}} F` : String(slots);
    }}
    function fillManualForm() {{
      const group = easiestDistance.value;
      const eventIds = (raceGroups()[group] || []).filter(id => Object.keys(DATASETS[id].course_factors || {{}}).length);
      fillRaceSelect(easiestManualRace, eventIds, eventIds[0]);
      const years = Object.keys(DATASETS[easiestManualRace.value]?.course_factors || {{}}).sort().reverse();
      const previousYear = easiestManualYear.value;
      easiestManualYear.innerHTML = years.map(year => `<option value="${{year}}">${{year}}</option>`).join("");
      if (years.includes(previousYear)) easiestManualYear.value = previousYear;
      const prefix = easiestGender.value === "Male" ? "M" : "F";
      const divisions = Object.keys(groupModel(group).standards || {{}})
        .filter(division => division[0] === prefix)
        .sort((left, right) => Number(left.slice(1, 3)) - Number(right.slice(1, 3)));
      const previousDivision = easiestManualAgeGroup.value;
      easiestManualAgeGroup.innerHTML = divisions.map(division => `<option value="${{division}}">${{division}}</option>`).join("");
      const target = divisionFor(easiestGender.value, easiestAgeGroup.value);
      easiestManualAgeGroup.value = divisions.includes(previousDivision) ? previousDivision : divisions.includes(target) ? target : (divisions[0] || "");
    }}
    function addManualResult() {{
      const note = document.getElementById("easiestManualNote");
      const inputs = {{ swim: "easiestManualSwim", t1: "easiestManualT1", bike: "easiestManualBike", t2: "easiestManualT2", run: "easiestManualRun" }};
      const times = Object.fromEntries(Object.entries(inputs).map(([key, id]) => {{
        const value = document.getElementById(id).value.trim();
        return [key, value ? parseTime(value) : 0];
      }}));
      if (!easiestManualRace.value || !Object.values(times).every(Number.isFinite) || !SWIM_BIKE_RUN.every(split => times[split] > 0)) {{
        note.textContent = "Enter swim, bike, and run as HH:MM:SS (for example 01:10:00); transitions are optional.";
        return;
      }}
      myResults.push({{
        eventId: easiestManualRace.value, year: easiestManualYear.value, division: easiestManualAgeGroup.value,
        name: "Manual entry", ...times,
      }});
      note.textContent = "";
      Object.values(inputs).forEach(id => {{ document.getElementById(id).value = ""; }});
      saveMyResults();
      renderEasiest();
    }}
    function renderEasiestSearch() {{
      const group = easiestDistance.value;
      const head = document.getElementById("easiestSearchHead");
      const body = document.getElementById("easiestSearchBody");
      head.innerHTML = `<tr><th>Race</th><th>Year</th><th>Name</th><th>Country</th><th>Age group</th><th>Swim</th><th>T1</th><th>Bike</th><th>T2</th><th>Run</th><th>Overall</th><th></th></tr>`;
      const tokens = (identityKey(easiestSearch.value, "", "") || "").split("|")[0].split(" ").filter(Boolean);
      easiestSearchMatches = [];
      if (tokens.join("").length < 3) {{
        body.innerHTML = `<tr><td colspan="12" class="empty">Type at least three letters of your name.</td></tr>`;
        return;
      }}
      if (!nameSearchCache.has(group)) {{
        nameSearchCache.set(group, (raceGroups()[group] || []).flatMap(eventId => DATASETS[eventId].records.map(row => ({{
          eventId, row, nameKey: (identityKey(row.name, "", "") || "").split("|")[0],
        }}))));
      }}
      easiestSearchMatches = nameSearchCache.get(group)
        .filter(item => tokens.every(token => item.nameKey.includes(token)))
        .sort((left, right) => left.nameKey.localeCompare(right.nameKey) || right.row.year.localeCompare(left.row.year))
        .slice(0, 50);
      body.innerHTML = easiestSearchMatches.map(({{ eventId, row }}, index) => {{
        const added = myResults.some(result => result.eventId === eventId && result.year === row.year && result.name === row.name);
        return `<tr><td>${{escapeHtml(DATASETS[eventId].name)}}</td><td>${{yearCell(eventId, row.year)}}</td><td>${{escapeHtml(row.name)}}</td><td>${{escapeHtml(row.country)}}</td><td>${{escapeHtml(row.division)}}</td><td>${{duration(row.swim)}}</td><td>${{duration(row.t1)}}</td><td>${{duration(row.bike)}}</td><td>${{duration(row.t2)}}</td><td>${{duration(row.run)}}</td><td>${{duration(row.overall)}}</td><td>${{added ? "Added" : `<button type="button" class="small-button" data-add="${{index}}">Add</button>`}}</td></tr>`;
      }}).join("") || `<tr><td colspan="12" class="empty">No finisher found with this name.</td></tr>`;
    }}
    function renderMyResults(profile, division) {{
      document.getElementById("easiestResultsHead").innerHTML = `<tr><th>Race</th><th>Year</th><th>Name</th><th>Age group then</th><th>Swim</th><th>T1</th><th>Bike</th><th>T2</th><th>Run</th><th title="Split factors f of that race-year: swim / bike / run.">Course factors s / b / r</th><th title="A(then) \u00f7 A(${{division}}).">Age adjustment</th><th>Average-course swim / bike / run</th><th></th></tr>`;
      document.getElementById("easiestResultsBody").innerHTML = profile.rows.map(row => {{
        const result = row.result;
        const remove = `<button type="button" class="small-button" data-remove="${{row.index}}">Remove</button>`;
        const common = `<td>${{escapeHtml(DATASETS[result.eventId].name)}}</td><td>${{yearCell(result.eventId, result.year)}}</td><td>${{escapeHtml(result.name)}}</td><td>${{escapeHtml(result.division)}}</td><td>${{duration(result.swim)}}</td><td>${{result.t1 ? duration(result.t1) : "\u2014"}}</td><td>${{duration(result.bike)}}</td><td>${{result.t2 ? duration(result.t2) : "\u2014"}}</td><td>${{duration(result.run)}}</td>`;
        if (row.problem) return `<tr>${{common}}<td colspan="3">Not used: ${{row.problem}}</td><td>${{remove}}</td></tr>`;
        const factors = SWIM_BIKE_RUN.map(split => row.factors[split].toFixed(3)).join(" / ");
        const adjusted = SWIM_BIKE_RUN.map(split => duration(row.adjusted[split])).join(" / ");
        return `<tr>${{common}}<td>${{factors}}</td><td>${{row.ageAdjustment.toFixed(4)}}</td><td><strong>${{adjusted}}</strong></td><td>${{remove}}</td></tr>`;
      }}).join("") || `<tr><td colspan="13" class="empty">No results added for this distance.</td></tr>`;
      document.getElementById("easiestResultsNote").textContent = profile.used
        ? `Average-course split = raw split \u00d7 age adjustment \u00f7 course factor. Your ability is the geometric mean over ${{profile.used}} result${{profile.used === 1 ? "" : "s"}}: swim ${{duration(profile.splits.swim)}}, bike ${{duration(profile.splits.bike)}}, run ${{duration(profile.splits.run)}}, transitions ${{(100 * profile.transitionRatio).toFixed(0)}}% of the race median.`
        : "";
    }}
    function renderStrengthProfile(profile, group, division, averageTime) {{
      const body = document.getElementById("easiestProfileBody");
      const note = document.getElementById("easiestProfileNote");
      document.getElementById("easiestProfileTitle").textContent = `Your strength profile \u00b7 ${{division}}`;
      document.getElementById("easiestProfileHead").innerHTML = `<tr><th>Split</th><th>You, average course</th><th title="Share of ${{division}} finishers in qualifying races (course-adjusted) who were faster.">Rank in ${{division}}</th><th>Same-level athletes (median)</th><th>You vs. same level</th><th>Verdict</th></tr>`;
      if (!profile.used) {{
        body.innerHTML = `<tr><td colspan="6" class="empty">Add at least one past result to see your strengths and weaknesses.</td></tr>`;
        note.textContent = "";
        return null;
      }}
      const data = divisionRecords(group, division);
      const level = sameLevelPeers(data, averageTime);
      body.innerHTML = SWIM_BIKE_RUN.map(split => {{
        const you = profile.splits[split];
        const share = shareFaster(data.sorted[split], you);
        const peer = level.splits?.[split];
        const difference = Number.isFinite(peer) ? you / peer - 1 : null;
        const verdict = difference === null ? "\u2014"
          : difference <= -0.03 ? `<span class="strength">Strength</span>`
          : difference >= 0.03 ? `<span class="weakness">Weakness</span>` : "Average";
        return `<tr><td>${{splitLabel(split)}}</td><td>${{duration(you)}}</td><td>${{share === null ? "\u2014" : `top ${{Math.max(1, Math.ceil(100 * share))}}%`}}</td><td>${{duration(peer)}}</td><td>${{difference === null ? "\u2014" : `${{signedDuration(you - peer)}} (${{signedPercent(1 + difference)}})`}}</td><td>${{verdict}}</td></tr>`;
      }}).join("");
      note.textContent = `Same-level athletes: ${{level.count.toLocaleString()}} ${{division}} results in qualifying races whose course-adjusted finish was within \u00b1${{100 * level.width}}% of yours (${{duration(averageTime)}}). All times are converted to an average course with the split factors, so results from different races are comparable. A strength (at least 3% faster than same-level athletes) gains the most on courses where that split is hard.`;
      return level;
    }}
    function qualificationStandard(eventId, year, gender, ageGroup, system, options = {{}}) {{
      const result = easiestQualificationStandard(eventId, year, gender, ageGroup, system,
        options.cutoffMode || qualificationAssumptions.mode,
        options.extraPlaces ?? qualificationAssumptions.extraPlaces, options);
      return result?.available ? result : null;
    }}
    function easiestQualificationStandard(eventId, year, gender, ageGroup, system, mode, extraPlaces, options = {{}}) {{
      const strict = strictQualificationStandard(eventId, year, gender, ageGroup, system, {{ ...options, extraPlaces: 0 }});
      const places = strict?.scope === "age group" ? qualificationAssumptions.legacyExtraPlaces ?? extraPlaces : extraPlaces;
      const standard = mode === "places" ? strictQualificationStandard(eventId, year, gender, ageGroup, system,
        {{ ...options, extraPlaces: places }}) : strict;
      if (!standard) return null;
      const defaultTrace = DATASETS.im_kona?.kona_trace;
      const target = DATASETS[eventId].historical_qualification?.targets?.find(row => row.year === year && row.division === standard.division);
      const sourceCycle = target?.standard_cycle || target?.source?.allocation_cycle
        || (target?.source?.cycles?.length === 1 ? target.source.cycles[0] : null);
      const traces = Object.values(DATASETS.im_kona?.kona_traces || {{latest: defaultTrace}}).filter(Boolean);
      const currentCycle = DATASETS[eventId].qualification?.standard_cycle;
      const candidates = DATASETS[eventId].group === "im" ? traces.flatMap(trace => {{
        const sourceRows = system === "current"
          ? String(trace.counterfactual_standard_cycle) === String(currentCycle) ? trace.counterfactual_summaries || [] : []
          : trace.summaries?.all || [];
        return sourceRows.filter(row => row.event_id === eventId && row.year === year && row.gender === gender
          && (!row.slot_scope || row.slot_scope === standard.scope) && (!row.division || row.division === standard.division))
          .map(pool => ({{trace, pool}}));
      }}) : [];
      const compatible = system === "historical"
        ? sourceCycle ? candidates.filter(entry => entry.trace.year === String(sourceCycle)) : []
        : candidates.length > 1 && sourceCycle ? candidates.filter(entry => entry.trace.year === String(sourceCycle)) : candidates;
      const trace = compatible.length === 1 ? compatible[0].trace
        : system === "historical" && standard.scope === "age group" && !sourceCycle ? null : defaultTrace;
      const pool = compatible.length === 1 ? compatible[0].pool : null;
      const estimate = mode === "reported" ? {{time: pool?.reported_cutoff}} : mode === "density" ? pool?.cutoff_estimate : pool?.cutoff_scan;
      const ratio = (system === "current" ? trace?.counterfactual_standards : trace?.standards)?.[standard.division];
      const scanScope = pool?.slot_scope === "age group" ? "age-group" : "gender-pool";
      const scanLabel = pool?.cutoff_scan?.consecutive_absences
        ? `${{pool.cutoff_scan.consecutive_absences}}-absence ${{scanScope}} scan` : "Absence scan";
      const label = mode === "reported" ? "Reported cutoff" : mode === "density" ? "Match-density boundary" : scanLabel;
      const evidenceCycle = (system === "current" ? trace?.counterfactual_standard_cycle : trace?.year) ?? null;
      const evidenceRoster = system === "current" ? trace?.year ?? null : null;
      const metadata = {{ ...standard, cutoffPool: pool, cutoffCycle: evidenceCycle, cutoffRoster: evidenceRoster, estimatedCutoffUsed: false,
        strictNeeded: strict.needed, available: true, mode,
        cutoffSource: mode === "places" ? "Slot allocation + extra places" : "Strict allocation" }};
      if (mode === "places" || mode === "strict") return metadata;
      const unavailable = reason => ({{ ...metadata,
        available: Boolean(qualificationAssumptions.fallback),
        needed: qualificationAssumptions.fallback ? strict.needed : null,
        unavailableReason: reason, cutoffSource: `${{qualificationAssumptions.fallback ? "Strict fallback" : "No estimate"}}: ${{reason}}` }});
      if (standard.scope !== "gender" && system !== "historical") return unavailable("legacy age-group rules");
      if (isModifiedCourse(eventId, year)) return unavailable("modified course");
      if (system === "current" && !candidates.length) return unavailable(DATASETS[eventId].group === "im"
        ? "no World Championship start list for this race-year's qualifying cycle" : "no 70.3 World Championship start list");
      if (system === "historical" && standard.scope === "age group" && !sourceCycle) return unavailable("no confirmed compatible evidence cycle");
      if (compatible.length > 1) return unavailable("ambiguous qualifying cycle");
      if (mode === "reported" && (!Number.isFinite(estimate?.time) || !pool?.reported_cutoff_source)) return unavailable("no documented matching reported cutoff");
      if (standard.scope === "age group") {{
        if (!Number.isFinite(estimate?.time) || estimate.time <= 0) return unavailable("no matching age-group estimate");
        if (pool.slot_scope !== "age group" || pool.division !== standard.division || pool.pool_slots !== standard.slots || standard.slots <= 0) return unavailable("changed age-group allocation");
        return {{...metadata, needed: mode === "density" || mode === "scan" ? Math.max(strict.needed, estimate.time) : estimate.time, ageGraded: null, poolEquivalent: null,
          precision: mode === "reported" ? pool.reported_cutoff_precision : mode === "density" ? "estimate" : "second", estimatedCutoffUsed: true,
          cutoffSource: `${{label}}: WC ${{trace.year}} cycle, ${{standard.division}} raw ranking (${{mode === "reported" ? "documented report" : mode === "density" ? "exploratory breakpoint; target bounded by strict allocation" : "unverified"}})`}};
      }}
      if (system === "historical" && !DATASETS[eventId].historical_qualification?.targets?.some(row =>
        row.year === year && row.division === standard.division && String(row.standard_cycle) === trace?.year)) {{
        return unavailable("different qualifying cycle");
      }}
      if (!Number.isFinite(estimate?.time) || estimate.time <= 0 || !Number.isFinite(ratio) || ratio <= 0) return unavailable("no matching estimate");
      if (system !== "historical" && (standard.performanceSlots !== pool.pool_slots || Math.abs(standard.ratio - ratio) > 0.000001)) return unavailable("changed allocation or standard");
      const poolEquivalent = estimate.time / ratio;
      const modeledNeeded = standard.winner === null ? Infinity : Math.max(standard.winner, poolEquivalent);
      return {{ ...metadata, ratio, ageGraded: estimate.time, poolEquivalent,
        needed: mode === "density" || mode === "scan" ? Math.max(strict.needed, modeledNeeded) : modeledNeeded,
        precision: mode === "reported" ? pool.reported_cutoff_precision : mode === "density" ? "estimate" : "second",
        estimatedCutoffUsed: true, cutoffSource: `${{label}}: WC ${{system === "current" ? `${{trace.year}} start list ranked under ${{evidenceCycle}} rules` : `${{trace.year}} cycle`}} (${{mode === "reported" ? "reported, not independently verified" : mode === "density" ? "exploratory breakpoint; target bounded by strict allocation" : "unverified"}})` }};
    }}
    function easiestPoolEstimateCell(pool) {{
      if (!pool) return "Not available";
      const density = pool.cutoff_estimate;
      const scan = pool.cutoff_scan;
      const densityTime = Number.isFinite(density?.time) ? `~${{duration(Math.round(density.time / 60) * 60).slice(0, 5)}}` : "Unknown";
      const scanTime = Number.isFinite(scan?.time) ? qualificationDuration(scan.time) : "Unknown";
      const ageGroupScope = pool.slot_scope === "age group";
      const scanLabel = `${{scan?.consecutive_absences ?? (ageGroupScope ? 3 : 15)}}-absence ${{ageGroupScope ? "age-group" : "gender-pool"}} scan`;
      const cycle = pool.kona_cycle || DATASETS.im_kona?.kona_trace?.year;
      const ranking = pool.ranking_cycle && pool.ranking_cycle !== cycle ? ` start list ranked under ${{pool.ranking_cycle}} rules` : " cycle";
      return `<strong>${{escapeHtml(pool.year)}}</strong> · Density boundary ${{densityTime}}<br>${{scanLabel}} ${{scanTime}}<br><small>Exploratory match density, not acceptance; WC ${{escapeHtml(cycle)}}${{escapeHtml(ranking)}}${{density?.sensitive ? "; sensitive to single-race matches" : ""}}</small>`;
    }}
    // Step 1 ability shared by all qualification steps: past results converted
    // split by split to an average (standard) course, otherwise the typed time.
    function currentAbility(group = easiestDistance.value, division = divisionFor(easiestGender.value, easiestAgeGroup.value)) {{
      const profile = easiestProfile(group, division);
      const transitions = typicalTransitions(group);
      const averageTime = profile.used
        ? SWIM_BIKE_RUN.reduce((sum, split) => sum + profile.splits[split], 0) + profile.transitionRatio * transitions
        : parseTime(easiestTypedTime);
      return {{ group, division, profile, transitions, averageTime }};
    }}
    function renderEasiest() {{
      if (!["qtime", "easiest"].includes(activeTab)) return;
      const group = easiestDistance.value;
      const gender = easiestGender.value;
      const eventIds = (raceGroups()[group] || []).filter(isQualifyingEvent);
      populateAgeGroupSelect(easiestAgeGroup, compareAgeGroups(eventIds));
      const ageGroup = easiestAgeGroup.value;
      const division = divisionFor(gender, ageGroup);
      const system = qualificationSystem;
      easiestDeclines.disabled = dashboardContext.distance !== "im";
      const model = groupModel(group);
      const {{ profile, transitions: averageTransitions, averageTime }} = currentAbility(group, division);
      const hasProfile = profile.used > 0;
      easiestTime.disabled = hasProfile;
      easiestTime.value = hasProfile ? duration(averageTime) : easiestTypedTime;
      renderMyResults(profile, division);
      document.getElementById("easiestAbilityMetric").textContent = duration(averageTime);
      const rankingBody = document.getElementById("easiestRankingBody");
      if (!Number.isFinite(averageTime)) {{
        rankingBody.innerHTML = `<tr><td colspan="13" class="empty">Enter a finish time as HH:MM:SS.</td></tr>`;
        return;
      }}
      const level = renderStrengthProfile(profile, group, division, averageTime);
      const peerAverage = level?.splits
        ? SWIM_BIKE_RUN.reduce((sum, split) => sum + level.splits[split], 0) + averageTransitions
        : null;
      const dayToDay = model.fit?.overall?.residual_sd ?? 0.036;
      const sigma = hasProfile ? dayToDay * Math.sqrt(1 + 1 / profile.used) : dayToDay;
      const races = eventIds.map(eventId => {{
        const entries = qualificationYears(eventId, system)
          .filter(year => !isModifiedCourse(eventId, year))
          .map(year => {{
            const standard = qualificationStandard(eventId, year, gender, ageGroup, system);
            const expected = standard && predictRaceYear(eventId, year, hasProfile ? profile.splits : null, profile.transitionRatio, averageTime);
            if (!expected) return null;
            const needed = standard.needed;
            const chance = needed === Infinity ? 1 : needed === -Infinity ? 0 : normalCdf(Math.log(needed / expected.total) / sigma);
            const peerExpected = peerAverage ? predictRaceYear(eventId, year, level.splits, 1, null) : null;
            const fit = peerExpected ? (expected.total / peerExpected.total) / (averageTime / peerAverage) - 1 : null;
            return {{ year, standard, expected, needed, chance, margin: needed - expected.total, fit }};
          }})
          .filter(Boolean);
        const rates = entries.filter(entry => entry.standard.starters > 0).map(entry => 100 * entry.standard.qualifiers / entry.standard.starters);
        const fits = entries.map(entry => entry.fit).filter(Number.isFinite);
        return {{
          eventId, entries,
          cutoffPool: entries.map(entry => entry.standard.cutoffPool).filter(Boolean).sort((left, right) => right.year.localeCompare(left.year))[0],
          estimatedYears: entries.filter(entry => entry.standard.estimatedCutoffUsed).length,
          worstMargin: entries.length ? Math.min(...entries.map(entry => entry.margin)) : null,
          bestMargin: entries.length ? Math.max(...entries.map(entry => entry.margin)) : null,
          chance: entries.length ? entries.reduce((sum, entry) => sum + entry.chance, 0) / entries.length : -Infinity,
          qualified: entries.filter(entry => entry.margin >= 0).length,
          expected: lowerMedian(entries.map(entry => entry.expected.total)),
          needed: lowerMedian(entries.map(entry => entry.needed)),
          neededStandard: lowerMedian(entries.flatMap(entry => {{
            const factor = courseFactor(eventId, entry.year);
            return factor ? [entry.needed / factor] : [];
          }})),
          margin: lowerMedian(entries.map(entry => entry.margin)),
          fit: fits.length ? lowerMedian(fits) : null,
          rate: rates.length ? lowerMedian(rates) : null,
        }};
      }})
        .sort((left, right) => byNumberDescending(left.chance, right.chance) || byNumberDescending(left.margin, right.margin));

      const best = races.find(race => race.entries.length);
      document.getElementById("easiestBestMetric").textContent = best ? DATASETS[best.eventId].name.replace("IRONMAN ", "") : "\u2014";
      document.getElementById("easiestChanceMetric").textContent = best ? `${{Math.round(100 * best.chance)}}%` : "\u2014";
      const systemLabel = system === "historical" ? "historical rules, strict allocation" : "current-pool counterfactual, strict allocation";
      document.getElementById("easiestRankingTitle").textContent = `Where you qualify most easily \u00b7 ${{division}} \u00b7 ${{systemLabel}}`;
      document.getElementById("easiestRankingHead").innerHTML = `<tr><th>Race</th><th title="Latest published allocation; estimates describe their original cycle, not this allocation.">Slots</th><th>Race-years</th><th title="Density estimate and absence scan in the race-year's compatible scope; missing or incompatible evidence is unavailable.">Density & scope-specific scan</th><th title="Margin in the race-year where you were furthest from (worst) and furthest inside (best) the strict target.">Margin range (worst – best year)</th><th title="Season-adjusted overall course effect.">Course</th><th>Your expected time</th><th>Time needed</th><th title="Median time needed divided by each race-year's course and conditions factor: the fairest comparison of how hard the target is, independent of course.">Needed on a standard course</th><th>Median margin</th><th>Target met in</th><th>Estimated chance</th><th title="Your expected time relative to same-level athletes on this course; negative suits you.">Course fit for you</th><th title="Strict allocation only, not an inferred count of accepted slots.">Allocated qualifiers / 100 starters</th></tr>`;
      rankingBody.innerHTML = races.map((race, index) => {{
        if (!race.entries.length) return `<tr><td>${{escapeHtml(DATASETS[race.eventId].name)}}</td><td>${{slotText(race.eventId)}}</td><td colspan="12">No compatible target for selected race years. Not ranked.</td></tr>`;
        const percent = Math.round(100 * race.chance);
        const marginValue = race.margin === Infinity ? "any finish" : race.margin === -Infinity ? "no slot" : signedDuration(race.margin);
        const rangeText = value => value === Infinity ? "any finish" : value === -Infinity ? "no slot" : signedDuration(value);
        return `<tr><td>${{index + 1}}. ${{escapeHtml(DATASETS[race.eventId].name)}}</td><td>${{slotText(race.eventId)}}</td><td>${{race.entries.length}}</td><td>${{easiestPoolEstimateCell(race.cutoffPool)}}</td><td>${{rangeText(race.worstMargin)}} – ${{rangeText(race.bestMargin)}}</td><td>${{signedPercent(courseEffect(race.eventId, "overall"))}}</td><td>${{duration(race.expected)}}</td><td>${{neededText(race.needed)}}</td><td>${{neededText(race.neededStandard)}}</td><td>${{marginValue}}</td><td>${{race.qualified}} / ${{race.entries.length}}</td><td><span class="chance"><span style="width:${{percent}}%"></span></span><strong>${{percent}}%</strong></td><td>${{race.fit === null ? "\u2014" : signedPercent(1 + race.fit)}}</td><td>${{Number.isFinite(race.rate) ? race.rate.toFixed(1) : "\u2014"}}</td></tr>`;
      }}).join("") || `<tr><td colspan="13" class="empty">No qualifying race-years with course factors for this selection.</td></tr>`;
      document.getElementById("easiestRankingNote").textContent = `${{hasProfile
        ? "Expected times are built split by split from your results and each race-year's split factors."
        : "Expected times are your average-course time \u00d7 each race-year's overall factor; add results for a split-by-split prediction and the course-fit column."}} Chance per race-year = \u03a6(ln(needed \u00f7 expected) \u00f7 ${{(100 * sigma).toFixed(1)}}%), averaged over the race's race-years. This ranking uses strict allocation targets; all five cutoff approaches are compared per race-year below, and chance is modelled, not a historical acceptance probability. Slots show the latest allocation; historical mode uses each race-year's own slots. Races with few race-years (e.g. one) are much less certain than the percentage suggests.`;

      categoryPointChart(
        "easiestMarginChart",
        races.map(race => DATASETS[race.eventId].name),
        yearSeries(races.map(race => race.eventId), (eventId, year) => {{
          const entry = races.find(race => race.eventId === eventId).entries.find(item => item.year === year);
          if (!entry || !Number.isFinite(entry.margin)) return null;
          return {{
            value: entry.margin,
            detail: `needed ${{neededText(entry.needed)}} \u00b7 you ${{duration(entry.expected.total)}} \u00b7 chance ${{Math.round(100 * entry.chance)}}% \u00b7 ${{entry.standard.cutoffSource}}`,
          }};
        }}),
        {{ includeZero: true, formatValue: signedDuration, formatTick: signedDurationShort, yAxisLabel: "Time needed \u2212 your expected time" }},
      );

      fillRaceSelect(easiestDetailRace, races.filter(race => race.entries.length).map(race => race.eventId), best?.eventId);
      const detail = races.find(race => race.eventId === easiestDetailRace.value);
      document.getElementById("easiestDetailHead").innerHTML = `<tr><th>Year</th><th>Method</th><th>Cutoff source</th><th>${{division}} starters</th><th>Estimated pool age-graded cutoffs</th><th>Pool age-graded target used</th><th>Time needed (${{division}})</th><th>Your expected time</th>${{hasProfile ? "<th>Swim / bike / run / T1+T2</th>" : "<th>Overall factor</th>"}}<th>Margin</th><th>Chance</th></tr>`;
      document.getElementById("easiestDetailBody").innerHTML = detail ? detail.entries.map(entry => {{
        const parts = hasProfile
          ? ["swim", "bike", "run", "transitions"].map(key => duration(entry.expected[key])).join(" / ")
          : factorText(courseFactor(detail.eventId, entry.year));
        const marginValue = entry.margin === Infinity ? "any finish" : entry.margin === -Infinity ? "no slot" : signedDuration(entry.margin);
        return `<tr><td>${{yearCell(detail.eventId, entry.year)}}</td><td>${{escapeHtml(entry.standard.method)}}</td><td>${{qualificationEvidenceLink(entry.standard)}}</td><td>${{entry.standard.starters}}</td><td>${{easiestPoolEstimateCell(entry.standard.cutoffPool)}}</td><td>${{assumptionTime({{...entry.standard, needed: entry.standard.ageGraded}})}}</td><td><strong>${{assumptionTime(entry.standard)}}</strong><br><small>Strict: ${{assumptionTime(entry.standard, true)}}</small></td><td>${{duration(entry.expected.total)}}</td><td>${{parts}}</td><td>${{marginValue}}</td><td>${{Math.round(100 * entry.chance)}}%</td></tr>`;
      }}).join("") : `<tr><td colspan="11" class="empty">No race selected.</td></tr>`;
    }}
    function renderEasiestTab() {{
      if (!["qtime", "easiest"].includes(activeTab)) return;
      populateAgeGroupSelect(easiestAgeGroup, compareAgeGroups((raceGroups()[easiestDistance.value] || []).filter(isQualifyingEvent)));
      fillManualForm();
      renderEasiestSearch();
      renderEasiest();
    }}
    function excludeMeanQualificationRaceYear(eventId, year) {{
      return isModifiedCourse(eventId, year);
    }}
    function linearFit(points) {{
      if (points.length < 2) return null;
      const meanX = points.reduce((sum, point) => sum + point.x, 0) / points.length;
      const meanY = points.reduce((sum, point) => sum + point.y, 0) / points.length;
      const varianceX = points.reduce(
        (sum, point) => sum + (point.x - meanX) ** 2, 0
      );
      if (varianceX <= 0) return null;
      const covariance = points.reduce(
        (sum, point) => sum + (point.x - meanX) * (point.y - meanY), 0
      );
      const slope = covariance / varianceX;
      return {{ slope, intercept: meanY - slope * meanX }};
    }}
    function fitEquation(fit) {{
      const sign = fit.intercept < 0 ? "−" : "+";
      return `qualifying time = ${{fit.slope.toFixed(3)}} × mean finish time ${{sign}} ${{duration(Math.abs(fit.intercept))}}`;
    }}
    function meanQualificationScatter(eventIds, ageGroup, gender) {{
      const svg = document.getElementById("compareMeanQualification");
      const width = svg.viewBox.baseVal.width, height = svg.viewBox.baseVal.height;
      const raceIds = Object.keys(DATASETS);
      const allSeries = eventIds.map(eventId => {{
        const qualificationByYear = Object.fromEntries(
          raceQualificationYearlyValues(eventId, gender, ageGroup).map(entry => [entry.year, entry])
        );
        const points = Object.keys(DATASETS[eventId].overall).sort()
          .filter(year => compareYearVisible(year) && !excludeMeanQualificationRaceYear(eventId, year))
          .map(year => ({{
            year,
            x: meanFinishForYear(eventId, year),
            y: qualificationByYear[year]?.value,
            slotDetail: qualificationByYear[year]?.detail,
          }}))
          .filter(point => Number.isFinite(point.x) && Number.isFinite(point.y));
        return {{
          eventId,
          label: DATASETS[eventId].name,
          color: compareColors[raceIds.indexOf(eventId) % compareColors.length],
          points,
        }};
      }}).filter(item => item.points.length);
      const series = allSeries.filter(item => !hiddenMeanQualificationRaces.has(item.eventId));
      const points = series.flatMap(item => item.points);
      if (!allSeries.length) {{
        svg.innerHTML = `<text x="20" y="40">No matching race-year data available</text>`;
        qualificationResidualChart([], [], null);
        return;
      }}
      if (!points.length) hiddenMeanQualificationRaces.delete(allSeries[0].eventId);
      const visibleSeries = allSeries.filter(item => !hiddenMeanQualificationRaces.has(item.eventId));
      const visiblePoints = visibleSeries.flatMap(item => item.points);
      const globalFit = linearFit(visiblePoints);

      const legendColumnWidth = 190;
      const legendColumns = Math.max(1, Math.floor((width - 112) / legendColumnWidth));
      const legendRows = Math.ceil(allSeries.length / legendColumns);
      const margin = {{ left: 92, right: 28, top: 18 + legendRows * 22, bottom: 66 }};
      let xMinimum = Math.min(...visiblePoints.map(point => point.x));
      let xMaximum = Math.max(...visiblePoints.map(point => point.x));
      let yMinimum = Math.min(...visiblePoints.map(point => point.y));
      let yMaximum = Math.max(...visiblePoints.map(point => point.y));
      const xPadding = Math.max((xMaximum - xMinimum) * 0.1, 300);
      const yPadding = Math.max((yMaximum - yMinimum) * 0.1, 180);
      xMinimum -= xPadding; xMaximum += xPadding;
      yMinimum -= yPadding; yMaximum += yPadding;
      const x = value => margin.left + (value - xMinimum) * (width - margin.left - margin.right) / (xMaximum - xMinimum);
      const y = value => margin.top + (yMaximum - value) * (height - margin.top - margin.bottom) / (yMaximum - yMinimum);
      let markup = `<defs><clipPath id="meanQualificationClip"><rect x="${{margin.left}}" y="${{margin.top}}" width="${{width - margin.left - margin.right}}" height="${{height - margin.top - margin.bottom}}"/></clipPath></defs>`;
      for (let tick = 0; tick <= 5; tick++) {{
        const xValue = xMinimum + (xMaximum - xMinimum) * tick / 5;
        const yValue = yMinimum + (yMaximum - yMinimum) * tick / 5;
        const xPosition = x(xValue), yPosition = y(yValue);
        markup += `<line class="grid" x1="${{xPosition}}" y1="${{margin.top}}" x2="${{xPosition}}" y2="${{height - margin.bottom}}"/><text x="${{xPosition}}" y="${{height - 40}}" text-anchor="middle">${{duration(xValue).slice(0, 5)}}</text>`;
        markup += `<line class="grid" x1="${{margin.left}}" y1="${{yPosition}}" x2="${{width - margin.right}}" y2="${{yPosition}}"/><text x="${{margin.left - 9}}" y="${{yPosition + 4}}" text-anchor="end">${{duration(yValue).slice(0, 5)}}</text>`;
      }}
      markup += `<line class="axis" x1="${{margin.left}}" y1="${{margin.top}}" x2="${{margin.left}}" y2="${{height - margin.bottom}}"/><line class="axis" x1="${{margin.left}}" y1="${{height - margin.bottom}}" x2="${{width - margin.right}}" y2="${{height - margin.bottom}}"/>`;
      markup += `<text class="corner-label easy-label" x="${{margin.left + 12}}" y="${{margin.top + 20}}">Easiest to qualify</text>`;
      markup += `<text class="corner-label hard-label" x="${{width - margin.right - 12}}" y="${{height - margin.bottom - 12}}" text-anchor="end">Hardest to qualify</text>`;
      markup += `<text x="${{(margin.left + width - margin.right) / 2}}" y="${{height - 8}}" text-anchor="middle">Mean finish time (HH:MM)</text>`;
      markup += `<text x="18" y="${{(margin.top + height - margin.bottom) / 2}}" text-anchor="middle" transform="rotate(-90 18 ${{(margin.top + height - margin.bottom) / 2}})">Raw qualifying time (HH:MM)</text>`;
      if (globalFit) {{
        const fitMinimum = Math.min(...visiblePoints.map(point => point.x));
        const fitMaximum = Math.max(...visiblePoints.map(point => point.x));
        const equation = fitEquation(globalFit);
        markup += `<line class="global-fit" x1="${{x(fitMinimum)}}" y1="${{y(globalFit.intercept + globalFit.slope * fitMinimum)}}" x2="${{x(fitMaximum)}}" y2="${{y(globalFit.intercept + globalFit.slope * fitMaximum)}}" stroke="#15231e" stroke-width="3.5" stroke-dasharray="9 6" clip-path="url(#meanQualificationClip)"><title>Global linear fit: ${{equation}}</title></line>`;
        markup += `<rect x="${{width - margin.right - 520}}" y="${{margin.top + 7}}" width="508" height="27" rx="3" fill="#ffffff" fill-opacity="0.92" stroke="#aebcb5"/>`;
        markup += `<text class="global-fit-equation" x="${{width - margin.right - 20}}" y="${{margin.top + 25}}" text-anchor="end" font-size="12" font-weight="700" fill="#15231e">Global fit: ${{equation}}</text>`;
      }}
      allSeries.forEach((item, seriesIndex) => {{
        const legendColumn = seriesIndex % legendColumns;
        const legendRow = Math.floor(seriesIndex / legendColumns);
        const legendX = margin.left + legendColumn * legendColumnWidth;
        const legendY = 15 + legendRow * 22;
        const visible = !hiddenMeanQualificationRaces.has(item.eventId);
        markup += `<g class="trace-toggle" data-event-id="${{item.eventId}}" role="button" tabindex="0" aria-pressed="${{visible}}" aria-label="${{visible ? "Hide" : "Show"}} ${{item.label}}"><line x1="${{legendX}}" y1="${{legendY - 5}}" x2="${{legendX + 18}}" y2="${{legendY - 5}}" stroke="${{item.color}}" stroke-width="2.5"/><circle cx="${{legendX + 9}}" cy="${{legendY - 5}}" r="4" fill="${{item.color}}"/><text x="${{legendX + 25}}" y="${{legendY}}">${{item.label}}</text><title>Click to ${{visible ? "hide" : "show"}} ${{item.label}}</title></g>`;
      }});
      visibleSeries.forEach(item => {{
        const raceFit = linearFit(item.points);
        if (raceFit) {{
          const fitMinimum = Math.min(...item.points.map(point => point.x));
          const fitMaximum = Math.max(...item.points.map(point => point.x));
          markup += `<line x1="${{x(fitMinimum)}}" y1="${{y(raceFit.intercept + raceFit.slope * fitMinimum)}}" x2="${{x(fitMaximum)}}" y2="${{y(raceFit.intercept + raceFit.slope * fitMaximum)}}" stroke="${{item.color}}" stroke-width="2.5" stroke-opacity="0.82" clip-path="url(#meanQualificationClip)"/>`;
        }}
        item.points.forEach(point => {{
          const meanText = duration(point.x);
          const targetText = duration(point.y);
          const slotText = point.slotDetail ? ` · ${{point.slotDetail}}` : "";
          const accessibleLabel = `${{item.label}}, ${{point.year}}: mean ${{meanText}}, qualifying ${{targetText}}${{slotText}}`;
          markup += `<circle class="data-point" cx="${{x(point.x)}}" cy="${{y(point.y)}}" r="5.5" fill="${{item.color}}" tabindex="0" role="img" aria-label="${{accessibleLabel}}" data-series="${{item.label}}" data-year="${{point.year}}" data-value="Mean ${{meanText}} · target ${{targetText}}${{slotText}}"><title>${{accessibleLabel}}</title></circle>`;
        }});
      }});
      svg.innerHTML = markup;
      attachPointTooltips(svg);
      svg.querySelectorAll(".trace-toggle").forEach(toggle => {{
        const toggleTrace = () => {{
          const eventId = toggle.dataset.eventId;
          if (hiddenMeanQualificationRaces.has(eventId)) {{
            hiddenMeanQualificationRaces.delete(eventId);
          }} else if (visibleSeries.length > 1) {{
            hiddenMeanQualificationRaces.add(eventId);
          }}
          renderMeanQualificationCompare();
        }};
        toggle.addEventListener("click", toggleTrace);
        toggle.addEventListener("keydown", event => {{
          if (event.key === "Enter" || event.key === " ") {{
            event.preventDefault();
            toggleTrace();
          }}
        }});
      }});
      qualificationResidualChart(
        visibleSeries.map(item => item.eventId), visibleSeries, globalFit
      );
    }}
    function signedDuration(seconds) {{
      if (!Number.isFinite(seconds)) return "—";
      const sign = seconds > 0 ? "+" : seconds < 0 ? "−" : "";
      return `${{sign}}${{duration(Math.abs(seconds))}}`;
    }}
    function signedDurationShort(seconds) {{
      if (!Number.isFinite(seconds)) return "—";
      const sign = seconds > 0 ? "+" : seconds < 0 ? "−" : "";
      return `${{sign}}${{duration(Math.abs(seconds)).slice(0, 5)}}`;
    }}
    function qualificationResidualChart(eventIds, sourceSeries, globalFit) {{
      const sourcePoints = sourceSeries.flatMap(item => item.points);
      const svg = document.getElementById("compareQualificationResidual");
      if (sourcePoints.length < 2) {{ svg.innerHTML = `<text x="20" y="40">Not enough data for a global fit</text>`; return; }}
      if (!globalFit) {{ svg.innerHTML = `<text x="20" y="40">Mean finish times do not vary enough for a global fit</text>`; return; }}

      const pointsByEvent = Object.fromEntries(sourceSeries.map(item => [item.eventId, Object.fromEntries(
        item.points.map(point => {{
          const fitted = globalFit.intercept + globalFit.slope * point.x;
          return [point.year, {{
            value: point.y - fitted,
            detail: `Actual ${{duration(point.y)}} · fitted ${{duration(fitted)}}`,
          }}];
        }})
      )]));
      const residualSeries = yearSeries(eventIds, (eventId, year) => pointsByEvent[eventId]?.[year]);
      categoryPointChart(
        "compareQualificationResidual",
        eventIds.map(eventId => DATASETS[eventId].name),
        residualSeries,
        {{
          includeZero: true,
          formatValue: signedDuration,
          formatTick: signedDurationShort,
          yAxisLabel: "Actual minus fitted qualifying time (HH:MM)",
        }}
      );
    }}
    function renderQualificationCompare() {{
      const groups = raceGroups();
      if (compareImAgeGroup.value) {{
        renderQualificationCompareGroup("compareImQualification", (groups.im || []).filter(isQualifyingEvent), compareImAgeGroup.value, compareImGender.value);
      }}
      if (compare703AgeGroup.value) {{
        renderQualificationCompareGroup("compare703Qualification", (groups["703"] || []).filter(isQualifyingEvent), compare703AgeGroup.value, compare703Gender.value);
      }}
    }}
    function renderMeanQualificationCompare() {{
      const eventIds = (raceGroups()[compareScatterDistance.value] || []).filter(isQualifyingEvent);
      const ageGroups = compareAgeGroups(eventIds);
      populateAgeGroupSelect(compareScatterAgeGroup, ageGroups);
      if (compareScatterAgeGroup.value) {{
        meanQualificationScatter(eventIds, compareScatterAgeGroup.value, compareScatterGender.value);
        renderAdditionalCompare(
          eventIds, compareScatterAgeGroup.value, compareScatterGender.value
        );
      }}
    }}
    function populateAgeGroupSelect(select, ageGroups) {{
      const previous = select.value;
      select.innerHTML = ageGroups.map(ageGroup => `<option value="${{ageGroup}}">${{ageGroup}}</option>`).join("");
      select.value = ageGroups.includes(previous) ? previous : (ageGroups.includes("30-34") ? "30-34" : ageGroups[0]);
    }}
    function renderCompare() {{
      const groups = raceGroups();
      const imEvents = groups.im || [];
      const events703 = groups["703"] || [];
      renderCompareYears();
      renderRaceStatisticsCompare();
      renderDistributionCompare("compareImDistribution", imEvents);
      renderDistributionCompare("compare703Distribution", events703);
      renderSplitDistributions();
      populateAgeGroupSelect(compareImAgeGroup, compareAgeGroups(imEvents));
      populateAgeGroupSelect(compare703AgeGroup, compareAgeGroups(events703));
      renderQualificationCompare();
      renderMeanQualificationCompare();
      const fieldAgeGroup = document.getElementById("compareFieldAgeGroup");
      if (fieldAgeGroup) {{
        const fieldEvents = groups[document.getElementById("compareFieldDistance").value] || [];
        populateAgeGroupSelect(fieldAgeGroup, compareAgeGroups(fieldEvents));
        renderFieldCompare(fieldEvents, fieldAgeGroup.value, document.getElementById("compareFieldGender").value);
      }}
    }}
    function render() {{
      const lower = parseTime(fromInput.value);
      const upper = parseTime(toInput.value);
      if (!Number.isFinite(lower) || !Number.isFinite(upper) || lower > upper) return;
      const rows = filteredData();
      document.getElementById("finisherCount").textContent = rows.length.toLocaleString();
      document.getElementById("rangeLabel").textContent = `${{duration(lower)}}–${{duration(upper)}}`;
      const middle = Math.floor(rows.length / 2);
      const median = rows.length % 2
        ? rows[middle].overall
        : (rows[middle - 1]?.overall + rows[middle]?.overall) / 2;
      document.getElementById("medianFinish").textContent = rows.length ? duration(median) : "—";
      document.getElementById("summaryBody").innerHTML = summaryRows(rows);
      document.getElementById("finishersBody").innerHTML = finisherRows(rows);
    }}
    function downloadCsv() {{
      const rows = filteredData();
      const headers = ["Year", "Bib", "Name", "Country", "Gender", "Division", "Overall", "Swim", "Swim Pace", "T1", "Bike", "Bike Speed", "T2", "Run", "Run Pace"];
      const values = rows.map(row => [row.year, row.bib, row.name, row.country, row.gender, row.division, duration(row.overall), duration(row.swim), metric("swim", row.swim), duration(row.t1), duration(row.bike), metric("bike", row.bike), duration(row.t2), duration(row.run), metric("run", row.run)]);
      const csv = [headers, ...values].map(line => line.map(value => `"${{String(value).replaceAll('"', '""')}}"`).join(",")).join("\\r\\n");
      const link = document.createElement("a");
      link.href = URL.createObjectURL(new Blob([csv], {{ type: "text/csv" }}));
      link.download = `${{eventSelect.value}}_splits_${{fromInput.value.replaceAll(":", "")}}_${{toInput.value.replaceAll(":", "")}}.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(link.href), 1000);
    }}

    function selectEvent(resetRange = true) {{
      const current = dataset();
      const years = [...new Set(current.records.map(row => row.year))].sort();
      document.getElementById("eventSubtitle").textContent = `${{current.subtitle}} · finishers from ${{years[0]}}–${{years.at(-1)}}`;
      document.getElementById("distanceNote").textContent = `Zero-duration placeholders are excluded from split statistics. Paces use ${{current.distances.swim / 1000}} km swim, ${{current.distances.bike}} km bike, and ${{current.distances.run}} km run.`;
      yearsElement.innerHTML = years.map(year => `<label><input type="checkbox" value="${{year}}" ${{compareYearVisible(year) ? "checked" : ""}}>${{year}}</label>`).join("");
      if (resetRange) {{
        fromInput.value = current.default_from;
        toInput.value = current.default_to;
      }}
      render();
      renderQualification();
      renderOverall();
      renderStatistics();
      updateTitle();
    }}

    function renderSharedViews() {{
      selectEvent(false);
      renderCompare();
      renderOdds();
      renderExperimental();
      renderEasiestTab();
      renderKonaTrace();
      renderContextYears();
      decorateDashboard();
    }}

    eventSelect.innerHTML = Object.entries(DATASETS).map(([id, event]) => `<option value="${{id}}">${{event.name}}</option>`).join("");
    eventSelect.addEventListener("change", () => selectEvent(true));
    document.querySelectorAll(".tab-button").forEach(button => button.addEventListener("click", () => {{
      activeTab = button.dataset.tab;
      document.querySelectorAll(".tab-button").forEach(item => {{
        item.classList.toggle("active", item === button);
        item.setAttribute("aria-selected", item === button ? "true" : "false");
      }});
      document.querySelectorAll(".tab-panel").forEach(panel => panel.classList.toggle("active", panel.id === `${{activeTab}}Panel`));
      updateTitle();
      if (activeTab === "experimental") renderExperimentalDetails();
      if (activeTab === "easiest") renderEasiestTab();
    }}));
    [fromInput, toInput, searchInput].forEach(element => element.addEventListener("input", render));
    yearsElement.addEventListener("change", event => {{
      if (event.target.matches('input[type="checkbox"]')) toggleCompareYear(event.target.value);
    }});
    qualificationAgeGroup.addEventListener("change", renderQualification);
    qualificationGender.addEventListener("change", renderQualification);
    qualificationDeclines.addEventListener("input", renderQualification);
    qualificationLegacyDeclines.addEventListener("input", renderQualification);
    experimentalPercentile.addEventListener("input", renderExperimental);
    [maleSlots, femaleSlots].forEach(element => element.addEventListener("change", updateSlotAllocation));
    document.getElementById("resetSlots").addEventListener("click", () => {{
      delete slotAllocations[eventSelect.value];
      syncSlotControls();
      renderSharedViews();
    }});
    document.getElementById("download").addEventListener("click", downloadCsv);
    const compareImAgeGroup = document.getElementById("compareImAgeGroup");
    const compareImGender = document.getElementById("compareImGender");
    const compare703AgeGroup = document.getElementById("compare703AgeGroup");
    const compare703Gender = document.getElementById("compare703Gender");
    [compareImAgeGroup, compareImGender, compare703AgeGroup, compare703Gender].forEach(control => control.addEventListener("change", renderQualificationCompare));
    const compareScatterDistance = document.getElementById("compareScatterDistance");
    const compareScatterAgeGroup = document.getElementById("compareScatterAgeGroup");
    const compareScatterGender = document.getElementById("compareScatterGender");
    [compareScatterDistance, compareScatterAgeGroup, compareScatterGender].forEach(control => control.addEventListener("change", renderMeanQualificationCompare));
    [oddsDistance, oddsGender, oddsAgeGroup, oddsTimeBasis].forEach(control => control.addEventListener("change", renderOdds));
    experimentalDistance.addEventListener("change", renderExperimental);
    compareSplitDistance.addEventListener("change", renderSplitDistributions);
    document.getElementById("compareStatisticsDistance").addEventListener("change", renderRaceStatisticsCompare);
    document.getElementById("compareYears").addEventListener("change", event => {{
      if (event.target.matches('input[type="checkbox"]')) toggleCompareYear(event.target.value);
    }});
    ["konaGender", "konaAgeGroup", "konaEvidence", "konaRace", "konaMatchStatus"].forEach(id => document.getElementById(id).addEventListener("change", renderKonaTrace));
    document.getElementById("konaCycle").addEventListener("change", () => {{ initializeKonaTrace(); updateDashboardScope(); }});
    document.getElementById("konaSearch").addEventListener("input", renderKonaTrace);
    document.getElementById("konaMatchesBody").addEventListener("change", event => {{
      const reviewKey = event.target.dataset.konaReview;
      if (!reviewKey) return;
      if (event.target.value) konaReviews[reviewKey] = event.target.value;
      else delete konaReviews[reviewKey];
      try {{ localStorage.setItem(konaReviewStorageKey, JSON.stringify(konaReviews)); }}
      catch {{ konaReviewStorageAvailable = false; }}
      renderKonaTrace();
    }});
    easiestDistance.addEventListener("change", () => {{
      const defaults = {{ im: "10:30:00", "703": "05:00:00" }};
      if (Object.values(defaults).includes(easiestTypedTime)) easiestTypedTime = defaults[easiestDistance.value];
      renderEasiestTab();
    }});
    easiestGender.addEventListener("change", renderEasiestTab);
    [easiestAgeGroup, easiestDetailRace].forEach(control => control.addEventListener("change", renderEasiest));
    easiestDeclines.addEventListener("input", renderEasiest);
    easiestTime.addEventListener("input", () => {{
      if (!Number.isFinite(parseTime(easiestTime.value))) return;
      easiestTypedTime = easiestTime.value;
      renderEasiest();
    }});
    easiestSearch.addEventListener("input", renderEasiestSearch);
    easiestManualRace.addEventListener("change", fillManualForm);
    document.getElementById("easiestManualAdd").addEventListener("click", addManualResult);
    document.getElementById("easiestSearchBody").addEventListener("click", event => {{
      const index = event.target.closest("[data-add]")?.dataset.add;
      if (index === undefined) return;
      const {{ eventId, row }} = easiestSearchMatches[Number(index)];
      myResults.push({{
        eventId, year: row.year, division: String(row.division).trim().toUpperCase(), name: row.name,
        swim: row.swim, t1: row.t1, bike: row.bike, t2: row.t2, run: row.run,
      }});
      if (row.gender === "Male" || row.gender === "Female") easiestGender.value = row.gender;
      saveMyResults();
      renderEasiestTab();
    }});
    document.getElementById("easiestResultsBody").addEventListener("click", event => {{
      const index = event.target.closest("[data-remove]")?.dataset.remove;
      if (index === undefined) return;
      myResults.splice(Number(index), 1);
      saveMyResults();
      renderEasiestTab();
    }});
    const modifiedCourseText = Object.values(DATASETS)
      .flatMap(event => Object.entries(event.modified_courses || {{}}).map(([year, description]) => `${{event.name}} ${{year}} (${{description}})`))
      .join(", ") || "none";
    document.querySelectorAll(".modified-course-list").forEach(element => element.textContent = modifiedCourseText);
    [oddsTime, oddsDeclines].forEach(control => control.addEventListener("input", () => {{
      if (control === oddsTime && !Number.isFinite(parseTime(oddsTime.value))) return;
      renderOdds();
    }}));
    {dashboard_ui}
    selectEvent(true);
    initializeKonaTrace();
    renderCompare();
    renderOdds();
    renderExperimental();
    initializeDashboardUI();
  </script>
</body>
</html>"""


def build_index_html():
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="0; url=dashboard.html">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>IRONMAN qualification analysis</title>
</head>
<body>
  <p><a href="dashboard.html">Open the IRONMAN qualification dashboard</a></p>
</body>
</html>
"""


def main():
    ensure_output_directories()
    datasets = load_dashboard_data()
    data_json = json.dumps(datasets, ensure_ascii=False).replace("</", "<\\/")
    DATA_FILE.write_text(
        f"window.DASHBOARD_DATA = {data_json};\n", encoding="utf-8"
    )
    OUTPUT_FILE.write_text(build_html(datasets), encoding="utf-8")
    INDEX_FILE.write_text(build_index_html(), encoding="utf-8")
    counts = ", ".join(
        f"{event['name']}: {len(event['records'])}"
        for event in datasets.values()
    )
    print(f"Embedded finishers ({counts}).")
    print(f"Saved dashboard to {OUTPUT_FILE.resolve()}")
    print(f"Saved dashboard data to {DATA_FILE.resolve()}")
    print(f"Saved Pages entry point to {INDEX_FILE.resolve()}")


if __name__ == "__main__":
    main()