"""Calculate predictions from real observation metadata, without downloading FITS."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

from science import load_targets, propagate, read_observations

ROOT = Path(__file__).resolve().parents[3]


def write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets", type=Path, default=ROOT / "shared/targets.json")
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--pairs", type=Path, help="CSV with record_id_1,record_id_2")
    parser.add_argument("--output", type=Path, required=True, help="New output directory")
    parser.add_argument("--reference-fits", type=Path, help="Optional common IMAGE WCS grid")
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Output directory already exists; choose a new directory")

    import astropy
    from astropy import units as u
    from astropy.coordinates import SkyCoord
    from astropy.time import Time

    targets = load_targets(args.targets)
    observations = read_observations(args.metadata, targets)
    grid = None
    if args.reference_fits:
        from astropy.io import fits
        from astropy.wcs import WCS

        with fits.open(args.reference_fits, memmap=False) as hdus:
            grid = WCS(hdus["IMAGE"].header, hdus).celestial
    results, by_id = [], {}
    for obs in observations:
        coord = propagate(targets[obs["target_id"]], obs["mjd_mid"], obs["time_scale"])
        instant = Time(obs["mjd_mid"], format="mjd", scale=obs["time_scale"])
        row = {
            "record_id": obs["record_id"],
            "target_id": obs["target_id"],
            "obs_id": obs["obs_id"],
            "collection": obs["collection"],
            "detector": obs["detector"],
            "scan_id": obs.get("scan_id", ""),
            "mjd_mid": obs["mjd_mid"],
            "time_scale": obs["time_scale"],
            "observation_mid_utc": instant.utc.isot,
            "predicted_icrs_ra_deg": float(coord.ra.deg),
            "predicted_icrs_dec_deg": float(coord.dec.deg),
            "model": "angular_proper_motion_only_no_parallax",
        }
        if grid is not None:
            # Strip the velocity before projection onto the common image grid.
            point = SkyCoord(coord.ra, coord.dec, frame="icrs")
            x, y = grid.world_to_pixel(point)
            row["reference_x_pixel_0based"] = float(x)
            row["reference_y_pixel_0based"] = float(y)
        results.append(row)
        by_id[obs["record_id"]] = (obs, coord, row, instant)

    pairs = []
    if args.pairs:
        with args.pairs.open(encoding="utf-8-sig", newline="") as stream:
            pair_reader = csv.DictReader(stream)
            if not {"record_id_1", "record_id_2"}.issubset(pair_reader.fieldnames or []):
                raise ValueError("Pairs require record_id_1 and record_id_2")
            for requested in pair_reader:
                first = by_id[requested["record_id_1"]]
                second = by_id[requested["record_id_2"]]
                a, b = first[0], second[0]
                for key in ("target_id", "detector", "collection"):
                    if a[key] != b[key]:
                        raise ValueError(
                            f"Pair has different {key}; explicit recalibration is outside v0"
                        )
                if second[3] <= first[3]:
                    raise ValueError("Pair must have strictly increasing observation time")
                # Separations use position-only ICRS coordinates, avoiding frame-time transforms.
                c1 = SkyCoord(first[1].ra, first[1].dec, frame="icrs")
                c2 = SkyCoord(second[1].ra, second[1].dec, frame="icrs")
                separation = c1.separation(c2).arcsec
                east, north = c1.spherical_offsets_to(c2)
                pair = {
                    "target_id": a["target_id"],
                    "record_id_1": a["record_id"],
                    "record_id_2": b["record_id"],
                    "detector": a["detector"],
                    "collection": a["collection"],
                    "baseline_julian_years": (second[3] - first[3]).to_value(u.yr),
                    "expected_separation_arcsec": separation,
                    "expected_east_arcsec": east.arcsec,
                    "expected_north_arcsec": north.arcsec,
                    "nominal_displacement_pixels_6p15": separation / 6.15,
                    "scan_id_1": a.get("scan_id", ""),
                    "scan_id_2": b.get("scan_id", ""),
                    "comparison_status": "POSITION_FORECAST_ONLY_BANDPASS_AND_IMAGE_QA_PENDING",
                }
                if grid is not None:
                    for axis in ("x", "y"):
                        col = f"reference_{axis}_pixel_0based"
                        pair[f"expected_d{axis}_common_grid"] = second[2][col] - first[2][col]
                pairs.append(pair)
        if not pairs:
            raise ValueError("Pairs file is empty")

    manifest = {
        "status": "PREDICTIONS_COMPUTED_NOT_IMAGE_DETECTIONS",
        "astropy_version": astropy.__version__,
        "observation_count": len(results),
        "pair_count": len(pairs),
        "targets_with_metadata": sorted({r["target_id"] for r in results}),
        "targets_without_metadata": sorted(set(targets) - {r["target_id"] for r in results}),
        "model": "angular proper motion only; excludes annual parallax, orbital motion and perspective acceleration",
        "time_policy": "midpoint(t_min,t_max); MJD; time_scale column defaults explicitly to UTC",
        "inputs": {},
    }
    for label, path in (
        ("targets", args.targets),
        ("metadata", args.metadata),
        ("pairs", args.pairs),
        ("reference_fits", args.reference_fits),
    ):
        if path:
            manifest["inputs"][label] = {
                "path": str(path.resolve()),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
    # Write only after successful validation and calculation of every requested row.
    args.output.mkdir(parents=True)
    write_csv(args.output / "positions_by_observation.csv", results)
    if pairs:
        write_csv(args.output / "motion_between_observations.csv", pairs)
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Computed {len(results)} positions and {len(pairs)} pairs in {args.output}")
    print("These are predictions, not proof of source detection or comparable photometry.")


if __name__ == "__main__":
    main()
