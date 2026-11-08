"""Check dipole controls and prevent masked cores becoming valid flux."""

import numpy as np
from tasks_def import aperture_measure, dipoles


def test_signed_pair_and_no_motion_control():
    yy, xx = np.indices((59, 59))
    noise = np.random.default_rng(45).normal(0, 1, (59, 59))
    moving = noise.copy()
    for x, amplitude in ((31, 40), (26, -40)):
        moving += amplitude * np.exp(-((xx - x) ** 2 + (yy - 29) ** 2) / (2 * 0.9**2))
    pairs = dipoles(moving)["pairs"]
    assert any(p["positive_xy"] == [31, 29] and p["negative_xy"] == [26, 29] for p in pairs)
    assert dipoles(noise)["pairs"] == []


def test_masked_peaks_are_not_candidates():
    image = np.random.default_rng(12).normal(0, 1, (59, 59))
    image[29, 29] = 100
    image[29, 34] = -100
    image[28, 29] = np.nan
    assert dipoles(image)["pairs"] == []


def test_aperture_units_background_and_mask_rejection():
    image = np.full((41, 41), 10.0)
    image[20, 20] += 100
    variance = np.ones_like(image)
    background_mask = np.zeros_like(image, dtype=bool)
    result = aperture_measure(image, variance, (20, 20), background_mask)
    assert result["status"] == "ok"
    np.testing.assert_allclose(result["sum_mjy_sr"], 100)
    assert result["error_mjy_sr"] > 0
    image[20, 20] = np.nan
    assert (
        aperture_measure(image, variance, (20, 20), background_mask)["status"]
        == "masked_or_edge_aperture"
    )
    assert (
        aperture_measure(np.ones((41, 41)), variance, (0, 0), background_mask)["status"]
        == "masked_or_edge_aperture"
    )


def test_background_experiment_keeps_source_exclusion():
    image = np.full((59, 59), 10.0)
    image[29, 29] += 100
    yy, xx = np.indices(image.shape)
    source = (xx - 29) ** 2 + (yy - 29) ** 2 < 11**2
    variance = np.ones_like(image)
    assert (
        aperture_measure(image, variance, (29, 29), source)["status"] == "insufficient_background"
    )
    wide = aperture_measure(image, variance, (29, 29), source, (12, 25))
    assert wide["status"] == "ok"
    np.testing.assert_allclose(wide["sum_mjy_sr"], 100)
