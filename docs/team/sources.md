# Nguồn công việc và thay đổi hợp đồng

Mỗi loại thông tin có một nơi quản lý. Bảng này giúp nhóm đối chiếu khi
Issue, wiki, schema và tài liệu cũ mô tả khác nhau.

| Cần biết gì | Tra ở đâu |
| --- | --- |
| Hôm nay làm gì, ai nhận, hạn và Done when | GitHub Issue được giao, cùng bình luận cập nhật |
| Endpoint, trường JSON, đơn vị, lỗi, chữ ký hàm bàn giao | Trang The API contract trên wiki |
| Vai trò, kiến thức chuyên môn, vòng hỗ trợ | Wiki theo vai trò và tài liệu DOCX ngày 8/11 |
| Cách clone, tạo nhánh, đặt code, quản lý dữ liệu/dependency | README gốc và mẫu Issue/PR |
| Backend ở một commit đang thực hiện gì | Code, Pydantic models, test và /openapi.json của đúng commit |
| FE thử mẫu nào | api_samples/ và hướng dẫn FE của cùng phiên bản |
| Bối cảnh trước khi đổi cách giao task | Các ghi chú ngày 3–7/11 và bản SRS/QA snapshot |

Issue quyết định phạm vi việc, còn hợp đồng quyết định giao diện giữa các bên.
Nếu Issue yêu cầu đổi giao diện, cần đi qua quy trình thay đổi hợp đồng.
Khi code lệch hợp đồng, ghi nhận sự khác nhau và sửa qua nhánh task/PR.

## Mâu thuẫn đã biết ngày 9 tháng 11

Repo hiện ở MINIONS-WORKFORCE/Human-Binoculars. Các địa chỉ cũ trong tài liệu
có thể chuyển hướng, nhưng link bàn giao mới nên dùng địa chỉ hiện tại.

docs/SRS-MVP.md và QA-matrix.md là bản chụp của một kế hoạch trước đó.
Chúng có API_MODE, các route /files và cách đặt trường khác với wiki 7 endpoint.
Issue #14 yêu cầu DATA_MODE=fixture và bộ endpoint wiki. Tác vụ này căn cứ
Issue và hợp đồng wiki mới. Khi dùng tiêu chí QA từ snapshot cần đối chiếu
lại phần giao diện đã đổi.

API 0.1 trên wiki và schema Day 6 v0.2 là hai đời hợp đồng khác nhau.
Tên phiên bản nhỏ hơn không tự biểu thị tài liệu cũ hơn.
Các ghi chú Day 6 dùng app.legacy_main; hướng dẫn hiện tại dùng app.main.
Đối chiếu commit và tên schema khi review để tránh nối nhầm hai đời API.

SECURITY.md hiện còn nội dung mẫu với các phiên bản minh họa.
Những mục đó chưa phải danh sách phiên bản backend đã được nhóm công bố.
Quy định bảo vệ secret và dữ liệu cục bộ lấy từ README/.gitignore hiện tại.

## Thay đổi API theo wiki

1. Mở Discussions theo mẫu tiêu đề [API] Đổi …, nêu endpoint/trường cần sửa
   và tác động tới bên nhận.
2. Gắn người sở hữu API là Đông và các bên sử dụng endpoint.
3. Sau khi được thống nhất theo wiki, cập nhật hợp đồng, api_version và
   lịch sử thay đổi.
4. Cập nhật đồng thời Pydantic model, JSON mẫu, OpenAPI và kiểm thử liên quan.
   Frontend cập nhật kiểu sinh từ schema và MSW cùng phiên bản.
5. Áp dụng mốc khóa hợp đồng theo wiki. Bản đọc ngày 9/11 ghi từ 12:00 ngày
   14/11 chỉ thêm trường, giữ các trường và tên đã chốt.

Quy trình này áp dụng khi thay đổi hợp đồng chung. Việc triển khai để khớp
hợp đồng đã thống nhất đi theo quy trình Issue và PR của repo.
Nếu mốc khóa hoặc người duyệt được nhóm sửa, cập nhật link quyết định và bản
hướng dẫn này cùng lúc.

## Đề xuất ghi quyết định kỹ thuật

Với thay đổi lớn như chuyển sang job nền, đổi cách nhóm ảnh hoặc đổi schema,
để lại một ghi chú ngắn trong Discussion/Issue liên quan gồm bối cảnh,
lựa chọn được chốt, người tham gia, phiên bản và tác động lên các module.
Liên kết quyết định trong PR để người đến sau tìm được lý do.

Đây là đề xuất ghi nhận, còn nội dung kỹ thuật và quyền merge/review vẫn theo
quy định đã có của nhóm. Hạn chế sao chép đầy đủ bảng schema sang nhiều file;
hướng dẫn sử dụng nên trỏ tới hợp đồng và chỉ thêm ví dụ cần cho người đọc.

Nguồn gồm [Issues](https://github.com/MINIONS-WORKFORCE/Human-Binoculars/issues),
[hợp đồng](https://github.com/MINIONS-WORKFORCE/Human-Binoculars/wiki/The-API-contract),
[wiki vai trò](https://github.com/MINIONS-WORKFORCE/Human-Binoculars/wiki),
[README](../../README.md) và [bản SRS](../SRS-MVP.md).
