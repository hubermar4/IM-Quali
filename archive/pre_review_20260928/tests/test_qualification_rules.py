import sys
import unittest
import warnings
from pathlib import Path

import pandas as pd


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

import qualification_full


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


if __name__ == "__main__":
    unittest.main()