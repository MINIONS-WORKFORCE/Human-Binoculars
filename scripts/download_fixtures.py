"""Download and setup the SPHEREx 5-target fixture pack for offline development.
Authored by Khoi for Issue #34.
Done When:
    Anyone runs this script (or downloads from Team Drive), and find_frames()
    operates 100% offline with >= 3 frames per target.

Usage:
    python scripts/download_fixtures.py
    python scripts/download_fixtures.py --verify-only
    python scripts/download_fixtures.py --zip-path /path/to/downloaded.zip
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
FIXTURES_DIR = DATA_DIR / "fixtures"
LOCAL_ZIP = DATA_DIR / "fixtures_spherex_5targets.zip"

# Team Google Drive link placeholder (configure or pass via --url / env)
DEFAULT_DRIVE_URL = os.getenv(
    "SPHEREX_FIXTURES_URL",
    "https://drive.google.com/uc?export=download&id=1SPHEREx_5Targets_Fixture_Pack_2026",
)

EXPECTED_TARGETS = ["barnard", "wise0855", "epsindib", "rwaur", "rdra"]


def verify_fixtures(fixtures_path: Path = FIXTURES_DIR) -> bool:
    """Verifies that all 5 targets exist with >= 3 valid FITS frames each."""
    print("=" * 70)
    print("KIỂM TRA TÍNH TOÀN VẸN BỘ FIXTURE (OFFLINE VERIFICATION)")
    print(f"Thư mục kiểm tra: {fixtures_path}")
    print("=" * 70)

    manifest_path = fixtures_path / "manifest.json"
    if not manifest_path.exists():
        print(f"[-] THẤT BẠI: Không tìm thấy {manifest_path}")
        return False

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[-] THẤT BẠI: Lỗi đọc manifest.json: {exc}")
        return False

    total_valid_fits = 0
    all_ok = True

    manifest_entries = manifest.get("entries", [])
    expected_total = 0

    for target in EXPECTED_TARGETS:
        target_dir = fixtures_path / target
        if target_dir.exists():
            fits_files = list(target_dir.glob("*.fits"))
            valid_files = []
            for f in fits_files:
                if f.stat().st_size > 10000:
                    with open(f, "rb") as fp:
                        if fp.read(8) == b"SIMPLE  ":
                            valid_files.append(f)
            d6_count = sum(1 for f in valid_files if "_D6_" in f.name)
            d1_count = sum(1 for f in valid_files if "_D1_" in f.name)
            det_summary = f"D6: {d6_count}, D1: {d1_count}"
        else:
            target_entries = [e for e in manifest_entries if e.get("target_key") == target]
            if not target_entries:
                print(f"[-] {target}: Thiếu thư mục mục tiêu và không có trong manifest!")
                all_ok = False
                continue
            valid_files = []
            for e in target_entries:
                raw_path = Path(e.get("fits_path") or e.get("path") or "")
                f = raw_path if raw_path.is_absolute() else (ROOT_DIR / raw_path)
                if f.is_file() and f.stat().st_size > 10000:
                    with open(f, "rb") as fp:
                        if fp.read(8) == b"SIMPLE  ":
                            valid_files.append(f)
            dets = sorted({e.get("detector_short") or e.get("detector", "") for e in target_entries})
            det_summary = ", ".join(dets)

        status_icon = "✅" if len(valid_files) >= 3 else "❌"
        print(
            f" {status_icon} Mục tiêu '{target:10s}': {len(valid_files)} khung hợp lệ "
            f"({det_summary}) -> {'ĐẠT (>= 3)' if len(valid_files) >= 3 else 'CHƯA ĐẠT'}"
        )
        total_valid_fits += len(valid_files)
        expected_total += max(6, len(valid_files))
        if len(valid_files) < 3:
            all_ok = False

    print("-" * 70)
    print(f"Tổng số khung FITS hợp lệ: {total_valid_fits}/{expected_total}")
    if all_ok:
        print("=> TẤT CẢ 5 MỤC TIÊU ĐỀU ĐẠT TIÊU CHUẨN NGHIỆM THU ĐẦU-CUỐI!")
    else:
        print("=> CÓ MỤC TIÊU CHƯA ĐỦ SỐ KHUNG!")
    print("=" * 70)
    return all_ok


def download_file(url: str, dest_path: Path):
    """Downloads a file with a progress bar."""
    print(f"Đang tải dữ liệu từ: {url}")
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    def _progress(block_num, block_size, total_size):
        if total_size > 0:
            downloaded = block_num * block_size
            percent = min(100.0, downloaded * 100.0 / total_size)
            sys.stdout.write(f"\r -> Đã tải: {downloaded / (1024*1024):.1f}/{total_size / (1024*1024):.1f} MB ({percent:.1f}%)")
            sys.stdout.flush()

    urllib.request.urlretrieve(url, dest_path, reporthook=_progress)
    print()


def extract_zip(zip_path: Path, dest_dir: Path):
    """Extracts zip archive into destination directory."""
    print(f"Đang giải nén {zip_path.name} vào {dest_dir}...")
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest_dir)
    print("-> Giải nén hoàn tất!")


def main():
    parser = argparse.ArgumentParser(description="SPHEREx Fixture Downloader & Verifier")
    parser.add_argument("--url", default=DEFAULT_DRIVE_URL, help="URL to download fixture zip")
    parser.add_argument("--zip-path", help="Path to already downloaded zip file")
    parser.add_argument("--verify-only", action="store_true", help="Only verify existing fixtures")
    args = parser.parse_args()

    if args.verify_only:
        ok = verify_fixtures(FIXTURES_DIR)
        sys.exit(0 if ok else 1)

    # 1. If fixtures directory already populated and valid, verify and exit
    if FIXTURES_DIR.exists() and (FIXTURES_DIR / "manifest.json").exists():
        if verify_fixtures(FIXTURES_DIR):
            print("\nBộ fixture đã có sẵn đầy đủ tại data/fixtures/.")
            return

    # 2. Check if a local zip file is available
    zip_to_use = Path(args.zip_path) if args.zip_path else LOCAL_ZIP
    if not zip_to_use.exists():
        print(f"Không tìm thấy tệp nén tại {zip_to_use}.")
        try:
            download_file(args.url, zip_to_use)
        except Exception as exc:
            print(f"\n[!] Không thể tự động tải qua URL ({exc}).")
            print("Vui lòng tải thủ công tệp 'fixtures_spherex_5targets.zip' từ Google Drive của nhóm")
            print(f"và lưu vào đường dẫn: {LOCAL_ZIP}")
            sys.exit(1)

    # 3. Extract zip
    extract_zip(zip_to_use, FIXTURES_DIR)

    # 4. Verify after extraction
    ok = verify_fixtures(FIXTURES_DIR)
    if ok:
        print("\nCÀI ĐẶT FIXTURE PACK THÀNH CÔNG! SẴN SÀNG CHẠY OFFLINE.")
    else:
        print("\nCẢNH BÁO: Kiểm tra fixture chưa hoàn tất.")
        sys.exit(1)


if __name__ == "__main__":
    main()
