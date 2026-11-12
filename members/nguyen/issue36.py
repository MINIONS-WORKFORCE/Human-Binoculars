"""Issue 36: export tables, diagnostics, and existing API 0.1 payloads offline."""

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from shared.science import APERTURE_ARCSEC, astrometry, photometry
from shared.science_api import astrometry_payload, photometry_payload


def write_json(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf8"
    )


def export_result(result, output):
    """Retain rejected measurements as CSV rows with null flux and reasons."""
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "diagnostics.json", result)
    photo = "aperture_arcsec" in result
    rows = []
    for point in result["points"]:
        row = {"data_kind": result["data_kind"], **point}
        if photo:
            row["aperture_arcsec"] = result["aperture_arcsec"]
            row["aperture_is"] = "radius"
        else:
            measured = row.pop("measured")
            predicted = row.pop("predicted")
            for key in ["ra", "dec", "err_arcsec"]:
                row[f"measured_{key}"] = measured[key] if measured else None
            for key in ["ra", "dec"]:
                row[f"predicted_{key}"] = predicted[key] if predicted else None
        rows.append(
            {
                k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
                for k, v in row.items()
            }
        )
    fields = list(rows[0]) if rows else ["data_kind", "frame_id", "mjd", "warnings"]
    with (output / "points.csv").open("w", newline="", encoding="utf8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "data_kind": result["data_kind"],
        "n_rows": len(rows),
        "warnings": result["warnings"],
    }
    if photo:
        target_points = [p for p in result["points"] if not p["is_reference_star"]]
        summary.update(
            aperture_arcsec=result["aperture_arcsec"],
            aperture_is="radius",
            n_target_rows=len(target_points),
            n_valid_target_fluxes=sum(p["flux_mjy"] is not None for p in target_points),
            variability=result["variability"],
        )
    else:
        fit = result["fit"]
        summary.update(
            fit=fit,
            catalog_pm=result["catalog_pm"],
            pmdec_sign_matches_catalog=bool(
                fit and fit["pmdec"] * result["catalog_pm"]["pmdec"] > 0
            ),
        )
    api_path = output / "api_payload.json"
    try:
        payload = photometry_payload(result) if photo else astrometry_payload(result)
        write_json(api_path, payload)
        summary["api_payload_status"] = "written"
    except (ValueError, TypeError) as exc:
        # Do not leave a stale success from a preceding run.
        api_path.unlink(missing_ok=True)
        summary.update(api_payload_status="not_exportable", api_payload_reason=str(exc))
    write_json(output / "summary.json", summary)
    return summary


def run_manifest(manifest, output, aperture_arcsec=APERTURE_ARCSEC):
    document = json.loads(manifest.read_text(encoding="utf8"))
    if document["data_kind"] not in {"mock", "observational"}:
        raise ValueError("data_kind must be mock or observational")
    targets = json.loads((ROOT / "fixtures/targets.json").read_text(encoding="utf8"))
    target = next(t for t in targets if t["id"] == document["target_id"])
    entries = []
    for original in document["entries"]:
        entry = dict(original, data_kind=document["data_kind"])
        for key in ["path", "spectral_wcs_path", "sapm_path"]:
            if entry.get(key):
                path = Path(entry[key])
                entry[key] = str(
                    (manifest.parent / path if not path.is_absolute() else path).resolve(
                        strict=True
                    )
                )
        entries.append(entry)
    if target["id"] == "barnard":
        result = astrometry(entries, target, diagnostics=True)
    elif target["id"] == "r-dra":
        result = photometry(
            entries,
            target,
            aperture_arcsec,
            reference_stars=document.get("reference_stars", []),
            diagnostics=True,
        )
    else:
        raise ValueError("Issue 36 supports barnard and r-dra")
    return export_result(result, output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, nargs="?")
    parser.add_argument(
        "--from-diagnostics",
        type=Path,
        help="Re-export a saved diagnostic report; does not read FITS",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--aperture-arcsec", type=float, default=APERTURE_ARCSEC)
    args = parser.parse_args()
    if (args.manifest is None) == (args.from_diagnostics is None):
        parser.error("Use exactly one manifest or --from-diagnostics")
    if args.from_diagnostics is not None:
        print("Re-exporting saved report; no new FITS measurement", file=sys.stderr)
        result = json.loads(args.from_diagnostics.read_text(encoding="utf8"))
        summary = export_result(result, args.output)
    else:
        summary = run_manifest(args.manifest, args.output, args.aperture_arcsec)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
