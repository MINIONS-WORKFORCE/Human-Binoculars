# Khôi: IRSA Data + Database

Nơi lưu trữ các script truy vấn SIA2/TAP, tải ảnh cutout FITS, kiểm tra định dạng và cấu trúc dữ liệu SPHEREx phục vụ toàn bộ hệ thống.

---

## 1. Các module & script đã hoàn thành

### A. Module cốt lõi: `shared/pipeline/irsa.py` (Issue #15, #21 & #34)
Hợp đồng giao diện (API contract) chuẩn giữa **Khôi** $\rightarrow$ **Hữu Hoàng** (Xử lý ảnh) và **Đông** (Backend):
- `find_images(ra_deg, dec_deg, collection='spherex_qr2', detector=None, ...)`: Truy vấn SIA2 kèm cơ chế tự động Fallback sang TAP (ADQL) khi gặp sự cố mạng hoặc 502 Proxy. Chuẩn hóa tên trường theo chuẩn ObsCore (`obs_id`, `obs_publisher_did`, `t_min`, `t_max`, `access_url`...).
- `download_cutout(access_url, ra_deg, dec_deg, size_deg, dest_path, ...)`: Tải một ảnh cutout FITS đơn lẻ, xác thực cấu trúc header FITS và kiểm tra mã `OBSID`.
- `fetch_cutouts(images, ra_deg, dec_deg, size_deg, out_dir, ...)`: Tải các cutout FITS, gom nhóm theo đợt quan sát (visit clusters), tính mã băm SHA-256, kiểm tra tính hợp lệ của header FITS và tự động xuất tệp `manifest.json`.
- `find_frames(query=None, target_key=None, detector=None, mode='fixture', ...)`: Tìm và cung cấp danh sách khung quan sát SPHEREx.
  - **Chế độ `fixture`:** Chạy **100% offline**, đọc từ `manifest.json` và trả về metadata + đường dẫn FITS trên máy mà không gọi mạng.
  - **Chế độ `live`:** Tự động truy vấn IRSA và tải cutout vào thư mục cache nếu cần.

### B. Hợp nhất tải ảnh & Đóng gói Fixture Pack: `Issue #34 (Task 11/11)`
- **Hợp nhất hàm tải ảnh (DRY):** Chuyển toàn bộ việc tải cutout trong `members/huu-hoang/five_targets.py` sang gọi `download_cutout()` trong `shared/pipeline/irsa.py`, xóa bỏ hoàn toàn sự trùng lặp code mạng.
- **Chốt cỡ Cutout:** Thống nhất cỡ cutout $0.05^\circ$ ($3^\prime$) cho toàn bộ 5 mục tiêu, tương thích với cả `tan_pipeline.py` và backend `observed_frames.py`.
- **Script đóng gói:** [`scripts/pack_fixtures.py`](../../scripts/pack_fixtures.py) nén 30 khung FITS + `manifest.json` thành `data/fixtures_spherex_5targets.zip` (111.7 MB, SHA-256 xác thực).
- **Script tải & xác minh tự động:** [`scripts/download_fixtures.py`](../../scripts/download_fixtures.py) cho phép đồng đội tải và giải nén chỉ bằng một lệnh:
  ```bash
  python scripts/download_fixtures.py --verify-only
  ```
- **Tài liệu hướng dẫn:** Cập nhật toàn diện [`data/README.md`](../../data/README.md).

### C. Bộ Fixture 5 Mục Tiêu & Manifest: `build_five_targets_fixture.py` (Issue #21)
- **30 khung FITS thật** cho cả 5 mục tiêu thách thức ở hai detector: **SPHEREx-D6** (4.4–5.0 µm) và **SPHEREx-D1** (0.75–1.11 µm).
- Mỗi mục tiêu có **6 khung** (3 khung D6 + 3 khung D1, vượt mức tối thiểu $\ge 3$ khung).
  | Key | Mục tiêu | D6 | D1 | Tổng khung | Tiêu chuẩn $\ge 3$ |
  | :--- | :--- | :---: | :---: | :---: | :---: |
  | `barnard` | **Barnard's Star** | 3 | 3 | **6** | ✅ ĐẠT |
  | `wise0855` | **WISE 0855-0714** | 3 | 3 | **6** | ✅ ĐẠT |
  | `epsindib` | **Epsilon Indi B** | 3 | 3 | **6** | ✅ ĐẠT |
  | `rwaur` | **RW Aurigae** | 3 | 3 | **6** | ✅ ĐẠT |
  | `rdra` | **R Draconis** | 3 | 3 | **6** | ✅ ĐẠT |

### D. Unit Tests: `members/khoi/test_irsa.py` (13/13 tests PASSED)
Kiểm tra toàn diện:
- Chuẩn hóa detector (`SPHEREx-D1` .. `D6`).
- Xây dựng URL cutout IRSA.
- Gom cụm visit theo mốc thời gian.
- **Hoạt động 100% offline** của `find_frames(mode="fixture")` với cả 5 mục tiêu.
- Lọc theo detector `D6` và `D1`.
- Hàm `download_cutout()` với mock response và kiểm tra header FITS.
- Hàm `verify_fixtures()` từ `scripts/download_fixtures.py`.

Chạy test:
```bash
.venv\Scripts\pytest.exe members/khoi/test_irsa.py -v
```

---

## 2. Bảng tổng hợp số khung hình khảo sát (5 Mục Tiêu × 6 Detectors - QR2)

| Mục tiêu (Target) | RA (J2025.5) | Dec (J2025.5) | D1 | D2 | D3 | D4 | D5 | D6 | Tổng khung |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Barnard's Star** | 269.4464° | 4.7668° | 45 | 45 | 42 | 44 | 48 | 42 | **266** |
| **WISE 0855-0714** | 133.7609° | -7.2422° | 46 | 51 | 46 | 46 | 51 | 44 | **284** |
| **Epsilon Indi B** | 331.0954° | -56.8008° | 48 | 75 | 66 | 46 | 60 | 61 | **356** |
| **RW Aurigae** | 76.9565° | 30.4013° | 45 | 38 | 38 | 44 | 39 | 36 | **240** |
| **R Draconis** | 248.1674° | 66.7551° | 95 | 97 | 106 | 93 | 96 | 97 | **584** |
| **TỔNG CỘNG** | | | **279** | **306** | **298** | **273** | **294** | **280** | **1,730** |
