import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

from course_difficulty import (
    course_and_season_effects,
    estimate_course_factors,
    identity_key,
    repeat_athlete_records,
)


def record(name, race_year, year, division="M40-44", seconds=40000, gender="Male", country="AUT"):
    return {
        "name": name, "gender": gender, "country": country, "division": division,
        "race_year": race_year, "year": year,
        "swim": seconds * 0.1, "bike": seconds * 0.5, "run": seconds * 0.4, "overall": seconds,
    }


def athlete_name(index):
    return f"Athlete {chr(97 + index // 26)}{chr(97 + index % 26)}"


class IdentityTests(unittest.TestCase):
    def test_names_match_across_accents_case_and_order(self):
        self.assertEqual(
            identity_key("Mårten  Bomark", "Male", "SWE"),
            identity_key("BOMARK, Marten", "Male", "SWE"),
        )

    def test_ambiguous_and_inconsistent_identities_are_dropped(self):
        frame = pd.DataFrame([
            record("Anna Berg", "a:2020", 2020),
            record("Anna Berg", "b:2022", 2022),
            record("Same Name", "a:2020", 2020),
            record("Same Name", "a:2020", 2020, seconds=45000),
            record("Same Name", "b:2022", 2022),
            record("Age Jump", "a:2020", 2020, division="M25-29"),
            record("Age Jump", "b:2022", 2022, division="M60-64"),
            record("Only Once", "a:2020", 2020),
        ])
        kept = set(repeat_athlete_records(frame)["name"])
        self.assertEqual(kept, {"Anna Berg"})


class EstimatorTests(unittest.TestCase):
    def synthetic(self, true_log, returning_log=0.0, seed=7):
        generator = np.random.default_rng(seed)
        rows = []
        for athlete in range(600):
            ability = generator.normal(np.log(40000), 0.12)
            races = sorted(generator.choice(list(true_log), size=generator.integers(2, 4), replace=False))
            for appearance, race_year in enumerate(races):
                year = int(race_year.split(":")[1])
                log_time = ability + true_log[race_year] + (returning_log if appearance else 0.0)
                seconds = float(np.exp(log_time + generator.normal(0, 0.02)))
                rows.append(record(athlete_name(athlete), race_year, year, seconds=seconds))
        return pd.DataFrame(rows)

    def test_recovers_known_race_year_factors(self):
        true_log = {"a:2020": 0.0, "b:2021": np.log(1.10), "c:2022": np.log(0.95)}
        frame = self.synthetic(true_log)
        factors, fit = estimate_course_factors(frame, set(true_log))
        mean_log = np.mean(list(true_log.values()))
        for race_year, value in true_log.items():
            self.assertAlmostEqual(factors[race_year]["overall"], np.exp(value - mean_log), delta=0.005)
            self.assertGreater(factors[race_year]["repeat_athletes"], 300)
        self.assertAlmostEqual(fit["overall"]["returning"], 1.0, delta=0.005)
        self.assertEqual(fit["overall"]["athletes"], 600)
        self.assertEqual(fit["overall"]["records"] + fit["overall"]["trimmed"], len(frame))
        self.assertAlmostEqual(fit["overall"]["residual_sd"], 0.02 * np.sqrt(1 - 1 / 2.5), delta=0.004)

    def test_returning_athlete_gain_is_not_booked_to_later_race_years(self):
        true_log = {"a:2020": 0.0, "b:2021": 0.0, "c:2022": 0.0}
        factors, fit = estimate_course_factors(
            self.synthetic(true_log, returning_log=np.log(0.98)), set(true_log)
        )
        self.assertAlmostEqual(fit["overall"]["returning"], 0.98, delta=0.003)
        for race_year in true_log:
            self.assertAlmostEqual(factors[race_year]["overall"], 1.0, delta=0.004)

    def test_age_grading_removes_ageing_between_races(self):
        rows = [
            record(athlete_name(index), race_year, year, division=division, seconds=seconds)
            for index in range(50)
            for race_year, year, division, seconds in (
                ("a:2020", 2020, "M40-44", 40000),
                ("b:2021", 2021, "M45-49", 40000 / 0.9),
            )
        ]
        ratios = {"M40-44": 1.0, "M45-49": 0.9}
        factors, _ = estimate_course_factors(
            pd.DataFrame(rows), {"a:2020", "b:2021"}, lambda gender, division: ratios[division]
        )
        self.assertAlmostEqual(factors["a:2020"]["overall"], 1.0, places=6)
        self.assertAlmostEqual(factors["b:2021"]["overall"], 1.0, places=6)


class CourseSeasonTests(unittest.TestCase):
    def test_separates_course_from_season(self):
        course = {"flat": 0.95, "hilly": 1.08}
        season = {"2020": 1.02, "2021": 0.98}
        factors = {
            f"{event}:{year}": {split: course[event] * season[year] for split in ("swim", "bike", "run", "overall")}
            for event in course
            for year in season
            if (event, year) != ("flat", "2020")
        }
        courses, seasons = course_and_season_effects(factors, set(factors))
        # Season effects average zero over the three observed race-years.
        scale = np.exp(np.mean(np.log([season[label.split(":")[1]] for label in factors])))
        for event, value in course.items():
            self.assertAlmostEqual(courses[event]["overall"], value * scale, places=4)
        for year, value in season.items():
            self.assertAlmostEqual(seasons[year]["bike"], value / scale, places=4)


if __name__ == "__main__":
    unittest.main()
