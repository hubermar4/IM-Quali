import json
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

    def test_dashboard_html_loads_both_data_files_before_app(self):
        html = build_dashboard.build_html({})
        ironman = html.index('<script src="dashboard_data_im.js"></script>')
        ironman_703 = html.index('<script src="dashboard_data_703.js"></script>')
        app = html.index("<script>\n")
        self.assertLess(ironman, ironman_703)
        self.assertLess(ironman_703, app)

    def test_dashboard_payloads_are_split_by_distance_and_under_file_limit(self):
        payloads = build_dashboard.build_data_payloads(self.datasets)
        self.assertEqual(set(payloads), {"im", "703"})
        merged = {}
        for group, payload in payloads.items():
            self.assertLess(
                len(payload.encode("utf-8")),
                build_dashboard.MAX_DATA_FILE_SIZE,
            )
            prefix = "Object.assign(window.DASHBOARD_DATA || {}, "
            group_data = json.loads(
                payload[payload.index(prefix) + len(prefix):].strip().rstrip(");")
            )
            self.assertTrue(group_data)
            self.assertTrue(all(dataset["group"] == group for dataset in group_data.values()))
            merged.update({
                event_id: build_dashboard.expand_dataset(dataset)
                for event_id, dataset in group_data.items()
            })
        self.assertEqual(merged, self.datasets)

    def test_compact_payload_stores_records_as_rows_and_references_default_trace(self):
        payloads = build_dashboard.build_data_payloads(self.datasets)
        prefix = "Object.assign(window.DASHBOARD_DATA || {}, "
        payload = payloads["im"]
        group_data = json.loads(payload[payload.index(prefix) + len(prefix):].strip().rstrip(");"))
        for dataset in group_data.values():
            self.assertEqual(dataset["records"]["columns"], list(build_dashboard.RECORD_COLUMNS))
            self.assertTrue(all(len(row) == len(build_dashboard.RECORD_COLUMNS) for row in dataset["records"]["rows"]))
        kona = group_data["im_kona"]
        self.assertNotIn("kona_trace", kona)
        self.assertEqual(kona["kona_trace_ref"], max(kona["kona_traces"], key=int))
        self.assertEqual(kona["kona_trace_cycles"][-1]["year"], kona["kona_trace_ref"])

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

    def test_age_group_top_twenty_threshold_uses_valid_finishers(self):
        stats = self.datasets["im_austria"]["division_stats"]["2017"]["M30-34"]
        self.assertGreater(stats["finishers"], 0)
        self.assertLessEqual(stats["winner"], stats["top_20_percent"])
        self.assertLessEqual(stats["top_20_percent"], stats["median"])

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
                    # Downstream river swims (California, Chattanooga) are about 30% faster.
                    lower = 0.55 if split == "swim" else 0.8
                    self.assertTrue(lower < entry[split] < 1.25, f"{label} {split}")
                # US races and single-edition 70.3 races share few athletes with the other races.
                minimum = 75 if dataset["group"] == "im" else 50
                self.assertGreaterEqual(entry["repeat_athletes"], minimum, label)
        for split in ("t1", "t2"):
            values = [entry[split] for dataset in self.datasets.values()
                      for entry in dataset["course_factors"].values() if split in entry]
            self.assertTrue(values, split)
            self.assertTrue(all(math.isfinite(value) and value > 0 for value in values), split)

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
            for split in ("swim", "t1", "bike", "t2", "run", "overall"):
                fit = model["fit"][split]
                self.assertGreater(fit["records"], 0, event_id)
                if split not in ("t1", "t2"):
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
            if dataset["group"] == "im" or dataset["qualifying"]:
                self.assertTrue(0.85 < model["course"]["overall"] < 1.15, event_id)

    def test_historical_standards_follow_the_qualifying_cycle(self):
        cycles = {
            row["year"]: row["standard_cycle"]
            for row in self.datasets["im_703_zellamsee"]["historical_qualification"]["targets"]
            if row["slot_scope"] == "gender"
        }
        self.assertEqual(cycles, {"2025": "2026", "2026": "2027"})

    def test_counterfactual_winners_are_separate_from_performance_pool_metrics(self):
        winner_matches = []
        for trace in self.datasets["im_kona"].get("kona_traces", {}).values():
            self.assertIn("counterfactual_winners", trace)
            for winner in trace["counterfactual_winners"]:
                for match in winner["matches"]:
                    self.assertEqual(match["initial_slot"], "Automatic winner")
                    self.assertIsNone(match["pool_rank"])
                    summary = next(row for row in trace["counterfactual_summaries"]
                                   if row["event_id"] == match["event_id"] and row["year"] == match["year"]
                                   and row["gender"] == winner["gender"])
                    self.assertEqual(summary["slot_scope"], "gender")
                    plotted_matches = sum(1 for point in summary["ranking_evidence"] if point[2] > 0)
                    self.assertEqual(summary["matched_pool_starters"], plotted_matches)
                    winner_matches.append(match)
        self.assertTrue(winner_matches, "expected at least one matched automatic winner in current-rule re-ranking")

    def test_half_distance_championship_trace_covers_only_its_cycle(self):
        traces = self.datasets["im_kona"]["wc703_traces"]
        venues = {"2022": "St. George", "2023": "Lahti", "2024": "Taupo", "2025": "Marbella", "2026": "Nice"}
        self.assertEqual(set(traces), set(venues))
        for cycle, venue in venues.items():
            self.assertEqual(traces[cycle]["venues"], {"Male": [venue], "Female": [venue]}, cycle)
        trace = traces["2026"]
        covered = {(race["event_id"], race["year"]) for race in trace["covered_races"]}
        # 2026 70.3 races after the Nice championship belong to the 2027 cycle.
        self.assertIn(("im_703_zellamsee", "2025"), covered)
        self.assertIn(("im_703_valencia", "2026"), covered)
        self.assertNotIn(("im_703_krakow", "2026"), covered)
        self.assertNotIn(("im_703_zellamsee", "2026"), covered)
        for objective, rows, cycle in (("historical", trace["summaries"]["all"], "2026"),
                                       ("current", trace["counterfactual_summaries"], "2027")):
            self.assertTrue(rows, objective)
            for row in rows:
                label = f"{objective} {row['event_id']} {row['year']} {row['gender']}"
                self.assertEqual(row["slot_scope"], "gender", label)
                self.assertEqual(row["kona_cycle"], "2026", label)
                self.assertEqual(row["ranking_cycle"], cycle, label)
                historical = next(
                    target for target in self.datasets[row["event_id"]]["historical_qualification"]["targets"]
                    if target["year"] == row["year"] and target["gender"] == row["gender"]
                )
                if objective == "historical":
                    self.assertEqual(row["pool_slots"], historical["performance_slots"], label)
        self.assertEqual(trace["counterfactual_standard_cycle"], "2027")
        # Age-group-allocation cycle: historical rows rank inside the age group, current rows in the gender pool.
        legacy = traces["2025"]
        self.assertIn(("im_703_zellamsee", "2024"), {(race["event_id"], race["year"]) for race in legacy["covered_races"]})
        self.assertTrue(legacy["summaries"]["all"])
        for row in legacy["summaries"]["all"]:
            self.assertEqual(row["slot_scope"], "age group", row["event_id"])
            target = next(t for t in self.datasets[row["event_id"]]["historical_qualification"]["targets"]
                          if t["year"] == row["year"] and t["division"] == row["division"])
            self.assertEqual(row["pool_slots"], target["slots"], f"{row['event_id']} {row['division']}")
        self.assertTrue(all(row["slot_scope"] == "gender" for row in legacy["counterfactual_summaries"]))
        # No published cycle mapping exists for these race-years, so no evidence is inferred.
        self.assertEqual(traces["2022"]["covered_races"], [])
        self.assertEqual(traces["2023"]["covered_races"], [])

    def test_new_race_years_use_their_qualifying_cycle(self):
        expected = {
            ("im_florida", "2025"): "2026", ("im_cozumel", "2025"): "2026", ("im_texas", "2026"): "2026",
            ("im_california", "2026"): "2027", ("im_chattanooga", "2026"): "2027", ("im_italy", "2026"): "2027",
            ("im_703_valencia", "2026"): "2026", ("im_703_kraichgau", "2026"): "2026",
            ("im_703_krakow", "2026"): "2027", ("im_703_porec", "2026"): "2027",
        }
        for (event_id, year), cycle in expected.items():
            rows = [row for row in self.datasets[event_id]["historical_qualification"]["targets"] if row["year"] == year]
            self.assertTrue(rows, f"{event_id} {year}")
            self.assertEqual({row["standard_cycle"] for row in rows}, {cycle}, f"{event_id} {year}")
        self.assertFalse(self.datasets["im_703_nice_wc"]["qualifying"])
        self.assertEqual(self.datasets["im_703_nice_wc"]["historical_qualification"]["targets"], [])


if __name__ == "__main__":
    unittest.main()