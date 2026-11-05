"""Audit documented SPHEREx survey rules using actual exposure headers.

Survey labels are derived from the Explanatory Supplement, not literal archive IDs.
Never infer a survey from a seven-day gap, planning period or QR release.
"""

import argparse
import csv
import hashlib
import json
import math
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from http.client import HTTPException
from itertools import combinations
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

SUPPLEMENT = "https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp_QR.pdf"
START_SOURCE = "https://spherex.caltech.edu/page/data-tools"


def classify_survey(pa, date_obs, flags, non_survey):
    """Conservative application of v2.0 pp.8-9/14 with science start 2025-05-01.

    May 2026 is deliberately unclassified: the supplement specifies 12.5 months,
    not an exact UTC phase boundary. Do not resolve this by rounding a month.
    """
    if str(non_survey).strip().lower() not in {"false", "f", "0"}:
        return "", "NON_SURVEY_OR_MISSING_SURVEY_STATUS"
    flag_tokens = set(re.split(r"[,;\s]+", str(flags).strip().lower()))
    if "all_sky" not in flag_tokens:
        return "", "NOT_DOCUMENTED_ALL_SKY_RULE"
    if any("deep" in token for token in flag_tokens):
        return "", "AMBIGUOUS_ALL_SKY_DEEP_FLAGS"
    try:
        angle = float(pa) % 360
        instant = datetime.fromisoformat(str(date_obs))
        if instant.tzinfo is None:
            instant = instant.replace(tzinfo=UTC)
    except (TypeError, ValueError):
        return "", "MISSING_OR_INVALID_PA_DATE"
    if not math.isfinite(angle):
        return "", "MISSING_OR_INVALID_PA_DATE"
    near_zero = min(angle, 360 - angle) <= 0.1
    near_180 = abs(angle - 180) <= 0.1
    if not (near_zero or near_180):
        return "", "PA_OUTSIDE_DOCUMENTED_ORIENTATIONS"
    start = datetime(2025, 5, 1, tzinfo=UTC)
    guard_start = datetime(2026, 5, 1, tzinfo=UTC)
    guard_end = datetime(2026, 6, 1, tzinfo=UTC)
    end_guard = datetime(2027, 5, 1, tzinfo=UTC)
    if start <= instant < guard_start:
        return str(1 if near_zero else 2), "DERIVED_FIRST_PHASE"
    if guard_end <= instant < end_guard:
        return str(3 if near_zero else 4), "DERIVED_SECOND_PHASE"
    return "", "PHASE_BOUNDARY_OR_DATE_OUTSIDE_GUARDED_RULE"


def parse_image_header(blob):
    from astropy.io import fits

    offset = 0
    headers = []
    for _ in range(2):
        end = None
        for position in range(offset, len(blob) - 79, 80):
            if blob[position : position + 8] == b"END     ":
                end = ((position + 80 + 2879) // 2880) * 2880
                break
        if end is None or end > len(blob):
            raise ValueError("Header exceeds available range")
        headers.append(fits.Header.fromstring(blob[offset:end].decode("ascii"), sep=""))
        offset = end
    if headers[0].get("NAXIS") != 0 or headers[1].get("EXTNAME") != "IMAGE":
        raise ValueError("Unexpected FITS primary/IMAGE layout")
    return headers[1], blob[:offset]


def fetch_header(item, cache, transport="irsa"):
    key, row = item
    filename = hashlib.sha256(key.encode()).hexdigest()[:24]
    saved = cache / (filename + ".json")
    if saved.exists():
        previous = json.loads(saved.read_text(encoding="utf-8"))
        header_path = cache / (filename + ".header")
        if (
            previous.get("status") == "HEADER_OK"
            and previous.get("source_url") == row["access_url"]
            and header_path.exists()
            and hashlib.sha256(header_path.read_bytes()).hexdigest()
            == previous.get("header_sha256")
        ):
            return previous
    url = row["access_url"]
    record = {
        "key": key,
        "obs_id": row["obs_id"],
        "collection": row["collection"],
        "source_url": url,
        "retrieved_utc": datetime.now(UTC).isoformat(),
    }
    try:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname != "irsa.ipac.caltech.edu":
            raise ValueError("Only official IRSA HTTPS URLs are permitted")
        request_url = url
        if transport == "aws":
            prefix = "/ibe/data/spherex/"
            if not parsed.path.startswith(prefix):
                raise ValueError("Unexpected IRSA archive path")
            request_url = (
                "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/"
                + parsed.path.removeprefix(prefix)
            )
        record["request_url"] = request_url
        request = Request(
            request_url,
            headers={
                "Range": "bytes=0-65535",
                "User-Agent": "Nguyen-SPHEREx-header-audit/1.0",
            },
        )
        with urlopen(request, timeout=40) as response:
            # Bounded read even if a server ignores the Range header.
            status = response.status
            content_range = response.headers.get("Content-Range", "")
            blob = response.read(65536)
        header, raw_header = parse_image_header(blob)
        if str(header.get("OBSID", "")) != row["obs_id"]:
            raise ValueError("Header OBSID does not match requested observation")
        pa_old, pa_new = header.get("SPS_PA_ECL"), header.get("SPS_EPA")
        if (
            pa_old is not None
            and pa_new is not None
            and abs(float(pa_old) - float(pa_new)) > 0.1
        ):
            raise ValueError("Conflicting PA header names")
        selected = {
            name: header.get(name)
            for name in (
                "OBSID",
                "DETECTOR",
                "DATE-OBS",
                "MJD-OBS",
                "SPS_FLAGS",
                "NON_SURVEY",
                "SPS_PA_ECL",
                "SPS_EPA",
            )
        }
        record.update(
            status="HEADER_OK",
            header=selected,
            http_status=status,
            content_range=content_range,
            header_bytes=len(raw_header),
            header_sha256=hashlib.sha256(raw_header).hexdigest(),
        )
        (cache / (filename + ".header")).write_bytes(raw_header)
    except (OSError, ValueError, HTTPException) as error:
        record.update(status="HEADER_ERROR", error=f"{type(error).__name__}: {error}")
    saved.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows, empty_fields):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=list(rows[0]) if rows else empty_fields
        )
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--positions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, choices=range(1, 7), default=6)
    parser.add_argument("--transport", choices=("irsa", "aws"), default="irsa")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    cache = args.output / "header-cache"
    cache.mkdir(exist_ok=True)
    rows = read_csv(args.metadata)
    positions = {r["record_id"]: r for r in read_csv(args.positions)}
    if len({r["record_id"] for r in rows}) != len(rows) or set(positions) != {
        r["record_id"] for r in rows
    }:
        raise ValueError("Require unique matching metadata and position IDs")
    exposures = {r["collection"] + ":" + r["obs_id"]: r for r in rows}
    headers = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [
            pool.submit(fetch_header, item, cache, args.transport)
            for item in exposures.items()
        ]
        for number, future in enumerate(as_completed(futures), 1):
            record = future.result()
            headers[record["key"]] = record
            if number % 50 == 0 or number == len(futures):
                errors = sum(r["status"] != "HEADER_OK" for r in headers.values())
                print(f"Headers: {number}/{len(futures)}; errors={errors}", flush=True)
    from astropy.time import Time

    classified = []
    for row in rows:
        record = headers[row["collection"] + ":" + row["obs_id"]]
        h = record.get("header", {})
        pa = (
            h.get("SPS_PA_ECL") if h.get("SPS_PA_ECL") is not None else h.get("SPS_EPA")
        )
        survey, reason = classify_survey(
            pa, h.get("DATE-OBS"), h.get("SPS_FLAGS"), h.get("NON_SURVEY")
        )
        if record["status"] != "HEADER_OK":
            survey, reason = "", "HEADER_ERROR"
        time_offset = None
        if record["status"] == "HEADER_OK" and h.get("DATE-OBS"):
            time_offset = (
                Time(h["DATE-OBS"], scale="utc").mjd - float(row["t_min"])
            ) * 86400
            if abs(time_offset) > 2:
                survey, reason = "", "HEADER_METADATA_TIME_MISMATCH"
        classified.append(
            {
                "record_id": row["record_id"],
                "target_id": row["target_id"],
                "collection": row["collection"],
                "detector": row["detector"],
                "obs_id": row["obs_id"],
                "date_obs_utc": h.get("DATE-OBS", ""),
                "planned_pa_deg": pa,
                "sps_flags": h.get("SPS_FLAGS", ""),
                "non_survey": h.get("NON_SURVEY", ""),
                "derived_survey_number": survey,
                "classification_status": reason,
                "header_source_url": record.get("request_url", record["source_url"]),
                "header_sha256": record.get("header_sha256", ""),
                "header_minus_metadata_start_seconds": time_offset,
                "header_scope": "Shared planned pointing across six detectors of the same OBSID, as documented",
            }
        )
    from collections import Counter, defaultdict

    from astropy import units as u
    from astropy.coordinates import SkyCoord
    from astropy.time import Time

    groups = defaultdict(lambda: defaultdict(list))
    for row in classified:
        if row["derived_survey_number"]:
            groups[(row["target_id"], row["collection"], row["detector"])][
                row["derived_survey_number"]
            ].append(row)
    pairs = []
    for (target, collection, detector), surveys in sorted(groups.items()):
        representatives = []
        for survey, members in sorted(surveys.items()):
            members.sort(key=lambda r: float(positions[r["record_id"]]["mjd_mid"]))
            representatives.append(members[len(members) // 2])
        for first, second in combinations(representatives, 2):
            first, second = sorted(
                [first, second],
                key=lambda r: float(positions[r["record_id"]]["mjd_mid"]),
            )
            a, b = positions[first["record_id"]], positions[second["record_id"]]
            ca = SkyCoord(
                float(a["predicted_icrs_ra_deg"]) * u.deg,
                float(a["predicted_icrs_dec_deg"]) * u.deg,
            )
            cb = SkyCoord(
                float(b["predicted_icrs_ra_deg"]) * u.deg,
                float(b["predicted_icrs_dec_deg"]) * u.deg,
            )
            baseline = (
                Time(float(b["mjd_mid"]), format="mjd", scale="utc")
                - Time(float(a["mjd_mid"]), format="mjd", scale="utc")
            ).to_value(u.yr)
            pairs.append(
                {
                    "target_id": target,
                    "collection": collection,
                    "detector": detector,
                    "record_id_1": first["record_id"],
                    "record_id_2": second["record_id"],
                    "derived_survey_1": first["derived_survey_number"],
                    "derived_survey_2": second["derived_survey_number"],
                    "baseline_julian_years": baseline,
                    "expected_separation_arcsec": ca.separation(cb).arcsec,
                    "nominal_displacement_pixels_6p15": ca.separation(cb).arcsec / 6.15,
                    "status": "PREDICTION_BETWEEN_DOCUMENT_RULE_DERIVED_SURVEYS_IMAGE_QA_PENDING",
                }
            )
    write_csv(args.output / "survey_classification.csv", classified, ["record_id"])
    write_csv(
        args.output / "expected_motion_between_surveys.csv",
        pairs,
        ["target_id", "status"],
    )
    manifest = {
        "status": "DOCUMENT_RULE_DERIVED_LABELS_NOT_ARCHIVE_ISSUED_IDS",
        "observation_count": len(rows),
        "unique_exposure_headers": len(headers),
        "header_errors": sum(r["status"] != "HEADER_OK" for r in headers.values()),
        "classification_counts": dict(
            Counter(r["classification_status"] for r in classified)
        ),
        "survey_counts": dict(
            Counter(r["derived_survey_number"] or "UNCLASSIFIED" for r in classified)
        ),
        "pair_count": len(pairs),
        "sources": [SUPPLEMENT, START_SOURCE],
        "source_document_version": "2.0, 2026-08-25; survey definition pp.8-9 and header description p.14",
        "source_document_sha256": hashlib.sha256(
            (args.output / "SPHEREx_Expsupp_QR-current.pdf").read_bytes()
        ).hexdigest()
        if (args.output / "SPHEREx_Expsupp_QR-current.pdf").exists()
        else None,
        "policy": "Science start 2025-05-01; PA 0/180 degrees within 0.1 degree; all_sky only; May 2026 and dates beyond conservative phase bounds remain unclassified. No exact UTC 12.5-month boundary invented.",
        "header_reuse": "Planned pointing is identical across all six bands for a single observation according to the supplement.",
        "representative_policy": "Median-time available observation per target/detector/release/derived survey; pair order follows actual observation time, not survey number.",
        "limitations": "Catalog angular proper-motion predictions only. No parallax/orbits/perspective acceleration, matching bandpass, detection or image-motion claims.",
        "inputs": {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (args.metadata, args.positions)
        },
    }
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2), flush=True)
    if manifest["header_errors"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
