"""Offline numerical regression tests. All images here are synthetic."""

import json
import sys
from pathlib import Path

import astropy.units as u
import numpy as np
import pytest
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS
from photutils.aperture import SkyCircularAperture

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from shared.science import (
    APERTURE_ARCSEC,
    astrometry,
    photometry,
    propagate,
)


def image(tmp_path, k=0, flux=100, centre=(269.4485, 4.7394), xy=(32, 32), angle=0):
    w = WCS(naxis=2)
    w.wcs.crpix = [33, 33]
    w.wcs.crval = centre
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    a = np.deg2rad(angle)
    w.wcs.cd = np.array([[-np.cos(a), np.sin(a)], [np.sin(a), np.cos(a)]]) * 6.15 / 3600
    yy, xx = np.indices((65, 65))
    data = 7 + flux * np.exp(-((xx - xy[0]) ** 2 + (yy - xy[1]) ** 2) / 2)
    header = w.to_header()
    header["BUNIT"] = "MJy/sr"
    path = tmp_path / f"image{k}.fits"
    fits.HDUList(
        [
            fits.PrimaryHDU(),
            fits.ImageHDU(data, header, name="IMAGE"),
            fits.ImageHDU(np.ones_like(data) * 0.01, name="VARIANCE"),
            fits.ImageHDU(np.zeros_like(data, dtype=np.uint32), name="FLAGS"),
        ]
    ).writeto(path)
    item = {
        "path": str(path),
        "mjd": 60000 + k * 365.25,
        "detector": "SPHEREx-D3",
        "release": "spherex_qr2",
        "survey": "synthetic",
        "wavelength_um": 2.0,
        "comparison_band": "verified-test-band",
    }
    return item, w


def test_photometry_flux_unit_background_and_variance(tmp_path):
    item, w = image(tmp_path)
    result = photometry([item], [(269.4485, 4.7394)])
    r = result["rows"][0]
    ap = SkyCircularAperture(
        SkyCoord(269.4485, 4.7394, unit="deg"), APERTURE_ARCSEC * u.arcsec
    ).to_pixel(w)
    weights = ap.to_mask(method="exact").to_image((65, 65))
    data = fits.getdata(item["path"], "IMAGE")
    expected = np.sum(weights * (data - 7)) * (6.15 / 206264.80624709636) ** 2 * 1e9
    # Tiny Gaussian wings in the annulus remove < 0.01% of aperture flux.
    assert r["flux_mjy"] == pytest.approx(expected, rel=1e-4)
    assert (
        r["err_mjy"] > np.sqrt(np.sum(weights**2) * 0.01) * (6.15 / 206264.80624709636) ** 2 * 1e9
    )
    assert r["detected"]
    assert result["chi2_reduced"] is None
    json.dumps(result, allow_nan=False)


def test_variability_and_passband_isolation(tmp_path):
    items = [image(tmp_path, k, flux=f)[0] for k, f in enumerate([100, 100, 120])]
    positions = [(269.4485, 4.7394)] * 3
    result = photometry(items, positions)
    assert result["chi2_reduced"] > 5
    assert result["statistics"][0]["dof"] == 2
    for item in items:
        item["comparison_band"] = None
    assert photometry(items, positions)["statistics"] == []
    for k, item in enumerate(items):
        item["comparison_band"] = f"band{k}"
    assert photometry(items, positions)["chi2_reduced"] is None


@pytest.mark.parametrize("problem", ["flag", "nan", "zero_variance", "edge", "unit"])
def test_reject_bad_source(tmp_path, problem):
    item, _ = image(tmp_path)
    pos = (269.4485, 4.7394)
    with fits.open(item["path"], mode="update", memmap=False) as h:
        if problem == "flag":
            h["FLAGS"].data[32, 32] = 1
        if problem == "nan":
            h["IMAGE"].data[32, 32] = np.nan
        if problem == "zero_variance":
            h["VARIANCE"].data[32, 32] = 0
        if problem == "unit":
            h["IMAGE"].header["BUNIT"] = "Jy"
    if problem == "edge":
        pos = (269.50, 4.74)
    result = photometry([item], [pos])
    assert result["rows"][0]["flux_mjy"] is None
    assert result["rows"][0]["warnings"]
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("angle", [0, 71, 180])
def test_barnard_pm_and_orientation(tmp_path, angle):
    target = next(
        t
        for t in json.loads((ROOT / "fixtures/targets.json").read_text(encoding="utf8"))
        if t["id"] == "barnard"
    )
    mjds = [60000 + k * 180 for k in range(4)]
    positions = propagate(target, mjds)
    reference = SkyCoord(*positions[0], unit="deg")
    items = []
    for k, (mjd, pos) in enumerate(zip(mjds, positions)):
        _, w = image(tmp_path, k, centre=(reference.ra.deg, reference.dec.deg), angle=angle)
        x, y = w.world_to_pixel(SkyCoord(*pos, unit="deg"))
        # independent known source placement on a common WCS
        (tmp_path / f"image{k}.fits").unlink()
        item, _ = image(
            tmp_path,
            k,
            centre=(reference.ra.deg, reference.dec.deg),
            xy=(x, y),
            angle=angle,
        )
        item["mjd"] = mjd
        items.append(item)
    result = astrometry(items, positions, reference=target)
    assert result["fit"]["pmdec"] == pytest.approx(target["pmdec"], abs=5)
    assert result["fit"]["pmra"] == pytest.approx(target["pmra"], abs=5)
    assert result["fit"]["pmdec_sign_matches_reference"]
    assert result["fit"]["pmdec_error"] > 0
    json.dumps(result, allow_nan=False)


def test_no_fit_with_single_epoch(tmp_path):
    item, _ = image(tmp_path)
    assert astrometry([item], [(269.4485, 4.7394)])["fit"] is None
    with pytest.raises(ValueError, match="Exactly one"):
        photometry([item], [])


def test_catalogue_provenance_and_gaia_epoch():
    # The current team table is a different, preserved J2000 schema.
    shared = json.loads((ROOT / "shared/targets.json").read_text(encoding="utf8"))
    assert len(shared["targets"]) == 5
    targets = json.loads((ROOT / "fixtures/targets.json").read_text(encoding="utf8"))
    assert len(targets) == 5
    for t in targets:
        assert 0 <= t["ra_deg"] < 360 and -90 <= t["dec_deg"] <= 90
        assert t["pmra_convention"] == "mu_alpha_cos_delta"
        for field in ["ra_deg", "dec_deg", "pmra", "pmdec", "epoch_jyear"]:
            source = t["sources"][field]
            assert source["url"].startswith("https://")
            assert (ROOT / "fixtures" / source["record"]).is_file()
        if "gaia_dr3" in t["crosscheck"]:
            assert t["epoch_jyear"] == 2016
            assert t["crosscheck"]["comparison"]["gaia_backprop_simbad_separation_mas"] < 100
    barnard = next(t for t in targets if t["id"] == "barnard")
    assert barnard["pmdec"] > 10000


def test_ra_wrap_and_empty_input():
    t = {"ra_deg": 359.9999, "dec_deg": 60, "epoch_jyear": 2000, "pmra": 1000, "pmdec": 2000}
    pos = propagate(t, [51544.5, 51909.75])
    assert pos[1][0] < 0.01
    assert pos[1][1] > pos[0][1]
    assert photometry([], [])["chi2_reduced"] is None
    assert astrometry([], [])["fit"] is None


def test_background_offset_and_flag_rejection(tmp_path):
    item, _ = image(tmp_path)
    pos = [(269.4485, 4.7394)]
    first = photometry([item], pos)["rows"][0]
    with fits.open(item["path"], mode="update", memmap=False) as hdus:
        hdus["IMAGE"].data += 1000
    second = photometry([item], pos)["rows"][0]
    assert second["flux_mjy"] == pytest.approx(first["flux_mjy"], rel=1e-10)
    assert second["err_mjy"] == pytest.approx(first["err_mjy"])
    with fits.open(item["path"], mode="update", memmap=False) as hdus:
        hdus["FLAGS"].data[32, 32] = 1
    assert astrometry([item], pos)["rows"][0]["ra_deg"] == pytest.approx(pos[0][0], abs=1e-6)


def test_bad_annulus_and_release_separation(tmp_path):
    entries = [image(tmp_path, k)[0] for k in range(2)]
    entries[1]["release"] = "spherex_qr3"
    result = photometry(entries, [(269.4485, 4.7394)] * 2)
    assert result["chi2_reduced"] is None
    assert len(result["statistics"]) == 2
    with fits.open(entries[0]["path"], mode="update", memmap=False) as hdus:
        hdus["FLAGS"].data[:] = 1
        hdus["FLAGS"].data[29:36, 29:36] = 0
    assert photometry(entries[:1], [(269.4485, 4.7394)])["rows"][0]["flux_mjy"] is None
