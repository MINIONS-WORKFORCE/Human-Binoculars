# Hướng dẫn chạy MVP (Nhánh `huu-hoang`)

Tài liệu này giúp các thành viên trong nhóm kéo nhánh `huu-hoang` về máy và chạy được ngay bản MVP (**SPHEREx Sky Viewer**), kể cả khi chưa tải bộ FITS gốc (~795 MB) lẫn khi chạy đầy đủ cả 6 detector (`D1`–`D6`).

---

## 1. Dữ liệu nào đã có trên Git vs. dữ liệu nào nằm cục bộ (`NFR-08`)

Theo quy tắc `NFR-08` trong [SRS-MVP.md](SRS-MVP.md) và file [`.gitignore`](../.gitignore), toàn bộ thư mục `data/` và file `*.fits` **không được đẩy lên Git**.

* **Đã có sẵn trên Git (chỉ cần `git pull origin huu-hoang`):**
  * Toàn bộ code Backend (`members/dong/`), Frontend (`frontend/`), Pipeline ảnh (`members/huu-hoang/`, `shared/`) và bộ test.
  * **66 ảnh PNG SPHEREx thật** phục vụ chạy fallback/mock:
    * `api_samples/png/targets/{barnard,wise0855,epsindib,rwaur,rdra}_{0,1,2}.png` và `*_diff.png` (30 ảnh).
    * `frontend/src/mocks/target_png/` (30 ảnh tương ứng cho MSW mock) + 6 ảnh gốc `api_samples/png/frame-{0,1,2}*.png`.
* **Không đẩy lên Git (nằm cục bộ trong `data/`):**
  * **156 file FITS gốc** (`data/five_targets/*/inputs/*.fits`, ~795 MB tổng cộng, 26 khung cho mỗi detector `D1`–`D6` trên 5 mục tiêu) và 480 file sản phẩm render tĩnh (`data/five_targets/*/frames/`).
  * `data/fixtures/manifest.json` (khi có `data/five_targets/` và chạy backend, hàm `sync_five_targets_manifest()` trong [`members/dong/app/services/observed_frames.py`](../members/dong/app/services/observed_frames.py) sẽ tự đồng bộ lại file này).

---

## 2. Chuẩn bị môi trường (chạy 1 lần sau khi clone/pull)

```powershell
# 1. Tạo và kích hoạt môi trường Python 3.12+
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# 2. Cài gói Frontend
npm --prefix frontend install

# 3. Tạo file cấu hình .env từ mẫu
Copy-Item .env.example .env       # macOS/Linux: cp .env.example .env
```

---

## 3. Hai cách chạy MVP

### Cách 1 — Chạy xem ngay (không cần tải ~795 MB FITS)

Phù hợp để kiểm tra nhanh giao diện và xem **ảnh PNG SPHEREx thật** của cả 5 ngôi sao đã được commit sẵn.

* **Chạy Frontend độc lập với ảnh PNG mẫu thật (MSW Mock):**
  1. Trong `.env`, giữ nguyên `# VITE_USE_MOCK=false` (không bật `false`, mặc định dev mode của `frontend/src/config.ts` tự bật MSW mock).
  2. Chạy lệnh:
     ```powershell
     npm --prefix frontend run dev
     ```
  3. Mở `http://localhost:5173/`.
* **Hoặc chạy kèm Backend ở chế độ fallback PNG:**
  1. Đặt trong `.env`: `DATA_MODE=fixture` và `VITE_USE_MOCK=false`.
  2. Chạy Backend ở terminal 1:
     ```powershell
     .venv\Scripts\python -m uvicorn members.dong.app.main:app --host 127.0.0.1 --port 8000
     ```
  3. Chạy Frontend ở terminal 2 (`npm --prefix frontend run dev`), mở `http://localhost:5173/`.

---

### Cách 2 — Chạy đầy đủ 100% MVP (đủ 6 detector `D1`–`D6` từ 156 FITS thật + Photometry đa dải)

#### Bước 1: Lấy dữ liệu FITS cục bộ vào `data/five_targets/`
Chọn **1 trong 2 cách**:
* **Cách A (tải trực tiếp từ NASA IRSA bằng 1 lệnh):**
  ```powershell
  .venv\Scripts\python members/huu-hoang/five_targets.py --download
  ```
  Lệnh này tự giải quyết tọa độ J2026 từ SIMBAD, tải đủ 156 cutout FITS (`D1`–`D6`) cho cả 5 mục tiêu (`barnard`, `wise-0855`, `eps-ind-b`, `rw-aur`, `r-dra`) và render sản phẩm tĩnh.
* **Cách B (chép offline từ Google Drive/USB của nhóm):**
  Giải nén thư mục `five_targets` vào đúng đường dẫn `data/five_targets/`.

#### Bước 2: Cấu hình `.env` để Frontend nối API thật
Mở file `.env` ở thư mục gốc và đảm bảo có các dòng sau (lưu ý bỏ dấu `#` trước `VITE_USE_MOCK=false`):

```env
DATA_MODE=fixture
API_HOST=127.0.0.1
API_PORT=8000
CORS_ALLOW_ORIGINS=*
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_USE_MOCK=false
```

#### Bước 3: Chạy Backend & Frontend (2 terminal song song)
* **Terminal 1 (Backend FastAPI ở cổng `8000`):**
  ```powershell
  .venv\Scripts\python -m uvicorn members.dong.app.main:app --host 127.0.0.1 --port 8000
  ```
  *(Hoặc dùng `npm run dev:be`. Khi khởi động, backend tự đồng bộ `data/fixtures/manifest.json` và phục vụ cả FITS thật lẫn photometry đa dải `D1`–`D6`.)*
* **Terminal 2 (Frontend Vite ở cổng `5173`, đã cấu hình proxy `/api` sang `127.0.0.1:8000` trong `frontend/vite.config.ts`):**
  ```powershell
  npm --prefix frontend run dev
  ```
* Truy cập trình duyệt tại **`http://localhost:5173/`**.

---

## 4. Lưu ý (Tips) khi dùng giao diện & đọc kết quả

1. **Chuyển detector `D1`–`D6` trên giao diện:**
   * Chọn lần lượt `D1` đến `D6` trên thanh chọn detector để xem 6 dải bước sóng hồng ngoại thật khác nhau của SPHEREx (`0.75–5.00 µm`).
   * Mỗi lần đổi detector hoặc mục tiêu, hệ thống chiếu lại FITS qua lưới `59×59` TAN thống nhất và trả về chuỗi ảnh gốc + ảnh hiệu (`Difference`).
2. **Chế độ Offline của bản đồ sao (`Sky map`):**
   * Khi chọn **`Synthetic stars (offline)`** ở mục `Gaia layer`, bản đồ Aladin Lite chủ động ngắt tải nền ảnh DSS/HiPS từ máy chủ CDS từ xa và chỉ hiển thị **40 vòng tròn sao mẫu màu vàng trên nền xám** — đây là hành vi đúng thiết kế giúp chạy ổn định khi mất mạng hoặc bị chặn kết nối tới CDS.
   * Muốn xem nền trời thật và dữ liệu Gaia DR3 thật (khi có mạng), chuyển `Gaia layer` sang `Gaia DR3 (CDS / VizieR)`.
3. **Hiểu đúng các cảnh báo khoa học (`Warnings`):**
   * `SATURATION_POSSIBLE`: Sao mục tiêu quá sáng làm một số pixel ở tâm có thể bị bão hòa (được mask tím `#703090` khi xử lý để không làm sai lệch phép đo).
   * `MIXED_WAVELENGTH`: Bộ lọc biến thiên tuyến tính (LVF) của SPHEREx khiến các khung khác vị trí trên detector có bước sóng hơi lệch nhau; biến thiên độ sáng có thể do màu sắc chứ không chỉ do chuyển động.
   * `FEW_FRAMES`: Xuất hiện khi một cấu hình lọc ra ít hơn 3 khung (với 2 khung vẫn giữ lại để quan sát, nhưng chưa đủ 3 thời điểm độc lập để kết luận chắc chắn chuyển động riêng).
4. **Dấu thập đỏ (`Crosshair`) và vị trí ngôi sao:**
   * Điểm giao của dấu thập (`predicted_px`) đánh dấu tọa độ dự đoán của ngôi sao mục tiêu trên từng khung hình đã căn lưới WCS TAN.
5. **Nếu trình duyệt từng bật MSW Mock trước đó:**
   * `frontend/src/main.tsx` sẽ tự động gỡ Service Worker cũ và xóa cache khi `VITE_USE_MOCK=false`; nếu thấy dữ liệu cũ còn lưu, chỉ cần bấm `Ctrl + Shift + R` (Hard Reload).

---

## 5. Lệnh kiểm tra toàn bộ hệ thống (Tests)

```powershell
# 1. Test Python (138 tests: pipeline xử lý ảnh, API backend, IRSA/fixtures offline)
.venv\Scripts\pytest members/huu-hoang/ members/dong/ members/khoi/test_irsa.py

# 2. Test Frontend (Vitest + Typecheck + Lint)
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run lint

# 3. Test JS dùng chung ở gốc repo (Shared SkyMap / Charts / Target helpers)
frontend\node_modules\.bin\vitest.cmd run --passWithNoTests --exclude "frontend/**"

# 4. Test trình duyệt End-to-End (Playwright, dùng Edge nếu chưa cài Chromium)
cd frontend; $env:PW_CHANNEL="msedge"; npm run e2e
```
