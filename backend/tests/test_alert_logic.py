import unittest

from app.utils.geolocation import haversine_distance, is_within_radius

# Reference: Delhi (28.6139, 77.2090) in a 25 km ring.
DELHI_LAT, DELHI_LNG = 28.6139, 77.2090


class AlertRadiusTests(unittest.TestCase):
    def test_zero_distance_is_within_radius(self):
        self.assertTrue(is_within_radius(DELHI_LAT, DELHI_LNG, DELHI_LAT, DELHI_LNG, 25.0))

    def test_same_city_within_default_radius(self):
        # Noida is roughly 20 km east of central Delhi.
        self.assertTrue(is_within_radius(DELHI_LAT, DELHI_LNG, 28.6139, 77.3900, 25.0))

    def test_beyond_radius_is_excluded(self):
        # Agra is ~190 km from Delhi: must never alert with a 25 km radius.
        self.assertFalse(is_within_radius(DELHI_LAT, DELHI_LNG, 27.1767, 78.0081, 25.0))

    def test_within_custom_small_radius(self):
        self.assertTrue(is_within_radius(DELHI_LAT, DELHI_LNG, 28.6240, 77.2090, 5.0))

    def test_just_outside_boundary(self):
        # ~1.4 km east of Delhi point with a 1 km radius.
        self.assertFalse(is_within_radius(DELHI_LAT, DELHI_LNG, 28.6139, 77.2240, 1.0))

    def test_haversine_returns_expected_magnitude(self):
        # Agra to Delhi approx 190-200 km.
        distance = haversine_distance(DELHI_LAT, DELHI_LNG, 27.1767, 78.0081)
        self.assertTrue(170 < distance < 220, f"unexpected distance {distance}")


if __name__ == "__main__":
    unittest.main()