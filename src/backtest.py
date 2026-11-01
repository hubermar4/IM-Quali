"""Historical backtest of the former time-multiplier Race Finder model.

Three checks, each labelled with its objective (see dual-objectives.instructions.md):
    cutoffs      A  strict vs time-multiplier cut-off against scan estimates, leave-one-cycle-out
  athletes     -  leave-one-race-out prediction error for repeat athletes (model shared by A and B)
  reliability  A  chance vs outcome against the gender-pool strict / calibrated standard
               B  chance vs outcome against the historical age-group cut-off
Repeat athletes are not representative of all starters and only finishers are
scored, so DNF risk is not part of these results. These historical models do not
validate or calibrate the current rank-factor scenario.
"""
import math
from collections import defaultdict
from statistics import median

import numpy as np

import qualification_full
from course_difficulty import repeat_athlete_records

BINS = 10


def phi(value):
    return 0.5 * (1 + math.erf(value / math.sqrt(2)))


def _factor_by_cycle_loo(rows):
    """Median scan-estimate/strict ratio per gender with each cycle left out."""
    by_gender = defaultdict(list)
    for row in rows:
        by_gender[row["gender"]].append(row)
    factors = {}
    for gender, entries in by_gender.items():
        for cycle in {entry["kona_cycle"] for entry in entries}:
            others = [e["ratio"] for e in entries if e["kona_cycle"] != cycle]
            factors[(gender, cycle)] = median(others) if others else None
    return factors


def _scan_rows(traces):
    rows, seen = [], set()
    for cycle, trace in traces.items():
        for row in trace.get("counterfactual_summaries", []):
            key = (row["event_id"], row["year"], row["gender"], row.get("division"))
            scan = row.get("cutoff_scan") or {}
            if (row.get("slot_scope") != "gender" or not row.get("strict_cutoff") or key in seen):
                continue
            seen.add(key)
            rows.append({
                "event_id": row["event_id"], "year": row["year"], "gender": row["gender"],
                "kona_cycle": str(cycle), "strict": row["strict_cutoff"],
                "observed": scan["time"] if scan.get("criterion_met") and scan.get("time") else None,
                "reported": row.get("reported_cutoff"),
            })
    for row in rows:
        row["ratio"] = row["observed"] / row["strict"] if row["observed"] else None
    return rows


def cutoff_backtest(traces):
    rows = _scan_rows(traces)
    usable = [row for row in rows if row["observed"]]
    factors = _factor_by_cycle_loo(usable)
    result = {"objective": "A", "genders": {}}
    for gender in ("Male", "Female"):
        entries = [row for row in usable if row["gender"] == gender]
        if not entries:
            continue
        strict_err = [row["strict"] / row["observed"] - 1 for row in entries]
        calibrated_err = [
            row["strict"] * factors[(gender, row["kona_cycle"])] / row["observed"] - 1
            for row in entries if factors.get((gender, row["kona_cycle"]))
        ]
        reported = [
            (row["strict"], row["reported"]) for row in rows
            if row["gender"] == gender and row["reported"]
        ]
        reported_ratio = [reported_cutoff / strict for strict, reported_cutoff in reported]
        result["genders"][gender.lower()] = {
            "n": len(entries),
            "strict": {"bias": float(np.mean(strict_err)), "mae": float(np.mean(np.abs(strict_err)))},
            "calibrated": {"bias": float(np.mean(calibrated_err)), "mae": float(np.mean(np.abs(calibrated_err)))},
            "reported_n": len(reported_ratio),
            "reported_median_ratio": float(median(reported_ratio)) if reported_ratio else None,
        }
    return result, rows, factors


def _bins(pairs):
    """Reliability table: predicted chance bucket vs observed share."""
    if not pairs:
        return {"n": 0, "brier": None, "baseline_brier": None, "base_rate": None, "bins": []}
    probs = np.array([p for p, _ in pairs])
    outcomes = np.array([y for _, y in pairs], dtype=float)
    base = outcomes.mean()
    table = []
    for index in range(BINS):
        low, high = index / BINS, (index + 1) / BINS
        mask = (probs >= low) & ((probs < high) if index < BINS - 1 else (probs <= high))
        if mask.any():
            table.append({
                "low": low, "high": high, "n": int(mask.sum()),
                "predicted": float(probs[mask].mean()), "observed": float(outcomes[mask].mean()),
            })
    return {
        "n": len(pairs), "base_rate": float(base),
        "brier": float(np.mean((probs - outcomes) ** 2)),
        "baseline_brier": float(np.mean((base - outcomes) ** 2)),
        "bins": table,
    }


def athlete_backtest(frame, factors, fit, scan_rows, scan_factors, historical_targets):
    """Leave-one-race-out predictions for athletes with two or more race-years (distance group IM)."""
    records = repeat_athlete_records(frame)
    ratios = [qualification_full.get_ratio(g, d) for g, d in zip(records["gender"], records["division"])]
    records = records.assign(ratio=ratios)
    records = records[records["ratio"].notna() & records["overall"].gt(0)]
    returning_factor = fit["overall"]["returning"]
    log_returning = math.log(returning_factor)
    sigma = fit["overall"]["residual_sd"]

    prepared = []
    for key, group in records.groupby("key"):
        items = []
        for row in group.itertuples():
            event_id, year = row.race_year.split(":")
            factor = (factors.get(event_id, {}).get(year) or {}).get("overall")
            if not factor:
                continue
            items.append({
                "event_id": event_id, "year": year, "gender": row.gender, "division": row.division,
                "raw": float(row.overall), "adjusted": float(row.overall * row.ratio),
                "ratio": float(row.ratio), "log_factor": math.log(factor), "returning": bool(row.returning),
            })
        if len(items) >= 2:
            prepared.append(items)

    residuals, by_event, predictions = [], defaultdict(list), []
    for items in prepared:
        levels = [
            math.log(item["adjusted"]) - item["log_factor"] - item["returning"] * log_returning
            for item in items
        ]
        for index, item in enumerate(items):
            others = levels[:index] + levels[index + 1:]
            level = sum(others) / len(others)
            predicted = level + item["log_factor"] + item["returning"] * log_returning
            residual = math.log(item["adjusted"]) - predicted
            residuals.append(residual)
            by_event[item["event_id"]].append(residual)
            predictions.append((item, predicted, len(others)))

    residual_array = np.array(residuals)
    z = np.array([
        residual / (sigma * math.sqrt(1 + 1 / used))
        for residual, (_, _, used) in zip(residuals, predictions)
    ])
    summary = {
        "z_sd": float(z.std()),
        "n": len(residuals),
        "athletes": len(prepared),
        "model_sigma": sigma,
        "residual_sd": float(residual_array.std()),
        "residual_robust_sd": float(1.4826 * np.median(np.abs(residual_array - np.median(residual_array)))),
        "bias": float(residual_array.mean()),
        "within_one_sigma": float(np.mean(np.abs(residual_array) <= sigma)),
        "by_event": {
            event_id: {"n": len(values), "bias": float(np.mean(values)), "sd": float(np.std(values))}
            for event_id, values in sorted(by_event.items()) if len(values) >= 20
        },
    }

    scan_lookup = {(row["event_id"], row["year"], row["gender"]): row for row in scan_rows}
    targets = {
        (target["event_id"], target["year"], target["gender"], target["division"]): target
        for target in historical_targets if target.get("cutoff")
    }

    def score(scale):
        pairs = {"A_strict": [], "A_calibrated": [], "B_age_group": []}
        for item, predicted, used in predictions:
            sigma_eff = sigma * scale * math.sqrt(1 + 1 / used)
            row = scan_lookup.get((item["event_id"], item["year"], item["gender"]))
            if row:
                calibrated = row["strict"] * (scan_factors.get((item["gender"], row["kona_cycle"])) or 1)
                for name, standard in (("A_strict", row["strict"]), ("A_calibrated", calibrated)):
                    pairs[name].append((phi((math.log(standard) - predicted) / sigma_eff), item["adjusted"] <= standard))
            target = targets.get((item["event_id"], item["year"], item["gender"], item["division"]))
            if target:
                raw_predicted = predicted - math.log(item["ratio"])
                pairs["B_age_group"].append(
                    (phi((math.log(target["cutoff"]) - raw_predicted) / sigma_eff), item["raw"] <= target["cutoff"])
                )
        return pairs

    scored = score(1.0)
    reliability = {
        name: {"objective": objective, **_bins(scored[name])}
        for name, objective in (("A_strict", "A"), ("A_calibrated", "A"), ("B_age_group", "B"))
    }
    return summary, reliability


def run_backtest(frames_by_group, datasets, models, traces):
    """Assemble the dashboard payload; needs course factors already attached to the datasets."""
    if "im" not in frames_by_group:
        return None
    frame, _ = frames_by_group["im"]
    factors = {event_id: dataset["course_factors"] for event_id, dataset in datasets.items() if dataset["group"] == "im"}
    targets = [
        {**target, "event_id": event_id}
        for event_id, dataset in datasets.items() if dataset["group"] == "im"
        for target in dataset["historical_qualification"]["targets"]
        if target.get("slot_scope") == "age group"
    ]
    cutoffs, scan_rows, scan_factors = cutoff_backtest(traces)
    athletes, reliability = athlete_backtest(frame, factors, models["im"]["fit"], scan_rows, scan_factors, targets)
    return {"cutoffs": cutoffs, "athletes": athletes, "reliability": reliability}
