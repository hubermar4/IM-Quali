"""Race-year course and condition factors from athletes who raced several race-years.

The model is log(time) = athlete ability + race-year effect + returning effect,
fitted by alternating means on athletes matched across race-years. Athlete
ability cancels out, so the race-year effect measures course and race-day
conditions. The returning effect absorbs the gain of athletes on later
appearances (experience, or returning after a bad race), which would otherwise
make later race-years look easier.
"""
import re
import unicodedata

import numpy as np
import pandas as pd


SPLITS = ("swim", "bike", "run", "overall")
AGE_GROUP_PATTERN = r"^[MF](\d{2})-\d{2}$"
TRIM_SCALE = 4.0


def identity_key(name, gender, country):
    ascii_name = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode()
    tokens = sorted(re.sub(r"[^a-z ]", " ", ascii_name.casefold()).split())
    return f"{' '.join(tokens)}|{gender}|{country}" if tokens else None


def repeat_athlete_records(frame):
    """Athletes matched in two or more race-years; ambiguous identities are dropped."""
    frame = frame.copy()
    frame["key"] = [
        identity_key(name, gender, country)
        for name, gender, country in zip(frame["name"], frame["gender"], frame["country"])
    ]
    lower_age = pd.to_numeric(
        frame["division"].str.extract(AGE_GROUP_PATTERN)[0], errors="coerce"
    )
    frame = frame[frame["key"].notna() & lower_age.notna()].copy()
    lower_age = lower_age[frame.index]
    frame["birth_min"] = frame["year"] - lower_age - 4
    frame["birth_max"] = frame["year"] - lower_age

    # Two people with one identity in the same race cannot be told apart elsewhere.
    shared = frame.loc[frame.duplicated(["key", "race_year"], keep=False), "key"]
    frame = frame[~frame["key"].isin(set(shared))]
    by_key = frame.groupby("key").agg(
        birth_min=("birth_min", "max"),
        birth_max=("birth_max", "min"),
        race_years=("race_year", "nunique"),
    )
    keep = by_key.index[(by_key["birth_min"] <= by_key["birth_max"]) & (by_key["race_years"] >= 2)]
    records = frame[frame["key"].isin(set(keep))].sort_values(["key", "year", "race_year"], kind="stable")
    records["returning"] = records.groupby("key").cumcount().gt(0)
    return records.reset_index(drop=True)


def fit_race_year_effects(
    athletes, race_years, log_times, baseline, returning=None, iterations=3000, tolerance=1e-9
):
    """Alternating-means fixed-effects fit; race effects average zero over the baseline.

    Returns race-year effects, the returning-athlete effect relative to an
    athlete's first appearance, and the residuals.
    """
    returning = np.zeros(len(log_times), dtype=bool) if returning is None else np.asarray(returning, dtype=bool)
    fit_returning = returning.any() and not returning.all()
    athlete_counts = np.bincount(athletes)
    race_counts = np.bincount(race_years, minlength=len(baseline))
    race_effect = np.zeros(len(baseline))
    returning_effect = 0.0
    for _ in range(iterations):
        shift = returning_effect * returning
        athlete_effect = np.bincount(athletes, log_times - race_effect[race_years] - shift) / athlete_counts
        sums = np.bincount(race_years, log_times - athlete_effect[athletes] - shift, minlength=len(baseline))
        updated = np.divide(sums, race_counts, out=np.zeros(len(baseline)), where=race_counts > 0)
        updated -= updated[baseline & (race_counts > 0)].mean()
        updated_returning = returning_effect
        if fit_returning:
            partial = log_times - athlete_effect[athletes] - updated[race_years]
            updated_returning = float(partial[returning].mean())
        change = max(np.abs(updated - race_effect).max(), abs(updated_returning - returning_effect))
        race_effect, returning_effect = updated, updated_returning
        if change < tolerance:
            break
    shift = returning_effect * returning
    athlete_effect = np.bincount(athletes, log_times - race_effect[race_years] - shift) / athlete_counts
    residual = log_times - athlete_effect[athletes] - race_effect[race_years] - shift
    return race_effect, returning_effect, residual


def estimate_course_factors(frame, baseline_race_years, age_ratio=None):
    """Multiplicative factor per race-year and split relative to the baseline average.

    ``frame`` needs race_year, year, name, gender, country, division and the
    split columns in seconds. ``age_ratio(gender, division)`` age-grades times
    so that ageing between race-years does not bias later editions. Returns the
    race-year factors and, per split, the returning-athlete factor and fit
    diagnostics (records, athletes, trimmed outliers, trim limit, residual SD).
    """
    records = repeat_athlete_records(frame)
    if age_ratio is not None:
        ratios = pd.Series(
            [age_ratio(gender, division) for gender, division in zip(records["gender"], records["division"])],
            index=records.index,
            dtype="float64",
        )
        records = records[ratios.notna()].copy()
        for split in SPLITS:
            records[split] = records[split] * ratios[records.index]

    factors = {}
    fit = {}
    for split in SPLITS:
        subset = records[records[split] > 0]
        athletes, _ = pd.factorize(subset["key"])
        race_years, labels = pd.factorize(subset["race_year"])
        baseline = np.isin(labels, list(baseline_race_years))
        if not baseline.any():
            raise ValueError("no baseline race-year has repeat athletes")
        log_times = np.log(subset[split].to_numpy(dtype=float))
        returning = subset["returning"].to_numpy()
        effect, _, residual = fit_race_year_effects(athletes, race_years, log_times, baseline, returning)
        scale = 1.4826 * np.median(np.abs(residual))
        trim_limit = max(TRIM_SCALE * scale, 1e-9)
        # Refit without mechanicals, walked marathons and similar outliers.
        kept = np.abs(residual) <= trim_limit
        records_before = len(subset)
        subset = subset[kept]
        athletes, _ = pd.factorize(subset["key"])
        race_years = pd.Categorical(subset["race_year"], categories=labels).codes
        effect, returning_effect, residual = fit_race_year_effects(
            athletes, race_years, log_times[kept], baseline, returning[kept]
        )
        fit[split] = {
            "returning": round(float(np.exp(returning_effect)), 5),
            "records": int(len(subset)),
            "athletes": int(athletes.max() + 1),
            "trimmed": int(records_before - len(subset)),
            "trim_limit": round(float(trim_limit), 5),
            "residual_sd": round(float(residual.std()), 5),
        }
        spread = pd.Series(residual).groupby(race_years).agg(["std", "size"])
        for index, label in enumerate(labels):
            entry = factors.setdefault(label, {"se": {}})
            entry[split] = round(float(np.exp(effect[index])), 5)
            count = spread["size"].get(index, 0)
            entry["se"][split] = (
                round(float(spread["std"][index] / np.sqrt(count)), 5) if count > 1 else None
            )
            if split == "overall":
                entry["repeat_athletes"] = int(count)
    return factors, fit


def course_and_season_effects(factors, baseline_race_years, iterations=1000, tolerance=1e-12):
    """Split race-year factors into a course part per event and a season part per year.

    log factor = course + season + conditions, fitted per split over race-year
    labels "event:year". Season effects average zero over the baseline
    race-years, so a course factor is the typical factor of that course in an
    average season. Needs at least two events sharing seasons to be meaningful.
    """
    labels = list(factors)
    event_codes, events = pd.factorize(pd.Series([label.split(":")[0] for label in labels]))
    season_codes, seasons = pd.factorize(pd.Series([label.split(":")[1] for label in labels]))
    baseline = np.array([label in baseline_race_years for label in labels])
    event_counts = np.bincount(event_codes)
    season_counts = np.bincount(season_codes)
    course = {event: {} for event in events}
    season = {year: {} for year in seasons}
    for split in SPLITS:
        values = np.log([factors[label][split] for label in labels])
        course_effect = np.zeros(len(events))
        season_effect = np.zeros(len(seasons))
        for _ in range(iterations):
            updated_course = np.bincount(event_codes, values - season_effect[season_codes]) / event_counts
            updated_season = np.bincount(season_codes, values - updated_course[event_codes]) / season_counts
            updated_season -= updated_season[season_codes][baseline].mean()
            change = max(
                np.abs(updated_course - course_effect).max(), np.abs(updated_season - season_effect).max()
            )
            course_effect, season_effect = updated_course, updated_season
            if change < tolerance:
                break
        course_effect = np.bincount(event_codes, values - season_effect[season_codes]) / event_counts
        for index, event in enumerate(events):
            course[event][split] = round(float(np.exp(course_effect[index])), 5)
        for index, year in enumerate(seasons):
            season[year][split] = round(float(np.exp(season_effect[index])), 5)
    return course, season
