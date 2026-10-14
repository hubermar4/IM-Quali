import sys
import unittest
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

import gpx_course_model as model


class GpxCourseModelTests(unittest.TestCase):
    def test_terrain_power_targets(self):
        rider = model.Rider()
        self.assertEqual(model.target_power(0.01, rider), 240)
        self.assertEqual(model.target_power(0, rider), 200)
        self.assertEqual(model.target_power(-0.01, rider), 150)

    def test_flat_route_has_unit_difficulty(self):
        longitude_step = 1000 / 111195
        points = [
            model.TrackPoint(0, index * longitude_step, 0)
            for index in range(5)
        ]
        result = model.simulate(points, model.Rider(), 25, 100)
        self.assertAlmostEqual(result["course_difficulty_factor"], 1, places=4)
        self.assertEqual(result["elevation_gain_m"], 0)


if __name__ == "__main__":
    unittest.main()