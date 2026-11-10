# Khôi: IRSA Data + Database

Nơi lưu trữ các script truy vấn SIA2/TAP, tải ảnh cutout FITS, kiểm tra định dạng và cấu trúc dữ liệu SPHEREx phục vụ toàn bộ hệ thống.

---

## 1. Các module & script đã hoàn thành (Hoàn tất Issue #15 & SRS-MVP FR-05)

### A. Module cốt lõi: `shared/pipeline/irsa.py`
Hợp đồng giao diện (API contract) chuẩn giữa **Khôi** $\rightarrow$ **Hữu Hoàng** (Xử lý ảnh) và **Đông** (Backend):
- `find_images(ra_deg, dec_deg, collection='spherex_qr2', detector=None, ...)`: Truy vấn SIA2 kèm cơ chế tự động Fallback sang TAP (ADQL) khi gặp lỗi 502 Proxy. Chuẩn hóa tên trường theo chuẩn ObsCore (`obs_id`, `obs_publisher_did`, `t_min`, `t_max`, `access_url`...).
- `fetch_cutouts(images, ra_deg, dec_deg, size_deg, out_dir, ...)`: Tải các cutout FITS, gom nhóm theo đợt quan sát (visit clusters), tính mã băm SHA-256, kiểm tra định dạng FITS và tự động xuất tệp `manifest.json`.

### B. Script khảo sát: `members/khoi/survey_targets.py`
- Tự động bù chuyển động riêng (Proper Motion) từ J2000 về kỷ nguyên quan sát J2025.5.
- Truy vấn IRSA khảo sát toàn diện **5 mục tiêu thách thức** trên cả **6 detector** (`SPHEREx-D1` đến `D6`).
- Kết quả lưu tại:
  - Markdown: [`targets_summary.md`](targets_summary.md)
  - JSON: [`targets_summary.json`](targets_summary.json)

### C. Script tải và kiểm tra FITS: `members/khoi/fetch_barnard_d6.py`
- Tải thành công **12 cutout FITS thật** (kích thước $0.1^\circ$) cho **Sao Barnard** ở detector **D6** vào thư mục `data/cutouts/barnard_d6/`.
- Kiểm tra toàn diện cấu trúc Header 7 extension (`IMAGE`, `FLAGS`, `VARIANCE`, `ZODI`, `PSF`, `WCS-WAVE`):
  - Xác nhận định dạng OBSID: `YYYYW<tuần>_<phân_đoạn>_<id>` (ví dụ: `2025W33_2C_0321_1`).
  - Xác nhận từ khóa thời gian: `DATE`, `DATE-OBS`, `MJD-OBS`, `TMIN`, `TMAX`.
- Báo cáo chi tiết lưu tại: [`barnard_d6_inspection.md`](barnard_d6_inspection.md).

### D. Unit Tests: `members/khoi/test_irsa.py`
Kiểm tra tính đúng đắn của hàm chuẩn hóa detector, tạo URL cutout, gom nhóm visit và cấu trúc manifest.
Chạy test:
```bash
.venv\Scripts\pytest.exe members/khoi/test_irsa.py
```

---

## 2. Bảng tổng hợp số khung hình (5 Mục Tiêu × 6 Detectors - QR2)

| Mục tiêu (Target) | RA (J2025.5) | Dec (J2025.5) | D1 | D2 | D3 | D4 | D5 | D6 | Tổng khung |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Barnard's Star** | 269.4464° | 4.7668° | 45 | 45 | 42 | 44 | 48 | 42 | **266** |
| **WISE 0855-0714** | 133.7609° | -7.2422° | 46 | 51 | 46 | 46 | 51 | 44 | **284** |
| **Epsilon Indi B** | 331.0954° | -56.8008° | 48 | 75 | 66 | 46 | 60 | 61 | **356** |
| **RW Aurigae** | 76.9565° | 30.4013° | 45 | 38 | 38 | 44 | 39 | 36 | **240** |
| **R Draconis** | 248.1674° | 66.7551° | 95 | 97 | 106 | 93 | 96 | 97 | **584** |
| **TỔNG CỘNG** | | | **279** | **306** | **298** | **273** | **294** | **280** | **1,730** |
