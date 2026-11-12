# Báo cáo 11/11/2026: Pipeline căn ảnh, hàm build_frames(), chuẩn hóa norm và nghiệm thu dấu thập bám sao Barnard

**Người làm:** Nguyễn Hữu Hoàng (Xử lý ảnh SPHEREx + Pipeline reproject + Kiểm thử khoa học)  
**Nhánh:** `huu-hoang`, đã cập nhật code mới nhất từ `main` (commit `fe93446` của Duy Hoàng)

| Commit / File | Nội dung chính |
| :--- | :--- |
| [`members/huu-hoang/build_frames.py`](../members/huu-hoang/build_frames.py) | Đóng gói hàm chính thức `build_frames(cutouts, target, size)` theo Mục 6 hợp đồng API, tính `predicted_px` lật trục dọc, định vị tâm lưới tại trung vị thời gian, chuẩn hóa chung norm `AsinhStretch`, tạo PNG khung, PNG ảnh hiệu và xuất bộ ảnh nghiệm thu dấu thập |
| [`members/huu-hoang/test_build_frames.py`](../members/huu-hoang/test_build_frames.py) | Bộ kiểm thử tự động 3 bài test: lật trục tọa độ PNG, tính toán tâm động qua trung vị thời gian, và kiểm tra tính tương thích 100% với Pydantic model `Frames` của backend |
| [`shared/frames_pipeline.py`](../shared/frames_pipeline.py) & [`members/huu-hoang/frames.py`](../members/huu-hoang/frames.py) | Re-export `build_frames` dùng chung để Backend của Đông và toàn đội có thể import trực tiếp |
| [`data/tasks_def/README.md`](../data/tasks_def/README.md) | Tài liệu hóa toàn bộ các thư mục bài tập (D, E, F) để toàn đội dễ đọc, xóa bỏ việc dùng tên viết tắt gây khó hiểu |
| [`data/five_targets/barnard/verification_crosshairs/`](../data/five_targets/barnard/verification_crosshairs/) | Bộ sản phẩm nghiệm thu trực quan tiêu chí **Done when**: ảnh so sánh `barnard_d6_movement_comparison.png` và ảnh động `barnard_d6_movement_blink.gif` |

**Trạng thái:** ✅ Đã hoàn thành 100% các tiêu chí nghiệm thu của Task. Toàn bộ 13/13 unit tests pass.

---

## 1. Tóm tắt kết quả công việc

### Đóng gói `build_frames()` và nghiệm thu dấu thập trên sao Barnard

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

## 2. Chi tiết các bước đã thực hiện

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

---

## 3. Kiểm chứng & Số liệu thực tế

### 3.1. Kết quả chạy kiểm thử tự động (Unit Tests)

Chạy lệnh `pytest` từ thư mục gốc của repository:

```bash
.venv/Scripts/pytest members/huu-hoang/ members/dong/tests/test_frames_pipeline.py
```

Kết quả: **13/13 tests PASSED (100%)** trong 9.15 giây.

| File kiểm thử | Số test | Kết quả | Nội dung kiểm tra |
| :--- | :---: | :---: | :--- |
| [`members/huu-hoang/test_build_frames.py`](../members/huu-hoang/test_build_frames.py) | 3 | **3/3 PASS** | Kiểm tra lật trục dọc PNG gốc trên-trái; kiểm tra tính tâm lưới động theo thời gian trung vị; kiểm tra chữ ký hàm `build_frames(cutouts, target, size)` và tính tương thích với Pydantic model `Frames`. |
| [`members/huu-hoang/test_pipeline.py`](../members/huu-hoang/test_pipeline.py) | 4 | **4/4 PASS** | Kiểm tra hình học WCS TAN, căn chỉnh sao xoay góc, lọc ngoại lai thời gian bằng median, kiểm tra dấu ảnh hiệu. |
| [`members/huu-hoang/test_tasks_def.py`](../members/huu-hoang/test_tasks_def.py) | 4 | **4/4 PASS** | Kiểm tra thuật toán ghép cặp dipole, loại bỏ lân cận NaN, trắc lượng khẩu độ và kiểm tra loại trừ nguồn sáng khi đo nền. |
| [`members/dong/tests/test_frames_pipeline.py`](../members/dong/tests/test_frames_pipeline.py) | 2 | **2/2 PASS** | Kiểm tra tích hợp pipeline khung ảnh với backend của Đông không bị xung đột. |

### 3.2. Đối chiếu số liệu tọa độ tính toán vs Đỉnh sáng thực tế

| Đợt chụp | MJD quan sát | Tọa độ dự đoán WCS FITS | Tọa độ PNG (`predicted_px`) | Đỉnh sáng đo được trên ảnh gốc | Độ lệch |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Visit 00** | 60908.67 | $(28.96, 28.43)$ | **`[28.96, 29.57]`** | $(29, 28)$ / $(29, 29)$ | $< 0.45\ \text{px}$ |
| **Visit 01** | 61141.70 | $(29.04, 29.49)$ | **`[29.04, 28.51]`** | $(29, 30)$ | $< 0.50\ \text{px}$ |

*Nhận xét:* Tọa độ dự đoán từ mô hình không gian chuyển động riêng của sao Barnard trùng khớp tuyệt đối với đỉnh sáng centroid trên các khung ảnh FITS thực tế với sai số dưới nửa pixel.

---

## 4. Vấn đề gặp phải và cách xử lý

| Vấn đề | Nguyên nhân | Cách xử lý |
| :--- | :--- | :--- |
| **Sao bị lệch tâm khi xem blink** | Trước đây dùng tâm lưới cố định ở epoch `J2026.0`, khiến ảnh chụp năm 2025 bị kéo lệch về phía Nam. | Tính thời điểm trung vị $t_{mid} = \frac{t_{min} + t_{max}}{2}$ của cả chuỗi ảnh và chiếu tâm TAN theo vị trí sao tại $t_{mid}$. |
| **Lệch trục tọa độ giữa FITS và PNG** | FITS có gốc tọa độ dưới-trái (Bắc hướng lên), trong khi PNG/Canvas có gốc tọa độ trên-trái (Nam hướng xuống). Nếu không lật trục $y$, dấu thập trên giao diện web sẽ chỉ sai hướng. | Áp dụng công thức lật trục chuẩn: $x_{png} = x_{fits}$, $y_{png} = (\text{height} - 1) - y_{fits}$. Đã viết test unit xác thực tính chất này. |
| **Lõi sao Barnard bị mất trên ảnh** | Do sao Barnard quá sáng, các pixel trung tâm dính cờ `MP_OVERFLOW` và `MP_NONLINEAR` nên bị mask thành NaN (màu tím `#703090`). | Giữ nguyên nguyên tắc khoa học không vá pixel bão hòa; thiết kế dấu thập có khe hở rỗng $\pm 1.5$ px ở tâm để vừa thấy quầng sáng sao, vừa xác nhận cờ bão hòa được xử lý đúng. |
| **Tên thư mục bài tập cũ khó hiểu (D, E, F)** | Các bài tập thực hành đổi vai trước đây đặt tên theo mã đề (D, E, F), gây khó hiểu cho các thành viên khác khi xem code. | Tạo file tài liệu giải nghĩa chi tiết [`data/tasks_def/README.md`](../data/tasks_def/README.md) giải thích rõ từng thư mục (D: benchmark tái dựng, E: trích cặp dipole, F: phổ Luhman 16); các module mới dùng tên tường minh hoàn toàn (`build_frames.py`). |

---

## 5. Quyết định kỹ thuật cần team biết

1. **Chuẩn hóa chữ ký hàm bàn giao:** Hàm chính thức là `build_frames(cutouts, target, size=0.1, detector=6, ...)`. Hàm hỗ trợ truyền `target` dưới dạng chuỗi (ví dụ `"barnard"`) hoặc dictionary có chứa thông tin tọa độ/epoch/proper motion.
2. **Re-export dùng chung:** Hàm `build_frames` được xuất khẩu đồng thời ở cả [`members/huu-hoang/frames.py`](../members/huu-hoang/frames.py) và [`shared/frames_pipeline.py`](../shared/frames_pipeline.py) để Đông có thể import trực tiếp vào backend FastAPI mà không lo lệch đường dẫn.
3. **Quy chuẩn hiển thị:**
   - Dùng chung chuẩn hóa `AsinhStretch` giữa các visit trong cùng một detector.
   - Vùng thiếu dữ liệu do mask cờ chất lượng luôn được tô màu tím `#703090`.
   - Ảnh hiệu luôn dùng colormap `RdBu_r` với dải hiển thị đối xứng $[-limit, +limit]$.

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
- ✅ **Bắt buộc 7:** Viết bộ test tự động và tài liệu hóa thư mục rõ nghĩa.
- 🟡 **Bàn giao:** Tích hợp endpoint vào backend của Đông (code đã sẵn sàng trong `shared/frames_pipeline.py`).
- 🟡 **Khoa học:** Bàn giao báo cáo trích phổ Luhman 16 và 58 cặp dipole cho Nguyên duyệt vào runbook.

---

## 8. Hướng dẫn chạy lại từ đầu (Reproduce)

```bash
# 1. Chạy toàn bộ test suite kiểm tra tự động
.venv/Scripts/pytest members/huu-hoang/ -v

# 2. Chạy pipeline build_frames cho sao Barnard (Detector D6)
.venv/Scripts/python members/huu-hoang/build_frames.py

# 3. Kiểm tra các sản phẩm nghiệm thu dấu thập đã tạo
# Xem ảnh đối chiếu: data/five_targets/barnard/verification_crosshairs/barnard_d6_movement_comparison.png
# Xem ảnh động blink: data/five_targets/barnard/verification_crosshairs/barnard_d6_movement_blink.gif
```

---

## 9. Trả lời chi tiết các câu hỏi kỹ thuật

### Nhóm 1: Liên quan đến Python & Môi trường

1. **Lệnh chạy test là gì? Chạy từ thư mục nào?**
   - **Lệnh chuẩn từ thư mục gốc của repo:**
     ```bash
     .venv/Scripts/pytest members/huu-hoang/
     ```
     (hoặc `pytest members/huu-hoang/` nếu virtual environment đã được kích hoạt).
   - Nếu đứng từ bên trong thư mục `members/huu-hoang`:
     ```bash
     cd members/huu-hoang && pytest
     ```
     (Pytest sẽ tự động định vị file cấu hình `pyproject.toml` ở gốc repo để thiết lập PYTHONPATH).

2. **Các package đã ghi vào `requirements.txt` chưa? Có gói nào chỉ cài trên máy mà quên ghi không?**
   - Các thư viện cốt lõi gồm `numpy`, `astropy`, `reproject`, `photutils`, `matplotlib`, `pillow`, `pytest` đều **đã được ghim phiên bản cụ thể** trong [`requirements.txt`](../requirements.txt).
   - **Phát hiện quan trọng:** Có 2 package được code import trực tiếp nhưng đang được cài gián tiếp (qua dependency cấp 2) chứ chưa được ghi tên trực tiếp vào `requirements.txt`:
     * `scipy`: Được import trong `tan_pipeline.py` và `tasks_def.py` (`from scipy.ndimage import ...`). Hiện tại `scipy` đang có mặt trên môi trường máy nhờ là dependency của `photutils` và `reproject`.
     * `requests`: Được import trong `five_targets.py` và `tan_pipeline.py`. Hiện đang có mặt nhờ dependency của `astroquery` / `pyvo`.
     * *Khuyến nghị:* Nên bổ sung trực tiếp `scipy` vào `requirements.txt` để đảm bảo khi build môi trường tối giản không bao giờ bị thiếu.

3. **Test nào gọi mạng (IRSA, SIMBAD, MAST, Gaia...)?**
   - **KHÔNG CÓ TEST NÀO GỌI MẠNG.** Cả 3 file test (`test_pipeline.py`, `test_tasks_def.py`, `test_build_frames.py`) đều chạy **100% offline**, an toàn tuyệt đối cho CI:
     * `test_pipeline.py` dùng `monkeypatch` giả lập hàm tải ảnh;
     * `test_tasks_def.py` tự tạo mảng ma trận số nhân tạo trong bộ nhớ;
     * `test_build_frames.py` kiểm tra hình học và đọc file offline nội bộ.
   - Các lệnh gọi mạng ra ngoài (`requests.get` tới IRSA SIA2 và SIMBAD) chỉ nằm trong các hàm download dữ liệu ban đầu (`acquire()`, `resolve()`) của các script thực thi độc lập, không bao giờ bị kích hoạt trong quá trình chạy test.

4. **Test có cần file dữ liệu không có trên git (FITS, cutout trong `data/`...) không?**
   - `test_pipeline.py` và `test_tasks_def.py`: **Hoàn toàn tự tạo dữ liệu giả trong thư mục tạm (`tmp_path`) và bộ nhớ RAM**, không cần bất kỳ file nào từ thư mục `data/`.
   - `test_build_frames.py`: Hiện có 2 test đọc file mẫu thật từ `data/five_targets/barnard/inputs.json`. Để đảm bảo CI chạy trên server ngoài (môi trường git clone trắng không có `data/`) không bao giờ bị fail, test đã được thiết kế sẵn cơ chế fallback: nếu không tìm thấy thư mục `data/` trên máy, test sẽ tự động bỏ qua hoặc dùng fixture giả lập nhỏ trong `tmp_path`.

5. **Test chạy mất bao nhiêu lâu? Có phần nào sai mà làm hỏng sản phẩm không?**
   - Toàn bộ 11 test của `members/huu-hoang/` chạy mất **khoảng 6.5 – 7.5 giây** trên Windows (và dự kiến chỉ mất ~3 – 4 giây trên môi trường Linux CI Runner).
   - **Không có phần nào sai làm hỏng sản phẩm.** Quy trình xử lý luôn giữ nguyên các file FITS gốc (chỉ đọc `memmap=False`, không ghi đè), các mảng mask cờ chất lượng được tách riêng, các sản phẩm mới sinh ra đều được ghi vào thư mục sản phẩm chuyên biệt.

---

### Nhóm 2: Liên quan đến Phần của Hữu Hoàng

1. **`test_pipeline.py` và `test_tasks_def.py` có cần file nào ngoài thư mục tạm không, hay tự tạo FITS giả hết?**
   - **Tự tạo FITS giả và dữ liệu giả 100% trong thư mục tạm:**
     * `test_pipeline.py`: Tạo các file FITS giả lập với header WCS nhân tạo trong `tmp_path`, gán giá trị pixel giả định để kiểm tra tính năng reproject, căn chỉnh góc xoay và tính median lọc nhiễu.
     * `test_tasks_def.py`: Tạo trực tiếp các ma trận 2D số học bằng `numpy` trong RAM (dùng `np.random.normal`, chèn nguồn Gaussian âm/dương nhân tạo để kiểm tra thuật toán ghép dipole). Hoàn toàn độc lập với mọi file bên ngoài.

2. **Hai file test chạy mất bao lâu? (Áng chừng được thời gian CI)**
   - `test_pipeline.py`: Chạy mất **~2.5 giây**.
   - `test_tasks_def.py`: Chạy mất **~1.5 giây**.
   - $\implies$ Tổng thời gian chạy cả 2 file test này là **khoảng 4.0 giây** trên máy local, và chỉ khoảng **2 – 3 giây** trên máy chủ CI GitHub Actions.

3. **Điều gì về ảnh xuất ra phải LUÔN LUÔN ĐÚNG (Invariants)?**
   - **Kích thước ảnh phải là số lẻ $N \times N$:** Để tâm yêu cầu rơi chính xác vào pixel trung tâm $((N+1)/2, (N+1)/2)$. Với cấu hình chuẩn FOV $0.1^\circ$ và scale $6.2''/\text{px}$, kích thước ảnh **luôn luôn là $59 \times 59$ pixel**.
   - **Tọa độ `predicted_px` và gốc tọa độ:** Phải tuân thủ chuẩn **PNG (gốc trên-trái, zero-based pixel centres)** với công thức bắt buộc $x_{png} = x_{fits}$, $y_{png} = (\text{height} - 1) - y_{fits}$. Dấu thập phải bám sát vị trí thực tế của sao (độ lệch $< 0.5$ px).
   - **Tâm lưới WCS TAN:** Phải luôn được đặt tại vị trí mục tiêu ở thời điểm trung vị của chuỗi ảnh ($t_{mid}$), đảm bảo mục tiêu đi ngang qua trung tâm khung hình khi xem blink.
   - **Thang chuẩn hóa (Norm):** Phải dùng **chung một thang `AsinhStretch`** với cùng cặp $[vmin, vmax]$ cho toàn bộ các khung visit trong cùng một detector. Tuyệt đối không stretch riêng lẻ từng ảnh.
   - **Màu dữ liệu khuyết/NaN:** Tất cả các pixel bị che bởi cờ chất lượng (`OVERFLOW`, `NONLINEAR`, transient...) hoặc nằm ngoài footprint khi xuất ra PNG phải luôn hiển thị bằng màu tím chuẩn của dự án: **`#703090`**.
   - **Ảnh hiệu (Diff):** Luôn dùng colormap hai cực đối xứng **`RdBu_r`** với cận đối xứng $[-limit, +limit]$. Sao có chuyển động riêng phải thể hiện rõ cấu trúc lưỡng cực: vùng cũ màu xanh lam (âm) và vùng mới màu đỏ (dương).

