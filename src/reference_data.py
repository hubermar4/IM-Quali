"""Loaders for the editable reference data in data/reference/."""
import json
from functools import lru_cache

from project_paths import REFERENCE_DATA_DIR


@lru_cache(maxsize=None)
def load(name):
    with open(REFERENCE_DATA_DIR / name, encoding="utf-8") as handle:
        return json.load(handle)


def events():
    return load("events.json")


def coachcox_event_names():
    return {
        event_id: entry["coachcox_name"]
        for event_id, entry in events()["events"].items()
        if "coachcox_name" in entry
    }


def coachcox_half_event_names():
    return {
        event_id: entry["coachcox_703_name"]
        for event_id, entry in events()["events"].items()
        if "coachcox_703_name" in entry
    }


def event_display_names():
    return {
        event_id: entry["display_name"]
        for event_id, entry in events()["events"].items()
        if "display_name" in entry
    }


def gpx_event_files():
    return {
        event_id: entry["gpx_file"]
        for event_id, entry in events()["events"].items()
        if "gpx_file" in entry
    }


def current_slots():
    return load("current_slots.json")


def modified_courses():
    return {
        (entry["event"], entry["year"]): entry["description"]
        for entry in load("modified_courses.json")["modified_courses"]
    }


def standards(distance):
    """Return (current_cycle, {cycle: (men_ratios, women_ratios)}) for "full" or "half"."""
    block = load("age_group_standards.json")[distance]
    return block["current_cycle"], {
        cycle: (tables["men"], tables["women"]) for cycle, tables in block["cycles"].items()
    }


def qualification_constants():
    return load("qualification_constants.json")


def reported_pool_cutoffs():
    keys = ("cycle", "event", "race_year", "gender")
    return {
        tuple(entry[key] for key in keys): {k: v for k, v in entry.items() if k not in keys}
        for entry in load("reported_cutoffs.json")["cutoffs"]
    }


def cycle_calendar():
    return load("cycle_calendar.json")
