# Bàn giao giữa các vai trò

Một phần bàn giao cần giúp người nhận chạy được trên máy mình và biết giới hạn
của kết quả. Gửi link nhánh hoặc PR cùng commit cụ thể, đường dẫn file,
lệnh chạy, đầu vào mẫu, kết quả dự kiến và cách xử lý khi thiếu dữ liệu.

## Luồng công việc

| Người phụ trách | Nhận gì | Giao gì và cho ai |
| --- | --- | --- |
| Khôi | Tên hoặc tọa độ, detector, kích thước cutout | Dữ liệu quan sát, tọa độ có epoch, FITS và manifest cho Hữu Hoàng, Nguyên, Đông |
| Hữu Hoàng | Cutout và metadata của Khôi | Hàm xử lý ảnh, PNG, ảnh hiệu, grid/norm và vị trí pixel cho Đông; dữ liệu cần đo cho Nguyên |
| Nguyên | FITS, tọa độ dự đoán và thông tin chất lượng ảnh | Hàm/bảng photometry và astrometry có đơn vị, sai số, giới hạn khoa học cho Đông và Thạch |
| Đông | Hàm Python của ba bạn và hợp đồng wiki | Model/OpenAPI, JSON mẫu, API và lỗi cho Duy Hoàng, Thạch |
| Duy Hoàng | API, JSON/PNG mẫu, thông tin UI | Viewer, kiểm thử, CI, cách chạy và URL frontend cho Thạch/cả nhóm |
| Thạch | Viewer, metadata, bảng đo và kết luận khoa học | Giao diện thống nhất, biểu đồ, điều phối, nội dung trình bày cho nhóm |

Theo vòng dự phòng hiện tại, Đông hỗ trợ Duy Hoàng và Khôi. Tham khảo trang
vai trò trên wiki cho vòng đầy đủ. Người hỗ trợ cần được cung cấp ví dụ tái hiện
và đầu vào nhỏ để có thể tiếp nhận phần việc.

## Giao hàm Python

Ghi tên module import được, chữ ký hàm theo hợp đồng, đơn vị từng tham số,
cấu trúc trả về và lỗi có thể phát sinh. Dùng đường dẫn có thể cấu hình,
đóng FITS sau khi đọc và nêu rõ hàm nào gọi mạng.
Chế độ fixture đọc dữ liệu cục bộ theo quy ước, kiểm thử được khi mất mạng.

Chữ ký resolve/find_frames/build_frames/photometry/astrometry nằm ở mục 6
của hợp đồng wiki. Liên kết tới đó để tránh duy trì nhiều bản khác nhau.
Notebook có thể dùng để học và tái hiện, còn hàm người khác import cần được
đóng gói theo cấu trúc repo và Issue đang giao.

## Giao dữ liệu và ảnh

Manifest cần giữ nguồn quan sát, release, detector, thời gian, đường dẫn file,
đơn vị và thông tin tọa độ/epoch cần thiết. Ghi ngày truy vấn và tiêu chí chọn
dữ liệu để người nhận hiểu tập ảnh bao phủ khoảng thời gian nào.
Chuyển FITS thật qua thư mục cục bộ/drive được repo quy định.

PNG cần đi kèm kích thước, lưới, thang hiển thị và quy ước pixel theo hợp đồng.
Kiểm tra ảnh và predicted_px đã lật y nhất quán, nguồn đứng yên căn đúng,
vùng thiếu dữ liệu được biểu diễn rõ. Người làm ảnh bàn giao thông tin flags,
người làm khoa học xác nhận ý nghĩa các phép đo và ảnh hiệu.

Ghi rõ thứ đã được xác nhận. Tải được cutout chưa xác nhận mục tiêu đã được
nhận diện. Frame PNG tải được chưa xác nhận phép đo vị trí hoặc độ sáng.
Dữ liệu tổng hợp để thử UI cần được ghi nhãn trong tài liệu/mode theo hợp đồng.

## Giao API và frontend

Đông giao địa chỉ backend, DATA_MODE, phiên bản schema, ví dụ request/response,
cách mở ảnh, mã lỗi và cấu hình CORS. Duy Hoàng/Thạch dùng cùng JSON mẫu cho
MSW, kiểm tra schema và kiểu frontend để phát hiện lệch trường.

Kiểm tra trên máy người nhận bằng chế độ fixture trước khi nối dữ liệu thật.
Ghi một lượt thành công và một lượt lỗi cho endpoint được sửa.
Đối chiếu nhãn mock, thứ tự thời gian, đơn vị, PNG/overlay và trường hợp chỉ
có một frame. Kết quả nghiệm thu khoa học cần Nguyên xác nhận.

## Mẫu bàn giao trong Issue hoặc PR

```text
Issue và phạm vi
Nhánh / commit / PR
File hoặc module người nhận dùng
Người nhận và bước họ cần làm tiếp
Chế độ dữ liệu và biến môi trường cần đặt
Lệnh chạy và bộ đầu vào mẫu
Kết quả dự kiến
Lệnh kiểm tra đã chạy và kết quả
Đã kiểm chứng bằng fixture / dữ liệu thật / xác nhận khoa học
Giới hạn, lỗi còn tồn tại và phụ thuộc chưa nhận được
Link drive hoặc artifact nếu có dữ liệu thật
```

## Điều kiện xác nhận hoàn thành

Đối chiếu từng dòng Done when của Issue. Chỉ ghi đã đạt những tiêu chí có
bằng chứng. Nếu cần FE build, CI hoặc người khác kiểm tra, giữ các dòng đó
ở trạng thái chờ cho tới khi đã có kết quả.

Với Issue #14, backend pass test và JSON hợp lệ là đầu vào bàn giao.
Tiêu chí của toàn hợp đồng trên wiki còn có frontend build từ OpenAPI,
schema check trong CI và kiểm tra overlay. Ghi riêng tình trạng các tiêu chí
này để nhóm biết bước tiếp theo.

Nguồn gồm [hợp đồng wiki](https://github.com/MINIONS-WORKFORCE/Human-Binoculars/wiki/The-API-contract),
[hướng dẫn FE](../../shared/api-contract/frontend-guide.md) và
[mẫu PR](../../.github/pull_request_template.md).
