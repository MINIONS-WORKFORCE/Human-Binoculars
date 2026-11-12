"""Regression checks for the issue handoff contract, flags and calibration."""

import json

import numpy as np
import pytest
from astropy.io import fits
from pydantic import ValidationError
from test_science import ROOT, image

from shared.science import (
    APERTURE_ARCSEC,
)
from shared.science import (
    astrometry as public_astrometry,
)
from shared.science import (
    photometry as public_photometry,
)
from shared.science_contract import AstrometryResponse, PhotometryResponse
from shared.spherex_calibration import (
    assign_comparison_bands,
    bad_masks,
    measurement_metadata,
    solid_angles,
)


def astrometry(*args, **kwargs):
    return public_astrometry(*args, **kwargs, diagnostics=True)


def photometry(*args, **kwargs):
    return public_photometry(*args, **kwargs, diagnostics=True)


def target():
    return {
        "id": "rdra",
        "name": "R Dra synthetic test",
        "ra_deg": 269.4485,
        "dec_deg": 4.7394,
        "epoch_jyear": 2000.0,
        "pmra": 0.0,
        "pmdec": 0.0,
    }


def test_source_and_fullsample_are_not_bad_source_pixels(tmp_path):
    item, _ = image(tmp_path)
    with fits.open(item["path"], mode="update", memmap=False) as h:
        h["FLAGS"].data[31:34, 31:34] = (1 << 21) | (1 << 12)
    r = photometry([item], [(269.4485, 4.7394)])["rows"][0]
    assert r["flux_mjy"] is not None
    src, bg = bad_masks(np.array([1 << 21, 1 << 12, 1 << 1, 1 << 9], dtype=np.uint32), {})
    assert src.tolist() == [False, False, True, True]
    assert bg.tolist() == [True, False, True, True]


def test_header_bit_indices_override_defaults():
    src, bg = bad_masks(
        np.array([1 << 5, 1 << 7, 1 << 21], dtype=np.uint32), {"MP_SOURCE": 5, "MP_FULLSAMPLE": 7}
    )
    assert src.tolist() == [False, False, True]
    assert bg.tolist() == [True, False, True]


def test_dict_contract_and_synthetic_variability(tmp_path):
    entries = [image(tmp_path, k, flux=f)[0] for k, f in enumerate([100, 105, 80, 120, 90, 115])]
    r = photometry(entries, target(), APERTURE_ARCSEC)
    PhotometryResponse.model_validate(r)
    assert r["data_kind"] == "mock"
    assert r["variability"]["chi2_reduced"] > 5
    assert r["variability"]["reference_validated"] is False
    assert r["variability"]["is_variable"] is False
    assert len(r["points"]) == 6
    assert r["points"][0]["detector"] == 3
    assert "iso" in r["points"][0]
    json.dumps(r, allow_nan=False)
    r["points"][0]["flux_mjy"] = float("nan")
    with pytest.raises(ValidationError):
        PhotometryResponse.model_validate(r)


def test_empty_api_payloads_and_target_alias():
    t = {
        "target_key": "rdra",
        "name": "R Dra",
        "ra": 248.167,
        "dec": 66.755,
        "epoch": "J2016.0",
        "pmra": -20.0,
        "pmdec": 6.0,
    }
    p = photometry([], t)
    a = astrometry([], t)
    PhotometryResponse.model_validate(p)
    AstrometryResponse.model_validate(a)
    assert p["points"] == [] and p["variability"] is None
    assert a["points"] == [] and a["fit"] is None


def test_short_baseline_is_not_fitted(tmp_path):
    entries = []
    for k in range(3):
        e, _ = image(tmp_path, k)
        e["mjd"] = 60000 + k * 10
        entries.append(e)
    r = astrometry(entries, target())
    assert r["fit"] is None
    assert "NEED_THREE_MEASUREMENTS_AND_30_DAY_BASELINE" in r["warnings"]


def test_calibrated_wavelength_and_solid_angle_use_original_pixels(tmp_path):
    item, _ = image(tmp_path)
    with fits.open(item["path"], mode="update", memmap=False) as h:
        h["IMAGE"].header["CRPIX1A"] = 1
        h["IMAGE"].header["CRPIX2A"] = 1
    _yy, xx = np.indices((65, 65))
    cal = tmp_path / "wave.fits"
    fits.HDUList(
        [
            fits.PrimaryHDU(),
            fits.ImageHDU(1 + xx / 1000, name="CWAVE"),
            fits.ImageHDU(np.full(xx.shape, 0.025), name="CBAND"),
        ]
    ).writeto(cal)
    sapm = tmp_path / "sapm.fits"
    h = fits.ImageHDU(np.full(xx.shape, 36.0), name="IMAGE")
    h.header["BUNIT"] = "arcsec2"
    fits.HDUList([fits.PrimaryHDU(), h]).writeto(sapm)
    item.update(spectral_wcs_path=str(cal), sapm_path=str(sapm))
    m = measurement_metadata(item, (269.4485, 4.7394))
    assert m["wavelength_um"] == pytest.approx(1.032, abs=1e-8)
    assert m["bandwidth_um"] == pytest.approx(0.025)
    assert m["wavelength_calibrated"]
    with fits.open(item["path"]) as h:
        area = solid_angles(item, h["IMAGE"].header, (65, 65))
    assert area[32, 32] == pytest.approx(36 * (np.pi / (180 * 3600)) ** 2)


def test_full_passband_span_is_checked_not_just_labels():
    rows = [
        {
            "release": "qr2",
            "detector": "D1",
            "wavelength_um": w,
            "bandwidth_um": 0.02,
            "wavelength_calibrated": True,
            "comparison_band": "arbitrary",
        }
        for w in [1.0, 1.009, 1.018]
    ]
    assign_comparison_bands(rows)
    assert rows[0]["comparison_band"] == rows[1]["comparison_band"]
    assert rows[2]["comparison_band"] != rows[0]["comparison_band"]


def test_unverified_real_band_name_cannot_enable_chi_square(tmp_path):
    entries = [image(tmp_path, k)[0] for k in range(2)]
    for e in entries:
        e["survey"] = "real-label-but-unverified"
    r = photometry(entries, [(269.4485, 4.7394)] * 2)
    assert r["statistics"] == []


def test_zodi_model_is_subtracted(tmp_path):
    item, _ = image(tmp_path)
    before = photometry([item], [(269.4485, 4.7394)])["rows"][0]["flux_mjy"]
    with fits.open(item["path"], mode="update", memmap=False) as h:
        h["IMAGE"].data += 5
        h.append(fits.ImageHDU(np.full(h["IMAGE"].data.shape, 5.0), name="ZODI"))
    after = photometry([item], [(269.4485, 4.7394)])["rows"][0]["flux_mjy"]
    assert after == pytest.approx(before, rel=1e-10)


def test_committed_samples_match_models():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "issue36_backend_models", ROOT / "members/dong/app/api_models.py"
    )
    models = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(models)
    for name, model in [
        ("photometry_rdra", models.Photometry),
        ("astrometry_barnard", models.Astrometry),
    ]:
        payload = json.loads((ROOT / "api_samples" / f"{name}.json").read_text(encoding="utf8"))
        model.model_validate(payload)


def test_overflow_has_explicit_saturated_warning(tmp_path):
    item, _ = image(tmp_path)
    with fits.open(item["path"], mode="update", memmap=False) as h:
        h["FLAGS"].data[32, 32] = 1 << 1
    result = photometry([item], [(269.4485, 4.7394)])["rows"][0]
    assert result["flux_mjy"] is None
    assert result["warnings"] == ["SATURATED"]


def test_wrong_detector_metadata_is_not_measured(tmp_path):
    item, _ = image(tmp_path)
    with fits.open(item["path"], mode="update", memmap=False) as h:
        h["IMAGE"].header["DETECTOR"] = 1
    row = photometry([item], [(269.4485, 4.7394)])["rows"][0]
    assert row["flux_mjy"] is None
    assert row["warnings"] == ["DETECTOR_METADATA_MISMATCH"]
