import unittest
from unittest.mock import patch

from services.weather_service import build_mock_forecast, build_mock_weather_by_city, fetch_realtime_weather_by_adcode


class FakeResponse:
    def __init__(self, body: str) -> None:
        self.body = body.encode("utf-8")

    def read(self) -> bytes:
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class WeatherServiceTests(unittest.TestCase):
    def test_build_mock_weather_is_deterministic_for_same_location(self) -> None:
        state_one = build_mock_weather_by_city("陕西", "西安", "雁塔")
        state_two = build_mock_weather_by_city("陕西", "西安", "雁塔")
        self.assertEqual(state_one["weather"], state_two["weather"])
        self.assertEqual(state_one["temp"], state_two["temp"])
        self.assertEqual(state_one["wind"], state_two["wind"])

    def test_build_mock_forecast_returns_three_days(self) -> None:
        forecast = build_mock_forecast(build_mock_weather_by_city("陕西", "西安", "雁塔"))
        self.assertEqual(len(forecast), 3)
        self.assertIn("daytemp", forecast[0])
        self.assertIn("week_label", forecast[0])

    def test_fetch_realtime_weather_prefers_selected_city_for_district_query(self) -> None:
        payload = """
        {
          "status": "1",
          "lives": [
            {
              "province": "陕西",
              "city": "商南县",
              "weather": "阴",
              "temperature": "18",
              "humidity": "78",
              "winddirection": "东南",
              "windpower": "≤3",
              "reporttime": "2026-04-13 10:00:00"
            }
          ]
        }
        """
        if hasattr(fetch_realtime_weather_by_adcode, "clear"):
            fetch_realtime_weather_by_adcode.clear()

        with patch("services.weather_service._get_amap_key", return_value="fake-key"):
            with patch("services.weather_service.urlopen", return_value=FakeResponse(payload)):
                state = fetch_realtime_weather_by_adcode("611023", "陕西", "商洛市", "商南县")

        self.assertIsNotNone(state)
        self.assertEqual(state["province"], "陕西")
        self.assertEqual(state["city"], "商洛市")
        self.assertEqual(state["district"], "商南县")
