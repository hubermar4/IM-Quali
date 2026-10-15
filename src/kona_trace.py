import math
import re
from collections import Counter, defaultdict

import pandas as pd

import qualification_full
from course_difficulty import identity_key


HAMBURG_CUTOFF_URL = "https://tri-mag.de/szene/von-hamburg-nach-hawaii-so-schnell-musste-man-fuer-die-kona-quali-sein/"
REPORTED_POOL_CUTOFFS = {
    ("2026", "im_austria", "2026", "Male"): {
        "reported_cutoff": 8 * 3600 + 58 * 60,
        "reported_cutoff_precision": "minute",
        "reported_cutoff_source": "User report: last accepted men's performance-pool time",
    },
    ("2026", "im_hamburg", "2026", "Male"): {
        "reported_cutoff": 9 * 3600 + 3 * 60 + 44,
        "reported_cutoff_precision": "second",
        "reported_cutoff_source": "tri-mag.de, 9 June 2026",
        "reported_cutoff_url": HAMBURG_CUTOFF_URL,
        "reported_cutoff_athlete": "Dusan Milosevic",
    },
    ("2026", "im_hamburg", "2026", "Female"): {
        "reported_cutoff": 11 * 3600 + 4 * 60 + 32,
        "reported_cutoff_precision": "second",
        "reported_cutoff_source": "tri-mag.de, 9 June 2026",
        "reported_cutoff_url": HAMBURG_CUTOFF_URL,
        "reported_cutoff_athlete": "Janine Schulschek",
    },
}


def text_value(value):
    return "" if pd.isna(value) else str(value).strip()


def athlete_key(row):
    name = text_value(row.get("Name"))
    country = text_value(row.get("Country")).upper()
    gender = text_value(row.get("Gender", row.get("gender"))).title()
    return identity_key(name, gender, country) if name and country else None


def age_interval(division, year):
    match = re.fullmatch(r"[MF](\d{2})-(\d{2})", text_value(division).upper())
    if not match:
        return None
    lower, upper = map(int, match.groups())
    return int(year) - upper, int(year) - lower


def compatible_age(first_division, first_year, second_division, second_year):
    first = age_interval(first_division, first_year)
    second = age_interval(second_division, second_year)
    return bool(first and second and max(first[0], second[0]) <= min(first[1], second[1]))


def seconds_value(value):
    duration = qualification_full.parse_time(value)
    return duration.total_seconds() if duration is not None and duration > pd.Timedelta(0) else None


def estimate_pool_cutoff(pool_times, matched_ranks, initial_slots):
    pool_size = len(pool_times)
    ranks = set(rank for rank in matched_ranks if rank is not None and 1 <= rank <= pool_size)
    estimate = {"time": None, "rank": None, "low_time": None, "high_time": None,
                "low_rank": None, "high_rank": None, "matched_pool_starters": len(ranks),
                "bic_gain": None, "reason": "Insufficient pool matches"}
    if initial_slots <= 0 or pool_size < 4 or len(ranks) < 3:
        return estimate

    def likelihood(matched, total):
        unmatched = total - matched
        return (matched * math.log(matched / total) if matched else 0) + (
            unmatched * math.log(unmatched / total) if unmatched else 0)

    candidates = []
    before = 0
    for cutoff in range(1, pool_size):
        before += cutoff in ranks
        after = len(ranks) - before
        if before < 3 or before / cutoff <= after / (pool_size - cutoff):
            continue
        score = likelihood(before, cutoff) + likelihood(after, pool_size - cutoff)
        candidates.append((cutoff, score))
    if not candidates:
        return estimate
    best_rank, best_score = max(candidates, key=lambda item: item[1])
    bic_gain = 2 * (best_score - likelihood(len(ranks), pool_size)) - 2 * math.log(pool_size)
    estimate["bic_gain"] = round(bic_gain, 2)
    if bic_gain <= 0:
        estimate["reason"] = "No supported change in match density"
        return estimate
    weights = [(rank, math.exp(score - best_score)) for rank, score in candidates]
    weight_total = sum(weight for _, weight in weights)
    cumulative = 0
    low_rank = high_rank = None
    for rank, weight in weights:
        cumulative += weight / weight_total
        if low_rank is None and cumulative >= 0.05:
            low_rank = rank
        if cumulative >= 0.95:
            high_rank = rank
            break
    return {**estimate, "time": math.floor(pool_times[best_rank - 1]), "rank": best_rank,
            "low_time": math.floor(pool_times[low_rank - 1]),
            "high_time": math.floor(pool_times[high_rank - 1]),
            "low_rank": low_rank, "high_rank": high_rank, "reason": None}


def scan_pool_cutoff(pool_times, matched_ranks, initial_slots, consecutive_absences=15):
    if not isinstance(consecutive_absences, int) or isinstance(consecutive_absences, bool) or consecutive_absences < 1:
        raise ValueError("consecutive_absences must be a positive integer")
    pool_size = len(pool_times)
    ranks = set(rank for rank in matched_ranks if rank is not None and 1 <= rank <= pool_size)
    estimate = {"time": None, "rank": None, "athlete": None,
                "matched_pool_starters": len(ranks), "consecutive_absences": consecutive_absences,
                "criterion_met": False, "gap_start_rank": None, "gap_end_rank": None,
                "modeled_roll_down_percent": None,
                "reason": "Pool ends before the absence criterion is met"}
    if initial_slots <= 0:
        estimate["reason"] = "No initial performance-pool slots"
        return estimate
    last_match = None
    absences = 0
    for rank in range(initial_slots + 1, pool_size + 1):
        if rank in ranks:
            last_match = rank
            absences = 0
            continue
        absences += 1
        if absences == consecutive_absences:
            return {**estimate, "criterion_met": True,
                    "gap_start_rank": rank - consecutive_absences + 1, "gap_end_rank": rank,
                    "rank": last_match,
                    "time": math.floor(pool_times[last_match - 1]) if last_match is not None else None,
                    "modeled_roll_down_percent": round(100 * (last_match - initial_slots) / last_match, 2)
                        if last_match is not None and initial_slots > 0 else None,
                    "reason": None if last_match is not None else
                        "Strict allocation was the last supported boundary; no post-allocation match before the absence criterion"}
    return estimate


def build_kona_trace(kona_frame, calendar, events, read_results, event_names, year="2026", historical_targets=None,
                     ranking_cycle=None):
    ranking_cycle = str(ranking_cycle or year)
    starters = []
    identities = defaultdict(list)
    kona_rows = kona_frame.dropna(how="all").to_dict("records")
    identity_counts = Counter(athlete_key(row) for row in kona_rows)
    ambiguous = set()
    for row in kona_rows:
        gender = text_value(row.get("Gender", row.get("gender"))).title()
        division = text_value(row.get("Division")).upper()
        status = text_value(row.get("Finish")).upper()
        if not age_interval(division, year) or not division.startswith({"Male": "M", "Female": "F"}.get(gender, "?")):
            continue
        if status not in {"FIN", "DNF", "DQ", "NC"}:
            continue
        starter = {
            "cycle": str(year),
            "bib": text_value(row.get("Bib")), "name": text_value(row.get("Name")),
            "country": text_value(row.get("Country")), "gender": gender,
            "division": division, "status": status,
            "venue": text_value(row.get("Venue")) or "Kona",
            "kona_time": seconds_value(row.get("Overall Time")), "matches": [],
        }
        starters.append(starter)
        key = athlete_key(row)
        if key and identity_counts[key] == 1:
            identities[key].append(starter)
        elif key:
            ambiguous.add(key)

    name_to_event = {name: event_id for event_id, name in event_names.items()}
    covered, missing, pools = [], [], []
    for race in calendar:
        if str(race["qualification_cycle"]) != str(year):
            continue
        event_id = name_to_event.get(race["race_name"])
        race_year = str(race["event_year"])
        event = events.get(event_id, {})
        info = {
            "event_id": event_id, "name": event.get("name", race["race_name"]),
            "year": race_year, "date": race.get("race_date", ""),
            "source_url": race.get("qualification_url") or race.get("source_url", ""),
        }
        if event.get("group") != "im" or not event.get("qualifying", True) or race_year not in event.get("years", {}):
            missing.append(info)
            continue
        raw = read_results(event["years"][race_year])
        total_slots = race.get("total_qualifiers")
        if total_slots is None:
            missing.append({**info, "reason": "No cycle-specific slot allocation"})
            continue
        raw_rows = raw.to_dict("index")
        legacy = ranking_cycle not in qualification_full.STANDARDS
        cohorts = []
        if legacy:
            targets = (historical_targets or {}).get((event_id, race_year), [])
            for target in targets:
                source = target.get("source", {})
                allocation_cycle = source.get("allocation_cycle")
                if target.get("slot_scope") != "age group" or source.get("total") != total_slots:
                    continue
                if allocation_cycle and str(allocation_cycle) != str(year):
                    continue
                if source.get("cycles") and str(year) not in source["cycles"]:
                    continue
                division = target["division"]
                ranked_rows = sorted(
                    (seconds_value(row.get("Overall Time")), row_id)
                    for row_id, row in raw_rows.items()
                    if text_value(row.get("Division")).upper() == division
                    and text_value(row.get("Gender", row.get("gender"))).title() == target["gender"]
                    and text_value(row.get("Finish")).upper() == "FIN"
                    and seconds_value(row.get("Overall Time")) is not None
                    and seconds_value(row.get("Overall Time")) > 0
                )
                slots = target["slots"]
                times = [time for time, _ in ranked_rows]
                cohorts.append({
                    "gender": target["gender"], "division": division, "slot_scope": "age group",
                    "allocation_method": target["method"], "automatic_slots": 0, "pool_slots": slots,
                    "pool_times": times, "row_ids": [row_id for _, row_id in ranked_rows],
                    "strict_cutoff": times[slots - 1] if 0 < slots <= len(times) else None,
                })
            automatic = set()
        else:
            result = qualification_full.process_dataframe(race_year, raw.copy(), total_slots=total_slots, cycle=ranking_cycle)
            if result is not None:
                for gender in ("male", "female"):
                    cohorts.append({
                        "gender": gender.title(), "division": None, "slot_scope": "gender",
                        "automatic_slots": result[f"{gender}_auto"], "pool_slots": result[f"{gender}_slots"],
                        "pool_times": [adjusted for _, adjusted in result["pools"][gender]],
                        "row_ids": result["pool_row_ids"][gender],
                        "strict_cutoff": math.floor(result[f"{gender}_cut_td"].total_seconds())
                            if result[f"{gender}_cut_td"] is not None else None,
                    })
            automatic = set(result["automatic_row_ids"]) if result is not None else set()
        if not cohorts:
            missing.append({**info, "reason": "No cycle-compatible age-group allocation" if legacy else "No eligible finishers"})
            continue
        covered.append(info)
        counts = Counter(athlete_key(row) for row in raw_rows.values())
        ranked = {}
        for cohort in cohorts:
            for rank, (row_id, adjusted) in enumerate(zip(cohort["row_ids"], cohort["pool_times"]), 1):
                ranked[row_id] = {"pool_rank": rank, "age_graded": math.floor(adjusted), "slots": cohort["pool_slots"]}
        race_matches = []
        for row_id, row in raw_rows.items():
            if text_value(row.get("Finish")).upper() != "FIN":
                continue
            key = athlete_key(row)
            if counts[key] != 1:
                if key in identities:
                    ambiguous.add(key)
                continue
            candidates = identities.get(key, [])
            if len(candidates) != 1:
                continue
            starter = candidates[0]
            division = text_value(row.get("Division")).upper()
            if not division.startswith("M" if starter["gender"] == "Male" else "F"):
                continue
            if not compatible_age(division, race_year, starter["division"], year):
                continue
            finish = seconds_value(row.get("Overall Time"))
            if finish is None:
                continue
            pool_entry = ranked.get(row_id, {})
            pool_rank = pool_entry.get("pool_rank")
            gender = starter["gender"].lower()
            entry = {
                **info, "division": division, "finish_time": finish,
                "pool_rank": pool_rank, "age_graded": pool_entry.get("age_graded"),
                "initial_slot": "Automatic winner" if row_id in automatic else
                    ("Strict age-group slot" if legacy else "Strict pool slot") if pool_rank is not None and pool_rank <= pool_entry["slots"] else
                    "Outside strict allocation" if pool_rank is not None else "Unranked",
            }
            starter["matches"].append(entry)
            race_matches.append((starter, entry))
        for cohort in cohorts:
            gender = cohort["gender"]
            reported = REPORTED_POOL_CUTOFFS.get((str(year), event_id, race_year, gender), {}) \
                if not legacy and ranking_cycle == str(year) else {}
            pools.append({
                **info, **{key: value for key, value in cohort.items() if key != "row_ids"},
                "kona_cycle": str(year), "ranking_cycle": ranking_cycle,
                "total_slots": total_slots, "pool_size": len(cohort["pool_times"]),
                "reported_cutoff": reported.get("reported_cutoff"),
                "reported_cutoff_precision": reported.get("reported_cutoff_precision"),
                "reported_cutoff_source": reported.get("reported_cutoff_source"),
                "reported_cutoff_url": reported.get("reported_cutoff_url"),
                "reported_cutoff_athlete": reported.get("reported_cutoff_athlete"),
                "race_matches": [(starter, entry) for starter, entry in race_matches
                                 if starter["gender"] == gender and (not legacy or entry["division"] == cohort["division"])],
            })

    summaries = {"single": [], "all": []}
    for mode, rows in summaries.items():
        for pool in pools:
            matches = [(starter, entry) for starter, entry in pool["race_matches"] if mode == "all" or len(starter["matches"]) == 1]
            ranked_matches = [(starter, entry) for starter, entry in matches if entry["pool_rank"] is not None]
            deepest = max(ranked_matches, key=lambda item: item[1]["pool_rank"], default=None)
            rows.append({
                **{key: value for key, value in pool.items() if key not in {"race_matches", "pool_times"}},
                "cutoff_estimate": estimate_pool_cutoff(
                    pool["pool_times"], [entry["pool_rank"] for _, entry in ranked_matches], pool["pool_slots"]),
                "matched_starters": len(matches), "matched_pool_starters": len(ranked_matches),
                "deepest_rank": None, "observed_cutoff": None, "deepest_name": None,
                "estimated_skipped_slots": None,
                "candidate_deepest_rank": deepest[1]["pool_rank"] if deepest else None,
                "candidate_cutoff": deepest[1]["age_graded"] if deepest else None,
                "candidate_deepest_name": deepest[0]["name"] if deepest else None,
                "candidate_skipped_slots": max(0, deepest[1]["pool_rank"] - pool["pool_slots"])
                    if deepest and pool["pool_slots"] > 0 else None,
            })
            if mode == "all":
                rows[-1]["manual_pool_times"] = pool["pool_times"]
    for all_row, single_row, pool in zip(summaries["all"], summaries["single"], pools):
        estimate = all_row["cutoff_estimate"].copy()
        single = single_row["cutoff_estimate"]
        estimate["single_match_time"] = single["time"]
        estimate["single_match_starters"] = single["matched_pool_starters"]
        estimate["sensitive"] = False
        if estimate["time"] is not None and single["time"] is not None:
            estimate["sensitive"] = (estimate["high_rank"] < single["low_rank"] or
                                     single["high_rank"] < estimate["low_rank"])
            for bound, operation in (("low", min), ("high", max)):
                estimate[f"{bound}_rank"] = operation(
                    estimate[f"{bound}_rank"], single[f"{bound}_rank"], estimate["rank"], single["rank"])
                estimate[f"{bound}_time"] = operation(
                    estimate[f"{bound}_time"], single[f"{bound}_time"], estimate["time"], single["time"])
        all_row["cutoff_estimate"] = single_row["cutoff_estimate"] = estimate
        scan = scan_pool_cutoff(pool["pool_times"],
                               [entry["pool_rank"] for _, entry in pool["race_matches"]], pool["pool_slots"],
                               consecutive_absences=3 if pool["slot_scope"] == "age group" else 15)
        scan["athlete"] = next((starter["name"] for starter, entry in pool["race_matches"]
                                if scan["rank"] is not None and entry["pool_rank"] == scan["rank"]), None)
        all_row["cutoff_scan"] = single_row["cutoff_scan"] = scan
    return {
        "year": str(year), "starters": starters, "summaries": summaries,
        "venues": {
            gender: sorted({starter["venue"] for starter in starters if starter["gender"] == gender})
            for gender in ("Male", "Female")
        },
        "standard_cycle": ranking_cycle,
        "standards": {division: ratio for gender_standards in qualification_full.STANDARDS.get(ranking_cycle, ())
                  for division, ratio in gender_standards.items()},
        "slot_scope": "gender" if ranking_cycle in qualification_full.STANDARDS else "age group",
        "covered_races": covered, "missing_races": missing,
        "matched_starters": sum(bool(starter["matches"]) for starter in starters),
        "multiple_candidates": sum(len(starter["matches"]) > 1 for starter in starters),
        "ambiguous_identities": len(ambiguous),
    }