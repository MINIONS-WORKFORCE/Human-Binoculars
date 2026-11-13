# Khôi: IRSA Data & Database Specialist

Module, công cụ và tài liệu thuộc trách nhiệm của Khôi trong dự án **NASA Space Apps SPHEREx Sky Viewer**:

## 1. Công cụ & Mã nguồn cốt lõi
- **Module truy cập dữ liệu chính:** `shared/pipeline/irsa.py` (truy vấn SIA2, TAP ADQL fallback, tải cutout song song, chuyển đổi chế độ live/fixture).
- **Công cụ cào & hợp nhất dữ liệu tự động (Harvester):** [`fetch.py`](fetch.py)
  - Cào dữ liệu SPHEREx Level 2 (QR3) đa dải (D1–D6) qua IRSA SIA2/TAP.
  - Cào dữ liệu lịch sử AllWISE (W1 3.4µm, W2 4.6µm) qua IRSA IBE Image Service (tự động decompress gzip FITS).
  - Truy vấn danh mục sao Gaia DR3 (astrometry, proper motion, G magnitude) qua ESA/CDS TAP.
  - Lưu trữ siêu dữ liệu quan sát và tọa độ vào SQLite `data/spherex_sia2.db`.
  - Sinh tệp định dạng chuẩn `manifest.json` cho Backend & Frontend.

### Hướng dẫn sử dụng `fetch.py`
```bash
# Kích hoạt virtualenv
.\.venv\Scripts\Activate.ps1

# Cào dữ liệu mục tiêu Barnard's Star (cả 3 nguồn SPHEREx + WISE + Gaia)
python members/khoi/fetch.py --targets barnard --sources spherex,wise,gaia --fov 0.05

# Cào toàn bộ 5 mục tiêu hackathon
python members/khoi/fetch.py --targets all --fov 0.05

# Cào tọa độ thiên văn tùy biến
python members/khoi/fetch.py --name "Custom Source" --ra 123.456 --dec -12.345 --fov 0.05
```

## 2. Tài liệu kỹ thuật & Bàn giao
- **Runbook dữ liệu chi tiết:** [RUNBOOK_DATA.md](RUNBOOK_DATA.md) (Kiến trúc pipeline, danh mục ObsID của 5 mục tiêu, quy trình xử lý sự cố IRSA).
- **Bảng đo đạc Benchmark:** [BENCHMARKS.md](BENCHMARKS.md) (Số lượng ảnh và thời gian tải thực tế trên `spherex_qr3` ở các kích thước 0.05°, 0.1°, 0.2°).
- **Thông báo bàn giao Collection (13/11/2026):** [../../docs/team/collection_notice_20261113.md](../../docs/team/collection_notice_20261113.md).
- **Bộ dữ liệu mẫu Offline:** Lưu tại `data/fixtures/` và `data/fixtures_spherex_5targets.zip` (không commit FITS lên Git).
- **Tình trạng kiểm thử:** Backend tests pass 121/124 (3 skipped khi chạy offline).
