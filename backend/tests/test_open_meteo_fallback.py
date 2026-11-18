from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from pipeline.weather.open_meteo_fallback import _open_meteo_records


class OpenMeteoFallbackTests(unittest.TestCase):
    def test_forecast_records_are_limited_to_requested_12_hour_window(self):
        payload = {
            "hourly": {
                "time": [
                    "2026-11-18T23:00",
                    "2026-11-19T00:00",
                    "2026-11-19T01:00",
                    "2026-11-19T13:00",
                    "2026-11-19T14:00",
                ],
                "temperature_2m": [19, 20, 21, 24, 25],
                "relative_humidity_2m": [80, 78, 76, 60, 58],
                "wind_speed_10m": [4, 5, 6, 7, 8],
                "wind_direction_10m": [90, 100, 110, 180, 190],
                "wind_gusts_10m": [6, 7, 8, 10, 11],
            }
        }

        records = _open_meteo_records(
            payload,
            pd.Timestamp("2026-11-19T00:00:00Z"),
            "Open-Meteo forecast archive",
        )

        self.assertEqual([item["hour"] for item in records], [0, 1, 12])
        self.assertEqual(records[0]["temp_c"], 20.0)
        self.assertEqual(records[0]["wind_speed_kmh"], 5.0)
        self.assertEqual(records[0]["max_wind_speed_kmh"], 7.0)
        self.assertEqual(records[0]["source"], "Open-Meteo forecast archive")


if __name__ == "__main__":
    unittest.main()
