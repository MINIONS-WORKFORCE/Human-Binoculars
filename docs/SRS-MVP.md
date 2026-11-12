# SRS – SPHEREx Sky Viewer MVP (12/11)

Người viết: Thạch · Bản chụp ngày 9/11/2026, **cập nhật ngày 12/11/2026 theo hợp đồng API 0.1**

> Hợp đồng đang áp dụng là **API 0.1** trên [wiki hợp đồng](https://github.com/MINIONS-WORKFORCE/Human-Binoculars/wiki/The-API-contract), được sinh ra thành [`shared/api-contract/openapi.yaml`](../shared/api-contract/openapi.yaml) từ các model Pydantic của backend. Hợp đồng "v1" trong bản SRS ngày 9/11 (`s_ra`, `obs_collection`, `/files/…`, `NO_DATA`, lỗi 422…) **không còn hiệu lực**; mục 5 và 6 dưới đây đã viết lại theo 0.1. Khi file này lệch với wiki hoặc `openapi.yaml`, wiki và `openapi.yaml` là bản đúng.
>
> Bản SRS trực tuyến trên claude.ai chưa được đối chiếu với bản cập nhật này; ai giữ bản đó cần chép sang bằng tay. Kết quả chạy từng dòng nghiệm thu nằm ở [QA-matrix.md](QA-matrix.md).

## 1. Mục tiêu và phạm vi

Đến hết **12/11**, MVP làm trọn một việc: nhập một vị trí hoặc tên vật thể, gọi API 0.1, rồi xem ba thứ cạnh nhau: viewer blink các khung SPHEREx có ghi ngày chụp, bản đồ trời Aladin kèm Gaia DR3, và biểu đồ photometry (đường cong ánh sáng, phổ). Cả 5 mục tiêu kiểm thử đều chạy được.

**Chế độ dữ liệu hiện tại là `fixture`.** Khi máy có gói FITS fixture của Khôi (`data/fixtures/`, không commit vào git), backend dựng khung từ các cutout SPHEREx thật đó. Khi không có gói, backend trả mẫu tổng hợp: 3 khung PNG 39×39 (nhãn `FIX`) cho mọi vị trí hợp lệ. Photometry và astrometry luôn là mẫu tổng hợp, và chỉ R Draconis có số đo photometry; các giá trị này dùng để thử giao diện, không phải số đo khoa học. `DATA_MODE=live` hiện trả lỗi `INTERNAL` vì các adapter dữ liệu thật chưa được nối vào API 0.1 (xem `shared/api-contract/frontend-guide.md`). Mục tiêu ban đầu "backend tìm ảnh SPHEREx thật trên IRSA" vì thế **chưa đạt** ở MVP này. Ngày 12/11, các lần chạy của Thạch dùng mẫu tổng hợp vì máy này chưa có gói FITS.

| Mức | Tính năng | Lý do |
| --- | --- | --- |
| Must | Nhập toạ độ hai dạng hoặc tên vật thể; chọn detector D1–D6 và FOV (`size`); trạng thái nằm trong URL | Yêu cầu MVP của đề |
| Must | `/api/frames` trả JSON đồng bộ kèm PNG cùng một thang độ sáng (`norm`) | Phần lõi của sản phẩm |
| Must | Viewer blink ghi rõ ngày (`iso`), bước sóng, detector và release của từng khung | Phần người dùng nhìn thấy |
| Must | 5 nút mục tiêu dùng `target_key`, nhờ đó có `predicted_px` để vẽ dấu thập | Barnard dịch rất nhanh nên cần vị trí dự đoán |
| Must | Báo lỗi rõ ràng cho `BAD_COORDS`, `BAD_PARAM`, `UNKNOWN_TARGET`, `FRAME_NOT_FOUND`, `NO_FRAMES` và cảnh báo `FEW_FRAMES` | Yêu cầu MVP của đề |
| Should | Ảnh hiệu (`diff_png`) có nút bật/tắt | Đã có |
| Should | Cảnh báo `SATURATION_POSSIBLE`, `MIXED_WAVELENGTH` theo từng phản hồi | Có trong enum của hợp đồng |
| Should | Link công khai cho frontend và backend | Luyện deploy trước ngày thi |
| Could | Panel photometry: đường cong ánh sáng và phổ từ `/api/photometry` | Đã ghép vào frontend |
| Could | Bản đồ Aladin + overlay Gaia DR3 cạnh viewer | Đã ghép vào frontend |
| Could | Biểu đồ astrometry (`/api/astrometry`) | Chưa làm |
| Won't | Job bất đồng bộ, tự phát hiện vật thể, ảnh màu giả, mã nhúng | Để dành cho ngày thi hoặc bỏ |

**Luật thi:** MVP nằm trong repo đào tạo, và code không được chép sang repo dự thi. Thứ mang sang ngày thi là kỹ năng và hợp đồng API. Có được mang bản in hợp đồng vào hay không thì phải hỏi Local Lead (đã có trong checklist trước ngày thi).

**Thay đổi so với lộ trình:** 4 ngày này thay buổi diễn tập 9/11 và việc viết runbook 11/11 bằng việc xây MVP thật. Ngày đổi vai 10/11 làm ngay trên các module của MVP, và ngày 12/11 dùng để nghiệm thu và retro thay cho mini-hackathon ISS. Nhóm cần chốt việc này (mục 10).

## 2. Hiện trạng repo ngày 12/11

`main` và `dev` đã trùng nhau từ PR #47 (11/11) và đã có hợp đồng API 0.1, backend fixture, frontend, CI. Số test là kết quả chạy lại ngày 12/11 trên nhánh `thach/integrate-frontend` (cài `npm ci`/`pip` theo README): frontend 159 test đơn vị và 10 test Playwright (Microsoft Edge, bản build mock); thư mục gốc 218 test JS; backend 72 test đạt, 1 bỏ qua; validator kiểm 6 JSON mẫu đạt.

| Người | Đã có (nơi nằm) | Còn thiếu cho MVP |
| --- | --- | --- |
| Duy Hoàng | `frontend/` trên `main`: bộ khung Vite + React + TS với mock MSW và CI (Issue 18); viewer blink có preload, dấu thập, nút ảnh hiệu và e2e; ô nhập tên và hai dạng toạ độ | Chọn FOV (`size`); URL lưu detector và vị trí; trạng thái "đang chậm" |
| Đông | `app.main` bảy endpoint theo hợp đồng 0.1 (Issue 14), phục vụ khung fixture (Issue 24), CI/CD đóng gói bản dựng, Playwright trong CI; mã lỗi và `openapi.yaml` sinh từ model | `DATA_MODE=live` chưa có (trả `INTERNAL`); resolver chỉ biết Barnard; chưa có bản deploy công khai |
| Khôi | Fixture 5 mục tiêu và `manifest.json`, `find_frames` ngoại tuyến (Issue 21), SIA2/TAN pipeline (Issue 15), `shared/pipeline/irsa.py`; Issue 34 (gộp tải cutout, gói fixture trên drive) đang ở nhánh `khoi/issue-34-drive-cutout-refactor`, chưa vào `dev` | Nối đường dữ liệu thật vào API 0.1 cùng Đông và Hữu Hoàng |
| Hữu Hoàng | Bài A–F xử lý ảnh trên cutout thật (đưa về cùng lưới TAN, median theo detector × đợt, ảnh hiệu, kiểm tra nhảy sao nền), `tan_pipeline.py` được CI đóng gói; nhánh `huu-hoang` chưa vào `dev` | Đầu ra theo dạng `Frames` của hợp đồng 0.1 (`grid`, `norm`, `predicted_px`) |
| Nguyên | `shared/targets.json` (5 mục tiêu, J2000 và chuyển động riêng) trên `dev`; nhánh `nguyen/day03-04` | Bảng photometry/astrometry có đơn vị và sai số cho Đông và Thạch; sai số cho phép của dịch chuyển (mục 9) |
| Thạch | Design tokens (#6), SRS và QA matrix (#11), đọc toạ độ có dấu hai chấm và khoảng trắng (#27), `shared/charts/` (có biểu đồ photometry), `shared/skymap/` (Aladin + Gaia); nay ghép biểu đồ và bản đồ vào `frontend/` (nhánh `thach/integrate-frontend`) | Chạy QA matrix trên máy khác; Gaia thật chưa kiểm vì máy này không vào được CDS |

Những điểm các phần còn lệch nhau, mục 5 đã chốt cách xử lý và mục 10 giữ phần chưa chốt:

- **FOV:** hợp đồng 0.1 nhận `size` bằng độ trong khoảng [0,02; 0,3]; mặc định 0,1. Frontend chưa có ô chọn FOV. Mẫu tổng hợp bỏ qua `size` (PNG luôn 39×39, ô ≈ 6,15″); nhánh dựng từ FITS thật chưa được chạy trên máy này.
- **Detector:** số nguyên 1–6, mặc định 6. Chuỗi `SPHEREx-D6` của bản v1 đã bỏ.
- **Release:** hợp đồng 0.1 **không có tham số release**. Mỗi khung và mỗi điểm photometry mang trường `release` (ví dụ `qr2`) chỉ để hiển thị. Việc chọn QR2/QR3 trên giao diện (FR-02 cũ) bị bỏ.
- **Đợt quét:** trường `survey` là số nguyên do backend điền. Cách chia đợt (30 ngày của Hữu Hoàng hay quy tắc tài liệu SPHEREx của Nguyên) chưa được chốt.
- **Khoá mục tiêu:** API dùng `target_key` = `barnard`, `wise0855`, `epsindib`, `rwaur`, `rdra`, còn `shared/targets.json` dùng `id` = `barnard`, `wise0855`, `epsilon-indi-b`, `rw-aur`, `r-dra`. Frontend đang dùng khoá của API (`frontend/src/targets.ts`).
- **Toạ độ:** `predicted_px` chỉ có khi gửi `target_key`; gõ toạ độ tự do thì API trả `null` và viewer không vẽ dấu thập.
- **Photometry fixture:** chỉ `target_key=rdra` có 6 điểm; mọi mục tiêu khác trả `points: []`, panel hiện thông báo rỗng.

## 3. Kiến trúc và luồng dữ liệu

```mermaid
flowchart TB
  T["Thạch · giao diện<br/>design-tokens.css, charts, skymap"] -- "tokens, PhotometryChart, SkyMap" --> V["Frontend · Duy Hoàng, Thạch<br/>nhập toạ độ, blink, bản đồ Aladin, biểu đồ"]
  N["targets.json · Nguyên<br/>5 mục tiêu"] -- 5 nút --> V
  V -- "GET /api/resolve, /api/frames,<br/>/api/photometry, /api/astrometry" --> B["Backend FastAPI · Đông<br/>app.main, DATA_MODE=fixture"]
  B -- "JSON + PNG 39×39" --> V
  V -- "Gaia DR3 (VizieR)" --> C[("CDS: Aladin, VizieR<br/>(ngoài nhóm)")]
  B -. "live: chưa nối" .-> K["irsa.py · Khôi<br/>SIA2 + cutout"]
  K -. manifest.json .-> H["Xử lý ảnh · Hữu Hoàng<br/>TAN, median theo đợt"]
  K -.-> I[("IRSA (ngoài nhóm)")]
```

Nét liền là phần đang chạy; nét đứt là đường dữ liệu thật chưa nối vào API 0.1. Trình duyệt chỉ nói chuyện với backend của nhóm cho dữ liệu SPHEREx, không gọi IRSA trực tiếp. Bản đồ trời và lớp Gaia là ngoại lệ: Aladin Lite gọi thẳng CDS (ảnh nền HiPS và VizieR), nên nơi chặn CDS chỉ mất bản đồ, viewer blink vẫn chạy.

## 4. Yêu cầu chức năng

Mỗi yêu cầu có một người sở hữu và một người đỡ theo vòng dự phòng, nên khi một người trễ thì đã biết ai vào giúp. Yêu cầu Must phải xong trước 12/11; Should và Could chỉ làm sau khi Must đã đạt. Cột trạng thái ghi theo repo ngày 12/11 và chỉ tính phần đã chạy trên mock hoặc fixture.

| ID | Yêu cầu | Mức | Sở hữu | Đỡ | Trạng thái 12/11 |
| --- | --- | --- | --- | --- | --- |
| FR-01 | Nhập vị trí dạng độ thập phân, giờ–phút–giây (kể cả dấu hai chấm hoặc khoảng trắng) hoặc tên vật thể, ra RA/Dec theo độ; nhập sai thì báo lỗi ngay tại ô nhập | Must | Duy Hoàng | Thạch | Xong (test đơn vị và e2e) |
| FR-02 | Chọn detector D1–D6 (`detector`) và FOV 2′, 5′ hoặc 10′ (`size` = 0,0333; 0,0833; 0,1667). Không còn chọn release | Must | Duy Hoàng | Thạch | Một phần: có detector, chưa có FOV |
| FR-03 | URL `?q=&fov=&det=` mở lại đúng khung nhìn đang xem | Must | Duy Hoàng | Thạch | Chưa làm |
| FR-04 | 5 nút mục tiêu gửi `target_key` để có `predicted_px` | Must | Duy Hoàng | Hữu Hoàng | Xong (khoá theo API) |
| FR-05 | `/api/frames`: JSON đồng bộ, khung xếp theo `mjd` tăng dần, `grid`, `norm`, `reference_frame_id`, `warnings` | Must | Đông | Duy Hoàng | Xong ở chế độ fixture (mẫu tổng hợp đã chạy; dựng từ FITS cần gói fixture); live chưa có |
| FR-06 | PNG xám 8-bit cùng một thang `norm` (mẫu tổng hợp: 39×39); ảnh hiệu xám 128 = 0; vị trí pixel theo gốc trên-trái, tâm pixel ở số nguyên | Must | Hữu Hoàng | Khôi | Xong ở fixture; ảnh từ IRSA chưa nối |
| FR-07 | Backend kiểm tra đầu vào và trả lỗi theo mục 5; mọi JSON mang `api_version` = `0.1` | Must | Đông | Duy Hoàng | Xong |
| FR-08 | Viewer blink các khung theo thời gian; ghi ngày, bước sóng, detector; play, pause, tốc độ, thanh trượt khung; dấu thập ở `predicted_px` | Must | Duy Hoàng | Thạch | Xong |
| FR-09 | Hiển thị đang tải, lỗi theo `error.code` và cảnh báo; nhãn dữ liệu mock/fixture | Must | Duy Hoàng | Đông | Một phần: có lỗi và nhãn mock; chưa có "đang chậm" |
| FR-10 | Fixture cho 5 mục tiêu chạy khi mất mạng | Must | Khôi (dựng), Đông (phục vụ) | Hữu Hoàng | Xong (fixture cục bộ) |
| FR-11 | Ảnh hiệu (`diff_png`) có nút bật/tắt | Should | Hữu Hoàng (ảnh), Duy Hoàng (nút) | Nguyên | Xong |
| FR-12 | Hiển thị cảnh báo của phản hồi: `SATURATION_POSSIBLE`, `MIXED_WAVELENGTH`, `FEW_FRAMES`, `TRUNCATED` | Should | Hữu Hoàng | Nguyên | Một phần: viewer in `warnings`, chưa giải thích từng mã |
| FR-13 | Deploy frontend và backend lên link công khai | Should | Duy Hoàng | Đông | Chưa làm |
| FR-14 | Panel đường cong ánh sáng và phổ từ `/api/photometry` (E6): điểm không phát hiện vẽ thành giới hạn trên 3σ, điểm có `flagged` vẽ rỗng, lọc detector, bảng số liệu | Could | Thạch | Nguyên | Xong trên mock và fixture |
| FR-15 | Bản đồ Aladin + overlay Gaia DR3 cạnh viewer, tâm theo vị trí đang xem, chọn Gaia thật, sao giả hoặc tắt | Could | Thạch | Duy Hoàng | Xong; Gaia thật chưa kiểm vì không vào được CDS |
| FR-16 | Biểu đồ astrometry từ `/api/astrometry` | Could | Thạch | Nguyên | Chưa làm |

FR-02 bỏ lựa chọn 20′ vì 0,333° vượt giới hạn 0,3° của hợp đồng.

## 5. Hợp đồng API 0.1

Nguồn chính là wiki và `openapi.yaml`. Bản tóm tắt này để tra cứu nhanh. Mọi phản hồi JSON có `api_version` = `0.1`. Thay đổi trường đi qua quy trình thảo luận và review của wiki.

| Endpoint | Tham số bắt buộc | Tham số tuỳ chọn | Trả về |
| --- | --- | --- | --- |
| `GET /api/health` | không có | không có | `status` (`ok`/`degraded`), `mode` (`fixture`/`live`), `fixture_targets`, `irsa_reachable`, `git_sha` |
| `GET /api/resolve` | `name` | không có | `target_key`, `name`, `ra`, `dec`, `epoch`, `pmra`, `pmdec`, `parallax_mas`, `kind`, `source` |
| `GET /api/frames` | `ra`, `dec` | `detector`=6, `size`=0,1, `max_frames`=60, `target_key` | `target`, `detector`, `grid`, `norm`, `reference_frame_id`, `frames[]`, `warnings[]` |
| `GET /api/frames/{id}.png` | không có | không có | PNG 39×39, xám 8-bit |
| `GET /api/frames/{id}/diff.png` | không có | không có | PNG ảnh hiệu, xám 128 = 0 |
| `GET /api/photometry` | `ra`, `dec` | `target_key`, `detector`, `aperture_arcsec`=12,3 | `target`, `reference_star`, `points[]`, `variability` |
| `GET /api/astrometry` | `ra`, `dec` | `target_key`, `detector` | `target`, `catalog_pm`, `points[]`, `fit` |

### Quy ước đầu vào

- **Toạ độ:** `ra` trong [0, 360), `dec` trong [−90, 90], ICRS theo độ.
- **FOV:** `size` là độ trong [0,02; 0,3]. Frontend đổi từ phút cung: 2′ → 0,0333, 5′ → 0,0833, 10′ → 0,1667. Mẫu tổng hợp kiểm tra nhưng không cắt lại ảnh.
- **Detector:** số nguyên 1–6. Với photometry và astrometry, bỏ trống là lấy mọi detector có số liệu.
- **`target_key`:** `barnard`, `wise0855`, `epsindib`, `rwaur`, `rdra`. Không gửi thì `predicted_px` là `null`. Khoá lạ trả `UNKNOWN_TARGET`.
- **`max_frames`:** 1–200. `max_frames=1` làm phản hồi có `FEW_FRAMES` và `TRUNCATED`.
- **Resolver fixture:** chỉ nhận Barnard's Star, Barnard, Barnards Star. Tên khác trả `UNKNOWN_TARGET`; frontend tự nhận 5 mục tiêu và tên phụ ngoại tuyến trước khi hỏi `/api/resolve`.

### Trường chính trong phản hồi

| Trường | Kiểu | Ý nghĩa |
| --- | --- | --- |
| `frames[].id` | chuỗi mờ | Dùng để ghép URL ảnh; không suy ra ý nghĩa từ nội dung |
| `frames[].mjd`, `iso` | số, chuỗi | Thời điểm quan sát; xếp `frames[]` theo `mjd` tăng dần |
| `frames[].wavelength_um`, `bandwidth_um` | số | Bước sóng trung tâm và độ rộng của kênh |
| `frames[].release`, `survey` | chuỗi, số nguyên | Đợt phát hành (ví dụ `qr2`) và số đợt quét |
| `frames[].bad_pixel_frac` | số 0–1 | Tỷ lệ pixel bị che |
| `frames[].predicted_px` | `[x, y]` hoặc `null` | Vị trí dự đoán, gốc trên-trái, tâm pixel ở số nguyên; vẽ ở `(x+0,5)·k`, `(y+0,5)·k` |
| `frames[].png`, `diff_png` | đường dẫn | Ghép với gốc API bằng `new URL(path, base)`. Gọi `/api/frames` trước để ảnh được đăng ký |
| `grid` | object | `width`, `height`, `pixscale_arcsec`, `projection` = `TAN`, `center_ra`, `center_dec` |
| `norm` | object | `vmin`, `vmax`, `stretch` = `asinh`; dùng chung cho mọi khung |
| `photometry.points[]` | mảng | `frame_id`, `mjd`, `wavelength_um`, `detector`, `release`, `survey`, `flux_mjy`, `err_mjy`, `snr`, `detected`, `flagged`, `is_reference_star` |
| `photometry.variability` | object hoặc `null` | `chi2_reduced`, `dof`, `is_variable`, `method` |
| `astrometry.points[]`, `fit` | mảng, object | Vị trí đo và dự đoán theo khung; `fit` gồm `pmra`, `pmdec`, sai số, `n_points`, `baseline_days` |

### Cảnh báo và mã lỗi

Cảnh báo không chặn kết quả: HTTP vẫn là 200 và nằm trong `warnings[]` (mảng chuỗi). Lỗi chặn kết quả và có dạng `{"api_version": "0.1", "error": {"code", "message", "details"}}`; frontend quyết định theo `code`.

| Mã | Nơi xuất hiện | Khi nào | Frontend làm gì |
| --- | --- | --- | --- |
| `SATURATION_POSSIBLE` | `warnings` của `/api/frames` | Có thể có pixel bão hoà | Hiện cảnh báo |
| `FEW_FRAMES` | `warnings` của `/api/frames` | Ít hơn 3 khung, hoặc danh sách lọc ra rỗng | Hiện cảnh báo; blink ít ý nghĩa |
| `TRUNCATED` | `warnings` của `/api/frames` | Đã cắt theo `max_frames` | Ghi chú nhỏ |
| `MIXED_WAVELENGTH` | `warnings` của `/api/frames` | Các khung khác bước sóng | Cảnh báo khi so độ sáng theo thời gian |
| `BAD_COORDS` | HTTP 400 | `ra` hoặc `dec` ngoài khoảng | Lỗi cạnh ô nhập vị trí; `details.fields` nêu tên trường |
| `BAD_PARAM` | HTTP 400 | Tham số khác sai (detector, `size`, `max_frames`, `name`…) | Lỗi cạnh ô tương ứng |
| `UNKNOWN_TARGET` | HTTP 404 | `target_key` hoặc tên không có | Gợi ý 5 mục tiêu có sẵn |
| `FRAME_NOT_FOUND` | HTTP 404 | Ảnh đã bị đẩy khỏi bộ nhớ hoặc server khởi động lại | Gọi lại `/api/frames` |
| `NO_FRAMES` | HTTP 404 | Gói FITS fixture không phủ lưới này (xem `error_no_frames.json`) | Hiện thông báo, gợi ý đổi vị trí hoặc detector |
| `INTERNAL` | HTTP 500 | Lỗi không mong đợi (kể cả `DATA_MODE=live` chưa nối) | Hiện lỗi chung, báo nhóm |
| `NETWORK` | chỉ trong frontend | Không kết nối được tới API | Nút thử lại |

OpenAPI còn khai báo 502, 503 và 504 cho mọi endpoint, nhưng backend 0.1 chưa phát ra các mã lỗi riêng cho chúng. **Thời gian:** API trả JSON đồng bộ, không có job bất đồng bộ. Hạn mức "đang chậm sau 30 giây" của bản v1 chưa cần cho fixture và chưa được cài trong frontend.

### Ví dụ phản hồi

Số liệu dưới đây là dữ liệu tổng hợp trong `api_samples/`, chỉ để minh hoạ cấu trúc, không phải phép đo. Phản hồi `/api/frames` được rút gọn còn một khung.

```json
{
  "api_version": "0.1",
  "target": { "ra": 269.4521, "dec": 4.6934, "name": "Barnard's Star", "target_key": "barnard" },
  "detector": 6,
  "grid": { "width": 39, "height": 39, "pixscale_arcsec": 6.15, "projection": "TAN",
            "center_ra": 269.4521, "center_dec": 4.6934 },
  "norm": { "vmin": 0.0, "vmax": 1.0, "stretch": "asinh" },
  "reference_frame_id": "fixture-barnard-d6-0",
  "frames": [
    { "id": "fixture-barnard-d6-0", "mjd": 60800.0, "iso": "2025-05-05T00:00:00Z",
      "wavelength_um": 4.7, "bandwidth_um": 0.037, "release": "qr2", "survey": 1,
      "bad_pixel_frac": 0.0, "predicted_px": [17.0, 19.0],
      "png": "/api/frames/fixture-barnard-d6-0.png",
      "diff_png": "/api/frames/fixture-barnard-d6-0/diff.png" }
  ],
  "warnings": []
}
```

## 6. Hợp đồng giữa các mảng

Code dùng chung nằm trong `shared/` theo đúng luật của repo. Mỗi mảnh chỉ gọi mảnh kế tiếp qua một hàm hoặc một định dạng, nên có thể làm song song trên dữ liệu giả rồi thay bằng phần thật. Chữ ký hàm `resolve`, `find_frames`, `build_frames`, `photometry`, `astrometry` nằm ở mục 6 của wiki hợp đồng; file này không chép lại để tránh có hai bản khác nhau. Cách giao và nhận xem [docs/team/handoff.md](team/handoff.md).

| Bàn giao | Người giao → người nhận | Định dạng | Thay tạm bằng gì khi chưa có |
| --- | --- | --- | --- |
| Tìm và tải ảnh | Khôi → Hữu Hoàng, Nguyên, Đông | `shared/pipeline/irsa.py`, FITS và `manifest.json` | Fixture 5 mục tiêu |
| Dựng khung | Hữu Hoàng → Đông | Hàm Python, PNG, `grid`, `norm`, `predicted_px` | `api_samples/` |
| Số đo | Nguyên → Đông, Thạch | Bảng photometry và astrometry có đơn vị, sai số, giới hạn khoa học | `photometry_rdra.json`, `astrometry_barnard.json` |
| API | Đông → Duy Hoàng, Thạch | HTTP theo mục 5; `openapi.yaml`; JSON và PNG mẫu trong `api_samples/` | MSW trong `frontend/src/mocks/` |
| Mục tiêu | Nguyên → Đông, Duy Hoàng | `shared/targets.json` | `frontend/src/targets.ts` |
| Giao diện | Thạch → Duy Hoàng | `shared/design-tokens.css`, `shared/charts/`, `shared/skymap/` | Style sẵn có trong viewer |

### Frontend gọi API thế nào

`frontend/src/api/client.ts` là client có kiểu, sinh kiểu từ `openapi.yaml` (`npm run gen:types`). CI báo lỗi nếu `openapi.yaml` đổi mà `schema.d.ts` chưa sinh lại, hoặc nếu một JSON mẫu không khớp schema. Với mock, MSW trả lời các lệnh gọi `/api/*` từ `api_samples/` và theo cùng quy tắc kiểm tra như backend (`frontend/src/mocks/handlers.ts`). Với backend thật, đặt `DATA_MODE=fixture` và `VITE_USE_MOCK=false` trong `.env` rồi chạy `npm run dev:be`.

### Thạch: biểu đồ và bản đồ

```tsx
import { PhotometryChart } from "../../../shared/charts/Charts.jsx";
import { SkyMap } from "../../../shared/skymap/SkyMap.jsx";

const data = await api.photometry({ ra, dec, targetKey }); // không truyền detector
<PhotometryChart data={data} />;
<SkyMap raDeg={ra} decDeg={dec} fovDeg={0.1} gaia="vizier" />; // "vizier" | "mock" | "off"
```

`PhotometryChart` nhận đúng phản hồi `/api/photometry`: trục x là `mjd` (đường cong ánh sáng) hoặc `wavelength_um` (phổ), có bộ lọc D1–D6 và bảng số liệu. `SkyMap` nhảy tới vị trí mỗi khi `raDeg`/`decDeg` đổi. Trong `frontend/`, hai panel này nằm ở `src/science/` và được nạp theo yêu cầu để viewer blink không phải chờ Plotly và Aladin.

## 7. Yêu cầu phi chức năng

| ID | Yêu cầu | Cách kiểm |
| --- | --- | --- |
| NFR-01 | Phản hồi fixture trả trong dưới 2 giây; khi có chế độ live thì ghi giới hạn thời gian ở wiki | Đông ghi log thời gian (`duration_ms` đã có trong log của backend) |
| NFR-02 | Sao đứng yên không dịch quá 1 pixel giữa các khung | Kiểm tra tâm sao như bài A của Hữu Hoàng, Nguyên xác nhận |
| NFR-03 | Mọi khung cùng lưới, cùng kích thước và cùng `norm` | Test tự động trên `grid` và `norm` |
| NFR-04 | Khi mất mạng, 5 mục tiêu vẫn chạy từ fixture; chỉ mất bản đồ Aladin và lớp Gaia | Ngắt mạng rồi bấm lần lượt 5 nút |
| NFR-05 | Dữ liệu tổng hợp luôn có nhãn: huy hiệu "Mock API" của trang, ghi chú dưới biểu đồ, nhãn `FIX` trên PNG | Thạch kiểm theo QA matrix |
| NFR-06 | Giao diện bằng tiếng Anh, dùng design tokens, nút cao tối thiểu 44px, dùng được bằng bàn phím, không cuộn ngang ở bề rộng 390px | Thạch kiểm theo QA matrix; có test Playwright cho phần cuộn ngang |
| NFR-07 | Mỗi module có test và README một trang ghi cách chạy; README này dùng luôn làm runbook | Người đỡ tự chạy lại được trong ngày đổi vai |
| NFR-08 | Không commit file FITS, cache hay `.env`; mỗi PR nhỏ và có người review | `.gitignore` và PR template |

## 8. Vai trò và kế hoạch 9–12/11

Ngày đầu chốt hợp đồng và cho mỗi người một đầu vào giả để không ai phải chờ; ngày thứ hai thay dữ liệu giả bằng dữ liệu thật; ngày thứ ba chạy đầu–cuối cho 5 mục tiêu; ngày cuối nghiệm thu. Giờ làm việc và luật 30 phút giữ như lộ trình. Bảng dưới là kế hoạch ban đầu của Thạch; kết quả thực tế nằm ở các mốc bên dưới.

| Người | 9/11 (T2): chốt hợp đồng | 10/11 (T3): dữ liệu thật | 11/11 (T4): đầu–cuối | 12/11 (T5): nghiệm thu |
| --- | --- | --- | --- | --- |
| Thạch | Mở PR cho tokens, Aladin và biểu đồ; viết QA matrix từ mục 9; theo dõi các mốc | Kiểm tra giao diện; ghép biểu đồ khi Must đã đạt | Kiểm tra ở bề rộng 390px; cập nhật SRS | Ghi kết quả nghiệm thu, quyết Go/No-Go |

Kế hoạch của năm người còn lại được giữ trong tài liệu trực tuyến và issue GitHub của từng người.

**Mốc kiểm tra (22:30 mỗi ngày), tình trạng ngày 12/11:**

- [x] **9/11:** hợp đồng vào `main` và Duy Hoàng chạy được mock trên máy mình. Đạt trễ: hợp đồng 0.1 vào `main` ngày 11/11 (PR #47), mock MSW chạy từ ngày 10/11.
- [ ] **10/11:** một mục tiêu chạy đầu–cuối bằng dữ liệu thật. **Không đạt:** API 0.1 mới chạy fixture, `DATA_MODE=live` chưa nối.
- [ ] **11/11:** toàn bộ mục Must trong checklist mục 9 đạt. **Chưa đạt:** còn FR-02 (FOV), FR-03 (URL) và các dòng cần dữ liệu thật.
- [ ] **12/11:** nghiệm thu xong, bản hợp đồng cuối đã ghi lại. Đang làm: QA matrix đã điền phần chạy tự động trên mock và fixture.

## 9. Tiêu chí nghiệm thu

MVP đạt khi tất cả các mục Must dưới đây đạt trên một máy không phải máy của người viết code. Nguyên chủ trì, Thạch ghi kết quả. Sai số cho phép của dịch chuyển do Nguyên chốt. Bảng chạy thử có cột kết quả cho từng dòng: [QA matrix](QA-matrix.md). Phần đã đánh dấu dưới đây chỉ là kết quả chạy tự động trên mock và fixture, chưa thay cho lần chạy trên máy khác.

**5 mục tiêu (Must):**

- [ ] **WISE 0855, D6:** có ít nhất 2 khung khác thời điểm, mỗi khung ghi ngày và detector; sao nền không dịch quá 1 pixel. (Mẫu tổng hợp: 3 khung; phần "sao nền" cần cutout thật.)
- [ ] **Barnard:** ngôi sao nằm trong khung và dấu thập đúng `predicted_px`; dịch chuyển giữa các khung khớp bảng kỳ vọng của Nguyên. (Mẫu tổng hợp: dấu thập đúng; khớp bảng cần cutout thật.)
- [ ] **Epsilon Indi B:** khung tải được với `target_key=epsindib`, đúng nguồn B chứ không nhầm sang A.
- [ ] **RW Aurigae:** khung tải được với `target_key=rwaur`; độ sáng thay đổi chỉ xác nhận được khi có số đo thật.
- [ ] **R Draconis:** khung tải được và panel photometry vẽ đủ 6 điểm D1–D6; cảnh báo `SATURATION_POSSIBLE` nếu API trả (Should).

**Hành vi chung (Must):**

- [x] Nhập `133.7951 -7.2451` và `08h55m10.831s -07d14m42.53s` cho ra cùng một vị trí (test đơn vị và e2e).
- [ ] Một toạ độ ngoài 5 mục tiêu trả về khung hoặc `NO_FRAMES`/`FEW_FRAMES` rõ ràng. (Fixture trả 3 khung cho mọi toạ độ hợp lệ.)
- [ ] Mất mạng thì 5 mục tiêu vẫn chạy trên fixture cục bộ.
- [x] Nhập sai thì báo lỗi ngay tại ô nhập; tham số sai gửi tới API thì nhận `BAD_COORDS` hoặc `BAD_PARAM` kèm `details.fields` (test đơn vị và e2e trên mock).
- [ ] Tải lại trang với URL đang xem thì mở lại đúng vị trí, FOV và detector. (Chưa làm.)
- [x] Phản hồi của chế độ mock và chế độ fixture khớp `openapi.yaml` (test tự động: `src/mocks/samples.test.ts` và `validate_api_samples.py`).
- [ ] Mỗi module có README, và người đỡ đã tự chạy lại được trong ngày đổi vai.

**Should:**

- [ ] Bật ảnh hiệu thì thấy Barnard thành một cặp sáng–tối. (Nút đã có; ảnh fixture là tổng hợp.)
- [ ] Link công khai mở được ở tab ẩn danh trên một máy khác.

## 10. Rủi ro và câu hỏi mở

| Rủi ro | Dấu hiệu sớm | Cách xử lý |
| --- | --- | --- |
| Dữ liệu thật chưa nối vào API 0.1 | `DATA_MODE=live` trả `INTERNAL`; 10/11 trượt | Demo bằng fixture; ghi rõ khi đó là mẫu tổng hợp hay cutout từ gói FITS; Đông, Khôi, Hữu Hoàng nối adapter theo issue |
| Mock và backend lệch nhau | Một trang chạy trên mock nhưng hiện khác khi nối backend thật | Mock MSW sao theo `members/dong/app/fixture_api.py`; chạy cùng một bộ mẫu trong `api_samples/`. Ngày 12/11 đã sửa một chỗ lệch: photometry chỉ có số đo cho R Draconis |
| Khoá mục tiêu của API khác `shared/targets.json` | `epsindib`, `rwaur`, `rdra` so với `epsilon-indi-b`, `rw-aur`, `r-dra` | Frontend dùng khoá của API; cần một bảng ánh xạ hoặc đổi tên khi nối `targets.json` |
| Không vào được CDS (Aladin, Gaia) từ một số mạng | Bản đồ trời màu xám, câu "Could not reach VizieR" | Aladin chỉ ở mức Could, viewer chính không phụ thuộc CDS; lớp Gaia có chế độ sao giả và chế độ tắt |
| Bản dựng frontend nặng | Gói Plotly (khoảng 1,2 MB) và Aladin (khoảng 2,4 MB) | Hai panel nạp theo yêu cầu; viewer và ô nhập tải ngay |
| Thiếu giờ: mỗi ngày thường chỉ khoảng 3 giờ | Mốc 10/11 trượt | Cắt Should và Could, giữ nguyên Must |

**Câu hỏi mở:**

1. Nhóm đồng ý thay lịch 9–12/11 của lộ trình bằng kế hoạch ở mục 8 không? Nếu đồng ý, mini-hackathon ISS ngày 12/11 bị bỏ.
2. Chia đợt theo khoảng cách 30 ngày (Hữu Hoàng) hay theo quy tắc trong tài liệu SPHEREx (Nguyên)? Đề xuất: dùng cách 30 ngày vì đã có test, Nguyên kiểm xem hai cách có cho cùng kết quả trên 5 mục tiêu không.
3. Detector và FOV mặc định cho từng mục tiêu là gì? Nguyên chốt.
4. Release (QR2, QR3) có cần để người dùng chọn không? Hợp đồng 0.1 không có tham số này; nếu cần thì phải thêm vào wiki.
5. Có deploy ngay trong MVP không, hay chỉ chạy trên máy?
6. Local Lead có cho mang bản in hợp đồng API vào ngày thi không?

## 11. Nguồn

- [Hợp đồng API 0.1 (wiki)](https://github.com/MINIONS-WORKFORCE/Human-Binoculars/wiki/The-API-contract) và [Issue 14](https://github.com/MINIONS-WORKFORCE/Human-Binoculars/issues/14)
- [`openapi.yaml`](../shared/api-contract/openapi.yaml), [hướng dẫn cho frontend](../shared/api-contract/frontend-guide.md) và [JSON mẫu](../api_samples/README.md)
- [Bàn giao giữa các vai trò](team/handoff.md), [làm việc từ GitHub Issue](team/workflow.md) và [nguồn và hợp đồng](team/sources.md)
- [Frontend README](../frontend/README.md): chạy mock, chạy với backend thật, `BlinkViewer`, biểu đồ và bản đồ
- [Nhật ký xử lý ảnh của Hữu Hoàng (TASKS.md)](../members/huu-hoang/TASKS.md)
- [SPHEREx Data Access – IRSA](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access) và [SPHEREx Cutout Capabilities](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/cutout_tool.html)
- Bản SRS gốc ngày 9/11 (hợp đồng v1, đã thay thế) nằm trong lịch sử git của file này (PR #11).
