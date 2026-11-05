"""Boundary and FITS-layout tests for conservative document-rule classification."""

import io
import unittest

from audit_official_surveys import classify_survey, parse_image_header


class SurveyTests(unittest.TestCase):
    def check_label(self, pa, day, expected):
        survey, status = classify_survey(pa, day, "all_sky", "False")
        self.assertEqual(survey, expected)
        self.assertTrue(status.startswith("DERIVED_"))

    def test_first_phase_zero(self):
        self.check_label(0, "2025-08-20T23:02:22.517", "1")

    def test_first_phase_180(self):
        self.check_label(180, "2026-03-22T05:28:36.944", "2")

    def test_second_phase_zero(self):
        self.check_label(0, "2026-07-16T20:59:22", "3")

    def test_second_phase_180(self):
        self.check_label(180, "2026-07-16T20:59:22", "4")

    def test_angle_wrap(self):
        self.check_label(360, "2025-08-20", "1")

    def test_non_survey(self):
        for value in (True, "True", None, ""):
            with self.subTest(value=value):
                self.assertEqual(
                    classify_survey(0, "2025-08-20", "all_sky", value)[0], ""
                )

    def test_deep_not_misclassified(self):
        self.assertEqual(classify_survey(0, "2025-08-20", "deep", False)[0], "")

    def test_all_sky_downlink_retains_survey_membership(self):
        self.assertEqual(
            classify_survey(0, "2025-08-20", "all_sky,downlink", False)[0], "1"
        )

    def test_ambiguous_deep_flag_requires_review(self):
        self.assertEqual(classify_survey(0, "2025-08-20", "all_sky,deep", False)[0], "")

    def test_nonstandard_angle(self):
        self.assertEqual(classify_survey(90, "2025-08-20", "all_sky", False)[0], "")

    def test_transition_guard(self):
        for day in ("2026-05-01", "2026-05-16", "2026-05-31"):
            with self.subTest(day=day):
                self.assertEqual(classify_survey(0, day, "all_sky", False)[0], "")

    def test_before_and_after_scope(self):
        for day in ("2025-04-30", "2027-05-01"):
            with self.subTest(day=day):
                self.assertEqual(classify_survey(0, day, "all_sky", False)[0], "")

    def test_invalid_values(self):
        for pa, day in (
            (None, "2025-08-20"),
            (0, "bad-date"),
            (float("nan"), "2025-08-20"),
        ):
            with self.subTest(pa=pa, day=day):
                self.assertEqual(classify_survey(pa, day, "all_sky", False)[0], "")

    def test_valid_header_blocks(self):
        import numpy as np
        from astropy.io import fits

        stream = io.BytesIO()
        hdus = fits.HDUList(
            [fits.PrimaryHDU(), fits.ImageHDU(np.zeros((2, 2)), name="IMAGE")]
        )
        hdus[1].header["OBSID"] = "SYNTHETIC-HEADER-TEST"
        hdus.writeto(stream)
        header, raw = parse_image_header(stream.getvalue())
        self.assertEqual(header["OBSID"], "SYNTHETIC-HEADER-TEST")
        self.assertEqual(len(raw) % 2880, 0)

    def test_truncated_header_rejected(self):
        with self.assertRaises(ValueError):
            parse_image_header(b"SIMPLE  =                    T".ljust(80, b" "))


if __name__ == "__main__":
    unittest.main()
