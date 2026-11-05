## Bảng mục tiêu đã đối chiếu

Tất cả tọa độ dưới đây là **ICRS tại epoch J2000**, lấy từ trang SIMBAD hiển thị `ep=J2000`. Không gắn lại epoch J2016 chỉ vì bibcode là Gaia. SIMBAD mô tả lưu tọa độ ở epoch 2000 và có thể chuyển sang epoch khác: https://simbad.cds.unistra.fr/Pages/guide/ch15.htx

| Mục tiêu       |         RA độ |        Dec độ | pmRA cosDec mas/năm | pmDec mas/năm |      J |      H |        K |
| -------------- | ------------: | ------------: | ------------------: | ------------: | -----: | -----: | -------: |
| Barnard        | 269.452076959 |  +4.693364967 |            −801.551 |    +10362.394 |  5.244 |  4.830 |    4.524 |
| WISE 0855      | 133.818908250 |  −7.247048000 |             −8123.7 |        +673.2 |  25.00 |  23.83 | Không có |
| Epsilon Indi B | 331.044146589 | −56.782844195 |           +3981.977 |     −2466.832 | 11.908 | 11.306 |   11.208 |
| RW Aur         |  76.956526035 | +30.401438174 |               +7.23 |        −20.33 |  8.378 |  7.621 |    7.020 |
| R Dra          | 248.167610833 | +66.754979417 |             −20.643 |        +6.149 |  3.710 |  3.125 |    2.230 |

Nguồn từng hàng và bibcode nằm trong `targets.json`; sai số/quality của độ sáng cũng được giữ ở đó. Dữ liệu tra cứu qua nội dung SIMBAD được công cụ tìm kiếm lập chỉ mục; đây không phải một phiên TAP trực tiếp. K bị thiếu là `null`, không phải 0.

- [Barnard SIMBAD](https://simbad.u-strasbg.fr/simbad/sim-basic?Ident=Barnard%27s+star&submit=SIMBAD+search)
- [WISE 0855 SIMBAD](https://simbad.u-strasbg.fr/simbad/sim-id?Ident=WISEA+J085510.74-071442.5)
- [Epsilon Indi B SIMBAD](https://simbad.u-strasbg.fr/simbad/sim-id?Ident=%2A+eps+Ind+B)
- [RW Aur SIMBAD](https://simbad.cds.unistra.fr/simbad/sim-id?Ident=RW+Aur)
- [R Dra SIMBAD](https://simbad.cds.unistra.fr/simbad/sim-id?Ident=%40376084&Name=V%2A+R+Dra&submit=submit)

## Bảng kết quả kỳ vọng v0

Công thức dự báo: `mu = hypot(pmRA_cosDec, pmDec) / 1000` (arcsec/năm), `displacement = mu × delta_years / 6.15` (pixel danh định). Không nhân cosDec lần thứ hai. Đây là phép tính từ catalog, **không phải kết quả phát hiện trên ảnh**.

| Mục tiêu       | Chuyển động arcsec/năm | Sau 0,5 năm pixel | Sau 1 năm pixel | Sau 1,5 năm pixel | Kỳ vọng nên kiểm                                             |
| -------------- | ---------------------: | ----------------: | --------------: | ----------------: | ------------------------------------------------------------ |
| Barnard        |               10.39335 |           0.84499 |         1.68998 |           2.53496 | Chủ yếu hướng bắc, hơi tây; đối chiếu sao nền                |
| WISE 0855      |                8.15155 |           0.66273 |         1.32545 |           1.98818 | Chủ yếu hướng tây, hơi bắc; phải phát hiện đủ S/N trước      |
| Epsilon Indi B |                4.68416 |           0.38083 |         0.76165 |           1.14248 | Đông nam; kiểm đúng nguồn B                                  |
| RW Aur         |                0.02158 |           0.00175 |         0.00351 |           0.00526 | Chủ yếu kiểm biến quang, không yêu cầu dịch chuyển nhìn thấy |
| R Dra          |                0.02154 |           0.00175 |         0.00350 |           0.00525 | Chủ yếu kiểm biến quang; xem chất lượng photometry           |

“Hướng đông/tây” là trên trời, chưa phải chiều trái/phải màn hình; WCS quyết định chiều ảnh. 6,15″/pixel là tỷ lệ danh định của ảnh SPHEREx; ảnh reproject có thể dùng tỷ lệ khác. Tài liệu PSF mô tả 10 pixel PSF ứng với một pixel ảnh và tỷ lệ 0,615″/pixel PSF: https://caltech-ipac.github.io/irsa-tutorials/spherex-intro/

Bảng sử dụng năm Julian 365,25 ngày. Sáu tháng lịch không luôn bằng 0,5 năm Julian. Khi có `t_min/t_max`, script dùng thời gian thực; không gán tháng 5 và tháng 11 mặc định thành hai đợt của mọi nguồn. Con số 1,5 năm chỉ là kịch bản dự báo, không khẳng định kho ảnh đã có baseline ấy.

## Những điều cần sửa hoặc làm rõ trong cách hiểu lộ trình

**1. WISE 0855 cần tách tọa độ đề bài và tọa độ astrometry.** Chuỗi `08 55 10.831 -07 14 42.53` đổi ra `133.795129167, -7.245147222` độ. Nó khác tọa độ J2000 SIMBAD đang cung cấp. Bài báo phát hiện liệt kê các phép đo có ngày riêng, ví dụ MJD 55320.4; nhãn J2000 của hệ tọa độ không đủ để suy ra epoch quan sát. Không đặt chuỗi trong đề vào `obstime=J2000` tùy tiện. Nguồn đối chiếu: https://doi.org/10.1088/2041-8205/786/2/L18

**2. Cửa sổ cắt nhỏ dễ bỏ mất sao chuyển động nhanh.** Dự báo tuyến tính từ J2000 tới khoảng J2026 cho Barnard là khoảng 270″, lớn hơn cả chiều rộng cutout 0,05° = 180″. Cần tìm footprint bao phủ vị trí dự đoán và cắt ở vị trí phù hợp. Việc SIA2 trả ảnh ở tọa độ cũ chỉ chứng minh footprint ảnh có giao vùng tìm; chưa chứng minh cutout nhỏ chứa nguồn hiện tại.

**3. Cùng detector chưa đủ cho so sánh độ sáng.** LVF khiến bước sóng tại nguồn thay đổi theo vị trí trên detector. Khung cộng của một detector có thể dùng để minh họa nhưng thay đổi phân bố bước sóng giữa hai đợt có thể giả dạng biến quang. Muốn kiểm khoa học, phải so bandpass tương thích hoặc cân bằng trọng số phổ, cùng calibration và xử lý nền. Đây là yêu cầu QA đề xuất từ nguyên lý LVF, không phải tính năng mới cần viết trong hai ngày đầu.

**4. Căn trên sao nền, không khóa mục tiêu đang chuyển động.** Cắt từng ảnh quanh tọa độ mục tiêu là được, nhưng phải reproject về một hệ trời cố định chung trước blink. Nếu đưa vị trí dự đoán của mục tiêu về cùng pixel rồi so trực tiếp, chính chuyển động cần quan sát sẽ bị loại bỏ.

**5. Không biến J/H/K thành dự báo flux SPHEREx.** Các phép đo có thời điểm, passband và chất lượng khác nhau. R Dra còn dùng nhiều catalog khác nhau trong ba ô; WISE có J/H rất yếu và không có K trong trang tóm tắt. Không gán nhãn toàn bộ là 2MASS, không coi giá trị thiếu là upper limit nếu nguồn không nói vậy. D5/D6 cho WISE là hướng ưu tiên thử, chưa phải cam kết sẽ thấy nguồn.

**6. `apply_space_motion` không tự thêm chuyển động thị sai của người quan sát.** Script v0 tính chuyển động góc ICRS, không có annual parallax, quỹ đạo đôi hoặc perspective acceleration. Astropy giả định vận tốc thẳng đều và RV bằng 0 khi không cung cấp. Muốn astrometry dưới pixel cho sao rất gần, cần bổ sung mô hình vị trí người quan sát và bộ tham số tương thích. Nguồn: https://docs.astropy.org/en/stable/coordinates/apply_space_motion.html

**7. Không tuyên bố phân giải được cặp Ba/Bb của Epsilon Indi B.** Dùng nó như nguồn B tổng hợp trong bài luyện SPHEREx; không lấy nhầm tọa độ A hoặc hành tinh Ab. Nếu muốn cả A và B trong một khung, phải đo khoảng cách góc và thiết kế tâm/FOV, không dùng mặc định 0,05° cho mọi tình huống.

**8. Giữ detector, release và provenance.** QR2/QR3 có khác biệt calibration; không cộng/trừ bản ghi trùng hoặc trộn release một cách cơ học. IRSA có sản phẩm hiệu chỉnh riêng giữa hai release. Metadata phải giữ collection, obs_id và band. Nguồn: https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/

**9. Cộng ảnh không đảm bảo luôn tăng S/N đúng sqrt(N).** Xấp xỉ đó cần nhiễu độc lập và phép kết hợp phù hợp; reproject tạo tương quan, median không có cùng hiệu suất với mean, nguồn di chuyển có thể nhòe trong stack dài. Cần ghi thời gian đầu/cuối, thời điểm đại diện, số ảnh và coverage của từng khung. Với một stack nhiều thời điểm, không coi trung điểm hai ảnh đầu/cuối là thời điểm hiệu dụng luôn đúng.

**10. Flux từ IMAGE cần đơn vị đúng.** IMAGE là surface brightness MJy/sr; tổng pixel không tự là Jy. Khi sang bài trích phổ/photometry ngày sau, phải tính diện tích góc pixel, nền, aperture/PSF và bất định. Không dùng giá trị PNG đã stretch để đo quang.
