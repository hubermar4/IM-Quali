import json
import re
from pathlib import Path

import pandas as pd
import backtest
import dashboard_insights
import qualification_full
import reference_data
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
COACHCOX_HALF_CACHE_DIR = CACHE_DIR / "CoachCoxHalfQualificationPages"
FULL_DISTANCE = {"swim": 3800, "bike": 180, "run": 42.2}
HALF_DISTANCE = {"swim": 1900, "bike": 90, "run": 21.1}
YEAR_PATTERN = re.compile(r"(20\d{2})")
PRO_DIVISIONS = {"MPRO", "FPRO"}
HALF_DISTANCE_PATTERN = re.compile(r"70\.?3|703", re.IGNORECASE)
_SLOTS = reference_data.current_slots()
_CONSTANTS = reference_data.qualification_constants()
DEFAULT_TOTAL_SLOTS = _SLOTS["default_total_slots"]
DEFAULT_SLOTS_PER_GENDER = _SLOTS["default_slots_per_gender"]
# Latest published allocation per race and its qualifying cycle; current mode
# applies it to every historical field.
RACE_SLOTS_IM = {event: (entry["slots"], entry["cycle"]) for event, entry in _SLOTS["im"].items()}
RACE_SLOTS_703 = {
  event: ({"male": entry["male"], "female": entry["female"]}, entry["cycle"])
  for event, entry in _SLOTS["703"].items()
}
_EVENT_REGISTRY = reference_data.events()
# World Championship races are not qualifying events for the age-group system.
NON_QUALIFYING_EVENTS = set(_EVENT_REGISTRY["non_qualifying_events"])
# Championship editions held in Nice (2023/2025 men, 2024 women); their start
# lists complement the local Kona files of the same championship year.
NICE_CHAMPIONSHIP_EVENT = _EVENT_REGISTRY["nice_championship_event"]
MODIFIED_COURSES = reference_data.modified_courses()
# Official ironman.com allocations for race-years missing from the Coach Cox lists.
OFFICIAL_SLOT_SOURCES = {
  (entry["event"], entry["year"]): {k: v for k, v in entry.items() if k not in ("event", "year")}
  for entry in _SLOTS["official_sources"]
}
COACHCOX_EVENT_NAMES = reference_data.coachcox_event_names()
COACHCOX_HALF_EVENT_NAMES = reference_data.coachcox_half_event_names()
EVENT_DISPLAY_NAMES = reference_data.event_display_names()
GPX_EVENT_FILES = reference_data.gpx_event_files()
LEGACY_RANK_OFFSETS = tuple(_CONSTANTS["legacy_rank_offsets"])


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
            "qualification_slot_source_url": _SLOTS.get("source_urls", {}).get(
              f"{'703' if group == '703' else 'kona'}_{slot_cycle}"
            ) if slot_cycle else None,
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


def coachcox_name_key(name):
  # Coach Cox spells some 70.3 races both "Portugal - Cascais" and "Portugal-Cascais".
  return re.sub(r"\s*-\s*", "-", name.strip()).lower()


def load_historical_slot_sources():
  matches = {}
  pages = (
    (COACHCOX_CACHE_DIR, "im", COACHCOX_EVENT_NAMES),
    (COACHCOX_HALF_CACHE_DIR, "him", COACHCOX_HALF_EVENT_NAMES),
  )
  for cache_dir, series, event_names in pages:
    wanted_names = {coachcox_name_key(name): event_id for event_id, name in event_names.items()}
    for cache_file in sorted(cache_dir.glob("qualification_*.html")):
      cycle_match = YEAR_PATTERN.search(cache_file.stem)
      if not cycle_match:
        continue
      cycle = cycle_match.group(1)
      source_url = f"https://coachcox.co.uk/imstats/{series}/qualification/{cycle}/races/"
      rows = parse_coachcox_races(
        cache_file.read_text(encoding="utf-8"), source_url, cycle
      )
      for row in rows:
        event_id = wanted_names.get(coachcox_name_key(row["race_name"]))
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
    cycles = source.get("cycles") or []
    if len(cycles) != 1 or (source["method"] == "performance" and cycles[0] not in module.STANDARDS):
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

    cycle = cycles[0]
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
    top_twenty = finishers["finish_td"].dt.total_seconds().groupby(finishers["Division"]).quantile(0.2)
    counts = times.size()
    statistics[year] = {
      division: {
        "starters": int(starters.get(division, 0)),
        "finishers": int(counts.get(division, 0)),
        "winner": round(winners[division].total_seconds()) if division in winners else None,
        "median": round(medians[division].total_seconds()) if division in medians else None,
        "top_20_percent": round(top_twenty[division]) if division in top_twenty else None,
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


def course_factor_frames(datasets):
  """Per distance group: repeat-athlete candidate records and the baseline race-years."""
  groups = {}
  for group in ("im", "703"):
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
    if frames:
      groups[group] = (pd.concat(frames, ignore_index=True), baseline)
  return groups


def load_course_factors(datasets):
  """Race-year factors plus course, season and returning-athlete effects per distance."""
  factors = {event_id: {} for event_id in datasets}
  models = {}
  frames_by_group = course_factor_frames(datasets)
  for group, module in (("im", qualification_full), ("703", qualification_half)):
    if group not in frames_by_group:
      continue
    combined, baseline = frames_by_group[group]
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


def current_pool_counterfactual_calendar(calendar, events, event_names, group="im"):
  """A cycle's own qualifying race-years, re-allocated with each race's latest slots.

  Kona starters only reveal the roll-down of the race-years that qualified for
  that championship, so current-rule estimates for e.g. Austria 2017 must use
  the Kona 2017 start list, ranked under the current rules and allocation.
  """
  name_to_event = {name: event_id for event_id, name in event_names.items()}
  rows = []
  for race in calendar:
    event = events.get(name_to_event.get(race["race_name"]), {})
    slots = event.get("qualification_slots")
    if event.get("group") != group or not event.get("qualifying", True):
      continue
    if group == "703":
      if not isinstance(slots, dict) or not all(isinstance(slots.get(key), int) and slots[key] > 0 for key in ("male", "female")):
        continue
      rows.append({**race, "male_qualifiers": slots["male"], "female_qualifiers": slots["female"],
                   "total_qualifiers": slots["male"] + slots["female"]})
      continue
    if not isinstance(slots, int) or slots <= 0:
      continue
    rows.append({**race, "total_qualifiers": slots})
  return rows


def half_distance_calendar(cycle):
  """70.3 qualifying race-years of one cycle with their published allocation."""
  rows = []
  for (event_id, year), source in sorted(HISTORICAL_SLOT_SOURCES.items()):
    event = EVENTS.get(event_id, {})
    if event.get("group") != "703" or source.get("cycles") != [str(cycle)] or source.get("other_cycles"):
      continue
    if source.get("male") is not None and source.get("female") is not None:
      male, female, total = source["male"], source["female"], source["male"] + source["female"]
    elif source.get("method") == "legacy" and source.get("total"):
      male, female, total = None, None, source["total"]
    else:
      continue
    rows.append({
      "qualification_cycle": str(cycle), "race_name": event_id, "event_year": year,
      "race_date": "", "source_url": source.get("source_url") or "",
      "male_qualifiers": male, "female_qualifiers": female, "total_qualifiers": total,
    })
  return rows


def build_half_distance_traces(historical_targets):
  """70.3 World Championship traces per cycle; same objectives as the Kona traces."""
  event_names = {event_id: event_id for event_id, event in EVENTS.items() if event["group"] == "703"}
  traces = {}
  for championship_id in sorted(NON_QUALIFYING_EVENTS):
    championship = EVENTS.get(championship_id)
    if not championship or championship["group"] != "703":
      continue
    venue = _EVENT_REGISTRY["events"].get(championship_id, {}).get("venue") or championship["name"]
    for cycle, csv_files in championship["years"].items():
      if cycle in traces:
        raise ValueError(f"Two 70.3 World Championship start lists for cycle {cycle}")
      start_list = read_results(csv_files).assign(Venue=venue)
      calendar = half_distance_calendar(cycle)
      options = {"module": qualification_half, "group": "703", "default_venue": venue}
      trace = build_kona_trace(
        start_list, calendar, EVENTS, read_results, event_names, year=cycle,
        historical_targets=historical_targets, **options,
      )
      counterfactual = build_kona_trace(
        start_list, current_pool_counterfactual_calendar(calendar, EVENTS, event_names, group="703"),
        EVENTS, read_results, event_names, year=cycle, historical_targets=historical_targets,
        ranking_cycle=qualification_half.CURRENT_CYCLE, **options,
      )
      add_counterfactual(trace, counterfactual)
      traces[cycle] = trace
  return traces


def add_counterfactual(trace, counterfactual_trace):
  trace["counterfactual_summaries"] = [
    {key: value for key, value in row.items() if key != "manual_pool_times"}
    for row in counterfactual_trace["summaries"]["all"]
  ]
  trace["counterfactual_winners"] = [
    {
      "name": starter["name"], "gender": starter["gender"],
      "matches": [
        {key: match.get(key) for key in ("event_id", "year", "division", "finish_time", "pool_rank", "initial_slot")}
        for match in starter["matches"] if match.get("initial_slot") == "Automatic winner"
      ],
    }
    for starter in counterfactual_trace["starters"]
    if any(match.get("initial_slot") == "Automatic winner" for match in starter["matches"])
  ]
  trace["counterfactual_standards"] = counterfactual_trace["standards"]
  trace["counterfactual_standard_cycle"] = counterfactual_trace["standard_cycle"]


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
    add_counterfactual(traces[cycle], counterfactual_trace)
  if "im_kona" in datasets:
    datasets["im_kona"]["kona_traces"] = traces
    datasets["im_kona"]["kona_trace"] = traces.get("2026")
    datasets["im_kona"]["kona_trace_cycles"] = [
      {"year": str(cycle), "available": str(cycle) in traces}
      for cycle in range(2017, 2027)
    ]
    datasets["im_kona"]["wc703_traces"] = build_half_distance_traces(historical_targets)
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
  if "im_kona" in datasets:
    race_datasets = {event_id: dataset for event_id, dataset in datasets.items() if event_id != "im_kona"}
    datasets["im_kona"]["rolldown_calibration"] = dashboard_insights.rolldown_calibration(traces)
    datasets["im_kona"]["dnf_rates"] = dashboard_insights.dnf_rates(race_datasets)
    datasets["im_kona"]["event_calendar"] = dashboard_insights.event_calendar(race_datasets, traces)
    datasets["im_kona"]["backtest"] = backtest.run_backtest(
      course_factor_frames(datasets), race_datasets, models, traces,
    )
  return datasets


def build_html(datasets):
    source = Path(__file__).parent
    template = (source / "dashboard_template.html").read_text(encoding="utf-8")
    style = (source / "dashboard.css").read_text(encoding="utf-8")
    script = (source / "dashboard_app.js").read_text(encoding="utf-8").replace(
        "@@DASHBOARD_UI@@", (source / "dashboard_ui.js").read_text(encoding="utf-8")
    )
    return template.replace("@@STYLE@@\n", style).replace("@@SCRIPT@@\n", script)


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