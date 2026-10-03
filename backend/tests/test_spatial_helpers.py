from __future__ import annotations

import sys
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from geoalchemy2 import WKTElement, WKBElement
import shapely.wkt
from shapely.geometry import box
from pipeline.spatial.spatial_helpers import safe_to_shape, event_bbox


class SpatialHelperTests(unittest.TestCase):
    def test_safe_to_shape_wkt_element(self):
        elem = WKTElement("POLYGON ((0 0, 10 0, 10 10, 0 10, 0 0))", srid=4326)
        shape = safe_to_shape(elem)
        self.assertEqual(shape.bounds, (0.0, 0.0, 10.0, 10.0))

    def test_safe_to_shape_wkb_element(self):
        b = box(1.0, 2.0, 3.0, 4.0)
        wkb_bytes = shapely.wkb.dumps(b)
        elem = WKBElement(wkb_bytes, srid=4326)
        shape = safe_to_shape(elem)
        self.assertEqual(shape.bounds, (1.0, 2.0, 3.0, 4.0))

    def test_safe_to_shape_wkt_string(self):
        wkt_str = "POLYGON ((5 5, 15 5, 15 15, 5 15, 5 5))"
        shape = safe_to_shape(wkt_str)
        self.assertEqual(shape.bounds, (5.0, 5.0, 15.0, 15.0))

    def test_safe_to_shape_shapely_geom(self):
        b = box(2.0, 3.0, 4.0, 5.0)
        shape = safe_to_shape(b)
        self.assertEqual(shape.bounds, (2.0, 3.0, 4.0, 5.0))

    def test_event_bbox_from_object_and_tuple(self):
        class DummyEvent:
            bbox = WKTElement("POLYGON ((10 20, 30 20, 30 40, 10 40, 10 20))", srid=4326)

        bounds = event_bbox(DummyEvent())
        self.assertEqual(bounds, (10.0, 20.0, 30.0, 40.0))

        raw_tuple = (10.0, 20.0, 30.0, 40.0)
        self.assertEqual(event_bbox(raw_tuple), (10.0, 20.0, 30.0, 40.0))


if __name__ == "__main__":
    unittest.main()
