# Báo cáo tiến độ: Pipeline căn ảnh build_frames(), nghiệm thu dấu thập Barnard, ảnh hiệu cặp sáng–tối (QA-19) & Kết luận khoa học 5 mục tiêu

**Người thực hiện:** Nguyễn Hữu Hoàng (Xử lý ảnh SPHEREx + Pipeline reproject + Tích hợp sản phẩm khoa học)  
**Nhánh:** `huu-hoang` (đã đồng bộ hoàn toàn với `origin/huu-hoang`)  
**Commit mới nhất:** `a192d6e` (`feat(frontend): display target scientific conclusions and QA-19 Barnard dipole verification`)

---

## 📌 Bảng tổng hợp các file và sản phẩm bàn giao

| Commit / File | Nội dung chính |
| :--- | :--- |
| [`members/huu-hoang/build_frames.py`](../members/huu-hoang/build_frames.py) | Đóng gói hàm chính thức `build_frames(cutouts, target, size)` theo Mục 6 hợp đồng API, tính `predicted_px` lật trục dọc, định vị tâm lưới tại trung vị thời gian, chuẩn hóa chung norm `AsinhStretch`, tạo PNG khung, PNG ảnh hiệu và xuất bộ ảnh nghiệm thu dấu thập |
| [`members/huu-hoang/test_build_frames.py`](../members/huu-hoang/test_build_frames.py) | Bộ kiểm thử tự động 3 bài test: lật trục tọa độ PNG, tính toán tâm động qua trung vị thời gian, và kiểm tra tính tương thích 100% với Pydantic model `Frames` của backend |
| [`shared/frames_pipeline.py`](../shared/frames_pipeline.py) & [`members/huu-hoang/frames.py`](../members/huu-hoang/frames.py) | Re-export `build_frames` dùng chung để Backend của Đông và toàn đội có thể import trực tiếp |
| [`frontend/src/targets.ts`](../frontend/src/targets.ts) | Định nghĩa 5 câu kết luận tiếng Anh khoa học cho 5 mục tiêu thử thách và hàm tra cứu `findPresetForTarget` |
| [`frontend/src/App.tsx`](../frontend/src/App.tsx) | Thiết kế thẻ hiển thị `Scientific Conclusion` (`.target-conclusion-card`) xuất hiện trực quan ngay dưới viewer trên website |
| [`frontend/src/blink/BlinkViewer.tsx`](../frontend/src/blink/BlinkViewer.tsx) | Bổ sung chỉ dẫn chế độ ảnh hiệu (Difference image) làm nổi bật cặp sáng–tối (dipole) do chuyển động riêng của sao Barnard |
| [`frontend/src/targets.test.ts`](../frontend/src/targets.test.ts) | Bộ unit test kiểm tra 5 câu kết luận tiếng Anh và cơ chế tra cứu mục tiêu (đạt **166/166 vitest pass**) |
| [`frontend/e2e/conclusion.spec.ts`](../frontend/e2e/conclusion.spec.ts) | Bộ e2e test Playwright chạy trên trình duyệt thật kiểm chứng giao diện kết luận khoa học và chế độ ảnh hiệu (đạt **7/7 Playwright pass**) |
| [`docs/QA-matrix.md`](QA-matrix.md) | Đánh dấu nghiệm thu mục **QA-19: Đạt** (Thấy một cặp sáng–tối trên website khi bật ảnh hiệu với Barnard) |
| [`data/five_targets/barnard/verification_crosshairs/`](../data/five_targets/barnard/verification_crosshairs/) | Bộ sản phẩm nghiệm thu trực quan tiêu chí **Done when**: ảnh so sánh `barnard_d6_movement_comparison.png` và ảnh động `barnard_d6_movement_blink.gif` |

---

## 1. Tóm tắt kết quả công việc

### A. Đóng gói `build_frames()` và nghiệm thu dấu thập trên sao Barnard

| Yêu cầu kỹ thuật | Kết quả đạt được | Minh chứng cụ thể |
| :--- | :--- | :--- |
| **Bọc thành `build_frames(cutouts, target, size)`** | ✅ **Xong.** Chuẩn hóa chữ ký hàm theo đúng Mục 6 Hợp đồng API. Nhận danh sách cutout, target (dict hoặc chuỗi `"barnard"`), kích thước `size` (mặc định 0.1°). | [`members/huu-hoang/build_frames.py`](../members/huu-hoang/build_frames.py) |
| **Đặt tâm lưới ở thời điểm giữa chuỗi khung** | ✅ **Xong.** Tự động tính $t_{mid} = \frac{t_{min} + t_{max}}{2}$ (cho Barnard là MJD $61033.97$). Tâm lưới WCS TAN chiếu tại vị trí sao ở $t_{mid}$, giúp sao đi ngang qua tâm ảnh khi xem blink. | Lưới $59 \times 59$ px, tâm pixel $(29.0, 29.0)$ |
| **Tính `predicted_px` theo gốc trên-trái (PNG)** | ✅ **Xong.** Lật trục dọc nhất quán theo chuẩn ảnh PNG: $x_{png} = x_{fits}$, $y_{png} = (\text{height} - 1) - y_{fits}$. Khung Visit 00 ra `[28.96, 29.57]`, Visit 01 ra `[29.04, 28.51]`. | Sao Barnard dịch chuyển $1.06$ pixel về phía Bắc theo Dec |
| **Dùng chung thang norm cho mọi khung** | ✅ **Xong.** Gom toàn bộ pixel hữu hạn qua các visit của detector để tính chung một cặp $[vmin=0.4202, vmax=4.4321]$ với `AsinhStretch`. | Giữ nguyên độ tương phản vật lý, không bị nhảy sáng khi blink |
| **Tạo PNG khung và PNG ảnh hiệu (Diff)** | ✅ **Xong.** Xuất đầy đủ PNG khung (thang xám, NaN màu tím `#703090`) và PNG ảnh hiệu lưỡng cực (RdBu_r) thể hiện rõ cặp tín hiệu dipole âm/dương do chuyển động riêng. | `D6_visit00.png`, `D6_visit01.png`, `D6_visit01_minus_D6_visit00.png` |
| **Done when: Trả dict khớp model `Frames`** | ✅ **ĐẠT.** Kết quả đầu ra validate trực tiếp thành công 100% với Pydantic model `Frames` từ backend Đông (`members.dong.app.api_models.Frames`). | `Frames.model_validate(res)` thành công không có lỗi |
| **Done when: PNG Barnard có dấu thập nằm trên sao** | ✅ **ĐẠT.** Xuất trọn bộ ảnh kiểm chứng có vẽ dấu thập 4 tia với khe hở rỗng $\pm 1.5$ px ở giữa, bám chính xác vào tâm sao Barnard đang di chuyển. | `barnard_d6_movement_comparison.png` & `barnard_d6_movement_blink.gif` |

---

### B. Nghiệm thu Task QA-19 & 5 câu kết luận tiếng Anh trên website

| Hạng mục nghiệm thu | Kết quả đạt được | Minh chứng cụ thể |
| :--- | :--- | :--- |
| **Ảnh hiệu Barnard thành cặp sáng–tối (QA-19)** | ✅ **ĐẠT.** Khi người dùng bấm tab **Difference** trên website, các ngôi sao nền bất động biến mất, vị trí cũ của sao thành cực tối và vị trí mới thành cực sáng (dipole). Dòng hint giải thích rõ hiện tượng. | Đánh dấu `Đạt` cho QA-19 trong [`docs/QA-matrix.md`](QA-matrix.md) |
| **Một câu kết luận tiếng Anh cho mỗi mục tiêu** | ✅ **ĐẠT.** Hiển thị thẻ card `Scientific Conclusion` trực quan ngay dưới Blink Viewer cho cả 5 mục tiêu thử thách (Barnard, WISE 0855, Epsilon Indi B, RW Aurigae, R Draconis). | [`frontend/src/targets.ts`](../frontend/src/targets.ts) & [`frontend/src/App.tsx`](../frontend/src/App.tsx) |
| **Kiểm thử tự động trên website** | ✅ **100% PASS.** 166 unit tests Vitest và 7 Playwright e2e tests chạy tự động trên trình duyệt thật đều vượt qua. | [`frontend/e2e/conclusion.spec.ts`](../frontend/e2e/conclusion.spec.ts) |

---

## 2. Chi tiết các bước kỹ thuật đã thực hiện

### 2.1. Căn chỉnh tọa độ & Tự động đặt tâm lưới tại trung vị thời gian ($t_{mid}$)
- Trước đây, việc căn ảnh dùng vị trí sao cố định tại epoch J2026.0 khiến sao bị lệch tâm ở các đợt chụp đầu (năm 2025).
- Trong `build_frames()`, pipeline quét toàn bộ thời gian chụp của các cutout đầu vào, xác định thời điểm bắt đầu $t_{min}$ (MJD 60902.86) và kết thúc $t_{max}$ (MJD 61165.08).
- Tính thời điểm trung vị:
  $$t_{mid} = \frac{t_{min} + t_{max}}{2} = 61033.97\ \text{MJD}\ (\approx 24/12/2025)$$
- Dùng không gian chuyển động riêng của Barnard (Proper Motion: $\mu_{\alpha} \cos \delta = -801.551\ \text{mas/yr}$, $\mu_{\delta} = +10362.394\ \text{mas/yr}$) để tính tọa độ sao tại $t_{mid}$ và đặt làm tâm chiếu WCS TAN (`CRVAL1 = 269.446272°`, `CRVAL2 = 4.768149°`).
- Lưới chiếu TAN được chọn kích thước lẻ $59 \times 59$ pixel ($FOV = 0.1^\circ$, scale $6.2''/\text{px}$), đảm bảo tâm sao tại $t_{mid}$ rơi trúng pixel chính giữa $(CRPIX = [30.0, 30.0]$, tức pixel 0-indexed $[29.0, 29.0]$).

### 2.2. Tính toán tọa độ `predicted_px` và lật trục tọa độ PNG
- FITS có gốc tọa độ $(0, 0)$ ở góc dưới-trái (trục $y$ hướng lên Bắc).
- PNG và HTML Canvas có gốc tọa độ $(0, 0)$ ở góc trên-trái (trục $y$ hướng xuống Nam).
- Hàm `compute_predicted_pixel()` thực hiện chuyển đổi chính xác:
  $$x_{png} = x_{fits}, \quad y_{png} = (\text{height} - 1) - y_{fits}$$
- **Kết quả tính toán trên sao Barnard (Detector D6):**
  * **Visit 00 (MJD 60908.67, Tháng 08–09/2025):** Tọa độ FITS là $(28.96, 28.43) \implies$ Tọa độ PNG là **`[28.96, 29.57]`**.
  * **Visit 01 (MJD 61141.70, Tháng 03–05/2026):** Tọa độ FITS là $(29.04, 29.49) \implies$ Tọa độ PNG là **`[29.04, 28.51]`**.
  * Sao dịch chuyển lên phía Bắc $\Delta y_{fits} = +1.06$ px, tương ứng trên ảnh PNG là di chuyển giật lên trên $\Delta y_{png} = -1.06$ px.

### 2.3. Lọc cờ chất lượng & Gom median đợt quan sát
- Hàm `load_cutout()` đọc đầy đủ các HDU (`IMAGE`, `FLAGS`, `VARIANCE`) và trích xuất bảng cờ bitwise từ header của `FLAGS`.
- Loại bỏ toàn bộ các pixel mang cờ lỗi chất lượng: `MP_OVERFLOW`, `MP_NONLINEAR` (bão hòa), `MP_TRANSIENT`, `MP_HOT`, `MP_COLD`, `MP_SUR_ERROR`... nhưng **giữ lại** cờ `MP_SOURCE` và `MP_FULLSAMPLE`.
- Các cutout cùng đợt (cách nhau dưới 30 ngày) được reproject bằng `reproject_interp` lên lưới TAN chung và tính median pixelwise (`np.nanmedian`), loại bỏ triệt để tia vũ trụ và nhiễu ngẫu nhiên.

### 2.4. Áp dụng chung thang chuẩn hóa norm AsinhStretch
- Nếu co giãn (stretch) riêng từng ảnh, độ tương phản tự động của matplotlib sẽ che lấp sự thay đổi độ sáng thực tế giữa các đợt.
- Pipeline gom toàn bộ các pixel hợp lệ trên cả 2 đợt quan sát của detector, lấy phân vị $2\%$ làm $vmin = 0.4202\ \text{MJy/sr}$ và phân vị $99.5\%$ làm $vmax = 4.4321\ \text{MJy/sr}$.
- Toàn bộ các ảnh PNG khung đều hiển thị qua cùng một đối tượng `ImageNormalize(vmin=vmin, vmax=vmax, stretch=AsinhStretch())`. Vùng thiếu dữ liệu do mask cờ bão hòa được gán màu tím chuẩn **`#703090`**.

### 2.5. Tạo ảnh hiệu lưỡng cực (Dipole Difference)
- Ảnh hiệu giữa 2 đợt được tính theo công thức: $\text{Diff} = \text{Visit01} - \text{Visit00}$.
- Do sao Barnard dịch chuyển từ vị trí cũ sang vị trí mới sau 9 tháng:
  * Tại vị trí cũ $(29.0, 28.4)$: độ sáng giảm $\implies$ tạo hõm âm (hiển thị màu xanh lam trên colormap `RdBu_r`).
  * Tại vị trí mới $(29.0, 29.5)$: độ sáng tăng $\implies$ tạo đỉnh dương (hiển thị màu đỏ trên colormap `RdBu_r`).
- Đây là dấu vết chuyển động riêng kinh điển (cặp dipole) được lưu tại [`D6_visit01_minus_D6_visit00.png`](../data/five_targets/barnard/frames/D6_visit01_minus_D6_visit00.png) và file FITS tương ứng.

### 2.6. Tạo sản phẩm nghiệm thu dấu thập (Crosshair Verification)
- Để nghiệm thu trực quan tiêu chí **Done when**, hàm xuất thêm các ảnh kiểm chứng tại [`data/five_targets/barnard/verification_crosshairs/`](../data/five_targets/barnard/verification_crosshairs/):
  * Dấu thập gồm 4 tia đối xứng, nét vẽ viền đen nổi bật trên nền sáng, thân tia màu đỏ rực rỡ, chừa khe rỗng ở giữa $\pm 1.5$ px để không che khuất quầng sáng và tâm sao.
  * Xuất ảnh so sánh 2 khung hình cạnh nhau: [`barnard_d6_movement_comparison.png`](../data/five_targets/barnard/verification_crosshairs/barnard_d6_movement_comparison.png) phóng to vùng trung tâm $24 \times 24$ px, thấy rõ dấu thập đỏ nằm ngay ngắn trên sao ở cả 2 thời điểm.
  * Xuất ảnh động GIF blink: [`barnard_d6_movement_blink.gif`](../data/five_targets/barnard/verification_crosshairs/barnard_d6_movement_blink.gif) đổi khung mỗi 0.8 giây, chứng minh trực quan sao nhảy vị trí và dấu thập bám sát theo sao.

### 2.7. Tích hợp 5 câu kết luận tiếng Anh khoa học lên website
Đã chuẩn hóa nội dung khoa học cho 5 mục tiêu thử thách vào [`frontend/src/targets.ts`](../frontend/src/targets.ts):
1. **Barnard's Star (`barnard`):**
   > *"Barnard's Star exhibits rapid proper motion across observation epochs, producing a pronounced bright–dark dipole signature in difference imaging that directly confirms its transverse motion relative to the background sky."*
2. **WISE 0855-0714 (`wise0855`):**
   > *"WISE 0855 is an ultra-cold sub-stellar brown dwarf whose thermal emission peaks predominantly in SPHEREx mid-infrared Detector 6 (4.5–5.0 µm) with noticeable proper motion displacement across survey visits."*
3. **Epsilon Indi B (`epsindib`):**
   > *"Epsilon Indi B is a nearby benchmark T-dwarf binary companion displaying shared proper motion with the host star and strong atmospheric methane absorption features in SPHEREx channels."*
4. **RW Aurigae (`rwaur`):**
   > *"RW Aurigae is a young T Tauri binary system exhibiting prominent infrared excess and irregular multi-magnitude dimming episodes caused by circumstellar dust occultation."*
5. **R Draconis (`rdra`):**
   > *"R Draconis is a high-amplitude pulsating Mira variable demonstrating substantial seasonal brightness modulation and saturated core pixels during peak infrared emission."*

Khối thẻ `.target-conclusion-card` được render ngay dưới Blink Viewer trong [`frontend/src/App.tsx`](../frontend/src/App.tsx), đồng bộ màu sắc và typography theo design tokens chuẩn.

### 2.8. Nghiệm thu trực tiếp chế độ Difference Image trên website (QA-19)
- Trong [`frontend/src/blink/BlinkViewer.tsx`](../frontend/src/blink/BlinkViewer.tsx), khi chuyển sang chế độ `Difference`, chỉ dẫn trên giao diện tự động đổi thành:  
  *"Difference image: Stationary background sources vanish, revealing moving objects like Barnard's Star as a distinct bright–dark dipole pair."*
- Trên ảnh hiệu, mức nền triệt tiêu về giá trị xám trung tính (128), vị trí cũ của sao bị âm ($<128$) và vị trí mới bị dương ($>128$), tạo thành cặp sáng–tối (dipole) trực quan.

---

## 3. Kiểm chứng & Số liệu thực tế

### 3.1. Kết quả kiểm thử tự động toàn diện

1. **Python Unit Tests:**
   ```bash
   .venv/Scripts/pytest members/huu-hoang/
   ```
   Kết quả: **11/11 tests PASSED (100%)** trong 18.60s.

2. **Frontend Unit Tests (Vitest):**
   ```bash
   npm --prefix frontend test
   ```
   Kết quả: **166/166 tests PASSED (100%)** trong 10.10s qua 9 test files.

3. **Frontend End-to-End Tests (Playwright):**
   ```bash
   cd frontend && npm run e2e
   ```
   Kết quả: **7/7 tests PASSED (100%)** trong 21.1s trên trình duyệt thật.

| Suite kiểm thử | Số test | Kết quả | Nội dung kiểm tra |
| :--- | :---: | :---: | :--- |
| [`members/huu-hoang/test_build_frames.py`](../members/huu-hoang/test_build_frames.py) | 3 | **3/3 PASS** | Lật trục dọc PNG gốc trên-trái, tâm động $t_{mid}$, tương thích Pydantic model `Frames`. |
| [`members/huu-hoang/test_pipeline.py`](../members/huu-hoang/test_pipeline.py) | 4 | **4/4 PASS** | Hình học WCS TAN, căn chỉnh sao xoay góc, lọc median, dấu ảnh hiệu. |
| [`members/huu-hoang/test_tasks_def.py`](../members/huu-hoang/test_tasks_def.py) | 4 | **4/4 PASS** | Thuật toán ghép dipole, loại bỏ lân cận NaN, trắc lượng khẩu độ và đo nền. |
| [`frontend/src/targets.test.ts`](../frontend/src/targets.test.ts) | 7 | **7/7 PASS** | Cấu trúc 5 mục tiêu, kiểm tra 5 câu kết luận tiếng Anh, hàm `findPresetForTarget`. |
| [`frontend/e2e/conclusion.spec.ts`](../frontend/e2e/conclusion.spec.ts) | 1 | **1/1 PASS** | Hiển thị thẻ kết luận khoa học trên website, chuyển đổi chế độ Difference, cập nhật khi đổi mục tiêu. |
| [`frontend/e2e/blink.spec.ts`](../frontend/e2e/blink.spec.ts) | 2 | **2/2 PASS** | Blink viewer loop, phím tắt, chuyển ảnh hiệu, vẽ dấu thập đỏ chính xác tại sao. |
| [`frontend/e2e/target-input.spec.ts`](../frontend/e2e/target-input.spec.ts) | 4 | **4/4 PASS** | Nhập tọa độ decimal, sexagesimal, tìm theo tên mục tiêu, xử lý lỗi đầu vào. |

### 3.2. Đối chiếu số liệu tọa độ tính toán vs Đỉnh sáng thực tế

| Đợt chụp | MJD quan sát | Tọa độ dự đoán WCS FITS | Tọa độ PNG (`predicted_px`) | Đỉnh sáng đo được trên ảnh gốc | Độ lệch |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Visit 00** | 60908.67 | $(28.96, 28.43)$ | **`[28.96, 29.57]`** | $(29, 28)$ / $(29, 29)$ | $< 0.45\ \text{px}$ |
| **Visit 01** | 61141.70 | $(29.04, 29.49)$ | **`[29.04, 28.51]`** | $(29, 30)$ | $< 0.50\ \text{px}$ |

---

## 4. Vấn đề gặp phải và cách xử lý

| Vấn đề | Nguyên nhân | Cách xử lý |
| :--- | :--- | :--- |
| **Sao bị lệch tâm khi xem blink** | Trước đây dùng tâm lưới cố định ở epoch `J2026.0`, khiến ảnh chụp năm 2025 bị kéo lệch về phía Nam. | Tính thời điểm trung vị $t_{mid} = \frac{t_{min} + t_{max}}{2}$ của cả chuỗi ảnh và chiếu tâm TAN theo vị trí sao tại $t_{mid}$. |
| **Lệch trục tọa độ giữa FITS và PNG** | FITS có gốc tọa độ dưới-trái (Bắc hướng lên), trong khi PNG/Canvas có gốc tọa độ trên-trái (Nam hướng xuống). Nếu không lật trục $y$, dấu thập trên giao diện web sẽ chỉ sai hướng. | Áp dụng công thức lật trục chuẩn: $x_{png} = x_{fits}$, $y_{png} = (\text{height} - 1) - y_{fits}$. Đã viết test unit xác thực tính chất này. |
| **Lõi sao Barnard bị mất trên ảnh** | Do sao Barnard quá sáng, các pixel trung tâm dính cờ `MP_OVERFLOW` và `MP_NONLINEAR` nên bị mask thành NaN (màu tím `#703090`). | Giữ nguyên nguyên tắc khoa học không vá pixel bão hòa; thiết kế dấu thập có khe hở rỗng $\pm 1.5$ px ở tâm để vừa thấy quầng sáng sao, vừa xác nhận cờ bão hòa được xử lý đúng. |
| **Website chưa hiển thị câu kết luận khoa học** | Giao diện frontend cũ chỉ nạp dữ liệu khung ảnh mà chưa có component hiển thị phân tích khoa học cho từng mục tiêu. | Thêm trường `conclusion` vào `TargetPreset`, xây dựng component `.target-conclusion-card` ngay dưới viewer trong `App.tsx` và viết bài test e2e kiểm chứng. |
| **Trình duyệt e2e Playwright thiếu file thực thi Chromium mặc định** | Môi trường Windows chưa tải headless Chromium của Playwright qua lệnh cài đặt riêng. | Tận dụng kênh trình duyệt có sẵn (`PW_CHANNEL=msedge`) cấu hình trực tiếp trong `playwright.config.ts`, giúp chạy e2e trơn tru mà không cần tải thêm gói nặng. |

---

## 5. Quyết định kỹ thuật cần team biết

1. **Chuẩn hóa chữ ký hàm bàn giao:** Hàm chính thức là `build_frames(cutouts, target, size=0.1, detector=6, ...)`. Hàm hỗ trợ truyền `target` dưới dạng chuỗi (ví dụ `"barnard"`) hoặc dictionary có chứa thông tin tọa độ/epoch/proper motion.
2. **Re-export dùng chung:** Hàm `build_frames` được xuất khẩu đồng thời ở cả [`members/huu-hoang/frames.py`](../members/huu-hoang/frames.py) và [`shared/frames_pipeline.py`](../shared/frames_pipeline.py) để Đông có thể import trực tiếp vào backend FastAPI.
3. **Quy chuẩn hiển thị:**
   - Dùng chung chuẩn hóa `AsinhStretch` giữa các visit trong cùng một detector.
   - Vùng thiếu dữ liệu do mask cờ chất lượng luôn được tô màu tím `#703090`.
   - Ảnh hiệu luôn dùng colormap `RdBu_r` với dải hiển thị đối xứng $[-limit, +limit]$.
4. **Kết luận khoa học thống nhất:** Cả 5 mục tiêu đều có một câu kết luận tiếng Anh chuẩn xác, ngắn gọn, súc tích, tuân thủ đúng yêu cầu giao diện tiếng Anh (QA-16) và hỗ trợ Thạch đưa vào slide/video thuyết trình.

---

## 6. Hạn chế đã biết

- **Lõi bão hòa của sao sáng:** Các ngôi sao rất sáng như Barnard hay R Draconis có lõi trung tâm mang cờ `MP_OVERFLOW`, `MP_NONLINEAR`. Theo chuẩn khoa học SPHEREx Level 2, các pixel này bị loại bỏ thành NaN chứ không nội suy vá lại.
- **Tính đồng thời giữa các detector:** Cutout của SPHEREx ở các detector khác nhau (D1, D3, D6) không được chụp hoàn toàn cùng một thời điểm vi mô, do đó ảnh RGB giả và so sánh đa kênh mang tính chất định tính hình học, chưa thể dùng để đo chỉ số màu tức thời.

---

## 7. Tiến độ các hạng mục công việc (Role Hữu Hoàng)

- ✅ **Bắt buộc 1:** Đóng gói hàm `build_frames()` chuẩn Mục 6 hợp đồng API.
- ✅ **Bắt buộc 2:** Định vị tâm lưới TAN tại trung vị thời gian chuỗi quan sát.
- ✅ **Bắt buộc 3:** Tính `predicted_px` lật trục dọc theo chuẩn PNG gốc trên-trái.
- ✅ **Bắt buộc 4:** Dùng chung thang norm AsinhStretch cho toàn bộ khung của detector.
- ✅ **Bắt buộc 5:** Tạo PNG khung và PNG ảnh hiệu diff dipole.
- ✅ **Bắt buộc 6:** Nghiệm thu tiêu chí Done when: Dict khớp model `Frames`, ảnh Barnard có dấu thập đỏ bám sát tâm sao.
- ✅ **Bắt buộc 7 (Mới):** Nghiệm thu QA-19 trên website: Bật ảnh hiệu Barnard thấy cặp sáng–tối (dipole) và hiển thị một câu kết luận tiếng Anh cho mỗi mục tiêu.
- 🟡 **Bàn giao Backend:** Trao đổi với Đông để tích hợp pipeline vào live endpoint backend (mã pipeline đã sẵn sàng trong `shared/frames_pipeline.py`).
- 🟡 **Khoa học:** Bàn giao báo cáo trích phổ Luhman 16 và 58 cặp dipole cho Nguyên duyệt vào runbook.
- 🟡 **Diễn tập:** Tự code tay từ đầu luồng xử lý dưới 90 phút trước ngày thi 14–15/11.

---

## 8. Hướng dẫn chạy lại từ đầu (Reproduce) & Tips cho đồng đội

Xem chi tiết từng bước (chạy nhanh bằng ảnh PNG mẫu có sẵn trên Git lẫn chạy đầy đủ 156 FITS `D1`–`D6` + các lưu ý SkyMap/Warnings) tại [`docs/RUN_MVP_GUIDE.md`](RUN_MVP_GUIDE.md).

```powershell
# 1. Tải & render đủ 156 cutout FITS (D1-D6) cho 5 mục tiêu vào data/five_targets/
.venv\Scripts\python members/huu-hoang/five_targets.py --download

# 2. Cấu hình .env để nối Frontend với Backend thật (VITE_USE_MOCK=false, DATA_MODE=fixture)
Copy-Item .env.example .env

# 3. Terminal 1: Khởi động Backend FastAPI (tự đồng bộ manifest.json & photometry D1-D6)
.venv\Scripts\python -m uvicorn members.dong.app.main:app --host 127.0.0.1 --port 8000

# 4. Terminal 2: Khởi động Frontend Vite (proxy /api -> 127.0.0.1:8000)
npm --prefix frontend run dev
# -> Truy cập http://localhost:5173/

# 5. Chạy các bộ test xác minh
.venv\Scripts\pytest members/huu-hoang/ members/dong/ members/khoi/test_irsa.py
npm --prefix frontend test
frontend\node_modules\.bin\vitest.cmd run --passWithNoTests --exclude "frontend/**"
```

---

## 9. Trả lời chi tiết các câu hỏi kỹ thuật

### Nhóm 1: Liên quan đến Python & Môi trường

1. **Lệnh chạy test là gì? Chạy từ thư mục nào?**
   - **Lệnh chuẩn từ thư mục gốc của repo:**
     ```bash
     .venv/Scripts/pytest members/huu-hoang/
     ```
   - Nếu đứng từ bên trong thư mục `members/huu-hoang`:
     ```bash
     cd members/huu-hoang && pytest
     ```

2. **Các package đã ghi vào `requirements.txt` chưa? Có gói nào chỉ cài trên máy mà quên ghi không?**
   - Các thư viện cốt lõi gồm `numpy`, `astropy`, `reproject`, `photutils`, `matplotlib`, `pillow`, `pytest` đều **đã được ghim phiên bản cụ thể** trong [`requirements.txt`](../requirements.txt).
   - `scipy` và `requests` hiện có mặt qua dependency cấp 2; khuyến nghị ghi rõ thêm `scipy` vào file cấu hình.

3. **Test nào gọi mạng (IRSA, SIMBAD, MAST, Gaia...)?**
   - **KHÔNG CÓ TEST NÀO GỌI MẠNG.** Cả 3 file test (`test_pipeline.py`, `test_tasks_def.py`, `test_build_frames.py`) đều chạy **100% offline**, an toàn tuyệt đối cho CI.

4. **Test có cần file dữ liệu không có trên git (FITS, cutout trong `data/`...) không?**
   - `test_pipeline.py` và `test_tasks_def.py`: Hoàn toàn tự tạo dữ liệu giả trong thư mục tạm (`tmp_path`) và bộ nhớ RAM.
   - `test_build_frames.py`: Có cơ chế fallback: nếu không tìm thấy `data/` trên máy, test sẽ tự động dùng fixture nhỏ trong thư mục tạm.

5. **Test chạy mất bao nhiêu lâu? Có phần nào sai mà làm hỏng sản phẩm không?**
   - Toàn bộ 11 test của `members/huu-hoang/` chạy mất **khoảng 15 – 18 giây** trên Windows.
   - **Không có phần nào sai làm hỏng sản phẩm.** Quy trình xử lý luôn giữ nguyên các file FITS gốc (chỉ đọc `memmap=False`, không ghi đè).

### Nhóm 2: Liên quan đến Phần của Hữu Hoàng

1. **`test_pipeline.py` và `test_tasks_def.py` có cần file nào ngoài thư mục tạm không, hay tự tạo FITS giả hết?**
   - Tự tạo FITS giả và dữ liệu giả 100% trong thư mục tạm và RAM.

2. **Hai file test chạy mất bao lâu?**
   - `test_pipeline.py` chạy mất **~2.5 giây**, `test_tasks_def.py` chạy mất **~1.5 giây**.

3. **Điều gì về ảnh xuất ra phải LUÔN LUÔN ĐÚNG (Invariants)?**
   - **Kích thước ảnh phải là số lẻ $N \times N$:** Chuẩn $59 \times 59$ pixel.
   - **Tọa độ `predicted_px` và gốc tọa độ:** Chuẩn PNG (gốc trên-trái), $x_{png} = x_{fits}$, $y_{png} = (\text{height} - 1) - y_{fits}$.
   - **Tâm lưới WCS TAN:** Đặt tại vị trí mục tiêu ở thời điểm trung vị của chuỗi ảnh ($t_{mid}$).
   - **Thang chuẩn hóa (Norm):** Chung một thang `AsinhStretch` với cùng cặp $[vmin, vmax]$ cho toàn bộ các khung trong detector.
   - **Màu dữ liệu khuyết/NaN:** Luôn hiển thị bằng màu tím chuẩn: **`#703090`**.
   - **Ảnh hiệu (Diff):** Luôn dùng colormap đối xứng **`RdBu_r`** và làm nổi bật cặp cực sáng–tối (dipole) khi vật thể dịch chuyển.

---

## 10. Cập nhật hoàn thiện 6 detector (D1–D6) & Photometry đa dải (13/11)

- **Dữ liệu thật đủ 6 detector (`D1`–`D6`):** Đã cập nhật [`members/huu-hoang/five_targets.py`](../members/huu-hoang/five_targets.py) sang `range(1, 7)` và tải đủ **156 cutout FITS thật từ IRSA** (~5,1 MB/file) cho cả 5 mục tiêu (`barnard`: 24, `wise0855`: 36, `epsindib`: 36, `rwaur`: 24, `rdra`: 36; mỗi detector `D1`–`D6` gồm 26 khung), xuất đủ bộ sản phẩm tĩnh `D1`–`D6` trong `data/five_targets/*/frames/` và đồng bộ [`data/fixtures/manifest.json`](../data/fixtures/manifest.json).
- **Tích hợp Backend + Photometry đa dải thật:** [`members/dong/app/services/observed_frames.py`](../members/dong/app/services/observed_frames.py) đồng bộ manifest và đo photometry khẩu độ trực tiếp trên FITS thật cho `barnard` (21 điểm), `wise0855` (36 điểm), `epsindib` (29 điểm), `rwaur` (24 điểm) bên cạnh mẫu 6 điểm của `rdra`, đồng thời đã nối proxy `/api` trong [`frontend/vite.config.ts`](../frontend/vite.config.ts).
- **Kiểm chứng 30 tổ hợp (`5 sao × D1..D6`):** 100% tổ hợp trả HTTP 200 với lưới `59×59` TAN, bước sóng riêng theo detector và 6 chuỗi PNG có hash SHA-256 khác biệt hoàn toàn; thời gian phản hồi `/api/frames` lần đầu đạt `1.03s–1.81s` (`< 2s`).
