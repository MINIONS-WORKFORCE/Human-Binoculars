"""SPHEREx & Multi-Mission Data Harvester / Scraper.

Author: Khôi (Backend / IRSA Data & Database Specialist)
NASA Space Apps Challenge 2026 - SPHEREx Sky Viewer

Harvests observation cutouts and catalogs for the challenge targets:
  - SPHEREx: Level 2 / QR3 FITS cutouts via IRSA SIA2/IBE
  - WISE: AllWISE W1/W2 historical FITS cutouts via IRSA IBE
  - Gaia DR3: Astrometry & Proper Motion catalog via ESA/CDS TAP
  - SQLite: Metadata storage in spherex_sia2.db
  - Manifest: Standardized manifest.json for backend & frontend consumption
"""

from __future__ import annotations

import argparse
import concurrent.futures
import gzip
import hashlib
import json
import logging
import math
import os
import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import requests

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("fetcher")

# Official NASA Space Apps Challenge Targets
DEFAULT_TARGETS: dict[str, dict[str, Any]] = {
    "barnard": {
        "name": "Barnard's Star",
        "ra": 269.452077,
        "dec": 4.693365,
        "description": "High proper motion M-dwarf star (~10.36 arcsec/yr)",
    },
    "wise0855": {
        "name": "WISE 0855-0714",
        "ra": 133.818908,
        "dec": -7.247048,
        "description": "Sub-zero cold brown dwarf (~250K) with rapid motion",
    },
    "epsindib": {
        "name": "Epsilon Indi B",
        "ra": 331.044147,
        "dec": -56.782844,
        "description": "Nearby brown dwarf binary system (Ba/Bb)",
    },
    "rwaur": {
        "name": "RW Aurigae",
        "ra": 76.956526,
        "dec": 30.401438,
        "description": "Young variable T Tauri star undergoing accretion",
    },
    "rdra": {
        "name": "R Draconis",
        "ra": 248.167611,
        "dec": 66.754979,
        "description": "Mira-type long period variable star (~245 days)",
    },
}

IRSA_SIA_URL = "https://irsa.ipac.caltech.edu/SIA"
WISE_IBE_SEARCH_URL = "https://irsa.ipac.caltech.edu/ibe/search/wise/allwise/p3am_cdd"
WISE_IBE_DATA_BASE = "https://irsa.ipac.caltech.edu/ibe/data/wise/allwise/p3am_cdd"


# -----------------------------------------------------------------------------
# SQLite Database Utilities
# -----------------------------------------------------------------------------
def init_database(db_path: Path) -> sqlite3.Connection:
    """Initializes the SQLite schema for observations, cutouts, and Gaia stars."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS observations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        obs_id TEXT NOT NULL,
        obs_publisher_did TEXT,
        target_key TEXT NOT NULL,
        mission TEXT NOT NULL,
        release TEXT,
        detector TEXT,
        mjd REAL,
        ra REAL,
        dec REAL,
        cutout_size_deg REAL,
        fits_path TEXT NOT NULL,
        file_size INTEGER,
        sha256 TEXT,
        cutout_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(obs_id, detector, cutout_size_deg)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS gaia_stars (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id TEXT NOT NULL,
        target_key TEXT NOT NULL,
        ra REAL NOT NULL,
        dec REAL NOT NULL,
        parallax REAL,
        pmra REAL,
        pmdec REAL,
        phot_g_mean_mag REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(source_id, target_key)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS harvest_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        target_key TEXT,
        source TEXT,
        count INTEGER,
        status TEXT,
        message TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    return conn


# -----------------------------------------------------------------------------
# SPHEREx Harvester
# -----------------------------------------------------------------------------
def harvest_spherex(
    target_key: str,
    ra: float,
    dec: float,
    size_deg: float,
    out_dir: Path,
    collection: str = "spherex_qr3",
    max_frames: int = 6,
    timeout_s: int = 90,
    retries: int = 3,
) -> list[dict[str, Any]]:
    """Harvests SPHEREx cutouts from IRSA SIA2/TAP service."""
    logger.info(f"[{target_key}] Querying IRSA SIA2 (collection={collection}, size={size_deg}°)...")
    target_dir = out_dir / target_key / "spherex"
    target_dir.mkdir(parents=True, exist_ok=True)

    try:
        from shared.pipeline.irsa import find_images, make_cutout_url
        raw_images = find_images(
            ra,
            dec,
            collection=collection,
            search_radius_deg=size_deg,
            timeout_s=timeout_s,
            retries=retries,
        )
    except Exception as exc:
        logger.warning(f"[{target_key}] SIA2 query failed: {exc}")
        return []

    if not raw_images:
        logger.warning(f"[{target_key}] IRSA returned 0 images in {collection}.")
        return []

    logger.info(f"[{target_key}] Found {len(raw_images)} SPHEREx images in {collection}. Downloading top {max_frames}...")

    # Group and pick up to max_frames per detector
    images_by_det: dict[str, list[dict[str, Any]]] = {}
    for img in raw_images:
        band = str(img.get("energy_bandpassname") or "D1")
        det = band.replace("SPHEREx-", "")
        images_by_det.setdefault(det, []).append(img)

    selected: list[dict[str, Any]] = []
    for det, rows in images_by_det.items():
        selected.extend(rows[:max_frames])

    def _download_single(row_item: dict[str, Any], idx: int) -> dict[str, Any] | None:
        access_url = row_item.get("access_url")
        if not access_url:
            return None
        obs_id = str(row_item.get("obs_id") or f"obs_{idx}")
        did = str(row_item.get("obs_publisher_did") or obs_id)
        bandpass = str(row_item.get("energy_bandpassname") or "D1")
        det = bandpass.replace("SPHEREx-", "")
        mjd = float(row_item.get("t_min") or 0.0)

        c_url = make_cutout_url(str(access_url), ra, dec, size_deg)
        safe_obs = re.sub(r"[^A-Za-z0-9_.-]", "_", obs_id)
        out_file = target_dir / f"{target_key}_{det}_{safe_obs}.fits"

        if out_file.exists() and out_file.stat().st_size > 1000:
            content = out_file.read_bytes()
            sha256 = hashlib.sha256(content).hexdigest()
            return {
                "obs_id": obs_id,
                "obs_publisher_did": did,
                "target_key": target_key,
                "mission": "SPHEREx",
                "release": collection,
                "detector": det,
                "mjd": mjd,
                "ra": ra,
                "dec": dec,
                "cutout_size_deg": size_deg,
                "fits_path": str(out_file),
                "file_size": len(content),
                "sha256": sha256,
                "cutout_url": c_url,
            }

        for attempt in range(retries):
            try:
                r = requests.get(c_url, timeout=timeout_s)
                r.raise_for_status()
                if not r.content.startswith(b"SIMPLE  ="):
                    raise ValueError("Not a valid FITS file")
                out_file.write_bytes(r.content)
                sha256 = hashlib.sha256(r.content).hexdigest()
                logger.info(f"  [+] Downloaded: {out_file.name} ({len(r.content):,} bytes)")
                return {
                    "obs_id": obs_id,
                    "obs_publisher_did": did,
                    "target_key": target_key,
                    "mission": "SPHEREx",
                    "release": collection,
                    "detector": det,
                    "mjd": mjd,
                    "ra": ra,
                    "dec": dec,
                    "cutout_size_deg": size_deg,
                    "fits_path": str(out_file),
                    "file_size": len(r.content),
                    "sha256": sha256,
                    "cutout_url": c_url,
                }
            except Exception as e:
                time.sleep(1.5 ** attempt)
        return None

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(_download_single, r, i) for i, r in enumerate(selected)]
        for f in concurrent.futures.as_completed(futures):
            res = f.result()
            if res:
                results.append(res)

    return results


# -----------------------------------------------------------------------------
# AllWISE Harvester
# -----------------------------------------------------------------------------
def harvest_wise(
    target_key: str,
    ra: float,
    dec: float,
    size_deg: float,
    out_dir: Path,
    bands: tuple[int, ...] = (1, 2),  # W1=3.4um, W2=4.6um
    timeout_s: int = 60,
    retries: int = 3,
) -> list[dict[str, Any]]:
    """Harvests historical AllWISE coadd FITS cutouts from IRSA IBE service (~2010 epoch)."""
    logger.info(f"[{target_key}] Searching AllWISE coadds at ({ra:.4f}, {dec:.4f})...")
    target_dir = out_dir / target_key / "wise"
    target_dir.mkdir(parents=True, exist_ok=True)

    try:
        resp = requests.get(WISE_IBE_SEARCH_URL, params={"POS": f"{ra},{dec}"}, timeout=timeout_s)
        resp.raise_for_status()
    except Exception as exc:
        logger.warning(f"[{target_key}] WISE IBE search failed: {exc}")
        return []

    # Parse coadd_id from IPAC table
    coadd_id = None
    try:
        from astropy.io import ascii as astropy_ascii
        tbl = astropy_ascii.read(resp.text, format="ipac")
        if len(tbl) > 0 and "coadd_id" in tbl.colnames:
            coadd_id = str(tbl["coadd_id"][0]).strip()
    except Exception as parse_err:
        logger.debug(f"[{target_key}] Astropy IPAC parse note: {parse_err}")

    if not coadd_id:
        # Fallback regex search
        match = re.search(r"(\d{4}[pm]\d{3}(?:_[a-z0-9]+)?)", resp.text)
        if match:
            coadd_id = match.group(1)

    if not coadd_id:
        logger.warning(f"[{target_key}] Could not identify coadd_id from WISE metadata.")
        return []

    logger.info(f"[{target_key}] Found AllWISE coadd tile: {coadd_id}")
    g1 = coadd_id[:2]
    g2 = coadd_id[:4]

    results = []
    for band in bands:
        band_name = f"W{band}"
        fits_filename = f"{coadd_id}-w{band}-int-3.fits"
        cutout_url = (
            f"{WISE_IBE_DATA_BASE}/{g1}/{g2}/{coadd_id}/{fits_filename}"
            f"?center={ra:.6f},{dec:.6f}&size={size_deg:.6f}"
        )
        out_file = target_dir / f"{target_key}_wise_{band_name}.fits"

        if out_file.exists() and out_file.stat().st_size > 1000:
            content = out_file.read_bytes()
            results.append({
                "obs_id": f"WISE_{coadd_id}_{band_name}",
                "obs_publisher_did": f"ivo://irsa.ipac/wise?{coadd_id}/{band_name}",
                "target_key": target_key,
                "mission": "WISE",
                "release": "AllWISE",
                "detector": band_name,
                "mjd": 55300.0,  # ~2010 nominal coadd epoch
                "ra": ra,
                "dec": dec,
                "cutout_size_deg": size_deg,
                "fits_path": str(out_file),
                "file_size": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
                "cutout_url": cutout_url,
            })
            continue

        for attempt in range(retries):
            try:
                r = requests.get(cutout_url, timeout=timeout_s)
                r.raise_for_status()
                raw_bytes = r.content
                if raw_bytes[:2] == b"\x1f\x8b":
                    fits_bytes = gzip.decompress(raw_bytes)
                else:
                    fits_bytes = raw_bytes

                if not fits_bytes.startswith(b"SIMPLE  ="):
                    raise ValueError("Not a valid FITS file from WISE IBE")

                out_file.write_bytes(fits_bytes)
                sha256 = hashlib.sha256(fits_bytes).hexdigest()
                logger.info(f"  [+] Downloaded AllWISE {band_name}: {out_file.name} ({len(fits_bytes):,} bytes)")
                results.append({
                    "obs_id": f"WISE_{coadd_id}_{band_name}",
                    "obs_publisher_did": f"ivo://irsa.ipac/wise?{coadd_id}/{band_name}",
                    "target_key": target_key,
                    "mission": "WISE",
                    "release": "AllWISE",
                    "detector": band_name,
                    "mjd": 55300.0,
                    "ra": ra,
                    "dec": dec,
                    "cutout_size_deg": size_deg,
                    "fits_path": str(out_file),
                    "file_size": len(fits_bytes),
                    "sha256": sha256,
                    "cutout_url": cutout_url,
                })
                break
            except Exception as e:
                time.sleep(1.5 ** attempt)

    return results


# -----------------------------------------------------------------------------
# Gaia DR3 Catalog Harvester
# -----------------------------------------------------------------------------
def harvest_gaia(
    target_key: str,
    ra: float,
    dec: float,
    radius_deg: float,
    out_dir: Path,
) -> list[dict[str, Any]]:
    """Harvests Gaia DR3 astrometric stars with proper motion within search radius."""
    logger.info(f"[{target_key}] Querying Gaia DR3 cone search (radius={radius_deg}°)...")
    target_dir = out_dir / target_key / "gaia"
    target_dir.mkdir(parents=True, exist_ok=True)

    out_json = target_dir / f"{target_key}_gaia_dr3.json"
    if out_json.exists():
        try:
            return json.loads(out_json.read_text(encoding="utf-8"))
        except Exception:
            pass

    try:
        from astroquery.gaia import Gaia
        import astropy.units as u
        from astropy.coordinates import SkyCoord

        coord = SkyCoord(ra, dec, unit=(u.deg, u.deg), frame="icrs")
        job = Gaia.cone_search_async(coord, radius=radius_deg * u.deg)
        tbl = job.get_results()

        stars = []
        for row in tbl:
            source_id = str(row.get("source_id", ""))
            s_ra = float(row.get("ra", 0.0) or 0.0)
            s_dec = float(row.get("dec", 0.0) or 0.0)
            parallax = float(row.get("parallax", 0.0) or 0.0) if not math.isnan(row.get("parallax", 0.0) or 0.0) else None
            pmra = float(row.get("pmra", 0.0) or 0.0) if not math.isnan(row.get("pmra", 0.0) or 0.0) else None
            pmdec = float(row.get("pmdec", 0.0) or 0.0) if not math.isnan(row.get("pmdec", 0.0) or 0.0) else None
            g_mag = float(row.get("phot_g_mean_mag", 0.0) or 0.0) if not math.isnan(row.get("phot_g_mean_mag", 0.0) or 0.0) else None

            stars.append({
                "source_id": source_id,
                "target_key": target_key,
                "ra": s_ra,
                "dec": s_dec,
                "parallax": parallax,
                "pmra": pmra,
                "pmdec": pmdec,
                "phot_g_mean_mag": g_mag,
            })

        # Save to JSON
        out_json.write_text(json.dumps(stars, indent=2), encoding="utf-8")
        logger.info(f"  [+] Saved {len(stars)} Gaia DR3 stars to {out_json.name}")
        return stars
    except Exception as exc:
        logger.warning(f"[{target_key}] Gaia DR3 query failed: {exc}")
        return []


# -----------------------------------------------------------------------------
# Main Harvester Orchestration
# -----------------------------------------------------------------------------
def harvest_target(
    target_key: str,
    target_info: dict[str, Any],
    size_deg: float,
    out_dir: Path,
    sources: list[str],
    db_conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Harvests data for a single target across requested sources."""
    name = target_info.get("name", target_key)
    ra = float(target_info["ra"])
    dec = float(target_info["dec"])

    logger.info(f"=== START HARVESTING: {name} (RA: {ra:.4f}°, Dec: {dec:.4f}°) ===")
    summary: dict[str, Any] = {"target": target_key, "name": name, "entries": [], "gaia_stars": 0}

    # 1. SPHEREx
    if "spherex" in sources:
        spx_entries = harvest_spherex(target_key, ra, dec, size_deg, out_dir)
        summary["entries"].extend(spx_entries)
        if db_conn and spx_entries:
            cursor = db_conn.cursor()
            for e in spx_entries:
                cursor.execute("""
                INSERT OR REPLACE INTO observations 
                (obs_id, obs_publisher_did, target_key, mission, release, detector, mjd, ra, dec, cutout_size_deg, fits_path, file_size, sha256, cutout_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    e["obs_id"], e["obs_publisher_did"], e["target_key"], e["mission"],
                    e["release"], e["detector"], e["mjd"], e["ra"], e["dec"],
                    e["cutout_size_deg"], e["fits_path"], e["file_size"], e["sha256"], e["cutout_url"]
                ))
            db_conn.commit()

    # 2. AllWISE
    if "wise" in sources:
        wise_entries = harvest_wise(target_key, ra, dec, size_deg, out_dir)
        summary["entries"].extend(wise_entries)
        if db_conn and wise_entries:
            cursor = db_conn.cursor()
            for e in wise_entries:
                cursor.execute("""
                INSERT OR REPLACE INTO observations 
                (obs_id, obs_publisher_did, target_key, mission, release, detector, mjd, ra, dec, cutout_size_deg, fits_path, file_size, sha256, cutout_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    e["obs_id"], e["obs_publisher_did"], e["target_key"], e["mission"],
                    e["release"], e["detector"], e["mjd"], e["ra"], e["dec"],
                    e["cutout_size_deg"], e["fits_path"], e["file_size"], e["sha256"], e["cutout_url"]
                ))
            db_conn.commit()

    # 3. Gaia DR3
    if "gaia" in sources:
        gaia_stars = harvest_gaia(target_key, ra, dec, size_deg, out_dir)
        summary["gaia_stars"] = len(gaia_stars)
        if db_conn and gaia_stars:
            cursor = db_conn.cursor()
            for s in gaia_stars:
                cursor.execute("""
                INSERT OR REPLACE INTO gaia_stars
                (source_id, target_key, ra, dec, parallax, pmra, pmdec, phot_g_mean_mag)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    s["source_id"], s["target_key"], s["ra"], s["dec"],
                    s["parallax"], s["pmra"], s["pmdec"], s["phot_g_mean_mag"]
                ))
            db_conn.commit()

    # Write target manifest
    manifest_file = out_dir / target_key / "manifest.json"
    manifest_data = {
        "target_key": target_key,
        "name": name,
        "ra": ra,
        "dec": dec,
        "cutout_size_deg": size_deg,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cutout_count": len(summary["entries"]),
        "gaia_stars_count": summary["gaia_stars"],
        "entries": summary["entries"],
    }
    manifest_file.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
    logger.info(f"[{target_key}] Manifest written to {manifest_file.name} ({len(summary['entries'])} cutouts).")

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="SPHEREx & Multi-Mission Data Harvester / Scraper (Khôi)"
    )
    parser.add_argument(
        "--targets",
        type=str,
        default="all",
        help="Comma-separated target keys (e.g. barnard,wise0855) or 'all' for the 5 challenge targets",
    )
    parser.add_argument("--ra", type=float, help="Custom RA in degrees (overrides targets)")
    parser.add_argument("--dec", type=float, help="Custom Dec in degrees (overrides targets)")
    parser.add_argument("--name", type=str, default="Custom Target", help="Target display name")
    parser.add_argument(
        "--fov",
        type=float,
        default=0.05,
        help="Field of view / cutout size in degrees (default: 0.05)",
    )
    parser.add_argument(
        "--sources",
        type=str,
        default="spherex,wise,gaia",
        help="Comma-separated data sources to harvest: spherex, wise, gaia",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/harvest",
        help="Output directory for downloaded data (default: data/harvest)",
    )
    parser.add_argument(
        "--sqlite",
        action="store_true",
        default=True,
        help="Store harvested observation metadata into SQLite DB (spherex_sia2.db)",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default="data/spherex_sia2.db",
        help="Path to SQLite database file",
    )

    args = parser.parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    sources = [s.strip().lower() for s in args.sources.split(",")]

    db_conn = None
    if args.sqlite:
        db_path = Path(args.db_path)
        db_conn = init_database(db_path)
        logger.info(f"Initialized SQLite database at {db_path}")

    # Determine targets to process
    targets_to_run: dict[str, dict[str, Any]] = {}
    if args.ra is not None and args.dec is not None:
        target_id = re.sub(r"[^a-z0-9]", "", args.name.lower()) or "custom"
        targets_to_run[target_id] = {
            "name": args.name,
            "ra": args.ra,
            "dec": args.dec,
            "description": "User custom coordinates",
        }
    elif args.targets.lower() == "all":
        targets_to_run = DEFAULT_TARGETS
    else:
        req_keys = [k.strip().lower() for k in args.targets.split(",")]
        for k in req_keys:
            if k in DEFAULT_TARGETS:
                targets_to_run[k] = DEFAULT_TARGETS[k]
            else:
                logger.error(f"Unknown target key '{k}'. Available: {list(DEFAULT_TARGETS.keys())}")

    if not targets_to_run:
        logger.error("No valid targets selected. Exiting.")
        return 1

    total_cutouts = 0
    total_gaia = 0
    start_time = time.time()

    print("\n=======================================================")
    print("  NASA Space Apps SPHEREx Sky Viewer - Data Harvester   ")
    print(f"  Targets: {list(targets_to_run.keys())}")
    print(f"  Sources: {sources} | FOV: {args.fov}°")
    print(f"  Output : {out_dir}")
    print("=======================================================\n")

    for key, info in targets_to_run.items():
        summary = harvest_target(key, info, args.fov, out_dir, sources, db_conn)
        total_cutouts += len(summary.get("entries", []))
        total_gaia += summary.get("gaia_stars", 0)

    if db_conn:
        db_conn.close()

    elapsed = time.time() - start_time
    print("\n=======================================================")
    print("  HARVEST COMPLETED SUCCESSFULLY!")
    print(f"  Total cutouts downloaded : {total_cutouts}")
    print(f"  Total Gaia stars indexed : {total_gaia}")
    print(f"  Total execution time     : {elapsed:.2f} seconds")
    print("=======================================================\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
