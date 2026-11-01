"""Race Finder inputs and historical time-multiplier calibration.

The legacy time-multiplier calibration compares objective A with scan estimates;
it does not calibrate or validate the active rank-factor scenario.
"""
import math
from collections import Counter, defaultdict
from statistics import median, pstdev

import reference_data

DNF_PRIOR_STARTERS = 1000


def _quantile(values, q):
    values = sorted(values)
    position = (len(values) - 1) * q
    low, high = math.floor(position), math.ceil(position)
    return values[low] + (values[high] - values[low]) * (position - low)


def rolldown_calibration(traces):
    """Historical scan-estimated cut-off divided by strict, per gender pool.

    Uses only the current-rules re-ranking of past Kona cycles (objective A),
    gender-pool races where the scan criterion was met.
    """
    ratios = {"Male": [], "Female": []}
    by_year = defaultdict(lambda: {"Male": [], "Female": []})
    for cycle, trace in traces.items():
        for row in trace.get("counterfactual_summaries", []):
            scan = row.get("cutoff_scan") or {}
            strict = row.get("strict_cutoff")
            if (row.get("slot_scope") != "gender" or row.get("gender") not in ratios
                    or not strict or not scan.get("time") or not scan.get("criterion_met")):
                continue
            ratio = scan["time"] / strict
            ratios[row["gender"]].append(ratio)
            by_year[str(cycle)][row["gender"]].append(ratio)
    result = {"basis": "cutoff_scan.time / strict_cutoff, current-rules re-ranking of Kona cycles", "genders": {}}
    for gender, values in ratios.items():
        if len(values) < 5:
            continue
        result["genders"][gender.lower()] = {
            "factor": round(median(values), 4),
            "q25": round(_quantile(values, 0.25), 4),
            "q75": round(_quantile(values, 0.75), 4),
            "sd_log": round(pstdev([math.log(v) for v in values]), 4),
            "n": len(values),
        }
    result["by_cycle"] = {
        cycle: {gender.lower(): round(median(v), 4) for gender, v in groups.items() if v}
        for cycle, groups in sorted(by_year.items())
    }
    return result


def dnf_rates(datasets):
    """Per event: pooled DNF/DNS rate over qualifying, unmodified race-years, shrunk to the distance mean."""
    raw = {}
    for event_id, dataset in datasets.items():
        starters = dnf = dns = 0
        years = 0
        for row in dataset.get("statistics", []):
            if str(row["year"]) in dataset.get("modified_courses", {}):
                continue
            if not row.get("starters"):
                continue
            starters += row["starters"]
            dnf += row.get("dnf") or 0
            dns += row.get("dns") or 0
            years += 1
        raw[event_id] = {"group": dataset["group"], "starters": starters, "dnf": dnf, "dns": dns, "years": years}
    totals = defaultdict(lambda: [0, 0])
    for entry in raw.values():
        totals[entry["group"]][0] += entry["starters"]
        totals[entry["group"]][1] += entry["dnf"]
    result = {}
    for event_id, entry in raw.items():
        total_starters, total_dnf = totals[entry["group"]]
        mean = total_dnf / total_starters if total_starters else 0.0
        shrunk = (entry["dnf"] + DNF_PRIOR_STARTERS * mean) / (entry["starters"] + DNF_PRIOR_STARTERS)
        result[event_id] = {
            "starters": entry["starters"],
            "dnf": entry["dnf"],
            "years": entry["years"],
            "raw_rate": round(entry["dnf"] / entry["starters"], 4) if entry["starters"] else None,
            "rate": round(shrunk, 4),
            "group_mean": round(mean, 4),
        }
    return result


def event_calendar(datasets, traces):
    """Next-edition date/slots from the cycle calendar plus the typical month from past editions."""
    calendar = reference_data.cycle_calendar()
    next_by_event = {entry["event_id"]: entry for entry in calendar["events"] if entry.get("event_id")}
    months = defaultdict(Counter)
    last_date = {}
    for trace in traces.values():
        for row in trace.get("counterfactual_summaries", []):
            date = row.get("date")
            if date:
                months[row["event_id"]][int(date[5:7])] += 1
                last_date[row["event_id"]] = max(last_date.get(row["event_id"], ""), date)
    events = {}
    for event_id in datasets:
        entry = next_by_event.get(event_id)
        typical = months[event_id].most_common(1)[0][0] if months[event_id] else None
        events[event_id] = {
            "next_date": entry["date"] if entry else None,
            "next_slots": entry["slots"] if entry else None,
            "typical_month": typical,
            "last_seen": last_date.get(event_id),
        }
    return {
        "cycle": calendar["cycle"],
        "window_start": calendar["window_start"],
        "championship_date": calendar["championship_date"],
        "source_url": calendar["source_url"],
        "retrieved": calendar["retrieved"],
        "events": events,
        "unmatched": [entry for entry in calendar["events"] if not entry.get("event_id")],
    }
