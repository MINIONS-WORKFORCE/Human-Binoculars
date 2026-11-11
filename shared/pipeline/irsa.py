"""SPHEREx IRSA Data Access Module (shared/pipeline/irsa.py).
Contract owner: Khoi (members/khoi).
Consumers: Dong (backend), Huu Hoang (image processing).

Provides SIA2 queries with automatic TAP fallback, cutout download,
and manifest.json generation conforming to SRS-MVP Section 6.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import math
import re
import time
import urllib.parse
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

IRSA_SIA_URL = "https://irsa.ipac.caltech.edu/SIA"
IRSA_TAP_URL = "https://irsa.ipac.caltech.edu/TAP/sync"


class UpstreamError(Exception):
    """Raised when IRSA returns an error or unparseable response."""


class UpstreamTimeout(UpstreamError):
    """Raised when IRSA times out repeatedly."""


def _normalize_detector(det: str | int | None) -> str | None:
    if det is None:
        return None
    s = str(det).strip()
    m = re.search(r"D?([1-6])$", s, re.IGNORECASE)
    if m:
        return f"SPHEREx-D{m.group(1)}"
    return s


def _request_with_retry(
    url: str,
    params: dict[str, Any] | None = None,
    *,
    timeout_s: int = 120,
    retries: int = 3,
) -> requests.Response:
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=timeout_s)
            if resp.status_code == 502 or resp.status_code >= 500:
                raise UpstreamError(f"HTTP {resp.status_code} server error from {url}")
            resp.raise_for_status()
            return resp
        except requests.Timeout as exc:
            last_err = UpstreamTimeout(f"Timeout after {timeout_s}s connecting to {url}: {exc}")
        except Exception as exc:
            last_err = UpstreamError(f"Request failed: {exc}")
        if attempt < retries - 1:
            time.sleep(2**attempt)
    raise last_err or UpstreamError("Request failed after retries")


def _parse_votable_xml(xml_bytes: bytes) -> list[dict[str, Any]]:
    """Parse SIA2 VOTable response using astropy.table.Table."""
    try:
        from astropy.table import Table

        table = Table.read(io.BytesIO(xml_bytes), format="votable", use_names_over_ids=True)
        results: list[dict[str, Any]] = []
        fields = (
            "obs_id",
            "obs_publisher_did",
            "obs_collection",
            "energy_bandpassname",
            "s_ra",
            "s_dec",
            "t_min",
            "t_max",
            "access_url",
            "access_format",
        )
        for row in table:
            entry: dict[str, Any] = {}
            for col in fields:
                if col in row.colnames:
                    val = row[col]
                    entry[col] = val.item() if hasattr(val, "item") else val
                else:
                    entry[col] = None
            results.append(entry)
        return results
    except Exception as exc:
        raise UpstreamError(f"Failed to parse VOTable from IRSA: {exc}") from exc


def _query_tap_fallback(
    ra_deg: float,
    dec_deg: float,
    collection: str,
    detector: str | None = None,
    t_min: float | None = None,
    t_max: float | None = None,
    timeout_s: int = 120,
) -> list[dict[str, Any]]:
    """Fallback query via IRSA TAP ADQL service."""
    adql_parts = [
        "SELECT",
        "  'https://irsa.ipac.caltech.edu/' || a.uri AS access_url,",
        "  p.obs_publisher_did,",
        "  p.obs_id,",
        "  p.collection AS obs_collection,",
        "  p.energy_bandpassname,",
        "  p.time_bounds_lower AS t_min,",
        "  p.time_bounds_upper AS t_max",
        "FROM spherex.artifact a",
        "JOIN spherex.plane p ON a.planeid = p.planeid",
        f"WHERE 1 = CONTAINS(POINT('ICRS', {ra_deg:.8f}, {dec_deg:.8f}), p.poly)",
        "  AND a.uri LIKE '%.fits'",
    ]
    if collection:
        adql_parts.append(f"  AND p.collection = '{collection}'")
    if detector:
        norm_det = _normalize_detector(detector)
        adql_parts.append(f"  AND p.energy_bandpassname = '{norm_det}'")
    if t_min is not None:
        adql_parts.append(f"  AND p.time_bounds_upper >= {t_min}")
    if t_max is not None:
        adql_parts.append(f"  AND p.time_bounds_lower <= {t_max}")
    adql_parts.append("ORDER BY p.time_bounds_lower ASC")

    adql = "\n".join(adql_parts)
    logger.info("Executing TAP fallback ADQL:\n%s", adql)

    params = {
        "REQUEST": "doQuery",
        "LANG": "ADQL",
        "FORMAT": "votable",
        "QUERY": adql,
    }
    resp = _request_with_retry(IRSA_TAP_URL, params=params, timeout_s=timeout_s, retries=2)
    return _parse_votable_xml(resp.content)


def find_images(
    ra_deg: float,
    dec_deg: float,
    collection: str = "spherex_qr2",
    detector: str | None = None,
    t_min: float | None = None,
    t_max: float | None = None,
    *,
    search_radius_deg: float = 0.05,
    timeout_s: int = 120,
    retries: int = 3,
) -> list[dict[str, Any]]:
    """Query IRSA for SPHEREx images covering (ra_deg, dec_deg).

    First attempts the IVOA SIA2 endpoint. If SIA2 fails, times out, or returns 502,
    automatically falls back to the IRSA TAP service.

    Returns a list of dicts with keys:
        obs_id, obs_publisher_did, obs_collection, energy_bandpassname,
        s_ra, s_dec, t_min, t_max, access_url, access_format.
    """
    norm_det = _normalize_detector(detector)
    sia_params: dict[str, Any] = {
        "COLLECTION": collection,
        "POS": f"CIRCLE {ra_deg:.8f} {dec_deg:.8f} {search_radius_deg:.6f}",
    }
    if t_min is not None or t_max is not None:
        t_low = f"{t_min}" if t_min is not None else "-Inf"
        t_high = f"{t_max}" if t_max is not None else "+Inf"
        sia_params["TIME"] = f"{t_low} {t_high}"

    raw_entries: list[dict[str, Any]] = []
    # Step 1: Attempt SIA2
    try:
        resp = _request_with_retry(IRSA_SIA_URL, params=sia_params, timeout_s=timeout_s, retries=retries)
        raw_entries = _parse_votable_xml(resp.content)
    except Exception as exc:
        logger.warning("SIA2 query failed (%s). Triggering TAP fallback...", exc)
        # Step 2: Fallback to TAP
        try:
            raw_entries = _query_tap_fallback(
                ra_deg,
                dec_deg,
                collection,
                detector=norm_det,
                t_min=t_min,
                t_max=t_max,
                timeout_s=timeout_s,
            )
        except Exception as tap_exc:
            raise UpstreamError(f"Both SIA2 and TAP queries failed. TAP error: {tap_exc}") from tap_exc

    # Deduplicate and filter by detector and collection
    seen_did: set[str] = set()
    filtered: list[dict[str, Any]] = []
    for item in raw_entries:
        did = str(item.get("obs_publisher_did") or item.get("obs_id") or item.get("access_url"))
        if did in seen_did:
            continue
        seen_did.add(did)

        # Check detector match
        bandpass = str(item.get("energy_bandpassname", ""))
        if norm_det and _normalize_detector(bandpass) != norm_det:
            continue
        # Check collection match if specified
        coll = str(item.get("obs_collection", ""))
        if collection and coll and coll != collection:
            continue

        filtered.append(item)

    # Sort deterministically by observation time (t_min)
    filtered.sort(key=lambda x: float(x.get("t_min") or 0.0))
    return filtered


def make_cutout_url(access_url: str, ra_deg: float, dec_deg: float, size_deg: float) -> str:
    """Construct standard IRSA cutout URL parameter format."""
    clean_url = str(access_url).strip()
    if not clean_url.startswith(("http://", "https://")):
        clean_url = "https://irsa.ipac.caltech.edu/" + clean_url.lstrip("/")
    sep = "&" if "?" in clean_url else "?"
    return f"{clean_url}{sep}center={ra_deg:.8f},{dec_deg:.8f}d&size={size_deg:.6f}"


def group_images_into_visits(images: list[dict[str, Any]], gap_days: float = 30.0) -> list[list[dict[str, Any]]]:
    """Group observations into separate visits when separated by more than gap_days."""
    if not images:
        return []
    sorted_imgs = sorted(images, key=lambda x: float(x.get("t_min") or 0.0))
    visits: list[list[dict[str, Any]]] = [[sorted_imgs[0]]]
    for img in sorted_imgs[1:]:
        prev_mjd = float(visits[-1][-1].get("t_min") or 0.0)
        curr_mjd = float(img.get("t_min") or 0.0)
        if curr_mjd - prev_mjd > gap_days:
            visits.append([img])
        else:
            visits[-1].append(img)
    return visits


def fetch_cutouts(
    images: list[dict[str, Any]],
    ra_deg: float,
    dec_deg: float,
    size_deg: float,
    out_dir: str | Path,
    *,
    max_per_visit: int = 6,
    timeout_s: int = 120,
    retries: int = 3,
) -> Path:
    """Downloads SPHEREx FITS cutouts from IRSA and writes manifest.json.

    Args:
        images: List of observation dicts from find_images().
        ra_deg: Right Ascension center in degrees.
        dec_deg: Declination center in degrees.
        size_deg: Cutout angular edge size in degrees (e.g. 0.05 or 0.1).
        out_dir: Destination directory for downloaded FITS files and manifest.
        max_per_visit: Maximum cutouts to download per observation visit group.
        timeout_s: Request timeout in seconds.
        retries: Number of retries per cutout download.

    Returns:
        Path to the generated manifest.json file.
    """
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    visits = group_images_into_visits(images, gap_days=30.0)
    selected_images: list[dict[str, Any]] = []
    for visit in visits:
        selected_images.extend(visit[:max_per_visit])

    entries: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []

    for idx, item in enumerate(selected_images, start=1):
        access_url = item.get("access_url")
        obs_id = str(item.get("obs_id") or f"obs_{idx:03d}")
        did = str(item.get("obs_publisher_did") or obs_id)
        bandpass = str(item.get("energy_bandpassname") or "D")
        det_short = bandpass.replace("SPHEREx-", "")
        mjd = float(item.get("t_min") or 0.0)
        t_max = float(item.get("t_max") or mjd)

        if not access_url:
            failed.append({"obs_id": obs_id, "reason": "Missing access_url in record"})
            continue

        cutout_url = make_cutout_url(access_url, ra_deg, dec_deg, size_deg)
        safe_obs = re.sub(r"[^A-Za-z0-9_.-]", "_", obs_id)
        filename = f"{safe_obs}_{det_short}_{idx:02d}.fits"
        dest_file = out_path / filename

        download_ok = False
        last_error = ""
        for attempt in range(retries):
            try:
                resp = requests.get(cutout_url, timeout=timeout_s)
                resp.raise_for_status()
                content = resp.content
                # Quick verification that it is a valid FITS file (starts with SIMPLE =)
                if not content.startswith(b"SIMPLE  ="):
                    raise ValueError("Downloaded content does not begin with standard FITS 'SIMPLE  =' header")
                dest_file.write_bytes(content)
                sha256 = hashlib.sha256(content).hexdigest()
                entries.append({
                    "obs_id": obs_id,
                    "obs_publisher_did": did,
                    "detector": det_short,
                    "mjd": mjd,
                    "t_max": t_max,
                    "path": str(dest_file.relative_to(out_path.parent if out_path.parent != out_path else out_path)),
                    "file_size": len(content),
                    "sha256": sha256,
                    "cutout_url": cutout_url,
                })
                download_ok = True
                break
            except Exception as exc:
                last_error = str(exc)
                if dest_file.exists():
                    dest_file.unlink(missing_ok=True)
                time.sleep(2**attempt)

        if not download_ok:
            failed.append({"obs_id": obs_id, "reason": last_error or "Download failed"})

    coll = images[0].get("obs_collection", "spherex_qr2") if images else "spherex_qr2"
    manifest_data = {
        "query": {
            "ra_deg": ra_deg,
            "dec_deg": dec_deg,
            "collection": coll,
            "size_deg": size_deg,
            "total_candidates": len(images),
            "downloaded": len(entries),
        },
        "failed": failed,
        "entries": entries,
    }

    manifest_path = out_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
    return manifest_path
