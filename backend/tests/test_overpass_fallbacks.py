from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from pipeline.thermal.context import OVERPASS_URLS, _overpass_request


class OverpassFallbackTests(unittest.TestCase):
    def test_current_public_fallbacks_are_configured(self):
        self.assertEqual(OVERPASS_URLS[0], "https://overpass-api.de/api/interpreter")
        self.assertIn(
            "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
            OVERPASS_URLS,
        )
        self.assertIn(
            "https://overpass.private.coffee/api/interpreter",
            OVERPASS_URLS,
        )

    def test_request_retries_next_instance_after_primary_failure(self):
        payload = {"elements": []}
        with patch(
            "pipeline.thermal.context._fetch_json",
            side_effect=[requests.Timeout("primary timed out"), payload],
        ) as fetch:
            result = _overpass_request("[out:json];out;")

        self.assertEqual(result, payload)
        self.assertEqual(fetch.call_count, 2)
        self.assertEqual(fetch.call_args_list[0].args[1], OVERPASS_URLS[0])
        self.assertEqual(fetch.call_args_list[1].args[1], OVERPASS_URLS[1])


if __name__ == "__main__":
    unittest.main()
