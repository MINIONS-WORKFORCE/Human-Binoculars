"""Package the SPHEREx 5-target fixture pack into a distributable zip archive.
Authored by Khoi for Issue #34.
Usage:
    python scripts/pack_fixtures.py
"""

from __future__ import annotations

import hashlib
import sys
import zipfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parents[1]
FIXTURES_DIR = ROOT_DIR / "data" / "fixtures"
OUTPUT_ZIP = ROOT_DIR / "data" / "fixtures_spherex_5targets.zip"


def pack_fixtures() -> Path:
    if not FIXTURES_DIR.exists():
        raise FileNotFoundError(f"Fixtures directory not found: {FIXTURES_DIR}")

    manifest_path = FIXTURES_DIR / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest.json not found in {FIXTURES_DIR}")

    fits_files = list(FIXTURES_DIR.glob("**/*.fits"))
    if len(fits_files) < 15:
        raise ValueError(f"Expected at least 15 FITS files for 5 targets, found {len(fits_files)}")

    print("=" * 70)
    print("ĐÓNG GÓI FIXTURE PACK 5 MỤC TIÊU SPHEREx")
    print(f"Thư mục nguồn: {FIXTURES_DIR}")
    print(f"Tệp nén đích:   {OUTPUT_ZIP}")
    print("=" * 70)

    with zipfile.ZipFile(OUTPUT_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # 1. Add manifest.json
        arcname = "manifest.json"
        zf.write(manifest_path, arcname=arcname)
        print(f" + Đã thêm {arcname}")

        # 2. Add each FITS file
        for f in sorted(fits_files):
            rel_arc = f.relative_to(FIXTURES_DIR)
            zf.write(f, arcname=str(rel_arc).replace("\\", "/"))
            print(f" + Đã thêm {rel_arc} ({f.stat().st_size / 1024:.1f} KB)")

    # Compute SHA-256 of the zip file
    content = OUTPUT_ZIP.read_bytes()
    sha256 = hashlib.sha256(content).hexdigest()
    size_mb = len(content) / (1024 * 1024)

    print("\n" + "=" * 70)
    print("HOÀN TẤT ĐÓNG GÓI!")
    print(f"Tệp lưu tại:  {OUTPUT_ZIP}")
    print(f"Kích thước:   {size_mb:.2f} MB")
    print(f"SHA-256:      {sha256}")
    print(f"Số file FITS: {len(fits_files)} khung")
    print("=" * 70)

    # Also save checksum file
    checksum_file = ROOT_DIR / "data" / "fixtures_spherex_5targets.zip.sha256"
    checksum_file.write_text(f"{sha256}  fixtures_spherex_5targets.zip\n", encoding="utf-8")
    return OUTPUT_ZIP


if __name__ == "__main__":
    pack_fixtures()
