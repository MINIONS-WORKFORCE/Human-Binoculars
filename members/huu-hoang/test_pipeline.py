"""Numerical acceptance checks: sky geometry, moving grid, and temporal median."""

import hashlib
import json

import frames
import numpy as np
import pytest
from astropy.coordinates import SkyCoord
from astropy.io import fits
from reproject import reproject_interp
from tan_pipeline import centroids, tan_grid


def test_target_center_and_orientation():
    w, shape = tan_grid(331.1, -56.8, 0.1)
    x, y = w.world_to_pixel(SkyCoord(331.1, -56.8, unit="deg"))
    np.testing.assert_allclose([x, y], (np.array(shape) - 1) / 2, atol=1e-8)
    assert w.pixel_to_world(x, y + 1).dec.deg > -56.8
    assert w.pixel_to_world(x + 1, y).ra.deg < 331.1


def test_rotated_offset_grid_keeps_star_position():
    target, shape = tan_grid(133.7951, -7.2451, 0.1)
    native = target.deepcopy()
    angle = np.deg2rad(23)
    native.wcs.pc = [[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]]
    native.wcs.crpix += [3.2, -2.7]
    yy, xx = np.indices(shape)
    star = target.pixel_to_world(24.3, 31.6)
    sx, sy = native.world_to_pixel(star)
    image = 100 * np.exp(-((xx - sx) ** 2 + (yy - sy) ** 2) / (2 * 1.2**2))
    aligned, _ = reproject_interp((image, native), target, shape_out=shape)
    positions = centroids(aligned)
    assert np.min(np.linalg.norm(positions - [24.3, 31.6], axis=1)) < 0.15


@pytest.mark.parametrize("explicit_clusters", [False, True])
def test_temporal_median_rejects_outlier_and_difference_has_sign(
    tmp_path, monkeypatch, explicit_clusters
):
    target, shape = tan_grid(133.7951, -7.2451, 0.1)
    entries, images = [], {}
    for i, (mjd, value) in enumerate(
        zip([60000, 60001, 60002, 60100, 60101, 60102], [10, 12, 1000, 20, 22, 1000])
    ):
        path = tmp_path / f"input{i}"
        path.write_bytes(str(i).encode())
        entries.append(
            {
                "path": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "obs_id": str(i),
                "detector": "D3",
                "mjd": mjd,
            }
        )
        if explicit_clusters:
            # Sparse sampling must retain the membership derived from the full catalog.
            entries[-1].update(
                cluster_id=i // 3,
                mjd=60000 + (i // 3) * 200 + (i % 3) * 40,
                cluster_start_mjd=60000 + (i // 3) * 200,
                cluster_end_mjd=60080 + (i // 3) * 200,
            )
        images[str(path)] = np.full(shape, float(value))

    def load(path, ra, dec):
        index = int(path.name.removeprefix("input"))
        return (
            images[str(path)],
            target,
            {
                "bunit": "MJy / sr",
                "detector": 3,
                "obs_id": str(index),
                "wave_um": 2.3,
                "date_obs": "2025-01-01",
            },
        )

    monkeypatch.setattr(frames, "load_cutout", load)
    manifest = tmp_path / "inputs.json"
    manifest.write_text(json.dumps(entries))
    report = frames.make_frames(
        133.7951, -7.2451, 0.1, 3, manifest=manifest, output=tmp_path / "output"
    )
    assert [f["n_inputs"] for f in report["frames"]] == [3, 3]
    with fits.open(tmp_path / "output/D3_visit00.fits") as h:
        assert h["MEDIAN"].data[29, 29] == 12
        assert h["NVALID"].data[29, 29] == 3
    with fits.open(tmp_path / "output/D3_visit01_minus_D3_visit00.fits") as h:
        assert h[0].data[29, 29] == 10
