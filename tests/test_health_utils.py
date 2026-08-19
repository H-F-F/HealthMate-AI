import unittest

from services.health_plans import build_macro_targets, diet_summary
from utils.health_utils import calculate_bmi, get_step_goal, get_water_goal


class HealthUtilsTests(unittest.TestCase):
    def test_calculate_bmi(self) -> None:
        self.assertAlmostEqual(calculate_bmi(70, 175), 22.8571, places=3)
        self.assertAlmostEqual(calculate_bmi(70, 1.75), 22.8571, places=3)

    def test_calculate_bmi_rejects_non_positive_values(self) -> None:
        with self.assertRaises(ValueError):
            calculate_bmi(0, 170)

    def test_get_water_goal_adjusts_by_temperature(self) -> None:
        self.assertEqual(get_water_goal(60, 35), 2300)
        self.assertEqual(get_water_goal(60, 5), 1600)
        self.assertEqual(get_water_goal(20, 20), 1000)

    def test_get_step_goal_by_age(self) -> None:
        self.assertEqual(get_step_goal(16), 10000)
        self.assertEqual(get_step_goal(30), 8000)
        self.assertEqual(get_step_goal(70), 6000)

    def test_diet_summary_counts_completed_meals_only(self) -> None:
        summary = diet_summary(
            {
                "done": {"breakfast": True, "lunch": False, "dinner": True},
                "calories": {"breakfast": 300, "lunch": 600, "dinner": 500},
                "macros": {"protein": 80, "carbs": 150, "fat": 35},
            }
        )
        self.assertEqual(summary["total_calories"], 800)
        self.assertEqual(summary["protein"], 80)

    def test_build_macro_targets(self) -> None:
        targets = build_macro_targets(65, 1500)
        self.assertGreaterEqual(targets["protein"], 100)
        self.assertGreaterEqual(targets["carbs"], 80)
        self.assertGreaterEqual(targets["fat"], 35)
