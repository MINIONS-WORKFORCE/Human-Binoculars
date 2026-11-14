"""Survey 5 targets x 6 SPHEREx detectors via SIA2/TAP.
Authored by Khoi (members/khoi/survey_targets.py).
Fulfills Issue #15 requirements.
"""

from __future__ import annotations

import json
import logging
import math
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# Add repo root to sys.path so we can import shared.pipeline.irsa
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from shared.pipeline.irsa import _normalize_detector, find_images

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("khoi.survey")

# The 5 Challenge Targets with J2000 positions and proper motions (mas/yr)
TARGETS_DEF = [
    {
        "id": "barnard",
        "name": "Barnard's Star",
        "ra_j2000": 269.452077,
        "dec_j2000": 4.693365,
        "pm_ra_cosdec": -801.55,
        "pm_dec": 10362.39,
        "notes": "Fastest proper motion star; moves ~10.37 arcsec/yr",
    },
    {
        "id": "wise-0855",
        "name": "WISE 0855-0714",
        "ra_j2000": 133.818908,
        "dec_j2000": -7.247048,
        "pm_ra_cosdec": -8118.0,
        "pm_dec": 680.0,
        "notes": "Coldest known brown dwarf; moves ~8 arcsec/yr",
    },
    {
        "id": "eps-ind-b",
        "name": "Epsilon Indi B",
        "ra_j2000": 331.044147,
        "dec_j2000": -56.782844,
        "pm_ra_cosdec": 3961.4,
        "pm_dec": -2538.3,
        "notes": "Nearby brown dwarf pair",
    },
    {
        "id": "rw-aur",
        "name": "RW Aurigae",
        "ra_j2000": 76.956526,
        "dec_j2000": 30.401438,
        "pm_ra_cosdec": 1.0,
        "pm_dec": -20.0,
        "notes": "Young T Tauri variable star",
    },
    {
        "id": "r-dra",
        "name": "R Draconis",
        "ra_j2000": 248.167611,
        "dec_j2000": 66.754979,
        "pm_ra_cosdec": -12.4,
        "pm_dec": 12.3,
        "notes": "Mira type pulsating variable",
    },
]

DETECTORS = ["SPHEREx-D1", "SPHEREx-D2", "SPHEREx-D3", "SPHEREx-D4", "SPHEREx-D5", "SPHEREx-D6"]


def propagate_coord_linear(
    ra_deg: float, dec_deg: float, pm_ra_cosdec: float, pm_dec: float, dt_years: float
) -> tuple[float, float]:
    """Linear propagation of coordinates over dt_years."""
    cos_dec = math.cos(math.radians(dec_deg))
    dra = (pm_ra_cosdec / 3600000.0) * dt_years / max(abs(cos_dec), 1e-6)
    ddec = (pm_dec / 3600000.0) * dt_years
    return (ra_deg + dra, dec_deg + ddec)


def survey_all_targets(collection: str | None = None, epoch_year: float = 2026.0) -> dict:
    """Surveys 5 targets across all 6 detectors in the specified collection."""
    collection = collection or os.getenv("SPHEREX_COLLECTION", "spherex_dr1")
    dt = epoch_year - 2000.0
    summary_results: list[dict] = []

    print("\n" + "=" * 80)
    print(f"KHÔI: BẮT ĐẦU TRUY VẤN KHẢO SÁT 5 MỤC TIÊU QUA IRSA ({collection.upper()})")
    print(f"Kỷ nguyên mục tiêu: J{epoch_year:.1f} (Đã bù chuyển động riêng Δt = {dt:.1f} năm)")
    print("=" * 80 + "\n")

    for tgt in TARGETS_DEF:
        ra_epoch, dec_epoch = propagate_coord_linear(
            tgt["ra_j2000"], tgt["dec_j2000"], tgt["pm_ra_cosdec"], tgt["pm_dec"], dt
        )
        print(f"-> Đang truy vấn mục tiêu: {tgt['name']} (ID: {tgt['id']})")
        print(f"   J2000: RA={tgt['ra_j2000']:.6f}°, Dec={tgt['dec_j2000']:.6f}°")
        print(
            f'   J{epoch_year:.1f}: RA={ra_epoch:.6f}°, Dec={dec_epoch:.6f}° (dịch chuyển: {math.hypot(ra_epoch - tgt["ra_j2000"], dec_epoch - tgt["dec_j2000"]) * 3600:.1f}")'
        )

        # Query all images at this position
        all_imgs = find_images(ra_epoch, dec_epoch, collection=collection, search_radius_deg=0.08)
        print(f"   => Tổng số ảnh tìm thấy: {len(all_imgs)}")

        # Count per detector
        counts: dict[str, int] = {d: 0 for d in DETECTORS}
        for img in all_imgs:
            bp = str(img.get("energy_bandpassname", ""))
            norm_bp = _normalize_detector(bp)
            if norm_bp in counts:
                counts[norm_bp] += 1

        target_row = {
            "id": tgt["id"],
            "name": tgt["name"],
            "ra_epoch": ra_epoch,
            "dec_epoch": dec_epoch,
            "total_frames": len(all_imgs),
            "counts": counts,
        }
        summary_results.append(target_row)
        for d in DETECTORS:
            short_d = d.replace("SPHEREx-", "")
            print(f"      {short_d}: {counts[d]} khung", end=" | ")
        print()

    # Build Markdown table
    md_lines = [
        "# BẢNG THỐNG KÊ SỐ KHUNG HÌNH SPHEREx (5 MỤC TIÊU × 6 DETECTOR)",
        f"- **Collection:** `{collection}`",
        f"- **Kỷ nguyên khảo sát:** `J{epoch_year:.1f}`",
        "- **Tác giả:** Khôi (`members/khoi/survey_targets.py`)",
        "",
        "| Mục tiêu (Target) | RA (J2025.5) | Dec (J2025.5) | D1 | D2 | D3 | D4 | D5 | D6 | Tổng khung |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]

    for row in summary_results:
        c = row["counts"]
        md_lines.append(
            f"| **{row['name']}** | {row['ra_epoch']:.4f}° | {row['dec_epoch']:.4f}° | "
            f"{c['SPHEREx-D1']} | {c['SPHEREx-D2']} | {c['SPHEREx-D3']} | "
            f"{c['SPHEREx-D4']} | {c['SPHEREx-D5']} | {c['SPHEREx-D6']} | **{row['total_frames']}** |"
        )

    md_content = "\n".join(md_lines)
    print("\n" + md_content + "\n")

    # Save to members/khoi/targets_summary.md and json
    out_dir = Path(__file__).resolve().parent
    (out_dir / "targets_summary.md").write_text(md_content, encoding="utf-8")
    (out_dir / "targets_summary.json").write_text(
        json.dumps(summary_results, indent=2), encoding="utf-8"
    )
    print(f"-> Đã lưu bảng thống kê vào: {out_dir / 'targets_summary.md'}")

    return {"collection": collection, "targets": summary_results}


if __name__ == "__main__":
    survey_all_targets()
