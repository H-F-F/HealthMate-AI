import unittest
from pathlib import Path
import shutil
import uuid

from services.profile_service import build_profile_payload, load_user_profile, save_user_profile, user_profile_path


class ProfileServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path("tests/.tmp") / f"profile-{uuid.uuid4().hex}"
        self.user_data_dir = self.temp_dir / "profiles"

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_and_load_user_profile(self) -> None:
        saved = save_user_profile(
            self.user_data_dir,
            "alice",
            weight_plan={"current": 70},
            weather_state={"city": "西安"},
            diet_log={"breakfast": "燕麦"},
            daily_metrics={"steps_done": 8000},
        )
        self.assertTrue(saved)
        self.assertTrue(user_profile_path(self.user_data_dir, "alice").exists())

        loaded = load_user_profile(self.user_data_dir, "alice")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["weather_state"]["city"], "西安")
        self.assertEqual(loaded["daily_metrics"]["steps_done"], 8000)

    def test_build_profile_payload_contains_all_sections(self) -> None:
        payload = build_profile_payload(
            weight_plan={"current": 60},
            weather_state={"city": "上海"},
            diet_log={"breakfast": "酸奶"},
            daily_metrics={"sleep_hours": 8.0},
        )
        self.assertEqual(set(payload.keys()), {"weight_plan", "weather_state", "diet_log", "daily_metrics"})

    def test_load_user_profile_returns_none_when_missing(self) -> None:
        self.assertIsNone(load_user_profile(self.user_data_dir, "missing"))
