"""Generate clearly labelled offline acceptance samples, never sky measurements."""

import json
import sys
from pathlib import Path

import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.time import Time
from astropy.timeseries import LombScargle
from astropy.wcs import WCS

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from shared.science import propagate
from shared.science_contract import AstrometryResponse, PhotometryResponse
from shared.science_contract import astrometry_response as astrometry
from shared.science_contract import photometry_response as photometry


def main():
    out = ROOT / "data/science_acceptance_mock"
    out.mkdir(parents=True, exist_ok=True)
    samples = out / "api_samples"
    samples.mkdir(parents=True, exist_ok=True)
    targets = json.loads((ROOT / "fixtures/targets.json").read_text(encoding="utf8"))
    rng = np.random.default_rng(20261110)
    rdra = dict(next(t for t in targets if t["id"] == "r-dra"))
    rdra["name"] = "R Dra (synthetic acceptance test)"
    mjds = 60000 + np.arange(20) * 18.0
    positions = propagate(rdra, mjds)
    w = WCS(naxis=2)
    w.wcs.crpix = [35, 35]
    w.wcs.crval = positions[0]
    w.wcs.cdelt = [-6.15 / 3600, 6.15 / 3600]
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    refsky = w.pixel_to_world(21, 34)
    ref = {
        "name": "Synthetic constant comparison star",
        "id": "synthetic-control-1",
        "ra_deg": float(refsky.ra.deg),
        "dec_deg": float(refsky.dec.deg),
        "epoch_jyear": float(Time(mjds[0], format="mjd").jyear),
        "pmra": 0.0,
        "pmdec": 0.0,
    }
    refsky2 = w.pixel_to_world(47, 34)
    ref2 = {
        **ref,
        "id": "synthetic-control-2",
        "name": "Synthetic constant comparison star 2",
        "ra_deg": float(refsky2.ra.deg),
        "dec_deg": float(refsky2.dec.deg),
    }
    yy, xx = np.indices((69, 69))
    entries = []
    for k, (mjd, pos) in enumerate(zip(mjds, positions)):
        x, y = w.world_to_pixel(SkyCoord(*pos, unit="deg"))
        amplitude = 100 * (1 + 0.20 * np.sin(2 * np.pi * (mjd - 60000) / 245.6))
        data = (
            7
            + amplitude * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / 2)
            + 100 * np.exp(-((xx - 21) ** 2 + (yy - 34) ** 2) / 2)
        )
        data += 100 * np.exp(-((xx - 47) ** 2 + (yy - 34) ** 2) / 2)
        data += rng.normal(0, 8, data.shape)
        flags = np.zeros(data.shape, dtype=np.uint32)
        flags[
            ((xx - x) ** 2 + (yy - y) ** 2 < 16)
            | ((xx - 21) ** 2 + (yy - 34) ** 2 < 16)
            | ((xx - 47) ** 2 + (yy - 34) ** 2 < 16)
        ] = 1 << 21
        header = w.to_header()
        header["BUNIT"] = "MJy/sr"
        header["OBSID"] = f"synthetic-rdra-{k:02d}"
        path = out / f"rdra-{k:02d}.fits"
        fits.HDUList(
            [
                fits.PrimaryHDU(),
                fits.ImageHDU(data, header, name="IMAGE"),
                fits.ImageHDU(np.full(data.shape, 64.0), name="VARIANCE"),
                fits.ImageHDU(flags, name="FLAGS"),
            ]
        ).writeto(path, overwrite=True)
        entries.append(
            {
                "path": str(path),
                "mjd": float(mjd),
                "wavelength_um": 2.0,
                "bandwidth_um": 0.025,
                "comparison_band": "synthetic-2um",
                "detector": "SPHEREx-D3",
                "release": "synthetic",
                "survey": 1,
                "data_kind": "mock",
            }
        )
    photo = photometry(entries, rdra, reference_stars=[ref, ref2])
    (samples / "photometry_rdra.json").write_text(
        json.dumps(photo, indent=2, allow_nan=False) + "\n", encoding="utf8"
    )
    (out / "rdra-manifest.json").write_text(
        json.dumps(
            {
                "target_id": "r-dra",
                "data_kind": "mock",
                "reference_stars": [ref, ref2],
                "entries": entries,
            },
            indent=2,
        ),
        encoding="utf8",
    )
    barnard = dict(next(t for t in targets if t["id"] == "barnard"))
    mjds = 60000 + np.arange(6) * 90.0
    positions = propagate(barnard, mjds)
    w.wcs.crval = positions[0]
    entries = []
    for k, (mjd, pos) in enumerate(zip(mjds, positions)):
        x, y = w.world_to_pixel(SkyCoord(*pos, unit="deg"))
        data = 7 + 100 * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / 2)
        header = w.to_header()
        header["BUNIT"] = "MJy/sr"
        header["OBSID"] = f"synthetic-barnard-{k:02d}"
        path = out / f"barnard-{k:02d}.fits"
        fits.HDUList(
            [
                fits.PrimaryHDU(),
                fits.ImageHDU(data, header, name="IMAGE"),
                fits.ImageHDU(np.ones(data.shape) * 0.01, name="VARIANCE"),
                fits.ImageHDU(np.full(data.shape, 1 << 21, dtype=np.uint32), name="FLAGS"),
            ]
        ).writeto(path, overwrite=True)
        entries.append(
            {
                "path": str(path),
                "mjd": float(mjd),
                "detector": "SPHEREx-D3",
                "release": "synthetic",
                "survey": 1,
                "data_kind": "mock",
                "png_wcs_header": dict(header),
                "png_shape": list(data.shape),
            }
        )
    astro = astrometry(entries, barnard)
    (samples / "astrometry_barnard.json").write_text(
        json.dumps(astro, indent=2, allow_nan=False) + "\n", encoding="utf8"
    )
    (out / "barnard-manifest.json").write_text(
        json.dumps({"target_id": "barnard", "data_kind": "mock", "entries": entries}, indent=2),
        encoding="utf8",
    )
    for name, model in [("photometry", PhotometryResponse), ("astrometry", AstrometryResponse)]:
        (samples / f"{name}.schema.json").write_text(
            json.dumps(model.model_json_schema(), indent=2) + "\n", encoding="utf8"
        )
    # Reproducible learning exercise: constant vs sine at 5% noise, and sampling aliases.
    n = 20
    t = np.arange(n) * 18.0
    sigma = np.full(n, 0.05)
    constant = 1 + rng.normal(0, 0.05, n)
    sine = constant + 0.2 * np.sin(2 * np.pi * t / 245.6)

    def chi(y):
        return float(np.sum(((y - np.average(y, weights=1 / sigma**2)) / sigma) ** 2) / (n - 1))

    sparse_t = np.arange(n) * 183.0
    sparse_y = 1 + 0.2 * np.sin(2 * np.pi * sparse_t / 245.6) + rng.normal(0, 0.05, n)
    freq, power = LombScargle(sparse_t, sparse_y, sigma).autopower(
        minimum_frequency=1 / 1000, maximum_frequency=1 / 30, samples_per_peak=20
    )
    exercise = {
        "data_kind": "mock",
        "n": n,
        "sigma_fraction": 0.05,
        "input_period_days": 245.6,
        "chi2_constant": chi(constant),
        "chi2_sine": chi(sine),
        "sparse_sampling_days": 183,
        "largest_periodogram_peak_days": float(1 / freq[np.argmax(power)]),
        "note": "A sampling alias demonstration; not a period measured for R Dra.",
    }
    (out / "learning_exercise.json").write_text(json.dumps(exercise, indent=2), encoding="utf8")
    assert photo["variability"] and photo["variability"]["reference_validated"]
    assert astro["fit"] and astro["fit"]["pmdec_sign_matches_catalog"]
    print(
        json.dumps(
            {
                "mock_photometry": photo["variability"],
                "mock_astrometry": astro["fit"],
                "exercise": exercise,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
