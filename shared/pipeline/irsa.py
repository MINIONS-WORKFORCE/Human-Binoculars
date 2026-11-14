"""SPHEREx IRSA Data Access Module (shared/pipeline/irsa.py).
Contract owner: Khoi (members/khoi).
Consumers: Dong (backend), Huu Hoang (image processing).

Provides SIA2 queries with automatic TAP fallback, cutout download,
and manifest.json generation conforming to SRS-MVP Section 6.
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import math
import re
import time
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


def _remaining_timeout(timeout_s: float, deadline: float | None) -> float:
    if deadline is None:
        return timeout_s
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise UpstreamTimeout("IRSA request deadline exceeded")
    return min(timeout_s, remaining)


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
    deadline: float | None = None,
) -> requests.Response:
    last_err: Exception | None = None
    for attempt in range(retries):
        timeout = _remaining_timeout(timeout_s, deadline)
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            if resp.status_code == 502 or resp.status_code >= 500:
                raise UpstreamError(f"HTTP {resp.status_code} server error from {url}")
            resp.raise_for_status()
            return resp
        except requests.Timeout as exc:
            last_err = UpstreamTimeout(f"Timeout after {timeout_s}s connecting to {url}: {exc}")
        except (requests.RequestException, UpstreamError) as exc:
            last_err = UpstreamError(f"Request failed: {exc}")
        if attempt < retries - 1:
            time.sleep(_remaining_timeout(2**attempt, deadline))
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
    deadline: float | None = None,
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
    resp = _request_with_retry(
        IRSA_TAP_URL, params=params, timeout_s=timeout_s, retries=2, deadline=deadline
    )
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
    deadline: float | None = None,
    tap_fallback: bool = True,
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
        resp = _request_with_retry(
            IRSA_SIA_URL, params=sia_params, timeout_s=timeout_s, retries=retries, deadline=deadline
        )
        raw_entries = _parse_votable_xml(resp.content)
    except UpstreamError as exc:
        if not tap_fallback:
            raise
        logger.warning("SIA2 query failed (%s). Trying TAP fallback.", type(exc).__name__)
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
                deadline=deadline,
            )
        except UpstreamTimeout:
            raise
        except UpstreamError as tap_exc:
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
    deadline: float | None = None,
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
        failure_kind = "upstream"
        for attempt in range(retries):
            timeout = _remaining_timeout(timeout_s, deadline)
            try:
                resp = requests.get(cutout_url, timeout=timeout)
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
            except (requests.RequestException, OSError, ValueError) as exc:
                last_error = str(exc)
                failure_kind = "timeout" if isinstance(exc, requests.Timeout) else "upstream"
                if dest_file.exists():
                    dest_file.unlink(missing_ok=True)
                if attempt < retries - 1:
                    time.sleep(_remaining_timeout(2**attempt, deadline))

        if not download_ok:
            failed.append({
                "obs_id": obs_id, "reason": last_error or "Download failed", "kind": failure_kind,
            })

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


def download_cutout(
    access_url: str,
    ra_deg: float,
    dec_deg: float,
    size_deg: float,
    dest_path: Path | str,
    *,
    expected_obs_id: str | None = None,
    timeout_s: int = 120,
    retries: int = 3,
) -> Path:
    """Download a single SPHEREx FITS cutout from IRSA with retry, validation, and OBSID check.

    Returns:
        Path to the downloaded FITS file.
    """
    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    cutout_url = make_cutout_url(access_url, ra_deg, dec_deg, size_deg)

    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            try:
                resp = requests.get(cutout_url, timeout=timeout_s)
            except requests.exceptions.SSLError:
                import urllib3

                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                resp = requests.get(cutout_url, timeout=timeout_s, verify=False)
            if resp.status_code == 422:
                raise ValueError(
                    f"HTTP 422 Unprocessable Content: center ({ra_deg:.6f}, {dec_deg:.6f}) outside exposure bounds"
                )
            resp.raise_for_status()
            content = resp.content
            if not content.startswith(b"SIMPLE  ="):
                raise ValueError("Response content does not begin with standard FITS 'SIMPLE  =' header")
            if expected_obs_id:
                try:
                    from astropy.io import fits

                    with fits.open(io.BytesIO(content)) as h:
                        h.verify("silentfix")
                        obsid_hdr = str(h["IMAGE"].header.get("OBSID", "")) if "IMAGE" in h else ""
                        if obsid_hdr and obsid_hdr != str(expected_obs_id):
                            raise ValueError(
                                f"Unexpected observation header OBSID '{obsid_hdr}' != expected '{expected_obs_id}'"
                            )
                except ImportError:
                    pass
            dest.write_bytes(content)
            return dest
        except Exception as exc:
            last_error = exc
            if dest.exists():
                dest.unlink(missing_ok=True)
            if attempt < retries - 1 and "HTTP 422" not in str(exc):
                time.sleep(2**attempt)
    raise last_error or UpstreamError(f"Failed to download cutout from {cutout_url}")


def _normalize_target_key(key: str | None) -> str | None:
    if not key:
        return None
    k = str(key).strip().lower()
    k = re.sub(r"[^a-z0-9]", "", k)
    # Map common variations
    mapping = {
        "barnard": "barnard",
        "barnardsstar": "barnard",
        "gj699": "barnard",
        "wise0855": "wise0855",
        "wise08550714": "wise0855",
        "wisej085510830714425": "wise0855",
        "epsindib": "epsindib",
        "epsilonindib": "epsindib",
        "gj845b": "epsindib",
        "rwaur": "rwaur",
        "rwaurigae": "rwaur",
        "rdra": "rdra",
        "rdraconis": "rdra",
    }
    return mapping.get(k, k)


def find_frames(
    query: dict[str, Any] | None = None,
    *,
    target_key: str | None = None,
    ra_deg: float | None = None,
    dec_deg: float | None = None,
    detector: str | int | None = None,
    collection: str = "spherex_qr2",
    cutout_size_deg: float = 0.0833,
    data_dir: Path | str | None = None,
    mode: str = "fixture",
    max_frames: int | None = None,
) -> list[dict[str, Any]]:
    """Finds SPHEREx observation frames in either offline fixture mode or live mode.

    Fulfills contract in SRS-MVP Section 6 and Issue #21.
    In 'fixture' mode: operates 100% offline without network calls.
    In 'live' mode: queries IRSA and fetches cutouts dynamically.

    Returns:
        List of frame dictionaries containing:
        obs_id, obs_publisher_did, target_key, detector, energy_bandpassname,
        mjd, t_min, t_max, ra, dec, fits_path, sha256, file_size.
    """
    # Extract params from query dict if provided
    q = query or {}
    t_key = target_key or q.get("target_key") or q.get("id") or q.get("target")
    norm_t_key = _normalize_target_key(t_key)
    ra = ra_deg if ra_deg is not None else q.get("ra") or q.get("ra_deg") or q.get("s_ra")
    dec = dec_deg if dec_deg is not None else q.get("dec") or q.get("dec_deg") or q.get("s_dec")
    det = detector if detector is not None else q.get("detector") or q.get("energy_bandpassname")
    norm_det = _normalize_detector(det)
    coll = q.get("collection") or q.get("obs_collection") or collection
    size_deg = q.get("cutout_size_deg") or cutout_size_deg
    active_mode = q.get("data_mode") or q.get("mode") or mode
    max_f = max_frames or q.get("max_frames")

    root = Path(__file__).resolve().parents[2]
    d_dir = Path(data_dir) if data_dir else root / "data"

    if active_mode == "fixture":
        # Search candidate manifest paths
        manifest_candidates = [
            d_dir / "fixtures" / "manifest.json",
            root / "data" / "fixtures" / "manifest.json",
            root / "members" / "khoi" / "fixtures_manifest.json",
            d_dir / "cutouts" / "barnard_d6" / "manifest.json",
        ]
        manifest_path = next((p for p in manifest_candidates if p.exists()), None)
        if not manifest_path:
            logger.warning("No fixture manifest found in candidate locations: %s", manifest_candidates)
            return []

        try:
            manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            logger.error("Failed to read manifest %s: %s", manifest_path, exc)
            return []

        entries = manifest_data.get("entries", [])
        matched_frames: list[dict[str, Any]] = []

        for e in entries:
            # 1. Check target_key match
            entry_target = _normalize_target_key(e.get("target_key") or e.get("target_name"))
            if norm_t_key and entry_target and entry_target != norm_t_key:
                continue

            # 2. Check detector match if requested
            entry_det = _normalize_detector(e.get("detector") or e.get("energy_bandpassname"))
            if norm_det and entry_det and entry_det != norm_det:
                continue

            # 3. Check spatial coordinates distance if ra & dec specified and no target_key
            if not norm_t_key and ra is not None and dec is not None:
                e_ra = float(e.get("ra") or e.get("s_ra") or 0.0)
                e_dec = float(e.get("dec") or e.get("s_dec") or 0.0)
                dist = math.hypot(e_ra - float(ra), e_dec - float(dec))
                if dist > 0.15:  # Tolerance radius
                    continue

            # Resolve local absolute fits_path
            raw_path = str(e.get("fits_path") or e.get("path") or "")
            fits_path = root / raw_path if not Path(raw_path).is_absolute() else Path(raw_path)

            frame_dict = {
                "obs_id": str(e.get("obs_id", "")),
                "obs_publisher_did": str(e.get("obs_publisher_did", "")),
                "target_key": e.get("target_key", t_key),
                "detector": entry_det or e.get("detector", ""),
                "energy_bandpassname": entry_det or e.get("energy_bandpassname", ""),
                "mjd": float(e.get("mjd") or e.get("t_min") or 0.0),
                "t_min": float(e.get("t_min") or e.get("mjd") or 0.0),
                "t_max": float(e.get("t_max") or e.get("mjd") or 0.0),
                "ra": float(e.get("ra") or ra or 0.0),
                "dec": float(e.get("dec") or dec or 0.0),
                "fits_path": str(fits_path),
                "sha256": e.get("sha256", ""),
                "file_size": e.get("file_size", 0),
            }
            matched_frames.append(frame_dict)

        # Sort by MJD
        matched_frames.sort(key=lambda x: x["mjd"])
        if max_f is not None and max_f > 0:
            matched_frames = matched_frames[:max_f]
        return matched_frames

    # Live mode: network fetch
    if ra is None or dec is None:
        raise ValueError("Live mode requires coordinates ra_deg and dec_deg")

    imgs = find_images(float(ra), float(dec), collection=coll, detector=norm_det, search_radius_deg=size_deg)
    out_cache = d_dir / "cache" / f"live_{float(ra):.4f}_{float(dec):.4f}"
    m_path = fetch_cutouts(imgs, float(ra), float(dec), float(size_deg), out_cache)
    m_data = json.loads(m_path.read_text(encoding="utf-8"))
    live_results = []
    for en in m_data.get("entries", []):
        live_results.append({
            "obs_id": en["obs_id"],
            "obs_publisher_did": en["obs_publisher_did"],
            "target_key": t_key,
            "detector": en["detector"],
            "energy_bandpassname": f"SPHEREx-{en['detector']}" if not en['detector'].startswith("SPHEREx-") else en['detector'],
            "mjd": en["mjd"],
            "t_min": en["mjd"],
            "t_max": en["t_max"],
            "ra": float(ra),
            "dec": float(dec),
            "fits_path": str(out_cache / en["path"]),
            "sha256": en["sha256"],
            "file_size": en.get("file_size", 0),
        })
    if max_f is not None and max_f > 0:
        live_results = live_results[:max_f]
    return live_results
