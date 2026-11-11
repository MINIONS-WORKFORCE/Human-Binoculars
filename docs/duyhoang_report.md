# Báo cáo 11/11/2026: Nối frontend với backend thật, trạng thái chờ và lỗi

**Người làm:** Duy Hoàng
**Nhánh:** `duy-hoang/frontend-real-api`, tạo từ `main` (`fe93446`)

**Task:** Chạy frontend với `VITE_USE_MOCK=false` trỏ vào backend của Đông. Sửa chỗ lệch kiểu dữ liệu. Thêm trạng thái chờ và lỗi theo bảng mã lỗi của hợp đồng.

| Done when | Kết quả |
| --- | --- |
| Blink chạy từ API thật | **Đạt.** Frontend ở `localhost:5180`, backend `npm run dev:be` (`DATA_MODE=fixture`) ở `127.0.0.1:8000`. `/api/frames` trả 200 qua CORS, 6 PNG tải được, viewer đi đủ 3 khung (05/2025, 11/2025, 04/2026), dấu thập nằm trên sao |
| Playwright có thêm 1 test cho trường hợp lỗi | **Đạt, thêm 2 test** trong `e2e/errors.spec.ts`. Cả bộ: 8/8 pass |

## 1. Kiểm tra lệch kiểu dữ liệu

| Cách kiểm tra | Kết quả |
| --- | --- |
| Sinh kiểu TS từ `/openapi.json` của backend đang chạy, so với `src/api/schema.d.ts` | Giống hệt (diff 0 dòng) |
| Test mới `src/api/parity.test.ts`: gửi cùng 24 request vào mock MSW và backend thật, so status và JSON (bỏ qua hash trong ID khung và `git_sha`) | **24/24 khớp.** Gồm các trường hợp thành công, `max_frames`, không có `target_key`, và mọi mã lỗi backend fixture trả được |
| Cố ý sửa mock (detector mặc định 6 thành 5) | Test báo đỏ 2 trường hợp, rồi đã trả lại như cũ |

**Kết luận:** schema và mock không lệch nhau. Các chỗ lệch thật nằm ở cách frontend xử lý response, và đã sửa:

| Chỗ lệch | Sửa |
| --- | --- |
| Bảng mã lỗi của hợp đồng có 8 mã, `friendlyMessage` chỉ có câu cho 5 mã. Thiếu `UPSTREAM_ERROR` (502), `UPSTREAM_TIMEOUT` (504) và `INTERNAL` (500), nên 3 mã này hiện câu chung chung | Thêm `ERROR_CODES` và `describeError()`: mỗi mã có một câu riêng và cờ `retry`. Mã lạ thì dựa vào status (5xx thì cho thử lại) |
| Response 200 mà không phải JSON (ví dụ `VITE_API_BASE_URL` sai nên nhận về trang HTML) bị trả về như dữ liệu `null` | Báo `HTTP_ERROR` |
| `frames: []` kèm `FEW_FRAMES` (hợp đồng nói đây không phải lỗi) hiện ra một viewer rỗng "Frame 0 / 0" | Hiện câu "No frames are left for these settings…" |

## 2. Trạng thái chờ và lỗi

| Trạng thái | Hiển thị |
| --- | --- |
| Đang gọi `/api/frames` | Vòng xoay nhỏ và "Loading frames…". Sau 3 giây thêm bộ đếm giây "The NASA archive can take up to 2 minutes", vì IRSA có thể mất tới 120 giây |
| Lỗi (`role="alert"`) | Câu theo mã lỗi kèm mã. Chỉ đọc `code`, không hiện `message` của server, đúng quy ước của hợp đồng |
| Lỗi có thể thử lại (`FRAME_NOT_FOUND`, `UPSTREAM_*`, `INTERNAL`, `NETWORK`, `HTTP_ERROR`) | Có nút **Try again**, gửi lại đúng request đó |
| Lỗi do đầu vào (`BAD_COORDS`, `BAD_PARAM`, `UNKNOWN_TARGET`) và `NO_FRAMES` | Không có nút thử lại, chỉ có câu hướng dẫn |
| Ảnh không tải được (thường là `FRAME_NOT_FOUND` sau khi backend khởi động lại) | Lớp phủ trên viewer có nút **Reload frames** (prop mới `onReload` của BlinkViewer) |

Trong bản build mock, nếu MSW không khởi động được (trình duyệt chặn service worker, cửa sổ ẩn danh…), trang vẫn hiện và báo lỗi bình thường thay vì trắng trang.

## 3. Playwright: `e2e/errors.spec.ts`
Backend fixture không bao giờ trả 502/504, nên test tự trả response bằng `page.route()`. Service worker của MSW sẽ trả lời trước `page.route()`, vì vậy test chặn service worker (`serviceWorkers: "block"`).

1. **504 `UPSTREAM_TIMEOUT`:**
   - Giữ request lại, thấy dòng "Loading frames…" và chưa có lỗi.
   - Thả request ra, thấy alert có câu "took more than 2 minutes" và mã lỗi, không có `message` gốc của server.
   - Bấm Try again thì blink chạy đủ 3 khung.
2. **400 `BAD_COORDS` và ảnh hết hạn:**
   - Lỗi 400 không có nút nào.
   - Sau đó khung tải được nhưng PNG trả 404 `FRAME_NOT_FOUND`: hiện lớp phủ, bấm Reload frames thì blink chạy.

**Test có bắt được lỗi thật không:** cố ý đặt `retry: false` cho `UPSTREAM_TIMEOUT` thì test 1 báo đỏ. Đã trả lại như cũ.

## 4. Kiểm chứng (Windows 11, Node 24.19, Edge)

| Lệnh | Kết quả |
| --- | --- |
| `npm run lint`, `npm run typecheck` | Không lỗi |
| `npm test` (Vitest) | 170 pass, 24 bỏ qua (test so mock với backend, chỉ chạy khi có `LIVE_API_URL`). Test client từ 11 lên 22 |
| `LIVE_API_URL=http://127.0.0.1:8000 npx vitest run src/api/parity.test.ts` | 24/24 pass |
| `npm run build` | Thành công, JS chính 240 kB (76 kB gzip) |
| `PW_CHANNEL=msedge npm run e2e` | **8/8 pass** (6 test cũ + 2 test lỗi) |
| `npm test` ở gốc repo | 197/197 pass |
| Trình duyệt, backend thật | Blink đi đủ 3 khung. Tắt backend rồi bấm preset WISE 0855 thì hiện `NETWORK` kèm Try again. Bật lại backend, bấm Try again thì blink WISE 0855 chạy |
| CORS | Mở từ một origin không có trong `CORS_ALLOW_ORIGINS` thì trình duyệt chặn và trang báo `NETWORK`. Thêm origin rồi khởi động lại backend thì chạy. Response 400/404 của backend có kèm header CORS |

## 5. Phát hiện cần báo team

| Cho | Vấn đề | Đề xuất |
| --- | --- | --- |
| **Đông** | Lỗi 500 bất ngờ (exception không bắt) trả `INTERNAL` nhưng **thiếu header `Access-Control-Allow-Origin`**. Đã thử bằng TestClient: route ném `RuntimeError` trả 500 với `ACAO=None`. Lý do là Starlette xử lý `Exception` ở middleware ngoài cùng, nằm ngoài `CORSMiddleware`. Trình duyệt vì vậy thấy `NETWORK` chứ không thấy `INTERNAL` | Thêm header CORS trong `unexpected_error`, hoặc bọc toàn bộ app trong CORS ở lớp ngoài cùng. Không sửa thay vì là code của Đông |
| Đông | Backend fixture chưa có đường nào trả `NO_FRAMES`, `UPSTREAM_ERROR`, `UPSTREAM_TIMEOUT` (chỉ khai báo trong OpenAPI) | Frontend đã xử lý sẵn; khi có chế độ live thì chạy lại `parity.test.ts` |
| Khôi / Nguyên | Tọa độ WISE 0855 không thống nhất. Frontend dùng `133.8189, -7.2470` (SIMBAD, epoch 2000), hướng dẫn của Đông dùng `133.7951, -7.2451`, pack FITS dùng `133.7372, -7.2403` (năm 2025). Sao chuyển động khoảng 8″/năm nên ba giá trị lệch nhau vài phút cung. Backend fixture chấp nhận mọi tọa độ nên hiện không gây lỗi | Thống nhất epoch trong `shared/targets.json`. Mình chưa đổi, để chờ bảng chung |
| Cả team | Origin của frontend phải có trong `CORS_ALLOW_ORIGINS` trong `.env` | Đã ghi vào `frontend/README.md` |

## 6. File thay đổi
- `frontend/src/api/client.ts`: `ERROR_CODES`, `describeError`, báo lỗi khi 200 không phải JSON.
- `frontend/src/App.tsx`: `LoadingFrames`, `FramesError` (Try again), trạng thái không có khung, truyền `onReload`.
- `frontend/src/blink/BlinkViewer.tsx`: prop `onReload` và nút Reload frames.
- `frontend/src/main.tsx`: vẫn render khi MSW không khởi động được.
- `frontend/src/index.css`: khung lỗi, vòng xoay (chậm lại khi bật `prefers-reduced-motion`).
- Test: `src/api/client.test.ts` (thêm 11), `src/api/parity.test.ts` (mới), `e2e/errors.spec.ts` (mới).
- `frontend/README.md`: chạy với backend thật, CORS, test so mock với backend, bảng trạng thái lỗi.
- Không đổi code backend, `requirements.txt` hay dependency nào.

## 7. Môi trường trên máy (không commit)
- `.venv` chỉ cài fastapi, uvicorn, pillow, httpx (bản ghim trong `requirements.txt`).
- `.env`: `DATA_MODE=fixture`, `VITE_USE_MOCK=false`, `CORS_ALLOW_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:5180`.

## 8. Việc tiếp theo
1. Mở PR `duy-hoang/frontend-real-api` vào `main`. Máy chưa có `gh`, nên mở trên web.
2. Báo Đông lỗi CORS ở response 500.
3. Deploy frontend và kiểm tra CORS với domain thật.
4. Script smoke (`/api/health` và 5 mục tiêu) trước mỗi lần demo.

---

# Báo cáo 10/11/2026: Khung frontend, MSW, CI và Blink viewer

**Người làm:** Duy Hoàng (Frontend A + DevOps + kiểm thử, người quản lý repo)
**Nhánh:** `duy-hoang/frontend-blink-viewer`, tạo từ `origin/dong/issue-14-api-contract-fixture` (commit `d050ac9`) vì `main` chưa có `api_samples/` và `openapi.yaml`

| Commit | Nội dung |
| --- | --- |
| `5baa5d6` | Phần A: khung `frontend/` (Vite + React + TS), MSW đọc `api_samples/`, kiểm tra schema, CI (Issue 18) |
| `f0981e8` | Phần B: BlinkViewer (tải trước bằng `img.decode()`, dấu thập, ảnh hiệu, điều khiển), Playwright, job e2e |
| `0ab5dcf` và commit này | Report |

**Trạng thái:** đã push lên `MINIONS-WORKFORCE/Human-Binoculars`, **chưa mở PR**, chưa kiểm tra kết quả CI trên GitHub.

---

## 1. Tóm tắt

### Phần A: Dựng khung Vite + React, cài MSW đọc `api_samples/`, thêm kiểm tra schema vào CI

| Tiêu chí | Kết quả |
| --- | --- |
| Dựng khung Vite + React | Xong. `frontend/` dùng Vite 8 + React 19 + TypeScript 5.9 |
| Cài MSW đọc `api_samples/` | Xong. MSW 3 trả đủ 7 endpoint, mô phỏng hành vi `fixture_api.py` của Đông |
| Kiểm tra schema file mẫu trong CI | Xong. Có 2 lớp: Pydantic (script của Đông) và OpenAPI (Ajv trong Vitest) |
| **Done when:** `npm run dev` gọi được `/api/frames` từ dữ liệu giả | **Đạt, đã kiểm tra trong trình duyệt.** `/api/frames` trả 200 với 3 khung, 6 ảnh PNG đều 200 |

### Phần B: Blink viewer

| Yêu cầu | Kết quả |
| --- | --- |
| Phát / dừng | Xong. Nút Play/Pause và phím cách. Viewer tự phát khi tải xong ảnh |
| Chỉnh tốc độ | Xong. Thanh trượt 1–10 khung/giây |
| Đi từng khung | Xong. Nút ◀ ▶, phím ← →, thanh trượt chọn khung. Đi tay thì tự dừng |
| Hiện ngày chụp và bước sóng từng khung | Xong. "Frame 2 / 3 · 2025-11-01 00:00 UTC · 4.70 µm · Detector D6" |
| Dấu thập | Xong. Vẽ tại `(x + 0.5) × cỡ pixel` theo `predicted_px` (gốc PNG ở góc trên trái), chừa khe ở giữa để thấy ngôi sao. Có công tắc bật/tắt |
| Chuyển sang ảnh hiệu | Xong. Công tắc Original / Difference, giữ nguyên khung đang xem |
| Tải trước bằng `img.decode()` | Xong. Tải song song cả 6 ảnh (3 gốc, 3 hiệu), chờ `decode()` xong hết mới phát, hiện "Loading images n / 6" |
| **Done when:** Blink mượt trên dữ liệu giả | **Đạt, có số đo** (mục 3.2) |
| **Done when:** Có 1 test Playwright cơ bản | **Đạt, có 2 test** |

---

## 2. Việc đã làm

### Phần A

#### A1. Chuẩn bị repo
- Clone lại repo vào một thư mục trống mới. Mọi việc từ nay làm trong bản clone này.
- Tạo nhánh từ nhánh Issue 14 của Đông, vì `main` (`ac68f01`) chưa có `api_samples/` và `openapi.yaml`.

#### A2. Khung `frontend/`
- Ứng dụng riêng, có `package.json` và `package-lock.json` riêng. Khi deploy chỉ cần trỏ Root Directory vào `frontend/`. Ngày 14/11 có thể copy nguyên thư mục sang repo mới.
- Các lệnh: `dev`, `build`, `build:mock`, `lint` (ESLint 10 + typescript-eslint + react-hooks), `typecheck` (`tsc -b`), `test` (Vitest 5), `e2e` (Playwright), `gen:types`.
- `vite.config.ts` làm 3 việc: đọc `.env` ở gốc repo, cho phép đọc `api_samples/` và `shared/` nằm ngoài `frontend/`, và cấu hình Vitest.
- Giao diện dùng `shared/design-tokens.css` của Thạch (nền tối).

#### A3. Kiểu TypeScript từ OpenAPI
- `npm run gen:types` chạy `openapi-typescript` trên `shared/api-contract/openapi.yaml` và sinh ra `src/api/schema.d.ts` (7 endpoint, 23 schema).
- `src/api/client.ts` là client có kiểu cho cả 7 endpoint, cùng `imageUrl` cho `png`/`diff_png`.
  - Lỗi theo hợp đồng được chuyển thành `ApiError` với `status`, `code`, `details`.
  - Mất mạng được báo bằng `NETWORK`; phản hồi lỗi không phải JSON được báo bằng `HTTP_ERROR`.
  - `friendlyMessage()` đổi mã lỗi thành câu tiếng Anh người xem hiểu được.

#### A4. MSW đọc `api_samples/`
- `src/mocks/samples.ts` nạp 6 file JSON và 6 ảnh PNG. Ảnh nhúng dạng data URL nên dùng được cả trong trình duyệt lẫn Node.
- `src/mocks/handlers.ts` mô phỏng `members/dong/app/fixture_api.py`:
  - Kiểm tra tham số giống backend: RA/Dec sai trả 400 `BAD_COORDS`; detector, size hoặc max_frames sai trả 400 `BAD_PARAM`; `target_key` lạ trả 404 `UNKNOWN_TARGET`.
  - Trả lại `ra`, `dec`, `detector`, `target_key` của request. Không gửi `target_key` thì `predicted_px = null`.
  - `max_frames` cắt bớt khung và thêm cảnh báo `TRUNCATED`/`FEW_FRAMES`.
  - ID khung sinh theo từng query. Ảnh chỉ tải được sau khi đã gọi `/api/frames`, nếu không thì trả 404 `FRAME_NOT_FOUND`, giống registry ảnh của backend.
  - PNG trả kèm `Content-Type: image/png` và `Cache-Control: public, max-age=86400`.
- Cách bật/tắt mock (`src/config.ts`):
  - `npm run dev`: mock bật mặc định.
  - `VITE_USE_MOCK=false`: gọi backend thật tại `VITE_API_BASE_URL`.
  - `VITE_USE_MOCK=true` hoặc `npm run build:mock`: bản build chạy hoàn toàn bằng dữ liệu giả.

#### A5. CI: `.github/workflows/ci.yml`
Đây là workflow đầu tiên của repo. Chạy khi có push, pull request, hoặc chạy tay. Tự hủy lần chạy cũ khi có push mới trên cùng nhánh.

| Job | Các bước |
| --- | --- |
| `api-samples` | Python 3.12, chỉ cài `fastapi` + `pillow` theo phiên bản ghi trong `requirements.txt`, rồi chạy `members/dong/scripts/validate_api_samples.py` |
| `frontend` | Node 24, `npm ci`. Kiểm tra `schema.d.ts` khớp `openapi.yaml` (sinh lại rồi `git diff --exit-code`). Sau đó lint, typecheck, test (gồm kiểm tra schema bằng Ajv), build |
| `e2e` | Cài Chromium, chạy Playwright trên bản build mock, lỗi thì upload báo cáo trong 7 ngày (thêm ở phần B) |
| `members-js` | Chạy `npm test` ở gốc repo (173 test JS sẵn có của các thành viên và `shared/`), để giữ `main` luôn chạy được |

#### A6. Thay đổi ngoài `frontend/`
- `package.json` gốc: lệnh `test` thêm `--exclude "frontend/**"`, vì `frontend/` có cấu hình test riêng.
- `.env.example`: thêm một dòng ghi chú về `VITE_USE_MOCK`.

### Phần B

#### B1. Code mới trong `frontend/src/blink/`

| File | Nội dung |
| --- | --- |
| `player.ts` | Reducer thuần, port từ bản luyện JS sang TS: `load/play/pause/toggle/tick/next/prev/seek/setFps`, thêm `setMode` (gốc/hiệu) và `toggleCrosshair`. `advanceClock` cộng dồn thời gian giữa các lần gọi rAF |
| `preload.ts` | `preloadImages(urls, onProgress)`: tải song song, `await img.decode()`, trả ảnh đúng thứ tự đầu vào. Ảnh lỗi thì báo `PreloadError` kèm url |
| `usePreloadedFrames.ts` | Hook tải trước cả ảnh gốc và ảnh hiệu. Danh sách khung mới thì bỏ kết quả cũ |
| `canvas.ts` | `crosshairPosition`, `drawImage` (tắt `imageSmoothingEnabled`), `drawCrosshair` (4 cánh, viền tối, màu `--color-marker`) |
| `BlinkViewer.tsx` | Component độc lập `<BlinkViewer frames grid detector imageUrl />`. Vòng `requestAnimationFrame` hủy trong hàm dọn của `useEffect`. Có dòng hướng dẫn "Watch the crosshair…". Canvas và nút có nhãn; vùng thông tin dùng `aria-live` (tắt khi đang phát) |
| `blink.css` | Giao diện theo design tokens |

Cách dùng BlinkViewer có trong `frontend/README.md`.

#### B2. Pixel vuông trên mọi màn hình
- Trên màn hình zoom 125% (`devicePixelRatio = 1.25`), canvas bị co không đều: bộ đệm 507px nhưng hiển thị trong 487.5 pixel màn hình.
- Cách sửa: tính số **nguyên** pixel màn hình cho mỗi pixel SPHEREx (`round(zoom × dpr)`, ở đây là 13), rồi đặt chiều rộng CSS bằng `39 × 13 / 1.25 = 405.6px`.
- Đo lại: đúng 13.0 pixel màn hình cho mỗi pixel SPHEREx.

#### B3. Các thay đổi khác
- `App.tsx`: thay lưới ảnh tạm bằng BlinkViewer, giữ phần chọn mục tiêu/detector và đường báo lỗi.
- Bàn phím: nếu đang focus vào nút thì phím cách để nút tự xử lý, còn mũi tên vẫn đi khung. Khi focus vào thanh trượt thì phím thuộc về thanh trượt.
- Sửa viền focus không hiện (`--focus-ring` là giá trị `outline`, đã dùng nhầm cho `box-shadow`).
- Thêm favicon rỗng để hết lỗi 404 trong console.

#### B4. Playwright
- `@playwright/test` 1.65. `playwright.config.ts` chạy `build:mock` rồi `vite preview` cổng 4173, nên test đúng bản sẽ deploy và không cần backend.
- `e2e/blink.spec.ts` có 2 test:
  1. **Luồng điều khiển:** chờ tải xong, Pause, Play rồi thấy khung tự đổi, Pause, nhấn → thì sang khung kế (ngày đổi, đúng định dạng UTC, bước sóng "4.70 µm"), bấm Difference thì nút bật và canvas đổi nhãn.
  2. **Dấu thập nằm trên ngôi sao:** đọc pixel canvas ở khung 1 (`predicted_px` = 17, 19). Tâm là pixel sao sáng màu xám. Trong khe (±1.25 pixel) không có màu dấu thập. Trên cánh (±1.75 pixel) có màu dấu thập. Cỡ pixel là số nguyên.
- `PW_CHANNEL=msedge` cho phép dùng Edge có sẵn khi không tải được Chromium.

---

## 3. Kiểm chứng (chạy trên máy: Windows 11, Node 24.19, npm 11.17)

### 3.1. Các lệnh

| Lệnh | Kết quả |
| --- | --- |
| `npm run lint` | Không lỗi |
| `npm run typecheck` | Không lỗi |
| `npm test` (Vitest) | 5 file, **62/62 pass**: client 11, schema mẫu 12, player 26, canvas 10, preload 3 |
| `npm run build` | Thành công, JS chính 231 kB (73 kB gzip) |
| `PW_CHANNEL=msedge npm run e2e` | **2/2 pass** |
| `npm test` ở gốc repo | 173/173 pass |
| `npm ci` lại từ đầu rồi `gen:types` | `schema.d.ts` giống từng byte, nên bước kiểm tra trong CI không báo sai |
| Validator của Đông trong venv mới (chỉ fastapi + pillow, giống CI) | `Validated 6 API samples` |
| `npm run dev`, mở trong trình duyệt | Console hiện `[MSW] Mocking enabled`. `/api/frames` trả 200, 6 ảnh PNG đều 200, viewer tự phát, dấu thập nằm trên ngôi sao |
| Bấm "Try an unknown target" | Trang hiện "That target is not in our list yet…" kèm mã `UNKNOWN_TARGET` |

### 3.2. Độ mượt
Đo bằng Edge headless (không bị giới hạn rAF), bản build mock, `devicePixelRatio = 1.25`. MutationObserver ghi lại thời điểm mỗi lần đổi khung; mỗi lần rAF kiểm tra canvas có bị trống không.

| Tốc độ | Khoảng cách mong đợi | Trung bình đo được | Nhỏ nhất – lớn nhất | Số lần canvas trống |
| --- | --- | --- | --- | --- |
| 1 fps | 1000 ms | 1001 ms | 998 – 1003 ms | 0 / 802 |
| 2 fps | 500 ms | 500 ms | 495 – 505 ms | 0 / 813 |
| 5 fps | 200 ms | 200 ms | 165 – 233 ms | 0 / 490 |
| 10 fps | 100 ms | 100 ms | 75 – 123 ms | 0 / 477 |

Trung bình khớp tốc độ đã chọn. Độ lệch ±1 khung hình màn hình (16.7 ms ở 60 Hz) là bình thường, vì đổi khung chỉ xảy ra lúc màn hình vẽ lại. Không lần nào canvas bị trống hay chớp.

Khi tab chạy nền (rAF bị hạ xuống 1 lần/giây), viewer đổi đúng 1 khung mỗi giây, không tua dồn khung.

### 3.3. Test có bắt được lỗi thật không
- Cố ý sửa `wavelength_um` thành chuỗi trong `frames_barnard_d6.json`: test schema báo đỏ `/frames/0/wavelength_um must be number`.
- Cố ý bỏ `+ 0.5` trong `crosshairPosition`: test Playwright dấu thập báo đỏ.
- Sau cả hai lần thử, code và dữ liệu đã được trả về nguyên trạng.

### 3.4. Chưa kiểm chứng
- Kết quả các job CI trên GitHub (đã push nhưng chưa xem). Trên máy, Playwright chạy bằng Edge vì không tải được Chromium.
- Chưa chạy với backend thật (`VITE_USE_MOCK=false` + `npm run dev:be`), nên CORS chưa được thử.
- Chưa thử trên điện thoại thật hay màn hình 120/144 Hz (unit test có mô phỏng 144 Hz và 30 Hz).

---

## 4. Vấn đề gặp và cách xử lý

| Vấn đề | Cách xử lý |
| --- | --- |
| npm cài TypeScript 7 mặc định, nhưng `typescript-eslint` và `openapi-typescript` chưa hỗ trợ | Ghim `typescript@~5.9.3` |
| MSW 3 đổi tên `onUnhandledRequest` thành `onUnhandledFrame`, tên cũ bị bỏ qua âm thầm | Typecheck phát hiện; đổi tên cho cả trình duyệt và Vitest |
| Import JSON làm TS hiểu `"0.1"` là `string`, tuple là `number[]` | Ép kiểu trong `samples.ts`; test Ajv chứng minh lúc chạy rằng ép kiểu này đúng |
| ESLint (react-hooks 7) cấm `setState` ngay trong effect | Tách việc tải thành hàm thuần; effect chỉ cập nhật khi promise trả về và bỏ kết quả cũ |
| Vitest ở gốc quét luôn test của `frontend/` | Thêm `--exclude "frontend/**"` |
| `.gitignore` chặn `.env.*` | Bật mock mặc định trong code, tắt bằng `VITE_USE_MOCK` |
| Pixel không đều ở `devicePixelRatio` lẻ | Làm tròn số pixel màn hình cho mỗi pixel SPHEREx (B2) |
| Bấm Play xong, mũi tên không có tác dụng | Với nút, chỉ bỏ qua phím cách |
| Không tải được Chromium cho Playwright (kẹt 0 MB, có vẻ do sandbox) | Dùng Edge có sẵn qua `PW_CHANNEL=msedge`; CI vẫn cài Chromium |
| Bản đầu của test dấu thập không bắt được lỗi lệch nửa pixel | Đo thêm ở mép khe, rồi cố ý gây lỗi để xác nhận test báo đỏ |

---

## 5. Quyết định cần team biết
1. **Tên biến môi trường:** task tổng ghi `VITE_API_BASE`, nhưng repo và hướng dẫn của Đông dùng `VITE_API_BASE_URL`. Mình giữ `VITE_API_BASE_URL`.
2. **`frontend/` đặt ở gốc repo**, không trong `members/duy-hoang/`, vì đây là ứng dụng sẽ deploy và Thạch sẽ ghép vào. Code luyện tập cũ vẫn ở `members/duy-hoang/`.
3. **Dependency mới chỉ nằm trong `frontend/package.json`** (msw 3, openapi-typescript 7, typescript 5.9, eslint 10, ajv, yaml, @playwright/test). `requirements.txt` không đổi. Cần báo team khi mở PR.
4. **Lỗi giả lập dùng `target_key` lạ** (404 `UNKNOWN_TARGET`), không dùng tọa độ trong `error_no_frames.json`, vì backend fixture vẫn trả khung cho WISE 0855.
5. **Viewer tự phát** khi tải xong ảnh; tốc độ 1–10 fps, mặc định 2 fps.
6. **Mock chỉ có 3 khung**, giống backend fixture. Không thêm khung giả để mock không khác backend.

---

## 6. Hạn chế đã biết
- `npm audit` báo 10 lỗ hổng moderate trong bộ công cụ ESLint (chỉ dùng khi phát triển).
- Bản build production có thêm chunk MSW (406 kB, 157 kB gzip), chỉ tải khi bật mock.
- Ở chế độ dev, `/api/frames` bị gọi 2 lần lúc mở trang (React StrictMode); bản build gọi 1 lần.
- Không tự xử lý khi `devicePixelRatio` đổi giữa chừng (zoom trình duyệt, đổi màn hình). Tải lại trang thì đúng lại.
- Tọa độ 4 mục tiêu ngoài Barnard lấy từ `members/duy-hoang/coords/targets.js`. Cần thay bằng `shared/targets.json` khi Nguyên công bố.
- Remote trên máy vẫn là địa chỉ cũ `HoangKhoi1704/...`. Push vẫn được nhờ GitHub chuyển hướng sang `MINIONS-WORKFORCE/Human-Binoculars`.

---

## 7. Tiến độ trong role Duy Hoàng

✅ xong · 🟡 có một phần · ⬜ chưa làm

### Bắt buộc
| # | Hạng mục | Trạng thái | Ghi chú |
| --- | --- | --- | --- |
| 1 | Tải trước toàn bộ khung rồi mới phát | ✅ | `img.decode()`, có tiến độ, báo lỗi theo ảnh |
| 2 | Canvas giữ pixel vuông | ✅ | Tắt làm mịn, số nguyên pixel màn hình cho mỗi pixel SPHEREx, có test |
| 3 | Vòng lặp rAF + reducer thuần | ✅ | Cộng dồn thời gian, hủy trong hàm dọn, 26 test reducer/clock |
| 4 | Điều khiển tối thiểu | ✅ | Phát/dừng, ← →, thanh trượt khung, tốc độ, gốc/hiệu, detector (chọn ở trang), ngày UTC/bước sóng/detector |
| 5 | Dấu thập tại `predicted_px` | ✅ | `(x+0.5)×cỡ pixel`, unit test 5 hệ số phóng, Playwright đọc pixel |
| 6 | MSW + kiểu từ OpenAPI | ✅ | |
| 7 | Kiểm thử | 🟡 | Đơn vị ✅. Playwright ✅ (với mock; task tổng muốn chạy với backend chế độ fixture). Component RTL ⬜. Smoke ⬜ |
| 8 | CI + deploy | 🟡 | CI đủ 4 job, đã push (chưa xem kết quả). Deploy và CORS ⬜ |

### Nên biết / nâng cao
| Hạng mục | Trạng thái |
| --- | --- |
| Dòng hướng dẫn "Watch the crosshair…" | ✅ |
| Hiện tiến độ thay vì biểu tượng xoay vô hạn | ✅ (khi tải ảnh) |
| Truy cập: nhãn, bàn phím, tương phản | ✅ Chưa kiểm bằng trình đọc màn hình thật |
| So sánh hai khung bằng thanh gạt / xuất GIF | ⬜ |

### Bài luyện trước 14/11
| Bài | Trạng thái |
| --- | --- |
| Trang blink đủ điều khiển | ✅ (trên 3 khung giả từ API, thay vì 10 PNG) |
| Dấu thập tại pixel cho trước, đổi hệ số phóng | ✅ |
| Test Playwright chạy trong GitHub Actions | 🟡 Đã push job `e2e`, chưa xem kết quả |
| Deploy Vercel/Netlify, gặp và xử lý CORS | ⬜ |

### Bàn giao
| Bàn giao | Cho | Trạng thái |
| --- | --- | --- |
| `<BlinkViewer frames=… />` độc lập | Thạch | ✅ Trên nhánh này, cách dùng trong `frontend/README.md` |
| Workflow CI, script smoke | Cả team | 🟡 CI xong, smoke chưa |
| URL frontend công khai | Thạch | ⬜ |

---

## 8. Việc tiếp theo
1. Xem kết quả 4 job CI ở tab Actions, rồi mở PR (base `main`; ghi "Related to #18" và báo team các dependency mới).
2. Deploy `frontend/` lên Vercel/Netlify. Có thể deploy bản `build:mock` trước để có URL cho Thạch, rồi nối backend và kiểm tra CORS.
3. Script smoke (`/api/health` + 5 mục tiêu) chạy trước mỗi lần demo.
4. Test component bằng React Testing Library; chạy Playwright với backend ở chế độ fixture.
5. Rebase nhánh khi PR Issue 14 của Đông được merge vào `main`.

---

## 9. Cách chạy lại

```bash
cd frontend
npm install
npm run dev                         # http://localhost:5173
npm test
PW_CHANNEL=msedge npm run e2e       # hoặc: npx playwright install chromium && npm run e2e
```

Console phải hiện `[MSW] Mocking enabled.` và viewer phải tự blink 3 khung của Barnard's Star.
