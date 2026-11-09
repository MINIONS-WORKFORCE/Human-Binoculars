# Ghi chú truy vấn SIA2 cho SPHEREx

**Người phụ trách:** Đông — Backend API và cache  
**Task:** Ghi chú SIA2 ngày 3/11  
**Người nhận:** Khôi và Hữu Hoàng  
**Ngày tổng hợp:** 05/11/2026

## Mục tiêu và kết quả

Tìm các ảnh SPHEREx bao phủ vùng quanh WISE 0855 bằng SIA2, hiểu các cột metadata và xác định đường truy cập tệp ảnh cho pipeline.

Với cùng vùng tìm kiếm, các phản hồi đã kiểm tra cho kết quả:

| Collection | Số dòng dữ liệu | Ghi nhận |
| --- | ---: | --- |
| `spherex_qr3` | 0 | Tệp HTML chỉ có tiêu đề cột, không có bản ghi. |
| `spherex_qr2` | 278 | Tệp `wise0855-qr2.html` có 51 cột metadata. |

Đây là kết quả từ các tệp phản hồi đã kiểm tra, không bảo đảm truy vấn lại sẽ giữ nguyên số dòng vì archive tiếp tục cập nhật. Chưa ghi nhận thời điểm chạy truy vấn gốc. Một dòng đại diện cho một sản phẩm dữ liệu; 278 dòng không có nghĩa là 278 thiên thể hay 278 thời điểm khác nhau.

## Tài liệu bàn giao

- [Google Docs hướng dẫn truy cập SPHEREx và API SIA2](https://docs.google.com/document/d/16kXNdC-F4NpiRmuAPOivl_F4oXcd7voJfzswldbesmU/edit): tab 1 tổng hợp các cách truy cập; tab 2 giải thích endpoint, collection, tham số và sự khác nhau giữa QR2 và QR3.
- [Google Sheets giải thích 51 cột SIA2](https://docs.google.com/spreadsheets/d/12FD_IZEMETIN4w_NXKSjFKmVc1zXG5vyF2Z62BftGGE/edit): bản chuyển đổi từ `wise0855_qr2_giai_thich_cot.xlsx`, lưu trong thư mục ChatGPT trên Drive. Bảng có đơn vị, ví dụ từ bản ghi đầu và lưu ý; 14 cột ưu tiên được tô xanh lá nhạt và đánh dấu “Có” trong cột “Ưu tiên 3/11”.

## Chạy lại truy vấn

Ví dụ dưới đây chạy trong PowerShell tại thư mục gốc repo và lưu phản hồi vào `data/`, nơi dành cho dữ liệu cục bộ theo README.

Tọa độ WISE 0855 từ đề bài:

- RA: `08h55m10.831s` ≈ `133.79513°`.
- Dec: `−07°14′42.53″` ≈ `−7.24515°`.
- Vùng tìm kiếm: hình tròn bán kính `0.05°` = 3 phút cung, đường kính `0.1°`.

### QR2

```powershell
curl.exe -L "https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_qr2&POS=circle+133.79513+-7.24515+0.05&RESPONSEFORMAT=HTML" -o data/wise0855-qr2.html
Start-Process .\data\wise0855-qr2.html
```

### QR3

```powershell
curl.exe -L "https://irsa.ipac.caltech.edu/SIA?COLLECTION=spherex_qr3&POS=circle+133.79513+-7.24515+0.05&RESPONSEFORMAT=HTML" -o data/wise0855-qr3.html
Start-Process .\data\wise0855-qr3.html
```

| Thành phần | Ý nghĩa |
| --- | --- |
| `curl.exe` | Gửi yêu cầu HTTP từ máy của mình. |
| `-L` | Theo chuyển hướng của máy chủ nếu có. |
| `/SIA` | Endpoint tìm kiếm ảnh SIA2 của IRSA. |
| `COLLECTION` | Chọn bộ dữ liệu cần tìm. |
| `POS=circle RA Dec radius` | Tìm ảnh có vùng phủ giao với hình tròn; các góc dùng đơn vị độ trong hệ ICRS. |
| Dấu `+` trong `POS` | Biểu diễn dấu cách giữa các giá trị trong URL. |
| `RESPONSEFORMAT=HTML` | Trả bảng metadata dưới dạng HTML để đọc bằng trình duyệt. |
| `-o` | Lưu phản hồi vào tệp được chỉ định. |

SIA2 trả danh sách sản phẩm phù hợp, chưa tải ảnh FITS. Dòng tiến trình `100%` của curl chỉ xác nhận việc tải phản hồi đã kết thúc; cần đọc nội dung để biết bảng có dữ liệu hoặc thông báo lỗi hay không.

## Các cột cần ưu tiên trong task ngày 3/11

| Cột | Ý nghĩa | Đơn vị hoặc cách dùng |
| --- | --- | --- |
| `obs_id` | Mã lần quan sát. | Một mã có thể có nhiều bản ghi detector; không dùng riêng mã này để khẳng định tệp là duy nhất. |
| `s_ra` | RA của tâm ảnh. | Độ, ICRS; không nhất thiết trùng RA mục tiêu. |
| `s_dec` | Dec của tâm ảnh. | Độ, ICRS; ảnh có thể bao phủ mục tiêu dù tâm nằm xa mục tiêu. |
| `energy_bandpassname` | Tên dải/detector, ví dụ `SPHEREx-D1`. | Dùng nhóm dữ liệu; cùng detector chưa bảo đảm cùng bước sóng tại vị trí mục tiêu vì LVF. |
| `em_min` | Giới hạn bước sóng nhỏ nhất của sản phẩm. | Mét; nhân với `10^6` để đổi sang micromet. |
| `em_max` | Giới hạn bước sóng lớn nhất của sản phẩm. | Mét; không phải bước sóng của mọi pixel trong ảnh. |
| `t_min` | Thời điểm bắt đầu quan sát. | MJD, đơn vị ngày; cần đổi thành ngày giờ khi hiển thị. |
| `t_max` | Thời điểm kết thúc quan sát. | MJD, đơn vị ngày; khác ngày công bố dữ liệu. |
| `access_url` | URL truy cập tệp của bản ghi. | Đầu vào để tải ảnh hoặc yêu cầu cutout. |
| `s_region` | Vùng trời được ảnh bao phủ. | Hình học theo ICRS; dùng kiểm tra footprint. |

Các cột bổ sung hữu ích cho backend:

- `obs_collection`: lưu release của sản phẩm, tránh nhầm hoặc trộn QR2 với QR3.
- `access_format`: định dạng tệp, ví dụ `image/fits`.
- `s_fov`: kích thước góc ước lượng của vùng ảnh; khác bán kính tìm kiếm trong `POS` và khác kích thước cutout.
- `cloud_access`: thông tin truy cập bản cloud, có thể dùng cho phương án dự phòng.

## Từ kết quả SIA2 đến ảnh cho pipeline

1. Chọn các bản ghi phủ lên vùng cần xem; kiểm tra release, detector và thời gian.
2. Lấy `access_url` của bản ghi.
3. Với URL FITS lưu tại IRSA, yêu cầu cutout bằng tham số `center=RA,Dec` và `size` theo độ.
4. Chuyển cutout và metadata cho pipeline xử lý ảnh; Khôi phụ trách lấy dữ liệu, Hữu Hoàng phụ trách xử lý ảnh.

Mẫu URL sau chỉ minh họa thao tác, cần thay `ACCESS_URL` bằng URL thật:

```text
ACCESS_URL?center=133.79513,-7.24515&size=0.05
```

`size` thuộc dịch vụ cutout, không phải tham số của endpoint `/SIA`. Nếu URL đã có query string, cần nối tham số đúng cách. Không tải nguyên tệp FITS nếu công việc chỉ cần vùng cắt nhỏ.

## Những lưu ý khi tích hợp

- QR2/QR3 là phiên bản xử lý và hiệu chuẩn, không phải số thứ tự lần quét bầu trời. Dùng `t_min`/`t_max` để xác định thời gian chụp.
- QR3 trả rỗng cho truy vấn đã thử chưa đủ để kết luận mục tiêu không có ảnh SPHEREx; kiểm tra collection, vùng phủ, thời gian và Data Explorer.
- Dữ liệu nạp hằng tuần; SIA2 có thể chậm khoảng một ngày so với thư mục hoặc Data Explorer.
- Không dùng `TARGET=WISE 0855` thay cho tìm theo vị trí một cách mặc định: `target_name` của khảo sát có thể là tên trường quan sát.
- Chọn ảnh so sánh và nhóm khung theo quy tắc khoa học do Nguyên thống nhất. Khi so độ sáng giữa QR2 và QR3 cần xử lý khác biệt hiệu chuẩn.
- Khi tạo cache, lưu rõ collection, tọa độ, kích thước vùng và các điều kiện lọc; cần cơ chế làm mới để nhận dữ liệu mới.

## Nguồn chính thức

- [SPHEREx Data Access](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/)
- [IRSA SIA2 và các tham số](https://irsa.ipac.caltech.edu/ibe/sia.html)
- [SPHEREx Quick Release Overview](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_qr.html)
- [SPHEREx Data Products](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/)

## Cách người nhận sử dụng

Khôi có thể dùng lệnh mẫu và bảng cột để xây dựng phần truy vấn, tải cutout và lưu metadata. Hữu Hoàng có thể dùng `access_url`, detector, thời gian và footprint để kiểm tra đầu vào trước khi xử lý ảnh. Các nội dung API chi tiết và toàn bộ 51 cột nằm trong Google Docs và Google Sheets được liên kết tại mục Tài liệu bàn giao.
