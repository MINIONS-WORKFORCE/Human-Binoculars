# Khôi: IRSA Data + Database

Nơi lưu trữ các script truy vấn SIA2/TAP, tải ảnh cutout FITS, kiểm tra định dạng và cấu trúc dữ liệu SPHEREx phục vụ toàn bộ hệ thống.

---

## 1. Các module & script đã hoàn thành

### A. Module cốt lõi: `shared/pipeline/irsa.py` (Issue #15 & Issue #21)
Hợp đồng giao diện (API contract) chuẩn giữa **Khôi** $\rightarrow$ **Hữu Hoàng** (Xử lý ảnh) và **Đông** (Backend):
- `find_images(ra_deg, dec_deg, collection='spherex_qr2', detector=None, ...)`: Truy vấn SIA2 kèm cơ chế tự động Fallback sang TAP (ADQL) khi gặp sự cố mạng hoặc 502 Proxy. Chuẩn hóa tên trường theo chuẩn ObsCore (`obs_id`, `obs_publisher_did`, `t_min`, `t_max`, `access_url`...).
- `fetch_cutouts(images, ra_deg, dec_deg, size_deg, out_dir, ...)`: Tải các cutout FITS, gom nhóm theo đợt quan sát (visit clusters), tính mã băm SHA-256, kiểm tra tính hợp lệ của header FITS và tự động xuất tệp `manifest.json`.
- `find_frames(query=None, target_key=None, detector=None, mode='fixture', ...)`: Tìm và cung cấp danh sách khung quan sát SPHEREx.
  - **Chế độ `fixture`:** Chạy **100% offline**, đọc từ `manifest.json` và trả về metadata + đường dẫn FITS trên máy mà không gọi mạng.
  - **Chế độ `live`:** Tự động truy vấn IRSA và tải cutout vào thư mục cache nếu cần.

### B. Bộ Fixture 5 Mục Tiêu & Manifest: `build_five_targets_fixture.py` (Issue #21)
- Tải về **30 khung FITS thật** cho cả 5 mục tiêu thách thức ở hai detector: **SPHEREx-D6** (bước sóng dài 4.4–5.0 µm) và **SPHEREx-D1** (bước sóng ngắn 0.75–1.11 µm).
- Mỗi mục tiêu có **6 khung** (3 khung D6 + 3 khung D1, vượt mức tối thiểu $\ge 3$ khung).
- Bảng tổng hợp số khung fixture:
  | Key | Mục tiêu | D6 | D1 | Tổng khung | Tiêu chuẩn $\ge 3$ |
  | :--- | :--- | :---: | :---: | :---: | :---: |
  | `barnard` | **Barnard's Star** | 3 | 3 | **6** | ✅ ĐẠT |
  | `wise0855` | **WISE 0855-0714** | 3 | 3 | **6** | ✅ ĐẠT |
  | `epsindib` | **Epsilon Indi B** | 3 | 3 | **6** | ✅ ĐẠT |
  | `rwaur` | **RW Aurigae** | 3 | 3 | **6** | ✅ ĐẠT |
  | `rdra` | **R Draconis** | 3 | 3 | **6** | ✅ ĐẠT |
- Tệp manifest gom toàn bộ fixture:
  - Bản chính: `data/fixtures/manifest.json`
  - Bản sao tham chiếu trong repo: [`members/khoi/fixtures_manifest.json`](fixtures_manifest.json)
  - Báo cáo tổng hợp: [`members/khoi/fixtures_summary.md`](fixtures_summary.md)

### C. Script khảo sát 5 mục tiêu: `members/khoi/survey_targets.py` (Issue #15)
- Bù chuyển động riêng (Proper Motion) từ J2000 về kỷ nguyên quan sát J2025.5.
- Khảo sát **1,730 ảnh quan sát SPHEREx** trên toàn bộ 6 detector.
- Kết quả lưu tại:
  - Markdown: [`targets_summary.md`](targets_summary.md)
  - JSON: [`targets_summary.json`](targets_summary.json)

### D. Tải và kiểm tra FITS sao Barnard: `members/khoi/fetch_barnard_d6.py` (Issue #15)
- Tải 12 cutout FITS thật ($0.1^\circ$) cho Barnard D6 vào `data/cutouts/barnard_d6/`.
- Kiểm tra chi tiết cấu trúc Header 7 extension và lưu báo cáo tại: [`barnard_d6_inspection.md`](barnard_d6_inspection.md).

### E. Unit Tests: `members/khoi/test_irsa.py` (11/11 tests PASSED)
Kiểm tra toàn diện:
- Chuẩn hóa detector (`SPHEREx-D1` .. `D6`).
- Xây dựng URL cutout IRSA.
- Gom cụm visit theo mốc thời gian.
- **Hoạt động 100% offline** của `find_frames(mode="fixture")` với cả 5 mục tiêu (chặn toàn bộ truy cập mạng bằng mock).
- Lọc theo detector `D6` và `D1`.
- Truy vấn theo tọa độ (`ra_deg`, `dec_deg`) và `query` dict.
- Tính toàn vẹn của tệp FITS (header `SIMPLE  =`, kích thước hợp lệ).

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
