"""Offline checks. Run the separate test_astropy.py once Astropy is installed."""

import csv
import json
import math
import tempfile
import unittest
from pathlib import Path

from science import (
    dec_to_degrees,
    decode_flags,
    definitions_from_header,
    load_targets,
    nominal_motion,
    ra_to_degrees,
    read_observations,
)

TARGETS = Path(__file__).resolve().parents[3] / "shared/targets.json"


class ScienceTests(unittest.TestCase):
    def test_challenge_coordinate_conversion(self):
        self.assertAlmostEqual(ra_to_degrees("08 55 10.831"), 133.79512916666667)
        self.assertAlmostEqual(dec_to_degrees("-07 14 42.53"), -7.245147222222222)

    def test_negative_zero_declination(self):
        self.assertEqual(dec_to_degrees("-00 30 00"), -0.5)

    def test_invalid_coordinate_ranges(self):
        for value in ("24 00 00", "12 60 00", "nan 00 00"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                ra_to_degrees(value)
        with self.assertRaises(ValueError):
            dec_to_degrees("+90 00 01")

    def test_exact_target_set_and_coordinate_roundtrip(self):
        targets = load_targets(TARGETS)
        self.assertEqual(set(targets), {"barnard", "wise0855", "epsilon-indi-b", "rw-aur", "r-dra"})

    def test_missing_k_is_not_zero(self):
        photo = load_targets(TARGETS)["wise0855"]["photometry"]["K"]
        self.assertIsNone(photo["magnitude"])
        self.assertEqual(photo["status"], "not_available_in_simbad_summary")

    def test_wise_reference_not_challenge_seed(self):
        a = load_targets(TARGETS)["wise0855"]["astrometry"]
        self.assertEqual(a["reference_epoch_jyear"], 2000)
        self.assertGreater(abs(a["ra_deg"] - ra_to_degrees("08 55 10.831")), 0.02)

    def test_nominal_motion_units(self):
        # 3/4/5 triangle, 5000 mas/year over 0.5 years gives 2.5 arcsec.
        self.assertEqual(nominal_motion(3000, 4000, 0.5, 5), (2.5, 0.5))

    def test_barnard_half_year_forecast(self):
        arcsec, pixels = nominal_motion(-801.551, 10362.394, 0.5)
        self.assertAlmostEqual(arcsec, 5.196674259005393)
        self.assertAlmostEqual(pixels, 0.8449876843911207)

    def test_invalid_motion_input(self):
        for args in ((1, 2, -1, 6.15), (1, 2, 1, 0), (math.nan, 2, 1, 6.15)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                nominal_motion(*args)

    def test_combined_flags_and_unknown_bit(self):
        names, unknown = decode_flags(
            (1 << 1) | (1 << 21) | (1 << 29), {"OVERFLOW": 1, "SOURCE": 21}
        )
        self.assertEqual(names, ["OVERFLOW", "SOURCE"])
        self.assertEqual(unknown, 1 << 29)

    def test_zero_flags(self):
        self.assertEqual(decode_flags(0, {"SOURCE": 21}), ([], 0))

    def test_flags_header_indices(self):
        result = definitions_from_header({"MP_SOURCE": 21, "HIERARCH MP_HOT": 10, "NAXIS": 2})
        self.assertEqual(result, {"SOURCE": 21, "HOT": 10})
        with self.assertRaises(ValueError):
            definitions_from_header({"NAXIS": 2})

    def test_metadata_rejects_empty_template(self):
        with self.assertRaises(ValueError):
            read_observations(
                Path(__file__).with_name("observations_template.csv"), load_targets(TARGETS)
            )

    def test_metadata_midpoint_and_duplicate_ids(self):
        fields = ["record_id", "target_id", "obs_id", "collection", "detector", "t_min", "t_max"]
        row = ["TEST_ONLY", "barnard", "SYNTHETIC_TEST", "spherex_qr2", "D6", 60000, 60002]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.csv"
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                writer.writerow(fields)
                writer.writerow(row)
            self.assertEqual(read_observations(path, load_targets(TARGETS))[0]["mjd_mid"], 60001)
            with path.open("a", newline="", encoding="utf-8") as stream:
                csv.writer(stream).writerow(row)
            with self.assertRaises(ValueError):
                read_observations(path, load_targets(TARGETS))

    def test_target_schema_is_json(self):
        content = json.loads(TARGETS.read_text(encoding="utf-8"))
        self.assertEqual(content["schema_version"], "1.0.0")
        self.assertEqual(content["nominal_pixel_scale_arcsec_per_pixel"], 6.15)


if __name__ == "__main__":
    unittest.main(verbosity=2)
