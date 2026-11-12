# Bàn giao xử lý ảnh — 10/11/2026

## Đông: pipeline dùng chung

Import `build_frames`, `diff_png`, `mask_flags`, `rgb_png` từ
`shared.frames_pipeline`. Mã nằm trong `shared/image_processing.py`.
`make_frames()` hiện tại giữ cấu trúc phản hồi API, dùng chung `mask_flags`.
Các sản phẩm mới trả riêng từ `build_frames()`; chưa thay schema HTTP.
`build_frames()` mặc định dùng WCS + SciPy bilinear; có thể chọn
`interpolation="reproject"` khi môi trường nạp được thư viện này.
Backend SciPy kiểm tra tọa độ khứ hồi, giữ NaN và loại biên ngoài các tâm pixel.

```python
report, images = build_frames(cutouts, target, root=repo_root, output=product_dir)
```

`cutouts` là danh sách bản ghi như `observation_manifest.json` cục bộ:
`path`, `mjd`, `obs_id`, `detector` (D1..D6), tùy chọn `sha256`, `cluster_id`.
`target` có `j2000_deg`, `pm_mas_yr` (RA đã nhân cos Dec).
Không truyền tọa độ J2026 vào trường J2000.

- Một lưới TAN cố định cho cả chuỗi, tâm ở vị trí dự đoán tại trung điểm
  thời gian ảnh đầu/cuối. Không kéo từng khung theo ngôi sao.
- Median theo detector/đợt; thời điểm khung là trung bình MJD các ảnh thành viên.
- Cùng thang asinh trong mỗi detector, cùng thang ảnh hiệu đối xứng trong chuỗi.
- `predicted_px` dùng gốc trên trái: `(x_fits, height-1-y_fits)`.
- PNG gốc không vẽ dấu thập; `crosshair_url` là ảnh riêng cùng kích thước pixel.
- Thiếu dữ liệu màu `#703090`. RGB gán D6/D3/D1 vào R/G/B trên cùng lưới.
- Không suy biến thiên từ ảnh hiệu chưa khớp bước sóng, PSF và nền.

Chạy `.venv/Scripts/python.exe members/huu-hoang/build_frames.py` để tạo
`data/observation_products/barnard_motion/`: frames.json, PNG, blink GIF,
overview và validation.json. Tâm sao được khớp Gaussian robust trên cường độ FITS
còn hợp lệ quanh lõi bão hòa, không đo từ PNG hoặc ép tâm vào dấu thập.
Đây là kiểm hiển thị, cần quy trình astrometry/PSF phù hợp để duyệt khoa học.

**Đã chạy được trên Windows:** cùng Python và phiên bản thư viện lần trước.
Import reproject vẫn bị chặn ở `_overlap` nhưng task dùng WCS/SciPy trực tiếp,
không thay đổi chính sách Windows và không dùng WSL. Đã xem ảnh thật, kiểm D6
dịch 1,128 pixel, dấu thập lệch tâm vùng cánh 0,173 và 0,152 pixel.
Lõi sao vẫn mask màu tím; không khôi phục pixel bão hòa.

Đối chiếu phép chiếu trên FITS kết quả WISE 0855 đã lưu từ lần trước:
2.906 pixel chung, max error 4,45e-8 MJy/sr; biên mới bảo thủ hơn (82 pixel
hữu hạn cũ bị loại). Xem `barnard_validation.json` và ảnh cục bộ
`data/observation_products/barnard_motion/D6-motion-detail.png`, `D6-blink.gif`.
33 test đạt cho hàm mới, mock API, frame jobs. Các script cũ gọi trực tiếp
reproject/astropy.stats chưa được sửa để dùng phương pháp này.

## Nguyên: phổ và ứng viên chuyển động

Đã đối chiếu trực tiếp báo cáo cục bộ: nền gần **0/18**, nền xa 12–25 px
**5/18** mẫu đạt bộ lọc số học. Chưa có phổ được duyệt khoa học.

- `evidence_manifest.json`: đường dẫn báo cáo và SHA-256 để đối chiếu đúng đầu vào.
- `dipole_candidates.csv`: đủ **58** ứng viên trích từ báo cáo đã lưu.
  Tọa độ x/y là pixel FITS đếm từ 0, gốc dưới trái, chưa lật sang PNG.
- Báo cáo gốc nằm trong `data/observation_products/luhman16_spectrum/`
  và `data/observation_products/change_candidates/` (data không được commit).
- Nguyên cần duyệt định danh nguồn, contamination vành nền, footprint/mask,
  hiệu chỉnh PSF/khẩu độ, đơn vị/sai số và tính không đồng thời của các mẫu.
- 58 dipole chưa phải 58 nguồn chuyển động được xác nhận: phải loại ảnh hưởng
  của bước sóng, nền, PSF và sai lệch căn ảnh.

Đây là gói bàn giao trong repo; chưa gửi tin nhắn cho đồng đội và chưa có xác nhận duyệt.

## Diễn tập 90 phút

Người học tự tạo thư mục trắng, ghi giờ bắt đầu/kết thúc thật và code lại:
cutout → mask → TAN → median → PNG/ảnh hiệu. Phân bổ gợi ý: 10/15/20/15/20
phút cho năm bước, 10 phút cuối kiểm tra. Ghi manifest, số ảnh, lý do loại,
kiểm tra sao nền và chiều tọa độ; so kết quả với bộ chuẩn sau khi tự hoàn thành.
Thời gian chạy script không thay thế thời gian tự code. Buổi diễn tập của
người học và phần duyệt của đồng đội vẫn đang chờ thực hiện.
