"""Required Astropy execution checks: missing dependencies fail, never silently pass."""

import unittest
import warnings
from pathlib import Path

from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time
from science import dec_to_degrees, load_targets, nominal_motion, propagate, ra_to_degrees


class AstropyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.targets = load_targets(Path(__file__).resolve().parents[3] / "shared/targets.json")

    def test_skycoord_converts_all_five(self):
        for target in self.targets.values():
            a = target["astrometry"]
            c = SkyCoord(a["ra_hms"], a["dec_dms"], unit=(u.hourangle, u.deg))
            self.assertAlmostEqual(c.ra.deg, ra_to_degrees(a["ra_hms"]), places=9)
            self.assertAlmostEqual(c.dec.deg, dec_to_degrees(a["dec_dms"]), places=9)

    def test_propagation_identity_at_reference_epoch(self):
        for t in self.targets.values():
            a = t["astrometry"]
            epoch = Time(a["reference_epoch_jyear"], format="jyear", scale="tt")
            with warnings.catch_warnings(record=True):
                c = propagate(t, epoch.mjd, "tt")
            original = SkyCoord(a["ra_deg"] * u.deg, a["dec_deg"] * u.deg)
            self.assertLess(original.separation(c).arcsec, 1e-6)

    def test_future_motion_has_expected_direction_and_size(self):
        start = Time(2025.5, format="jyear", scale="tt")
        end = Time(2026.0, format="jyear", scale="tt")
        for t in self.targets.values():
            a = t["astrometry"]
            with warnings.catch_warnings(record=True):
                c1, c2 = propagate(t, start.mjd, "tt"), propagate(t, end.mjd, "tt")
            p1, p2 = SkyCoord(c1.ra, c1.dec), SkyCoord(c2.ra, c2.dec)
            expected, _ = nominal_motion(a["pm_ra_cosdec_mas_per_yr"], a["pm_dec_mas_per_yr"], 0.5)
            self.assertAlmostEqual(p1.separation(p2).arcsec, expected, delta=0.002)
            east, north = p1.spherical_offsets_to(p2)
            self.assertEqual(east.arcsec > 0, a["pm_ra_cosdec_mas_per_yr"] > 0)
            self.assertEqual(north.arcsec > 0, a["pm_dec_mas_per_yr"] > 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
