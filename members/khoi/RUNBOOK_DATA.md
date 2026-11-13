# Runbook Kỹ thuật Dữ liệu IRSA & Database – Khôi

> **Phiên bản:** 1.0 (Chốt trước Hackathon ngày 13/11/2026)  
> **Người sở hữu:** Khôi (Backend / IRSA Data & Database Specialist)  
> **Người dự phòng:** Đông (Backend API / Cache), Hữu Hoàng (Xử lý ảnh)  
> **Phạm vi:** Module `shared/pipeline/irsa.py`, cơ sở dữ liệu SQLite, bộ mẫu FITS offline, quy trình xử lý sự cố mạng/IRSA.

---

## 1. Kiến trúc luồng dữ liệu (Data Pipeline Architecture)

```
[Người dùng / Frontend]
         │ (Tên / Tọa độ RA-Dec / Detector / Size)
         ▼
[Backend API / Đông]
         │
         ▼
[shared/pipeline/irsa.py] ◄── [Khôi]
         │
         ├───► Chế độ "live":
         │        1. Thử SIA2: https://irsa.ipac.caltech.edu/SIA (collection: spherex_qr3)
         │        2. Nếu SIA2 lỗi/502/timeout ──► Fallback TAP ADQL (spherex.plane)
         │        3. Tải song song Cutouts FITS qua ThreadPoolExecutor (max_workers=4)
         │        4. Ghi cache đĩa & SQLite `spherex_sia2.db`
         │
         └───► Chế độ "fixture" (Offline 100%):
                  Đọc trực tiếp từ `data/fixtures/manifest.json` và `data/fixtures/<target>/`
```

---

## 2. Danh mục 5 Mục tiêu Khoa học & Dữ liệu Mẫu Offline

Tất cả 30 file FITS dưới đây đã được lưu trữ cục bộ tại [data/fixtures/](file:///d:/Roy/NASA.ShereX/data/fixtures/) và đóng gói trong [data/fixtures_spherex_5targets.zip](file:///d:/Roy/NASA.ShereX/data/fixtures_spherex_5targets.zip):

### 1. Barnard's Star (Chuyển động riêng lớn ~10.36"/năm)
- **Tọa độ ICRS:** RA `269.4521°`, Dec `+4.6934°`
- **Bộ mẫu offline (`data/fixtures/barnard/`):**
  - `barnard_D1_01.fits`: ObsID `2025W35_1A_0432_4`, D1, MJD 60914.2125
  - `barnard_D1_02.fits`: ObsID `2025W35_1A_0432_4`, D1, MJD 60914.2125 (cutout 49×49)
  - `barnard_D1_03.fits`: ObsID `2025W35_1A_0658_2`, D1, MJD 60915.4326
  - `barnard_D6_01.fits`: ObsID `2025W35_1A_0432_4`, D6, MJD 60914.2125
  - `barnard_D6_02.fits`: ObsID `2025W35_1A_0658_1`, D6, MJD 60915.4311
  - `barnard_D6_03.fits`: ObsID `2025W35_1A_0658_2`, D6, MJD 60915.4326

### 2. WISE 0855-0714 (Sao lùn nâu siêu lạnh, T ~250K)
- **Tọa độ ICRS:** RA `133.8189°`, Dec `-7.2470°` (Tâm tìm kiếm: `133.7951°`, `-7.2451°`)
- **Bộ mẫu offline (`data/fixtures/wise0855/`):**
  - `wise0855_D1_01.fits`, `_D1_02.fits`, `_D1_03.fits`
  - `wise0855_D6_01.fits`, `_D6_02.fits`, `_D6_03.fits` (ObsIDs: `2025W19_1B_0116_1`, `2025W19_1B_0138_1`, `2025W19_1B_0241_1`)
- **Lưu ý đặc biệt:** `spherex_qr3` online hiện chưa có dữ liệu vị trí này; luôn kích hoạt fallback fixture khi chạy demo WISE 0855.

### 3. Epsilon Indi B (Hệ đôi sao lùn nâu Ba/Bb)
- **Tọa độ ICRS:** RA `331.0441°`, Dec `-56.7828°`
- **Bộ mẫu offline (`data/fixtures/epsindib/`):**
  - 3 ảnh detector D1 (0.75 – 1.05 µm) & 3 ảnh detector D6 (4.45 – 5.00 µm).

### 4. RW Aurigae (Sao trẻ đang bồi tụ & che khuất dị thường)
- **Tọa độ ICRS:** RA `76.9565°`, Dec `+30.4014°`
- **Bộ mẫu offline (`data/fixtures/rwaur/`):**
  - 3 ảnh detector D1 & 3 ảnh detector D6 ghi nhận các đợt biến đổi độ sáng mạnh.

### 5. R Draconis (Sao biến quang Mira chu kỳ ~245 ngày)
- **Tọa độ ICRS:** RA `248.1676°`, Dec `+66.7550°`
- **Bộ mẫu offline (`data/fixtures/rdra/`):**
  - 3 ảnh detector D1 & 3 ảnh detector D6 ghi nhận cực đại và cực tiểu quang thông hồng ngoại.

---

## 3. Quy trình xử lý sự cố IRSA trong 39 giờ thi (Emergency Runbook)

### Sự cố 1: IRSA phản hồi chậm (> 15 giây) hoặc trả mã lỗi HTTP 500 / 502 / 504 Gateway Timeout
- **Hành động ngay lập tức:**
  1. Module `shared/pipeline/irsa.py` tự động kích hoạt `_query_tap_fallback` (chuyển sang IRSA TAP ADQL).
  2. Nếu cả SIA2 và TAP đều nghẽn: Backend đặt biến môi trường `DATA_MODE=fixture`. Mọi truy vấn chuyển sang đọc FITS có sẵn trong `data/fixtures/` (trả về dưới 50ms, không phụ thuộc internet).

### Sự cố 2: Ban tổ chức hoặc IPAC cập nhật / thay đổi Collection trong giờ thi
- **Cách nhận diện:** Gọi SIA2 trả về `len(table) == 0`.
- **Cách khắc phục:**
  1. Kiểm tra collection mới trên trang IRSA SPHEREx hoặc chạy lệnh TAP:
     ```python
     # Kiểm tra các collection có sẵn trong bảng spherex.plane
     SELECT DISTINCT collection FROM spherex.plane
     ```
  2. Cập nhật biến môi trường trong file `.env` của backend:
     ```bash
     SPHEREX_COLLECTION=spherex_qr3      # hoặc collection mới được thông báo
     SPHEREX_COLLECTION_FALLBACK=spherex_qr2
     ```
  3. Khởi động lại service backend: hệ thống lập tức ăn collection mới mà không cần sửa code.

### Sự cố 3: Dữ liệu tải về bị thiếu hoặc lỗi giải nén FITS
- **Cách giải quyết:**
  - Giải nén file dự phòng `data/fixtures_spherex_5targets.zip` vào thư mục `data/fixtures/`.
  - Chạy `python -m pytest members/dong/tests` để đảm bảo 100% fixture hợp lệ và pass toàn bộ test contract.

---

## 4. Bàn giao & Ghép nối với đồng đội

- **Giao cho Đông (Backend):**
  - Sử dụng hàm `find_frames()` trong `shared/pipeline/irsa.py`.
  - Chữ ký hàm:
    ```python
    from shared.pipeline.irsa import find_frames
    
    frames = find_frames(
        ra_deg=269.4521,
        dec_deg=4.6934,
        detector="SPHEREx-D1",
        cutout_size_deg=0.05,
        mode="fixture",  # hoặc "live"
    )
    ```
- **Giao cho Hữu Hoàng (Xử lý ảnh):**
  - Cutouts trả về là file FITS đa tầng chuẩn HDU 0–6 (HDU 1: `IMAGE`, HDU 2: `FLAGS`, HDU 5: `PSF`).
  - Hữu Hoàng dùng WCS tại HDU 1 để reproject và che bit flags (`FLAGS != 0`) trước khi thực hiện median stacking và tạo difference image.
