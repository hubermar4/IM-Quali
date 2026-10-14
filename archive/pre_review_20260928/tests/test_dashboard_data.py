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


if __name__ == "__main__":
    unittest.main()