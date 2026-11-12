# Dữ liệu cục bộ: SPHEREx Fixture Packs (`data/`)

Toàn bộ thư mục `data/` (ngoại trừ tệp `README.md` này) được quản lý bởi `.gitignore` và **tuyệt đối không commit lên git** nhằm tránh làm phình repository.

Dữ liệu ảnh FITS và cutouts thật được chia sẻ qua Google Drive của nhóm.

---

## 1. Cấu trúc thư mục chuẩn (`data/fixtures/`)

Toàn bộ hệ thống Backend FastAPI (`members/dong`), Pipeline xử lý ảnh (`members/huu-hoang`), và mô-đun dữ liệu IRSA (`shared/pipeline/irsa.py`) thống nhất đọc dữ liệu từ cấu trúc sau:

```text
data/
  fixtures/
    manifest.json           # Tệp chỉ mục tổng hợp toàn bộ khung hình
    barnard/                # 6 khung FITS (3 khung D6 + 3 khung D1)
      barnard_D6_01.fits
      barnard_D6_02.fits
      barnard_D6_03.fits
      barnard_D1_01.fits
      barnard_D1_02.fits
      barnard_D1_03.fits
    wise0855/               # 6 khung FITS (3 khung D6 + 3 khung D1)
    epsindib/               # 6 khung FITS (3 khung D6 + 3 khung D1)
    rwaur/                  # 6 khung FITS (3 khung D6 + 3 khung D1)
    rdra/                   # 6 khung FITS (3 khung D6 + 3 khung D1)
```

- **Tổng số khung:** 30 khung FITS thật (kích thước cutout $0.05^\circ \approx 3^\prime$).
- **Mỗi mục tiêu:** Có **6 khung hình** (3 khung `SPHEREx-D6` dài 4.4–5.0 µm + 3 khung `SPHEREx-D1` ngắn 0.75–1.11 µm), đảm bảo tiêu chí nghiệm thu $\ge 3$ khung cho việc blink và trừ ảnh hiệu.

---

## 2. Hướng dẫn tải và cài đặt Fixture Pack

### Cách 1: Tự động bằng Script (Khuyên dùng)
Chỉ cần chạy lệnh sau từ thư mục gốc của repository:
```bash
python scripts/download_fixtures.py
```
Script sẽ tự động kiểm tra, tải gói `fixtures_spherex_5targets.zip` từ Google Drive của nhóm, giải nén vào `data/fixtures/` và xác minh toàn vẹn FITS.

### Cách 2: Tải thủ công từ Google Drive
1. Tải tệp nén **`fixtures_spherex_5targets.zip`** từ Google Drive của nhóm (thư mục `SPHEREx-Team-Drive / Fixtures`).
2. Đặt tệp zip vào thư mục `data/` trong repo:
   ```text
   data/fixtures_spherex_5targets.zip
   ```
3. Giải nén toàn bộ nội dung vào thư mục `data/fixtures/` sao cho tệp `manifest.json` nằm tại `data/fixtures/manifest.json`.

---

## 3. Lệnh kiểm tra xác minh (Offline Verification)

Sau khi giải nén, kiểm tra nhanh bằng 1 trong 2 lệnh sau:

### Kiểm tra bằng script:
```bash
python scripts/download_fixtures.py --verify-only
```
Kết quả mong đợi: `30/30 khung hợp lệ -> ĐẠT (>= 3)`.

### Kiểm tra bằng Python `find_frames()`:
```bash
python -c "from shared.pipeline.irsa import find_frames; print('Barnard frames:', len(find_frames(target_key='barnard', mode='fixture')))"
```
Kết quả mong đợi: Trả về `6` khung FITS hoàn toàn **offline** mà không cần kết nối mạng.
