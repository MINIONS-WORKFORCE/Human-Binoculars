"""Replay the bounded real-data snapshot offline; --download explicitly fetches it."""

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from astropy.io import fits

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from shared.science import photometry_measurements, propagate
from shared.science_contract import astrometry_response as astrometry
from shared.science_contract import photometry_response as photometry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data/science_validation")
    parser.add_argument("--output", type=Path, default=ROOT / "data/science_validation/results")
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    snapshot = json.loads(
        (ROOT / "members/nguyen/evidence/irsa_snapshot.json").read_text(encoding="utf8")
    )
    resources = snapshot["resources"]
    if args.download:
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        def fetch(record):
            path = args.data_dir / record["path"]
            if not path.exists():
                session = requests.Session()
                session.mount(
                    "https://",
                    HTTPAdapter(
                        max_retries=Retry(
                            total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504]
                        )
                    ),
                )
                response = session.get(record["url"], timeout=(15, 120))
                response.raise_for_status()
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(response.content)
            return path

        with ThreadPoolExecutor(max_workers=3) as pool:
            list(pool.map(fetch, resources))
    for resource in resources:
        path = args.data_dir / resource["path"]
        if not path.is_file():
            parser.error(f"Missing cached input {resource['path']}; use --download")
        if hashlib.sha256(path.read_bytes()).hexdigest() != resource["sha256"]:
            raise ValueError(f"Input differs from the reviewed snapshot: {resource['path']}")
    args.output.mkdir(parents=True, exist_ok=True)
    targets = json.loads((ROOT / "fixtures/targets.json").read_text(encoding="utf8"))
    summaries = {}
    for slug in ["barnard", "r-dra"]:
        target = next(t for t in targets if t["id"] == slug)
        entries = []
        for original in snapshot["targets"][slug]:
            e = dict(original)
            for key in ["path", "spectral_wcs_path", "sapm_path"]:
                e[key] = str((args.data_dir / e[key]).resolve())
            with fits.open(e["path"]) as h:
                header = h["IMAGE"].header
                if str(header["OBSID"]) != e["obs_id"] or int(header["DETECTOR"]) != int(
                    str(e["detector"]).split("D")[-1]
                ):
                    raise ValueError("Observation identity mismatch")
                e["mjd"] = float(header["MJD-AVG"])
            e["data_kind"] = "observational"
            entries.append(e)
        result = astrometry(entries, target) if slug == "barnard" else photometry(entries, target)
        (args.output / f"{slug}.json").write_text(
            json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf8"
        )
        if slug == "barnard":
            fit = result["fit"]
            passed = bool(
                fit
                and fit["pmdec_sign_matches_catalog"]
                and 0.5 < abs(fit["pmdec"] / target["pmdec"]) < 2
            )
            summaries[slug] = {
                "criterion_pmdec_sign_and_order": passed,
                "fit": fit,
                "warnings": result["warnings"],
            }
            if not passed:
                raise AssertionError("Barnard direction/order acceptance failed")
        else:
            summaries[slug] = {
                "n_inputs": len(entries),
                "n_valid_aperture_fluxes": sum(p["flux_mjy"] is not None for p in result["points"]),
                "chi2_reduced": result["variability"]["chi2_reduced"]
                if result["variability"]
                else None,
                "rejection_reasons": dict(
                    Counter(
                        w for p in result["points"] if p["flux_mjy"] is None for w in p["warnings"]
                    )
                ),
                "real_variability_confirmed": False,
            }
            sweep = []
            positions = propagate(target, [e["mjd"] for e in entries])
            for radius in [6.15, 9.225, 12.3, 18.45]:
                measured = photometry_measurements(entries, positions, radius)
                sweep.append(
                    {
                        "radius_arcsec": radius,
                        "valid": sum(r["flux_mjy"] is not None for r in measured["rows"]),
                        "rejections": dict(
                            Counter(
                                w
                                for r in measured["rows"]
                                if r["flux_mjy"] is None
                                for w in r["warnings"]
                            )
                        ),
                    }
                )
            (args.output / "r-dra-aperture-sweep.json").write_text(
                json.dumps(sweep, indent=2), encoding="utf8"
            )
        with (args.output / f"{slug}-points.csv").open("w", newline="", encoding="utf8") as stream:
            fields = list(result["points"][0]) if result["points"] else ["mjd"]
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(result["points"])
    (args.output / "summary.json").write_text(
        json.dumps(summaries, indent=2, allow_nan=False) + "\n", encoding="utf8"
    )
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
