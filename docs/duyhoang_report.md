# Báo cáo task 10/11/2026: Khung frontend, MSW, kiểm tra schema trong CI

**Người làm:** Duy Hoàng (Frontend A + DevOps + kiểm thử, người quản lý repo)
**Issue:** #18 (theo `shared/api-contract/frontend-guide.md`: "Duy Hoang can connect this validator to CI for Issue 18 and generate TypeScript from /openapi.json")
**Nhánh:** `duy-hoang/issue-18-frontend-skeleton`, tạo từ `origin/dong/issue-14-api-contract-fixture` (commit `d050ac9`)
**Thư mục làm việc:** `D:\nasa_app_challenge\fresh\NASA-space-challenges-PlanetXvsSphereX`

---

## 1. Tóm tắt

| Tiêu chí của task | Kết quả |
| --- | --- |
| Dựng khung Vite + React | Xong. `frontend/` dùng Vite 8 + React 19 + TypeScript 5.9 |
| Cài MSW đọc `api_samples/` | Xong. MSW 3 trả đủ 7 endpoint từ `api_samples/`, mô phỏng đúng hành vi `fixture_api.py` của Đông |
| Thêm bước kiểm tra schema file mẫu vào CI | Xong ở mức file workflow. Có 2 lớp kiểm tra: Pydantic (script của Đông) và OpenAPI (Ajv trong Vitest) |
| **Done when:** `npm run dev` gọi được `/api/frames` từ dữ liệu giả | **Đạt, đã kiểm tra trong trình duyệt.** `/api/frames` trả 200 với 3 khung, 6 ảnh PNG đều 200 |

**Trạng thái bàn giao:** mọi thứ đã chạy được trên máy, nhưng **chưa commit, chưa push, chưa mở PR**. Vì chưa push nên workflow CI chưa chạy lần nào trên GitHub.

---

## 2. Việc đã làm

### 2.1. Chuẩn bị repo
- Clone lại repo vào thư mục trống `D:\nasa_app_challenge\fresh\`.
- `main` (commit `ac68f01`) chưa có `api_samples/` và `openapi.yaml` vì nhánh Issue 14 của Đông chưa merge. Vì vậy nhánh task được tạo từ nhánh của Đông.
- Đặt tên nhánh theo đề xuất trong `docs/team/workflow.md`: `<tên>/issue-<số>-<việc>`.
- Bản clone cũ ở `D:\nasa_app_challenge\NASA-space-challenges-PlanetXvsSphereX` được giữ nguyên. Bản đó còn 6 file sửa và 2 file mới (`difference.js`, `difference.test.js`) chưa commit trên nhánh `duy-hoang/blink-viewer`.

### 2.2. Khung `frontend/`
- Ứng dụng riêng, có `package.json` và `package-lock.json` riêng. Khi deploy lên Vercel/Netlify chỉ cần trỏ Root Directory vào `frontend/`. Ngày 14/11 có thể copy nguyên thư mục sang repo mới.
- Các lệnh: `dev`, `build`, `lint` (ESLint 10 + typescript-eslint + react-hooks), `typecheck` (`tsc -b`), `test` (Vitest 5), `gen:types`.
- `vite.config.ts` làm 3 việc: đọc `.env` ở gốc repo (giống template sẵn có), cho phép đọc file ngoài `frontend/` (`server.fs.allow`) để lấy `api_samples/` và `shared/`, và cấu hình Vitest.
- Giao diện dùng `shared/design-tokens.css` của Thạch (nền tối).

### 2.3. Kiểu TypeScript từ OpenAPI (mục 6 trong task tổng)
- `npm run gen:types` chạy `openapi-typescript` trên `shared/api-contract/openapi.yaml` và sinh ra `src/api/schema.d.ts` (1004 dòng, 7 endpoint, 23 schema).
- `src/api/client.ts` là client có kiểu cho cả 7 endpoint (`health`, `resolve`, `frames`, `photometry`, `astrometry`, cùng `imageUrl` cho `png`/`diff_png`).
  - Lỗi theo hợp đồng (`error.code`) được chuyển thành `ApiError` với `status`, `code`, `details`.
  - Mất mạng được báo bằng mã `NETWORK`. Phản hồi lỗi không phải JSON được báo bằng `HTTP_ERROR`.
  - `friendlyMessage()` đổi mã lỗi thành câu tiếng Anh người xem hiểu được. Đây là yêu cầu "lỗi 404 hiện thông báo dễ hiểu" ở mục 7.

### 2.4. MSW đọc `api_samples/` (mục 6)
- `src/mocks/samples.ts` nạp 6 file JSON và 6 ảnh PNG. Ảnh được nhúng dạng data URL nên dùng được cả trong trình duyệt lẫn Node.
- `src/mocks/handlers.ts` mô phỏng `members/dong/app/fixture_api.py`:
  - Kiểm tra tham số giống backend: RA/Dec sai trả 400 `BAD_COORDS`; detector, size hoặc max_frames sai trả 400 `BAD_PARAM`; `target_key` lạ trả 404 `UNKNOWN_TARGET`.
  - Trả lại `ra`, `dec`, `detector`, `target_key` của request. Không gửi `target_key` thì `predicted_px = null`.
  - `max_frames` cắt bớt khung và thêm cảnh báo `TRUNCATED`/`FEW_FRAMES`.
  - ID khung không cố định, sinh theo từng query. Ảnh chỉ tải được sau khi đã gọi `/api/frames`, nếu không thì trả 404 `FRAME_NOT_FOUND`, giống registry ảnh của backend.
  - PNG trả kèm `Content-Type: image/png` và `Cache-Control: public, max-age=86400`.
  - Đường dẫn bắt đầu bằng `*/api/...` nên bắt được request dù `VITE_API_BASE_URL` trỏ đến origin nào.
- Cách bật/tắt mock (`src/config.ts`):
  - `npm run dev`: mock bật mặc định.
  - `VITE_USE_MOCK=false`: gọi backend thật tại `VITE_API_BASE_URL`.
  - `VITE_USE_MOCK=true` khi build: bản deploy chạy hoàn toàn bằng dữ liệu giả, dùng để demo khi backend chưa có host.
- `public/mockServiceWorker.js` sinh bằng `npx msw init`.

### 2.5. Trang tạm `App.tsx`
- Chọn 1 trong 5 mục tiêu và chọn detector D1–D6, rồi gọi `/api/frames`.
- Hiện số khung, tên mục tiêu, detector, kích thước lưới, cảnh báo. Mỗi khung hiện ảnh gốc và ảnh hiệu phóng 6 lần với `image-rendering: pixelated`, kèm giờ UTC, bước sóng, `predicted_px`, release/survey.
- Nút "Try an unknown target" để thử đường báo lỗi 404.
- Có badge cho biết trang đang dùng mock hay API thật.
- Trang này chỉ dùng để chứng minh khung chạy được. BlinkViewer sẽ thay phần lưới ảnh này.

### 2.6. Kiểm thử (23 test, Vitest)
- `src/api/client.test.ts`, 11 test, chạy với MSW `setupServer` dùng **chung bộ handler** với trình duyệt:
  - Trả 3 khung và đúng phần dữ liệu được gửi lại; `predicted_px` = (17,19), (19,19), (21,19).
  - Không gửi `target_key` thì `predicted_px` là null; `max_frames=1` sinh cảnh báo.
  - Ảnh PNG và ảnh hiệu trả 200 kèm `image/png`; ID lạ trả `FRAME_NOT_FOUND`.
  - Các trường hợp lỗi: `UNKNOWN_TARGET` 404, `BAD_COORDS` 400, `BAD_PARAM` 400, mất mạng (`NETWORK`), lỗi 502 không có JSON.
  - 4 endpoint còn lại.
- `src/mocks/samples.test.ts`, 12 test: **kiểm tra schema phía frontend**.
  - Kiểm tra 6 file JSON bằng Ajv (JSON Schema 2020-12) theo `components.schemas` trong `openapi.yaml`.
  - Kiểm tra 6 ảnh PNG đúng kích thước 39×39, xám 8-bit, khớp `grid`.
  - Kiểm tra `predicted_px` nằm đúng trên nguồn sáng (pixel ≥ 200), theo gốc tọa độ PNG ở góc trên trái.
  - Phần giải mã PNG tự viết trong `src/test/png.ts` nên Node không cần thư viện native.

### 2.7. CI: `.github/workflows/ci.yml`
Đây là workflow đầu tiên của repo. Chạy khi có push, pull request, hoặc chạy tay (`workflow_dispatch`). Tự hủy lần chạy cũ khi có push mới trên cùng nhánh.

| Job | Các bước |
| --- | --- |
| `api-samples` | Python 3.12. Chỉ cài `fastapi` + `pillow` theo đúng phiên bản ghi trong `requirements.txt`, rồi chạy `members/dong/scripts/validate_api_samples.py` |
| `frontend` | Node 24, `npm ci`. **Kiểm tra `schema.d.ts` khớp `openapi.yaml`** (sinh lại rồi `git diff --exit-code`). Sau đó lint, typecheck, test (gồm bước kiểm tra schema bằng Ajv), build |
| `members-js` | Chạy `npm test` ở gốc repo, gồm 173 test JS sẵn có của các thành viên và `shared/`, để giữ `main` luôn chạy được |

### 2.8. Thay đổi ngoài `frontend/`
- `package.json` gốc: lệnh `test` thêm `--exclude "frontend/**"`. `frontend/` có lệnh test và cấu hình riêng, nên Vitest ở gốc không nên quét vào đó.
- `.env.example`: thêm một dòng ghi chú về `VITE_USE_MOCK`.
- Ngoài repo: thêm cấu hình `frontend` (port 5180) vào `D:\nasa_app_challenge\.claude\launch.json` để mở preview.

---

## 3. Kiểm chứng (đều chạy trên máy, Windows 11, Node 24.19, npm 11.17)

| Lệnh | Kết quả |
| --- | --- |
| `npm run typecheck` (frontend) | Không lỗi |
| `npm run lint` (frontend) | Không lỗi |
| `npm test` (frontend) | 2 file, **23/23 pass** |
| `npm run build` (frontend) | Thành công: JS chính 225 kB (71 kB gzip), CSS 3.3 kB |
| `npm ci` lại từ đầu, rồi `gen:types` | `schema.d.ts` giống từng byte (SHA-1 `f03ff00…`), nên bước kiểm tra trong CI sẽ không báo sai |
| Validator của Đông, chạy trong venv mới chỉ có fastapi + pillow như CI | `Validated 6 API samples` |
| `npm test` ở gốc (sau khi loại `frontend/`) | 9 file, **173/173 pass** |
| Cố ý sửa `wavelength_um` thành chuỗi trong `frames_barnard_d6.json` | Test schema **báo đỏ đúng chỗ**: `/frames/0/wavelength_um must be number`. Sau đó đã khôi phục file bằng `git checkout` |
| Prettier `--check` | Các file mới đều đúng định dạng |
| **`npm run dev`, mở trong trình duyệt** | Console hiện `[MSW] Mocking enabled`. `GET /api/frames?ra=269.4521&dec=4.6934&target_key=barnard&detector=6` trả 200, trang hiện "3 frames · Barnard's Star · detector D6 · grid 39×39 at 6.15″/px", 6 ảnh PNG đều 200 |
| Bấm "Try an unknown target" | Trang hiện "That target is not in our list yet…" kèm mã `UNKNOWN_TARGET` |

**Chưa kiểm chứng:**
- Workflow CI chưa chạy trên GitHub runner vì chưa push.
- Chưa chạy frontend với backend thật (`VITE_USE_MOCK=false` + `npm run dev:be`), nên CORS giữa hai bên chưa được thử.
- Chưa kiểm tra bản build có `VITE_USE_MOCK=true`.

---

## 4. Vấn đề gặp và cách xử lý

| Vấn đề | Cách xử lý |
| --- | --- |
| npm cài TypeScript 7 mặc định, nhưng `typescript-eslint` chỉ hỗ trợ dưới 6.1 và `openapi-typescript` yêu cầu `^5` | Ghim `typescript@~5.9.3`, bản duy nhất thỏa cả ba gói |
| MSW đã lên v3: đổi tên `onUnhandledRequest` thành `onUnhandledFrame`. Test vẫn xanh vì tùy chọn sai tên bị bỏ qua âm thầm, typecheck mới phát hiện ra | Đổi sang `onUnhandledFrame` cho cả trình duyệt và Vitest. Vitest giờ báo lỗi thật khi có request không được mock |
| Import file JSON làm TypeScript hiểu `"0.1"` là `string` và tuple là `number[]`, nên không gán thẳng sang kiểu OpenAPI được | Ép kiểu trong `samples.ts`. Test Ajv chứng minh lúc chạy rằng ép kiểu này đúng |
| ESLint (react-hooks 7) cấm gọi `setState` ngay trong effect | Tách việc tải dữ liệu thành hàm thuần. Effect chỉ cập nhật state khi promise trả về, và bỏ qua kết quả của request cũ (tránh tranh chấp khi bấm liên tục) |
| Vitest ở gốc repo quét luôn test của `frontend/` | Thêm `--exclude "frontend/**"` vào lệnh test ở gốc |
| `.gitignore` chặn `.env.*`, nên không dùng được `.env.development` | Mặc định bật mock ngay trong code (`src/config.ts`), tắt bằng biến `VITE_USE_MOCK` trong `.env` |

---

## 5. Quyết định cần team biết

1. **Tên biến môi trường:** task tổng ghi `VITE_API_BASE`, nhưng repo và hướng dẫn của Đông dùng `VITE_API_BASE_URL`. Mình giữ `VITE_API_BASE_URL`.
2. **Vị trí `frontend/` ở gốc repo**, không nằm trong `members/duy-hoang/`. README quy định code thử riêng đặt trong `members/`, nhưng đây là ứng dụng sẽ deploy và Thạch sẽ ghép vào, nên cần chỗ ổn định. Code luyện tập cũ vẫn ở `members/duy-hoang/`.
3. **Dependency mới chỉ nằm trong `frontend/package.json`:** msw 3, openapi-typescript 7, typescript 5.9, eslint 10, ajv, yaml… `requirements.txt` không đổi. Theo checklist PR, cần báo team trong chat khi mở PR.
4. **Lỗi giả lập dùng `target_key` lạ (404 `UNKNOWN_TARGET`),** không dùng tọa độ trong `error_no_frames.json`. Lý do: backend fixture vẫn trả khung cho WISE 0855, và mock không nên khác backend.

---

## 6. Hạn chế đã biết
- `npm audit` báo 10 lỗ hổng mức moderate, đều nằm trong bộ công cụ ESLint (chỉ dùng khi phát triển, không vào bản build).
- Bản build production vẫn tạo chunk `browser-*.js` (406 kB, 157 kB gzip) cho MSW. Chunk này chỉ được tải khi `VITE_USE_MOCK=true`, bình thường không tải.
- Ở chế độ dev, `/api/frames` bị gọi 2 lần lúc mở trang. Đây là hành vi bình thường của React StrictMode, bản build chỉ gọi 1 lần.
- Tọa độ 4 mục tiêu ngoài Barnard lấy từ `members/duy-hoang/coords/targets.js` (SIMBAD J2000). Cần thay bằng `shared/targets.json` khi Nguyên công bố.
- Remote trong máy vẫn là địa chỉ cũ `HoangKhoi1704/NASA-space-challenges-PlanetXvsSphereX`. Theo `workflow.md`, repo giờ ở `MINIONS-WORKFORCE/Human-Binoculars`. Clone vẫn chạy, nhưng nên kiểm tra `git remote -v` trước khi push.

---

## 7. Tiến độ trong role Duy Hoàng

Chú thích: ✅ xong · 🟡 có một phần (thường là bản luyện JS trong `members/duy-hoang/`, chưa chuyển vào `frontend/`) · ⬜ chưa làm

### Bắt buộc

| # | Hạng mục | Trạng thái | Ghi chú |
| --- | --- | --- | --- |
| 1 | Tải trước toàn bộ khung rồi mới phát | 🟡 | Bản luyện có `loadFrames.js`, nhưng chưa dùng `img.decode()` và chưa có tiến độ tải. Chưa có trong `frontend/` |
| 2 | Canvas giữ pixel vuông | 🟡 | Bản luyện có `drawFrame` với `imageSmoothingEnabled = false`, đã có test. Trang tạm mới dùng `pixelated` trên `<img>` |
| 3 | Vòng lặp rAF + reducer thuần | 🟡 | Bản luyện có `playerReducer` (load/play/pause/toggle/tick/next/prev/seek/setFps, 14 test) và `requestAnimationFrame`. Cần chuyển sang TS |
| 4 | Điều khiển tối thiểu | 🟡 | Bản luyện có phím cách, mũi tên, tốc độ 0.5–10 fps. Chưa có công tắc Ảnh gốc/Ảnh hiệu và chọn detector trong viewer. Trang tạm đã có chọn detector |
| 5 | Dấu thập tại `predicted_px`, `(x+0.5)*scale` | 🟡 | Bản luyện có `drawCrosshair`, nhưng chưa vẽ theo `predicted_px`. Dữ liệu `predicted_px` đã có qua API/mock và test đã xác nhận nó nằm trên nguồn sáng |
| 6 | Mock MSW + sinh kiểu từ OpenAPI | ✅ | **Task hôm nay** |
| 7 | Kiểm thử: đơn vị / component / đầu cuối / smoke | 🟡 | Đơn vị: có (reducer, tọa độ, định dạng ở bản luyện; API client + schema hôm nay). Component (RTL): chưa. Playwright: chưa. Script smoke: chưa |
| 8 | CI + deploy | 🟡 | **CI: có file workflow hôm nay**, chưa chạy trên GitHub. Deploy, `VITE_API_BASE_URL` khi deploy, kiểm tra CORS: chưa |

### Nên biết / nâng cao
| Hạng mục | Trạng thái |
| --- | --- |
| Dòng hướng dẫn "Watch the crosshair…" | ⬜ |
| Hiện tiến độ thay vì biểu tượng xoay vô hạn | ⬜. API 0.1 hiện trả JSON đồng bộ, chưa có job |
| Truy cập: nút có nhãn, bàn phím, tương phản | 🟡 Trang tạm dùng label, focus ring và token có độ tương phản WCAG |
| So sánh hai khung bằng thanh gạt / xuất GIF | ⬜ |

### Bài luyện trước ngày 14/11
| Bài | Trạng thái |
| --- | --- |
| Trang blink 10 PNG đủ điều khiển | 🟡 `members/duy-hoang/blink-demo` (đã merge vào `main` qua PR #4) |
| Dấu thập tại pixel cho trước, đổi hệ số phóng | 🟡 Có hàm vẽ, chưa có test theo pixel và hệ số phóng |
| Test Playwright chạy trong GitHub Actions | ⬜ Đã có nền GitHub Actions từ hôm nay |
| Deploy Vercel/Netlify và gặp lỗi CORS một lần | ⬜ |

### Bàn giao cho người khác
| Bàn giao | Cho | Trạng thái |
| --- | --- | --- |
| `<BlinkViewer frames=… />` độc lập | Thạch | 🟡 Có bản JS luyện tập, chưa có bản TS dùng kiểu `Frame` từ OpenAPI |
| Workflow CI, script smoke | Cả team | 🟡 CI xong (chưa push), smoke chưa |
| URL frontend công khai | Thạch | ⬜ |

---

## 8. Việc tiếp theo đề xuất
1. **Commit, push và mở PR cho Issue 18** (dùng "Related to #18" nếu Issue còn tiêu chí khác), rồi xem CI chạy lần đầu trên GitHub.
2. Chuyển BlinkViewer sang `frontend/` bằng TS: tải trước có `decode()` và thanh tiến độ, canvas, reducer, dấu thập theo `predicted_px`, công tắc Ảnh gốc/Ảnh hiệu.
3. Thêm React Testing Library cho test component, dùng lại MSW.
4. Thêm Playwright với một kịch bản đầu cuối, chạy trong CI.
5. Deploy `frontend/` (Root Directory = `frontend`), chạy với backend thật để thử CORS.
6. Trước 14/11: commit hoặc lưu lại phần chưa commit trong bản clone cũ (`difference.js`…).

---

## 9. Cách chạy lại

```bash
cd D:/nasa_app_challenge/fresh/NASA-space-challenges-PlanetXvsSphereX/frontend
npm install
npm run dev
npm test
```

Mở http://localhost:5173. Console phải hiện `[MSW] Mocking enabled.` và trang phải hiện 3 khung của Barnard's Star.
