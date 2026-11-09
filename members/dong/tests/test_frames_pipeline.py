"""Verify archive column mapping and grouped image publication."""

import io
from contextlib import nullcontext

import numpy as np
from astropy.io import fits
from astropy.table import Table
from astropy.wcs import WCS
from PIL import Image

from shared import frames_pipeline as pipeline

QUERY = {
    "s_ra": 269.44636864652,
    "s_dec": 4.766880108377093,
    "obs_collection": "spherex_qr2",
    "energy_bandpassname": "SPHEREx-D6",
    "cutout_size_deg": 0.05,
}


def source(index, time):
    return {
        "obs_id": f"sample-{index}",
        "obs_publisher_did": f"ivo://example/{index}",
        "obs_collection": "spherex_qr2",
        "energy_bandpassname": "SPHEREx-D6",
        "s_ra": QUERY["s_ra"],
        "s_dec": QUERY["s_dec"],
        "t_min": time,
        "t_max": time + 0.001,
        "access_url": f"https://example.org/{index}.fits",
        "access_format": "image/fits",
    }


def test_discover_uses_field_names_instead_of_ids(monkeypatch):
    table = Table(rows=[source(1, 60900)])
    buffer = io.BytesIO()
    table.write(buffer, format="votable")
    xml = buffer.getvalue().replace(b'ID="obs_id"', b'ID="archive_field_0"')
    assert b'ID="archive_field_0"' in xml
    monkeypatch.setattr(pipeline, "request", lambda *args: xml)
    assert pipeline.discover(QUERY)[0]["obs_id"] == "sample-1"


def test_fixed_grid_median_groups_and_source_identity(tmp_path, monkeypatch):
    wcs = WCS(naxis=2)
    wcs.wcs.crpix = [15.5, 15.5]
    wcs.wcs.crval = [QUERY["s_ra"], QUERY["s_dec"]]
    wcs.wcs.cdelt = [-6.2 / 3600, 6.2 / 3600]
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    inputs = []
    for index, time in enumerate([60900, 60901, 60940]):
        metadata = source(index, time)
        wcs.wcs.crpix = [15.5 + index, 15.5]
        header = wcs.to_header()
        header["BUNIT"] = "MJy / sr"
        header["OBSID"] = metadata["obs_id"]
        header["DETECTOR"] = 6
        yy, xx = np.mgrid[:30, :30]
        pixels = (100 * np.exp(-((xx - 14 - index) ** 2 + (yy - 14) ** 2) / 4)).astype(
            np.float32
        )
        flags = fits.ImageHDU(np.zeros((30, 30), dtype=np.int32), name="FLAGS")
        flags.header["MP_BAD"] = 0
        path = tmp_path / f"{index}.fits"
        fits.HDUList(
            [fits.PrimaryHDU(), fits.ImageHDU(pixels, header=header, name="IMAGE"), flags]
        ).writeto(path)
        inputs.append((metadata, path))
    monkeypatch.setattr(pipeline, "local_inputs", lambda *args: inputs)
    result, images = pipeline.make_frames(
        QUERY, "fixture", tmp_path, tmp_path, lambda name: nullcontext()
    )
    assert [frame["n_images"] for frame in result["frames"]] == [2, 1]
    assert result["frames"][0]["source_obs_publisher_dids"] == [
        "ivo://example/0",
        "ivo://example/1",
    ]
    arrays = [np.asarray(Image.open(io.BytesIO(content))) for content in images.values()]
    assert all(array.shape == (30, 30, 2) for array in arrays)
    assert np.argmax(arrays[0][:, :, 0]) == np.argmax(arrays[1][:, :, 0])
