"""Prepare browser PNGs and a frames index from the local QR2 fixture pack."""

import argparse
import csv
import hashlib
import json
import os
from collections import defaultdict
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

import numpy as np
from astropy.io import fits
from PIL import Image

from build_wise0855_fixture import extract_sources


def build(pack: Path, exports: list[Path]) -> int:
    archive_sources = {}
    for export in exports:
        for source in extract_sources(export):
            archive_sources[urlsplit(source["access_url"]).path] = source

    with (pack / "metadata.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("Fixture metadata.csv has no cutouts.")

    groups = defaultdict(list)
    for row in rows:
        path = (pack / row["filename"]).resolve()
        if not path.is_relative_to(pack.resolve()):
            raise ValueError("A cutout path points outside the fixture pack.")
        archive_path = urlsplit(row["cutout_url"]).path
        source = archive_sources.get(archive_path)
        if source is None:
            raise ValueError(f"No matching QR2 SIA2 row for {row['filename']}")
        band = row["energy_bandpassname"]
        with fits.open(path, memmap=False) as hdus:
            image = hdus["IMAGE"]
            if (
                source["energy_bandpassname"] != band
                or image.header["OBSID"] != source["obs_id"]
                or f"SPHEREx-D{image.header['DETECTOR']}" != band
            ):
                raise ValueError(f"FITS and SIA2 metadata disagree for {row['filename']}")
            pixels = np.flipud(np.asarray(image.data, dtype=float))
        if pixels.ndim != 2:
            raise ValueError(f"Expected a 2D IMAGE in {row['filename']}")
        groups[row["target_name"], band].append((row, source, pixels))

    output = pack / "rendered"
    output.mkdir(exist_ok=True)
    index = []
    with TemporaryDirectory(dir=output) as directory:
        staging = Path(directory)
        for group in groups.values():
            finite = np.concatenate([pixels[np.isfinite(pixels)] for _, _, pixels in group])
            if not finite.size:
                raise ValueError("A target and detector group has no finite image pixels.")
            low, high = np.percentile(finite, [1, 99])
            scale = high - low if high > low else 1
            for row, source, pixels in group:
                valid = np.isfinite(pixels)
                gray = np.zeros(pixels.shape, dtype=np.uint8)
                gray[valid] = np.rint(255 * np.clip((pixels[valid] - low) / scale, 0, 1))
                image = Image.fromarray(np.stack([gray, valid.astype(np.uint8) * 255], axis=-1))
                buffer = BytesIO()
                image.save(buffer, format="PNG")
                png = buffer.getvalue()
                digest = hashlib.sha256(row["filename"].encode() + png).hexdigest()[:24]
                frame_id = f"fixture-{digest}"
                (staging / f"{frame_id}.png").write_bytes(png)
                index.append(
                    {
                        "frame_id": frame_id,
                        "target_ra_deg": float(row["search_ra_deg"]),
                        "target_dec_deg": float(row["search_dec_deg"]),
                        "cutout_size_deg": float(row["cutout_size_deg"]),
                        "source": source,
                    }
                )
        if len({row["frame_id"] for row in index}) != len(index):
            raise ValueError("Duplicate cutouts in the fixture pack.")
        manifest = staging / "frames.json"
        manifest.write_text(json.dumps({"frames": index}, indent=2) + "\n", encoding="utf-8")
        for row in index:
            name = f"{row['frame_id']}.png"
            os.replace(staging / name, output / name)
        os.replace(manifest, output / manifest.name)
    return len(index)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, default=Path("data/fixture_pack_v1"))
    parser.add_argument("sia2_html", type=Path, nargs="+", help="Saved QR2 SIA2 HTML result files")
    args = parser.parse_args()
    count = build(args.pack, args.sia2_html)
    print(f"Prepared {count} PNGs and frames.json in {args.pack / 'rendered'}")


if __name__ == "__main__":
    main()
