# API contract

Đông puts `openapi.yaml` here on 4/11, covering `/api/frames`, `/api/spectrum` and `/api/lightcurve`, with field names taken from the real SIA2 columns.

Frontend (Duy Hoàng, Thạch) and image processing (Hữu Hoàng) build against this file. Any change goes through a PR that tags all three.

## Hợp đồng v0

[openapi.yaml](openapi.yaml) mô tả ba endpoint GET. Đây là hợp đồng để review và
làm mock; backend hiện chỉ triển khai `/health`. Trang `/docs` của backend chưa
tự động chứa các endpoint trong file YAML này.

| Endpoint | Tham số bắt buộc | Kết quả chính |
| --- | --- | --- |
| `/api/frames` | `s_ra`, `s_dec`, `obs_collection`, `energy_bandpassname`, `cutout_size_deg` | `frames`, URL PNG, thời gian và `sources` |
| `/api/spectrum` | `s_ra`, `s_dec`, `obs_collection` | `points` theo bước sóng, flux, sai số và `sources` |
| `/api/lightcurve` | `s_ra`, `s_dec`, `obs_collection`, `energy_bandpassname` | `points` theo thời gian trong cùng miền bước sóng và `sources` |

Cả ba endpoint nhận thêm `t_min` và `t_max` tùy chọn, đơn vị MJD ngày. Khi có cả
hai, `t_min` phải nhỏ hơn hoặc bằng `t_max`. Chỉ có một giới hạn nghĩa là khoảng
mở ở đầu còn lại. Phản hồi `query` lặp lại tham số yêu cầu đã chuẩn hóa; bỏ những
giới hạn thời gian không được truyền.

Ví dụ đường dẫn của API ứng dụng, nối vào địa chỉ backend đang cấu hình:

```text
/api/frames?s_ra=133.79513&s_dec=-7.24515&obs_collection=spherex_qr2&energy_bandpassname=SPHEREx-D6&cutout_size_deg=0.05
```

## Tên trường và ánh xạ sang IRSA

Các tên metadata đã được đối chiếu với tiêu đề 51 cột trong phản hồi SIA2 thật
của truy vấn WISE 0855 QR2. Schema `SourceObservation` giữ nguyên tên như
`obs_id`, `obs_publisher_did`, `obs_collection`, `energy_bandpassname`, `s_ra`,
`s_dec`, `t_min`, `t_max`, `access_url`, `access_format`, `s_region`, `s_fov`,
`em_min` và `em_max`. Chú thích `x-sia2-column` trong YAML ghi nguồn từng trường.

| Tham số API ứng dụng | Cách dùng khi truy vấn IRSA |
| --- | --- |
| `s_ra`, `s_dec` | Tọa độ tâm vùng cần xem, độ ICRS; dùng xây `POS`. Tâm các ảnh trả về nằm riêng trong `sources[].s_ra/s_dec`. |
| `obs_collection` | Chuyển thành tham số SIA2 `COLLECTION`, dùng đúng tên `spherex_qr2`, `spherex_qr2_deep`, `spherex_qr3`, `spherex_qr3_deep`. Không tự đổi release khi kết quả rỗng. |
| `energy_bandpassname` | Lọc cột metadata cùng tên theo `SPHEREx-D1` đến `SPHEREx-D6`. Đây không phải tên tham số của endpoint SIA2. |
| `t_min`, `t_max` | Chuyển thành khoảng `TIME` theo MJD; không gửi chuỗi ISO làm giá trị SIA2 TIME. |
| `cutout_size_deg` | Trường riêng của ứng dụng: cạnh vùng cắt vuông theo độ, lớn hơn 0 và tối đa 0.2 độ trong v0. Khi dựng POS phải bao phủ cả vùng cắt. |

`s_fov` trong metadata mô tả vùng phủ ảnh nguồn; không đổi tên nó để biểu diễn
bán kính tìm kiếm hoặc kích thước cutout. `access_url` luôn là URL dữ liệu nguồn;
URL PNG đã xử lý nằm ở trường ứng dụng `image_url`.

## Quy tắc dữ liệu đầu ra

- Các trường `frames`, `points`, `image_url`, `frame_id`, `data_kind`, `flux`,
  `flux_error`, `wavelength_um`, `time_mjd` và `measurement_method` là dữ liệu
  ứng dụng tạo ra, không phải cột SIA2.
- `sources` chứa các sản phẩm đầu vào. Mỗi frame hoặc điểm đo tham chiếu chúng
  bằng `source_obs_publisher_dids`. Không dùng riêng `obs_id` làm khóa tệp vì một
  quan sát có thể có nhiều detector. Các định danh trong `sources` phải duy nhất.
- Mỗi frame chứa một detector và một collection. `n_images` bằng số định danh
  nguồn duy nhất được dùng. `t_min/t_max` là thời gian sớm nhất/muộn nhất của
  nguồn đóng góp, và phải nằm trong phạm vi truy vấn có giao quan sát phù hợp.
- `frames` và điểm light curve sắp theo thời gian tăng dần; các điểm phổ sắp
  theo bước sóng tăng dần. Frame có thể được cộng từ nhiều ảnh.
- `observation_time` của frame là trung điểm khoảng thời gian khung, dạng ISO
  UTC. `time_mjd` của điểm light curve cũng là trung điểm khoảng đóng góp.
- `em_min/em_max` nguồn dùng mét; `wavelength_um` và miền bước sóng light curve
  dùng micromet. `flux` và `flux_error` dùng đơn vị được khai báo ở `flux_unit`.
- Flux hoặc sai số không đo được là `null`, không thay bằng 0. Sai số có giá trị
  phải không âm. Khi có điểm đo, đơn vị và phương pháp đo phải được khai báo.
- HTTP 200 với danh sách rỗng và cảnh báo `NO_DATA` là truy vấn thành công nhưng
  không có dữ liệu phù hợp. Khi chưa đánh giá được phép đo, `flux_unit`,
  `measurement_method` và miền bước sóng light curve được để `null`.
- Ví dụ có dữ liệu trong YAML là dữ liệu tổng hợp, có `data_kind: mock` và cảnh
  báo `MOCK_DATA`. URL `example.org` và `/mock/` là minh họa, không phải ảnh thật.

Schema kiểm tra kiểu, phạm vi từng trường và các trường bắt buộc. Những quy tắc
liên trường như thứ tự thời gian, tham chiếu nguồn, tính trung điểm và độ nhất
quán đơn vị phải được backend kiểm tra khi triển khai.

## Lỗi chung

Tất cả lỗi dùng cùng cấu trúc `error.code`, `error.message`, `error.fields`.

| HTTP | Mã | Khi dùng |
| --- | --- | --- |
| 422 | `VALIDATION_ERROR` | Tọa độ, detector, collection, kích thước hoặc khoảng thời gian không hợp lệ. |
| 502 | `UPSTREAM_ERROR` | IRSA lỗi hoặc phản hồi không dùng được. |
| 504 | `UPSTREAM_TIMEOUT` | IRSA quá thời gian chờ. |
| 500 | `PROCESSING_ERROR` | Pipeline xử lý cục bộ thất bại. |

Khi triển khai FastAPI, lỗi validation mặc định cần được chuyển thành cấu trúc
này. Không đưa secret, đường dẫn máy cục bộ hay traceback vào thông báo lỗi.

## Những điểm cần nhóm xác nhận trước dữ liệu thật

1. Nguyên và Hữu Hoàng chốt quy tắc nhóm theo đợt quét, chọn bước sóng so sánh
   được và kiểm tra chất lượng. Cùng detector chưa bảo đảm cùng bước sóng do LVF.
2. Nguyên chốt phương pháp đo, xử lý nền, khẩu độ, sai số và đơn vị flux.
   `mJy` trong ví dụ mock không ấn định phương pháp đo khoa học thật.
3. Nhóm xác nhận giới hạn vùng cắt 0.2 độ của v0 dựa trên benchmark của Khôi.
4. V0 trả kết quả đồng bộ. Trước khi nối pipeline chậm, Đông và frontend cần
   bổ sung giao thức job nền, polling và thời hạn lưu kết quả vào hợp đồng.

Nguồn: [IRSA SIA2](https://irsa.ipac.caltech.edu/ibe/sia.html) và
[SPHEREx Data Access](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/).
