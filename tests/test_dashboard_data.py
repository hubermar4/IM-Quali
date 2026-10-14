import math
import sys
import unittest
import warnings
from collections import defaultdict
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

import build_dashboard


class DashboardDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            cls.datasets = build_dashboard.load_dashboard_data()

    def test_current_rules_conserve_all_slots(self):
        for event_id, dataset in self.datasets.items():
            allocation = dataset["qualification_slots"]
            expected = (
                allocation["male"] + allocation["female"]
                if isinstance(allocation, dict)
                else allocation
            )
            for summary in dataset["qualification"]["summaries"]:
                actual = sum(
                    summary[key]
                    for key in ("male_auto", "female_auto", "male_perf", "female_perf")
                )
                self.assertEqual(
                    actual,
                    expected,
                    f"{event_id} {summary['year']}",
                )

    def test_historical_rules_reconcile_with_source_slots(self):
        for event_id, dataset in self.datasets.items():
            by_year = defaultdict(list)
            for row in dataset["historical_qualification"]["targets"]:
                by_year[row["year"]].append(row)
            for year, rows in by_year.items():
                source_total = rows[0]["source"]["total"]
                if source_total is None:
                    continue
                if rows[0]["slot_scope"] == "age group":
                    actual = sum(row["slots"] for row in rows)
                    if rows[0]["method"].startswith("Official"):
                        # Slots of age groups without a finisher cannot be flagged.
                        self.assertLessEqual(actual, source_total, f"{event_id} {year}")
                        self.assertGreaterEqual(actual, 0.9 * source_total, f"{event_id} {year}")
                        continue
                else:
                    actual = sum(
                        next(row["slots"] for row in rows if row["gender"] == gender)
                        for gender in ("Male", "Female")
                    )
                self.assertLessEqual(
                    abs(actual - source_total),
                    1,
                    f"{event_id} {year}: {actual} vs {source_total}",
                )

    def test_performance_pool_has_enough_ranked_finishers(self):
        for event_id, dataset in self.datasets.items():
            pools = dataset["qualification"]["pools"]
            for summary in dataset["qualification"]["summaries"]:
                year_pool = pools.get(summary["year"])
                if not year_pool:
                    continue
                for gender in ("male", "female"):
                    self.assertGreaterEqual(
                        len(year_pool[gender]),
                        summary[f"{gender}_perf"],
                        f"{event_id} {summary['year']} {gender}",
                    )

    def test_performance_pool_model_reproduces_official_qualifiers(self):
        checked = set()
        for event_id, dataset in self.datasets.items():
            for row in dataset["historical_qualification"]["targets"]:
                check = row.get("official_check")
                if row["slot_scope"] != "gender" or not check or row["official_qualifiers"] is None:
                    continue
                label = f"{event_id} {row['year']} {row['gender']}"
                self.assertEqual(check["matched"], check["official"], label)
                self.assertEqual(check["predicted"], check["official"], label)
                checked.add(label)
        self.assertGreaterEqual(len(checked), 24)

    def test_legacy_official_allocation_equals_flag_counts(self):
        for event_id, dataset in self.datasets.items():
            for row in dataset["historical_qualification"]["targets"]:
                if row["method"].startswith("Official"):
                    self.assertEqual(
                        row["slots"], row["official_qualifiers"],
                        f"{event_id} {row['year']} {row['division']}",
                    )

    def test_split_race_days_are_combined(self):
        kona_2022 = next(
            row for row in self.datasets["im_kona"]["statistics"] if row["year"] == "2022"
        )
        self.assertGreater(kona_2022["female_finishers"], 1000)
        self.assertGreater(kona_2022["male_finishers"], 2000)

    def test_world_championship_has_no_qualification_estimate(self):
        kona = self.datasets["im_kona"]
        self.assertFalse(kona["qualifying"])
        self.assertEqual(kona["qualification"]["summaries"], [])
        self.assertEqual(kona["historical_qualification"]["targets"], [])

    def test_course_factors_cover_every_regular_race_year(self):
        for event_id, dataset in self.datasets.items():
            record_years = {row["year"] for row in dataset["records"]}
            expected = record_years - set(dataset["modified_courses"])
            self.assertEqual(set(dataset["course_factors"]), expected, event_id)
            for year, entry in dataset["course_factors"].items():
                label = f"{event_id} {year}"
                for split in ("swim", "bike", "run", "overall"):
                    self.assertTrue(0.8 < entry[split] < 1.25, f"{label} {split}")
                self.assertGreaterEqual(entry["repeat_athletes"], 150, label)

    def test_course_factors_average_one_over_qualifying_race_years(self):
        for group in ("im", "703"):
            logs = [
                math.log(entry["overall"])
                for dataset in self.datasets.values()
                if dataset["group"] == group and dataset["qualifying"]
                for entry in dataset["course_factors"].values()
            ]
            self.assertAlmostEqual(sum(logs) / len(logs), 0.0, places=3)

    def test_hilly_bike_course_is_slower_than_flat_one(self):
        def bike(event_id):
            return self.datasets[event_id]["course_model"]["course"]["bike"]

        self.assertGreater(bike("im_france"), bike("im_austria"))
        self.assertGreater(bike("im_austria"), bike("im_hamburg"))

    def test_course_model_exports_fit_and_age_standards(self):
        for event_id in ("im_austria", "im_703_zellamsee"):
            model = self.datasets[event_id]["course_model"]
            for split in ("swim", "bike", "run", "overall"):
                fit = model["fit"][split]
                self.assertGreater(fit["records"], fit["athletes"], event_id)
                self.assertLess(fit["trimmed"], 0.05 * fit["records"], event_id)
                self.assertTrue(0 < fit["residual_sd"] < fit["trim_limit"], event_id)
            standards = model["standards"]
            self.assertEqual(standards["M40-44"] > standards["M50-54"], True, event_id)
            self.assertTrue(all(0 < ratio <= 1 for ratio in standards.values()), event_id)

    def test_course_model_covers_full_distance_races(self):
        seasons = self.datasets["im_austria"]["course_model"]["season"]
        years = {
            year
            for dataset in self.datasets.values()
            if dataset["group"] == "im"
            for year in dataset["course_factors"]
        }
        self.assertEqual(set(seasons), years)
        for event_id, dataset in self.datasets.items():
            model = dataset["course_model"]
            self.assertTrue(0.97 < model["returning"]["overall"] < 1.01, event_id)
            if dataset["group"] == "im":
                self.assertTrue(0.85 < model["course"]["overall"] < 1.15, event_id)
            else:
                self.assertIsNone(model["course"], event_id)

    def test_historical_standards_follow_the_qualifying_cycle(self):
        cycles = {
            row["year"]: row["standard_cycle"]
            for row in self.datasets["im_703_zellamsee"]["historical_qualification"]["targets"]
            if row["slot_scope"] == "gender"
        }
        self.assertEqual(cycles, {"2025": "2026", "2026": "2027"})


if __name__ == "__main__":
    unittest.main()