import math
import sys
import unittest
import warnings
from pathlib import Path

import pandas as pd


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

import qualification_703
import qualification_full
from project_paths import RACE_HISTORY_DIR


class FullDistanceQualificationTests(unittest.TestCase):
    def test_unsupported_divisions_do_not_change_gender_split(self):
        rows = [
            ["Male", "M30-34", "09:00:00", 1, "FIN"],
            ["Female", "F30-34", "10:00:00", 1, "FIN"],
            ["Female", "F35-39", "10:10:00", 2, "FIN"],
            ["Female", "F40-44", "10:20:00", 2, "FIN"],
            ["Male", "MUNKNOWN", "", None, "DNF"],
            ["Male", "MUNKNOWN", "", None, "DNF"],
            ["Male", "MUNKNOWN", "", None, "DNF"],
        ]
        frame = pd.DataFrame(
            rows,
            columns=["Gender", "Division", "Overall Time", "Age Group Rank", "Finish"],
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = qualification_full.process_dataframe(
                "test", frame, total_slots=6
            )
        self.assertEqual(result["male_slots"], 1)
        self.assertEqual(result["female_slots"], 3)
        self.assertEqual(result["male_starters"], 1)
        self.assertEqual(result["female_starters"], 3)
        self.assertEqual(
            result["male_slots"] + result["female_slots"], 4
        )

    def test_automatic_slots_cannot_exceed_total(self):
        frame = pd.DataFrame(
            [
                ["Male", "M30-34", "09:00:00", 1, "FIN"],
                ["Female", "F30-34", "10:00:00", 1, "FIN"],
            ],
            columns=["Gender", "Division", "Overall Time", "Age Group Rank", "Finish"],
        )
        with self.assertRaisesRegex(ValueError, "automatic slots exceed"):
            qualification_full.process_dataframe("test", frame, total_slots=1)

    def test_duplicate_rank_one_uses_one_automatic_slot(self):
        frame = pd.DataFrame(
            [
                ["Male", "M30-34", "09:00:00", 1, "FIN"],
                ["Male", "M30-34", "09:01:00", 1, "FIN"],
                ["Female", "F30-34", "10:00:00", 1, "FIN"],
                ["Female", "F30-34", "10:10:00", 2, "FIN"],
            ],
            columns=["Gender", "Division", "Overall Time", "Age Group Rank", "Finish"],
        )
        result = qualification_full.process_dataframe(
            "test", frame, total_slots=4
        )
        self.assertEqual(result["male_auto"], 1)
        self.assertEqual(result["female_auto"], 1)
        self.assertEqual(result["male_slots"] + result["female_slots"], 2)

    def test_tbd_standard_winner_keeps_automatic_slot(self):
        frame = pd.DataFrame(
            [
                ["Male", "M30-34", "09:00:00", 1, "FIN"],
                ["Female", "F30-34", "10:00:00", 1, "FIN"],
                ["Female", "F80-84", "15:00:00", 1, "FIN"],
            ],
            columns=["Gender", "Division", "Overall Time", "Age Group Rank", "Finish"],
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = qualification_full.process_dataframe(
                "test", frame, total_slots=5
            )
        self.assertEqual(result["female_auto"], 2)
        self.assertEqual(result["female_finishers"], 2)

    def test_gender_split_rounds_half_up(self):
        frame = pd.DataFrame(
            [
                ["Male", "M30-34", "09:00:00", 1, "FIN"],
                ["Male", "M30-34", "09:10:00", 2, "FIN"],
                ["Female", "F30-34", "10:00:00", 1, "FIN"],
                ["Female", "F30-34", "10:10:00", 2, "FIN"],
            ],
            columns=["Gender", "Division", "Overall Time", "Age Group Rank", "Finish"],
        )
        result = qualification_full.process_dataframe("test", frame, total_slots=3)
        self.assertEqual(result["male_slots"], 1)
        self.assertEqual(result["female_slots"], 0)


class OfficialStandardTests(unittest.TestCase):
    """Official age-graded "Qualifier Time" equals floor(finish time x standard)."""

    CASES = (
        (qualification_full, "IM_Kalmar/ironmansweden2025-results.csv", "2026"),
        (qualification_full, "IM_Tallinn/ironmantallinn2026-results.csv", "2027"),
        (qualification_703, "IM_703_ZellAmSee/ironman703zellamsee-kaprun2025-results.csv", "2026"),
        (qualification_703, "IM_703_ZellAmSee/ironman703zellamsee-kaprun2026-results.csv", "2027"),
    )

    def test_standards_reproduce_official_qualifier_times(self):
        for module, relative_path, cycle in self.CASES:
            frame = pd.read_csv(RACE_HISTORY_DIR / relative_path)
            frame = frame[
                frame["Finish"].eq("FIN")
                & frame["Division"].astype(str).str.match(r"^[MF]\d{2}-\d{2}$", na=False)
                & frame["Qualifier Time"].notna()
            ]
            compared = 0
            for gender, division, finish, official in zip(
                frame["Gender"], frame["Division"], frame["Overall Time"], frame["Qualifier Time"]
            ):
                ratio = module.get_ratio(gender, division, cycle)
                if ratio is None:
                    continue
                seconds = module.parse_time(finish).total_seconds()
                expected = module.parse_time(official).total_seconds()
                self.assertEqual(
                    math.floor(round(seconds * ratio, 4)), expected,
                    f"{relative_path} {division} {finish}",
                )
                compared += 1
            self.assertGreater(compared, 1000, relative_path)


if __name__ == "__main__":
    unittest.main()