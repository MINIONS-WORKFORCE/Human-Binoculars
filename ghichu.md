# Ghi chú workspace và thực hành reproject

> **Cập nhật 07/11/2026:** đã triển khai các task ưu tiên mới trong [members/huu-hoang/TASKS.md](members/huu-hoang/TASKS.md): TAN tâm mục tiêu/tâm tìm kiếm, centroid nguồn nền, benchmark 10/50 ảnh, median/ảnh hiệu, `make_frames`, bộ mẫu năm mục tiêu, flags bão hòa và RGB giả. Xem [ảnh tổng quan](data/five_targets/overview.png) và [kiểm chứng đầu ra](data/five_targets/verification.json). Phần bên dưới giữ nguyên ghi chép demo hai ảnh ngày 06/11; checklist cũ không mô tả toàn bộ trạng thái hiện tại.

Cập nhật: 06/11/2026. Người học đã nắm SPHEREx, LVF, WCS không gian/phổ, flags, asinh và FITS; ghi chú này tập trung vào việc chạy và đọc kết quả.

## Mở gì trước? — Bài thực hành hôm nay

**Mục tiêu đã chạy:** đưa ảnh SPHEREx 2026 của vùng quanh WISE 0855 lên lưới WCS ảnh 2025. Đây là ví dụ hình học, chưa xác nhận nguồn sao lùn nâu trên từng ảnh. Hai ảnh chưa khớp bước sóng nên không dùng chênh lệch sáng/tối để kết luận biến thiên.

1. Xem ảnh trước mọi xử lý: [2025 gốc](data/reproject_wise0855/wise0855_2025_original.png), [2026 gốc](data/reproject_wise0855/wise0855_2026_original.png).
2. Xem [bảng so sánh trước/sau](data/reproject_wise0855/comparison.png). Hai ô đầu đã mask; ô thứ ba đã reproject.
3. Mở riêng [ảnh mốc 2025 sau mask](data/reproject_wise0855/wise0855_2025_reference.png) và [ảnh 2026 sau reproject](data/reproject_wise0855/wise0855_2026_aligned.png). Chúng dùng cùng lưới và thang hiển thị; tím là NaN.
4. Xem [GIF blink](data/reproject_wise0855/blink_aligned.gif), đổi khung mỗi 0,9 giây. Đây là luân phiên ảnh trên cùng lưới, không mô phỏng chuyển động giữa hai ngày.
5. Xem [footprint 2026](data/reproject_wise0855/footprint_2026.png) và [vùng hợp lệ cả hai năm](data/reproject_wise0855/common_valid.png): vàng dùng được, tím bị loại; không phải bản đồ độ sáng.
6. Muốn kiểm tra số liệu: mở [report.json](data/reproject_wise0855/report.json). Muốn đọc số đo ảnh và WCS: mở `reprojected.fits` bằng công cụ FITS hoặc Astropy, không đọc như văn bản.

### Tất cả file có tác dụng gì?

| File trong `data/reproject_wise0855/` | Dùng để làm gì? |
| --- | --- |
| `sia_qr2.xml` | Kết quả truy vấn IRSA gốc, bảng VOTable; không chứa ảnh |
| `catalog.ecsv` | Cùng danh sách metadata chuyển sang bảng Astropy |
| `inputs.json` | Nguồn gốc đúng hai ảnh: URL, OBSID, thời gian catalog, checksum |
| `wise0855_2025.fits`, `wise0855_2026.fits` | Hai cutout gốc; giữ để tính toán, không sửa |
| `wise0855_2025_original.png`, `wise0855_2026_original.png` | Hai bản hiển thị IMAGE trước mask/reproject; stretch riêng từng ảnh |
| `wise0855_2025_reference.png` | Ảnh 2025 sau mask, dùng làm mốc |
| `wise0855_2026_aligned.png` | Ảnh 2026 sau mask và reproject |
| `comparison.png` | Ghép 4 ô để xem tổng quan |
| `blink_aligned.gif` | Blink trên cùng lưới và cùng vùng hợp lệ |
| `footprint_2026.png` | Pixel đầu ra 2026 có dữ liệu hợp lệ |
| `common_valid.png` | Pixel hợp lệ ở cả hai năm |
| `reprojected.fits` | Kết quả số và mask, cùng WCS 2025 |
| `report.json` | Thống kê, kiểm tra, bước sóng, giới hạn hiển thị, phiên bản thư viện |
| `run.log` | Log UTF-8 tự lưu mỗi lần chạy script; lỗi vẫn được báo trong terminal |

Script `members/huu-hoang/reproject_demo.py`: `download()` lấy dữ liệu; `validate_inputs()` kiểm tra checksum, OBSID, detector và năm FITS; `load()` đọc và mask; các hàm `export_*` xuất PNG/GIF; `main()` gọi reproject, kiểm tra và ghi kết quả. Nếu thiếu ảnh, script hướng dẫn chạy `--download`.

### Checklist và phần chưa làm

- Đã có môi trường đầy đủ, hai ảnh thật 2025/2026, nguồn gốc và kiểm tra đầu vào, mask, reproject, FITS kết quả, PNG gốc/sau xử lý, footprint, vùng chung, GIF, report, log và hướng dẫn chạy lại.
- Đã kiểm tra hình học và đọc lại WCS trong FITS đầu ra. Chưa đối chiếu astrometry bằng sao nền độc lập.
- Chưa xác nhận phát hiện sao lùn nâu; chưa tính vị trí theo epoch, đo chuyển động, đo quang hoặc làm ảnh hiệu khoa học. Nếu yêu cầu “ảnh có sao lùn nâu” nghĩa là phải thấy và xác nhận nguồn trong cả hai ảnh, phần đó vẫn chưa hoàn tất; chỉ truy vấn quanh tọa độ chưa đủ.
- Chưa chọn cặp gần cùng bước sóng. Không diễn giải chênh lệch sáng của hai ảnh hiện tại thành biến thiên.
- Chưa tích hợp backend/frontend. `shared/api-contract/openapi.yaml` và `shared/data-layout.md` chưa có trong workspace; đây là các file nhóm dự kiến cung cấp, không tự tạo API giả cho bài thực hành cá nhân.
- Chưa commit/push/PR. Sản phẩm `data/` được gitignore; khi chia sẻ cần đính kèm PNG/GIF hoặc chạy script để tái tạo. Không tự thêm FITS vào Git.

### Những điểm dễ nhầm đã giải thích

- **Reproject = tái chiếu:** đổi lưới tọa độ, không chỉ resize, không cân nền và không kéo sao đang chuyển động về một chỗ.
- **Ảnh mốc không phải nền trời:** 2025 cung cấp lưới chuẩn; có thể chọn ngược hoặc tạo lưới mới.
- **Asinh chỉ để nhìn:** nén dải sáng khi xuất PNG/GIF, không thay số đo FITS, không tăng SNR.
- **Đốm trắng chưa chắc là mục tiêu:** có thể là sao nền, thiên hà hoặc giả ảnh; cần kiểm tra nguồn trước khi gán tên.
- **2025 nhạt/2026 đậm:** thang hiển thị chung làm khác biệt mức nền hiện rõ; khác bước sóng và xử lý dữ liệu có thể góp phần. Chưa phân tích riêng nguyên nhân.
- **Vai trò trong dự án:** chuẩn bị các ảnh cùng vị trí trời để blink/stack/difference; các bước phân tích khoa học cần thêm lựa chọn bước sóng, PSF, nền và sai số.

## Trạng thái môi trường sau khi cài đầy đủ

Đã hoàn tất cài đặt theo README trên máy hiện tại:

- Python **3.12.10** trong `.venv`: đáp ứng **3.12+**, không cần đổi Python.
- Đã cài toàn bộ `requirements.txt`, kiểm tra tất cả phiên bản ghim đều khớp; `pyvo` hiện là **1.9.1**. `pip check` không có xung đột.
- Node **24.22.2**, npm **11.19.1**, bản portable trong `.venv/node/`; đã kiểm tra SHA-256 của archive theo nodejs.org. Không cài Node toàn hệ thống.
- Đã chạy `npm ci` từ lockfile; npm audit báo 0 lỗ hổng tại thời điểm cài.
- Đã tạo `.env` từ `.env.example` và cài Git filter `nbstripout --install` cho repo này. nbstripout dùng Git filter, không bắt buộc có file `.git/hooks/pre-commit`.
- `check_env.py --online` báo **READY: environment OK**: QR3 có 0 ảnh, QR2 có 256 ảnh tại vùng truy vấn kiểm tra.
- `npm test`: **150 tests passed / 7 files**. `npm run build:starter`: thành công.
- Đã chạy lại reproject với môi trường đủ thư viện; tái tạo các output, kiểm tra nội suy và WCS đều đạt.

Mở terminal PowerShell mới tại gốc repo, kích hoạt Python và Node local bằng:

```powershell
# Chỉ áp dụng cho terminal hiện tại vì máy đang chặn chạy script PowerShell.
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
. .\scripts\activate-workspace.ps1
python --version
node --version
npm.cmd --version
```

Sau đó dùng `python`, `npm.cmd test`, hoặc `npm.cmd run dev:starter`. Chọn `.venv\Scripts\python.exe` làm interpreter/kernel khi dùng VS Code/Jupyter. Script kích hoạt không sửa PATH toàn máy.

## 1. Workspace đang có gì?

- Đây là repo training cho NASA Space Apps 2026, bài toán SPHEREx Sky Viewer. README yêu cầu repo thi được tạo riêng khi bắt đầu; không sao chép code training sang repo thi.
- `members/huu-hoang/`: phần xử lý ảnh: reproject, mask, stacking, difference và xuất PNG. Ví dụ mới nằm tại `members/huu-hoang/reproject_demo.py`.
- `members/duy-hoang/`: đã có bộ xử lý tọa độ, danh sách mục tiêu, viewer và blink demo. `coords/targets.js` có WISE 0855-0714 và Epsilon Indi B là các mục tiêu sao lùn nâu.
- `scripts/check_env.py`: kiểm tra môi trường và truy vấn IRSA. Ví dụ này dùng tâm tìm kiếm WISE 0855 từ script đó: RA=133.7951°, Dec=-7.2451°.
- `shared/`: dự kiến chứa phần dùng chung và API contract; `data/README.md` nói về fixture pack nhưng lúc bắt đầu workspace chỉ có README, chưa có FITS. `shared/data-layout.md` được nhắc trong README nhưng chưa tồn tại.
- `requirements.txt`: đã khai báo numpy, astropy, reproject, matplotlib, pyvo và các thư viện khác. Python máy là 3.12.10; đã tạo `.venv` và cài các thư viện cần cho ví dụ. Không thay đổi file requirements của nhóm.
- FITS và toàn bộ sản phẩm trong `data/` được gitignore theo quy định repo. Không có thao tác commit, push hoặc gửi tin nhắn cho nhóm.

## 2. Task đã thực hiện

**Đã chạy `reproject_interp` trên hai cutout SPHEREx thật của vùng trời quanh sao lùn nâu WISE 0855-0714, quan sát năm 2025 và 2026.** Ảnh 2025 làm mốc, ảnh 2026 được chuyển lên WCS và kích thước của ảnh 2025.

Đây là ví dụ căn lưới tọa độ. Chưa xác nhận phát hiện WISE 0855 trên từng ảnh, chưa đo chuyển động riêng hoặc độ sáng của nó. Dấu cộng đỏ trong hình là **tâm tìm kiếm cố định**, không phải vị trí sao được đo hay dự đoán theo epoch. Tọa độ trong `targets.js` và `check_env.py` khác nhau; không tự coi cả hai là vị trí sao ở thời điểm quan sát. Cutout rộng 0,1° để lấy vùng trời xung quanh mục tiêu.

### Hai ảnh đầu vào

Truy vấn SIA collection `spherex_qr2` trả về 264 bản ghi quanh vùng tìm kiếm với bán kính truy vấn 0,03°. Chọn cố định hai bản ghi detector D6 để lần chạy sau tái hiện cùng ví dụ; tải cutout 0,1° × 0,1°, không tải cả ảnh detector.

| Thuộc tính | Ảnh 2025 | Ảnh 2026 |
| --- | --- | --- |
| OBSID | `2025W19_1B_0116_1` | `2026W17_1B_0634_1` |
| `DATE-OBS` trong IMAGE, UTC | 2025-05-05T16:48:02.459 | 2026-04-23T10:28:29.888 |
| Kích thước IMAGE | 59 × 59 | 58 × 58 |
| Detector | D6 | D6 |
| Đơn vị | MJy / sr | MJy / sr |
| Bước sóng tại tâm tìm kiếm | 4,962055 µm | 4,612874 µm |
| Bandwidth tại tâm tìm kiếm | 0,037187 µm | 0,036219 µm |
| Pixel còn hợp lệ sau mask | 3.385 | 3.229 |

Thời điểm SIA trong `inputs.json` lệch vài mili giây đến khoảng 0,04 giây so với header do độ chính xác biểu diễn MJD của catalog. Bảng trên dùng header FITS. Không dùng `DATE` tạo/xử lý file làm ngày quan sát.

**Cùng D6 nhưng khác bước sóng tại tâm.** Cặp này đủ để thực hành đổi lưới; chưa được chọn tối ưu theo bước sóng. Muốn so sánh độ sáng hoặc tạo ảnh hiệu có ý nghĩa khoa học, cần chọn lại cặp gần bước sóng/bandwidth, xử lý PSF, nền và sai số. Hai phiên bản pipeline cũng khác nhau: v20 năm 2025 và v24 năm 2026.

## 3. Các bước đã làm, giải thích dễ hiểu

### Bước 1 — Tìm và tải đúng hai ảnh

Gửi yêu cầu đến SIA của IRSA, đọc ngày quan sát và detector, rồi lấy `access_url`. Thêm `?center=133.7951,-7.2451&size=0.1` để yêu cầu một miếng ảnh nhỏ quanh vùng cần học. Script kiểm tra năm trong catalog và xác nhận phản hồi tải về là FITS đọc được.

`inputs.json` lưu OBSID, URL, thời gian, kích thước và SHA-256 của hai file. Nhờ vậy có thể biết chính xác ảnh nào đã được dùng.

### Bước 2 — Lấy IMAGE và WCS thật của nó

Đọc HDU bằng tên, không gán cứng số thứ tự. Hai file thực tế đều có:

```text
PRIMARY, IMAGE, FLAGS, VARIANCE, ZODI, PSF, WCS-WAVE
```

Tức là **7 HDU tổng cộng**, gồm primary và 6 extension. `WCS-WAVE` là bảng, không phải ảnh 2D. Không giả định mọi sản phẩm SPHEREx đều đúng mẫu 6 HDU từng học.

Để căn vị trí trên trời, dùng `WCS(header, fobj=hdul).celestial`, giữ cả biến dạng SIP. WCS phổ được đọc riêng bằng key `W`, có bảng tra `WCS-WAVE`; loại các hệ số SIP không gian khỏi bản sao header khi dựng WCS phổ. Chỉ đánh giá bước sóng/bandwidth tại tâm tìm kiếm để báo cáo, không biến nó thành một ảnh phổ.

### Bước 3 — Che pixel có cờ lỗi

Đọc vị trí bit từ các keyword `MP_*` trong header FLAGS của **từng file**, vì năm 2026 có thêm một số loại cờ. Loại pixel có các bit chất lượng đã chọn hoặc giá trị không hữu hạn, thay bằng `NaN`.

Giữ `MP_SOURCE` và `MP_FULLSAMPLE`: đây là thông tin bổ sung; riêng SOURCE không đồng nghĩa pixel hỏng. Dùng điều kiện `FLAGS == 0` sẽ che cả những vùng được đánh dấu có nguồn thiên văn. Danh sách cờ bị loại và bitmask thực tế được lưu trong `report.json`; đây là lựa chọn tương đối chặt cho demo, chưa phải mask tối ưu cho đo quang.

### Bước 4 — Chọn ảnh 2025 làm tờ giấy kẻ ô chuẩn

Hình dung hai ảnh là hai bản đồ có ô lưới hơi khác nhau. Ta giữ nguyên ô lưới của bản đồ 2025, rồi hỏi với **mỗi ô đầu ra**:

1. Ô này ứng với RA/Dec nào trên ảnh 2025?
2. RA/Dec đó nằm ở tọa độ pixel nào trên ảnh 2026?
3. Lấy giá trị ở đó bằng nội suy bilinear từ các pixel lân cận.

Đoạn cốt lõi:

```python
aligned, footprint = reproject_interp(
    (image_2026, wcs_2026),
    wcs_2025,
    shape_out=image_2025.shape,
    order="bilinear",
)
common_valid = (
    np.isfinite(image_2025)
    & np.isfinite(aligned)
    & (footprint > 0)
)
```

`shape_out` quyết định đầu ra 59×59. WCS đích quyết định mỗi pixel nằm ở đâu trên trời. Chỉ resize lên 59×59 sẽ không làm được điều này.

Nội suy có thể làm ảnh mượt hơn và lan vùng NaN sang các pixel cần dùng pixel lỗi. Với dữ liệu MJy/sr, đây là ví dụ nội suy độ sáng bề mặt; không mặc định bảo toàn tổng flux nguồn hoặc độ phân giải ban đầu. Không nội suy bit flags bằng bilinear. Script không xuất variance sau reproject vì truyền sai số cần xử lý trọng số nội suy và tương quan giữa các pixel.

### Bước 5 — Dùng footprint và vùng hợp lệ chung

Với `reproject_interp`, footprint ở ví dụ này là 0/1: 1 nơi phép nội suy cho dữ liệu hợp lệ, 0 nơi không có. Nó không phải bản đồ SNR hay tỷ lệ diện tích phủ một pixel.

Footprint chỉ mô tả đầu ra của ảnh 2026; muốn so hai năm phải giao thêm với các pixel hữu hạn của ảnh 2025. Vì thế `COMMONVALID` nhỏ hơn vùng footprint.

### Bước 6 — Xuất hình và FITS kết quả

- `comparison.png`: ảnh 2025 đã mask, ảnh 2026 đã mask trước reproject, ảnh 2026 đã reproject, footprint.
- `reprojected.fits`: `REFERENCE2025`, `ALIGNED2026`, `FOOTPRINT`, `COMMONVALID`, cùng một WCS 2025 và đầy đủ SIP. Đây là sản phẩm demo mới, không phải một MEF SPHEREx nguyên bản có đủ phổ/PSF/variance.
- `report.json`: các thông số và kết quả kiểm tra.

Ba ảnh cường độ dùng chung thang asinh và giới hạn hiển thị để tránh tự co giãn từng ảnh gây hiểu nhầm. Hai ảnh có nền và hình thái khác nhau rõ; căn tọa độ không làm bước sóng, nền hay PSF trở nên giống nhau. Vùng trống/NaN không có nghĩa cường độ bằng 0.

## 4. Kết quả và kiểm tra đã chạy

| Kiểm tra | Kết quả |
| --- | --- |
| Kích thước ảnh 2026 sau reproject | 59 × 59 |
| Pixel hợp lệ chung | 2.909 / 3.481 = **83,57%** |
| Footprint hợp lệ ảnh 2026 trên lưới đích | **85,84%** |
| Sai lệch đổi sky → pixel 2026 → sky, lớn nhất trên các điểm thử | 3,74 × 10⁻⁷ arcsec |
| Reproject ảnh hằng bằng 1: sai số lớn nhất | 1,11 × 10⁻¹⁶ |
| Reproject ảnh 2025 về chính lưới nó: sai số tuyệt đối lớn nhất ở pixel hữu hạn chung | 9,29 × 10⁻⁸ MJy/sr |
| Đọc lại WCS cả bốn extension đầu ra và đối chiếu các điểm thử | Đạt, sai lệch dưới 10⁻⁶ arcsec |

Ví dụ cụ thể: tâm tìm kiếm cố định nằm tại pixel `(28,6103; 29,2233)` trong ảnh 2025 và `(28,5273; 28,0544)` trong ảnh 2026 gốc, tính từ 0. Sau reproject, tọa độ đó dùng lại pixel `(28,6103; 29,2233)` của lưới 2025. Đây là cách đọc ý nghĩa của việc căn lưới; không phải số đo chuyển động của sao.

Các kiểm tra trên xác nhận tính nhất quán số học/hình học của thao tác, không xác nhận độ chính xác astrometry tuyệt đối của IRSA. Chưa đối chiếu centroid sao nền hay catalogue độc lập. Reproject giữ chuyển động thật theo bầu trời; nó không ép sao lùn nâu ở hai epoch về cùng một chỗ.

## 5. Mở kết quả và chạy lại

Từ thư mục gốc repo, PowerShell:

```powershell
# Chạy offline với hai FITS đã tải; tái tạo hình, FITS đầu ra và report.
.venv\Scripts\python members/huu-hoang/reproject_demo.py

# Khi cần tải lại đúng hai OBSID từ IRSA (cần mạng).
.venv\Scripts\python members/huu-hoang/reproject_demo.py --download
```

Các thư viện xử lý chính đã chạy: numpy 2.5.4, astropy 8.0.2, reproject 0.21.0, matplotlib 3.11.2. Phiên bản thực tế lưu trong report. Với máy mới, tạo venv và cài `requirements.txt` theo README trước.

Sản phẩm nằm tại [data/reproject_wise0855/](data/reproject_wise0855/):

- [Hình trước/sau](data/reproject_wise0855/comparison.png)
- [Thông số và kiểm tra](data/reproject_wise0855/report.json)
- [Nguồn hai ảnh](data/reproject_wise0855/inputs.json)
- [FITS đã căn lưới](data/reproject_wise0855/reprojected.fits)

![Hai ảnh đã mask, ảnh sau reproject và footprint](data/reproject_wise0855/comparison.png)

Vì `data/` bị gitignore, link hình chỉ hoạt động trên máy có sản phẩm. Clone repo mới cần chạy với `--download` để tái tạo.

## 6. Tài liệu tham khảo

### GIF blink sau reproject

`blink_aligned.gif` luân phiên ảnh 2025 và ảnh 2026 đã reproject, mỗi khung 900 ms, lặp liên tục. Cả hai dùng cùng lưới 2025, cùng thang asinh và chỉ hiện vùng `COMMONVALID`; vùng tím là pixel bị loại ở cả hai khung hiển thị. Nhãn năm thay đổi theo khung. Chạy lại script sẽ tái tạo GIF. Do hai ảnh khác bước sóng và nền, thay đổi độ sáng khi blink chưa phải bằng chứng biến thiên hay phát hiện sao lùn nâu.

### Bổ sung ảnh gốc dễ xem

Script còn xuất `wise0855_2025_original.png` và `wise0855_2026_original.png` từ IMAGE gốc, trước mask và reproject. Mỗi hình dùng giới hạn percentile 2–99,5% và asinh riêng để dễ xem; không so trực tiếp độ sáng giữa hai PNG này. Không thay đổi dữ liệu FITS gốc. Hai ô đầu của `comparison.png` là ảnh đã mask, trước reproject; tiêu đề hình đã ghi rõ.

FITS lưu số đo dạng số thực, đơn vị, WCS và các extension chất lượng/phổ; PNG chỉ là bản hiển thị sau ánh xạ số đo sang sắc xám. Giữ FITS để tính toán, mở PNG để xem nhanh.

- [IRSA: SPHEREx Cutout Tool](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/cutout_tool.html): cách yêu cầu cutout qua URL.
- [IRSA: SPHEREx cutouts tutorial](https://caltech-ipac.github.io/irsa-tutorials/spherex-cutouts/): tìm và tải dữ liệu thật.
- [API reproject_interp](https://reproject.readthedocs.io/en/stable/api/reproject.reproject_interp.html): đầu vào, bilinear, shape_out và ý nghĩa footprint.
