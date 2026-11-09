# Làm việc từ GitHub Issue

Hướng dẫn này tổng hợp quy định trong README, mẫu Issue, mẫu PR và hợp đồng
wiki hiện tại. Công việc hằng ngày lấy từ Issue được giao. Lộ trình cũ dùng
để tra cứu bối cảnh. Các quy ước bổ sung được ghi rõ là đề xuất.

## Nhận việc

Đọc assignee, nội dung task, Done when, hạn bàn giao và người nhận. Đối chiếu
giao diện liên quan với hợp đồng wiki. Nếu dòng Owner trong mẫu còn tên người
tạo nhưng assignee và nội dung ghi người khác, xác nhận người chịu trách nhiệm
trong Issue trước khi coi đó là nhiệm vụ của mình.

Ghi tiến độ vào Issue thay vì chỉ nói trong chat. Tách rõ phần đã chạy trên máy,
phần đã push, PR đang chờ review và phần đã được người nhận kiểm tra.
Một task khác phụ thuộc vào bạn cần biết mẫu đầu vào nào đã dùng được.

## Tạo nhánh

README yêu cầu nhánh theo mẫu <thư mục thành viên>/<task>. Code thử riêng nằm
trong members/<tên>/, phần người khác import nằm trong shared/.

Trước khi đổi nhánh, xem git status. Khi working tree sạch, có thể dùng các
lệnh sau để bắt đầu từ main đã cập nhật.

```powershell
git status --short --branch
git switch main
git pull --ff-only origin main
git switch -c dong/issue-14-api-contract-fixture
```

Nếu còn thay đổi của task trước, lưu chúng trong commit phù hợp trên nhánh đó
hoặc dùng worktree riêng trước khi bắt đầu. Giữ các thay đổi cá nhân có chủ đích.
Nếu main đã có commit cục bộ khác remote khiến fast-forward thất bại, kiểm tra
lịch sử và phối hợp với người quản lý repo trước khi tích hợp.

**Đề xuất tên nhánh** là <tên>/issue-<số>-<việc>, ví dụ
khoi/issue-15-sia-cutouts. Số Issue giúp người nhận tìm lại phạm vi task.
Một người có thể có nhiều nhánh, nhưng mỗi nhánh cần mô tả được kết quả sẽ giao.

## Làm và kiểm tra

Chỉ mở rộng phạm vi khi cần để đạt Done when. Thay đổi giao diện dùng chung
theo quy trình [nguồn và hợp đồng](sources.md). Dùng JSON mẫu đã thống nhất khi
phần thật của đồng đội chưa sẵn sàng và ghi rõ dữ liệu nào là tổng hợp.

Chạy kiểm thử liên quan đến phần thay đổi. PR cần ghi lệnh đã chạy, kết quả,
chế độ dữ liệu và giới hạn kiểm chứng. Phân biệt test với dữ liệu giả,
test tải dữ liệu thật và việc xác nhận đúng về khoa học.

Đọc quy định của repo trước khi thêm dependency. Python cập nhật requirements.txt;
npm cập nhật package.json và package-lock.json. Báo thay đổi cho nhóm theo
checklist PR để người nhận cài cùng môi trường.

## Commit và push

Mỗi commit nên chứa một kết quả có thể review. Gộp các sửa nhỏ vào cùng phần
việc trước khi commit, theo cách nhóm đã trao đổi. Chọn các đường dẫn của task
khi stage và đọc staged diff trước khi ghi commit.

```powershell
git diff
git add -- members/dong/app/api_models.py
git diff --cached --stat
git diff --cached
git diff --cached --check
git commit -m "feat: define API fixture response models"
git push -u origin dong/issue-14-api-contract-fixture
```

Ví dụ trên chỉ stage một file; chọn thêm các file thực sự thuộc kết quả bàn giao.
Push nhánh task cần review. Repo hiện ở địa chỉ MINIONS-WORKFORCE/Human-Binoculars;
kiểm tra git remote -v nếu máy còn giữ địa chỉ trước khi đổi tên.

FITS, cutout thật, database, cache và .env nằm trong vùng lưu cục bộ được
gitignore hoặc team drive. Notebook cần xóa outputs theo README.
api_samples/ là ngoại lệ được Issue #14 và wiki yêu cầu để chia sẻ mẫu nhỏ,
tổng hợp. Ghi rõ tính chất mẫu và kiểm tra schema. Với ảnh quan sát cần chia sẻ,
dùng drive hoặc đính kèm PR theo README.

## Mở PR và bàn giao

Dùng mẫu PR của repo. Ghi vấn đề, hành vi sau thay đổi, cách chạy, bằng chứng
kiểm tra và phần còn cần đồng đội tích hợp. Liên kết Issue trong nội dung.

Chỉ dùng Closes #14 khi PR đáp ứng toàn bộ phạm vi đóng Issue #14. Nếu mới
giao model nhưng còn tiêu chí FE/CI chưa được kiểm tra, dùng Related to #14
và ghi rõ checklist còn lại. Push thành công chưa phải kết quả đã vào main.

README giao Duy Hoàng merge và yêu cầu main luôn chạy được. Sau review,
tác giả xử lý nhận xét, người nhận thử theo README và người merge kiểm tra
trạng thái các kiểm thử đang được cấu hình trong repo.
Số lượng reviewer hoặc cơ chế chặn merge chỉ coi là bắt buộc khi đã được
repo/nhóm chốt. Hợp đồng API có quy trình thảo luận riêng trên wiki.

## Khi bị chặn

README quy định bị chặn quá 30 phút thì mở Issue theo mẫu Blocked.
Liên kết với task gốc, ghi lỗi, cách tái hiện, điều đã thử, người cần hỗ trợ
và việc có thể chuyển sang làm. Việc chuyển sang lấy từ Issue/backlog hiện tại.
Đính kèm fixture hoặc mẫu giao diện sớm để phần phụ thuộc tiếp tục tiến triển.

Hạn từng Issue là mốc ưu tiên. README còn ghi bàn giao trước 22:30, vì vậy
task có hạn 21:00 phải được chuẩn bị để giao theo mốc sớm hơn.

Nguồn gồm [README](../../README.md), [mẫu task](../../.github/ISSUE_TEMPLATE/task.md),
[mẫu Blocked](../../.github/ISSUE_TEMPLATE/blocked.md) và
[mẫu PR](../../.github/pull_request_template.md).
