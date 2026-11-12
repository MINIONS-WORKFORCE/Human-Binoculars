# QA matrix – nghiệm thu MVP

> Bản chụp ngày 9/11/2026. Kết quả được điền trực tiếp trong tab QA matrix của [tài liệu SRS](https://claude.ai/artifact/KvqX1JdNRR63C4STr8v9Dp); file này chỉ để tra cứu. Đi kèm [SRS-MVP.md](SRS-MVP.md).

Mỗi dòng là một phép thử có kết quả đạt hoặc không đạt, lấy từ mục 9 và mục 7 của SRS. Chạy trên một máy không phải máy của người viết code. Khi chạy, ghi vào cột Ghi chú: máy nào, ngày nào, commit nào. Nếu không đạt, mở issue cho người sở hữu và dán link issue vào Ghi chú.

**Luật Go/No-Go (12/11):** Go khi mọi dòng Must đều Đạt. Một dòng Must Không đạt hoặc Bị chặn thì No-Go cho tới khi sửa xong. Dòng Should không chặn Go.

| ID | Phép thử | Mức | Đạt khi | Người chạy | Kết quả | Ghi chú |
| --- | --- | --- | --- | --- | --- | --- |
| QA-01 | Nhập `133.7951 -7.2451`, sau đó nhập `08h55m10.831s -07d14m42.53s` | Must | Hai lần nhập hiện cùng RA/Dec | Thạch | Chưa chạy |  |
| QA-02 | Nhập tên `Barnard's Star` | Must | Ra đúng mục tiêu Barnard | Thạch | Chưa chạy |  |
| QA-03 | Đổi FOV, detector, release rồi tải lại trang | Must | URL đổi theo; tải lại vẫn giữ nguyên cả ba | Thạch | Chưa chạy |  |
| QA-04 | Bấm lần lượt 5 nút mục tiêu | Must | Mỗi mục tiêu nằm trong khung, kể cả Barnard | Nguyên | Chưa chạy |  |
| QA-05 | WISE 0855, D6 | Must | Ít nhất 2 khung khác đợt; mỗi khung ghi ngày và detector; sao nền dịch không quá 1 pixel | Nguyên | Chưa chạy |  |
| QA-06 | Barnard, so hai đợt | Must | Dịch chuyển khớp bảng kỳ vọng, trong sai số Nguyên đã chốt | Nguyên | Chưa chạy |  |
| QA-07 | Epsilon Indi B với FOV mặc định | Must | Khung tải được, đúng nguồn B | Nguyên | Chưa chạy |  |
| QA-08 | RW Aurigae | Must | Khung tải được, ghi đủ nguồn ảnh | Thạch | Chưa chạy |  |
| QA-09 | R Draconis | Must | Khung tải được. Nếu có pixel bão hoà thì hiện `SATURATED` (phần này là Should) | Thạch | Chưa chạy |  |
| QA-10 | Một toạ độ ngoài 5 mục tiêu | Must | Ra khung hoặc `NO_DATA` trong vòng 120 giây; sau 30 giây hiện báo chậm | Thạch | Chưa chạy |  |
| QA-11 | Ngắt mạng tới IRSA | Must | 5 mục tiêu vẫn chạy; vị trí mới báo 502 hoặc 504 kèm nút thử lại | Khôi | Chưa chạy |  |
| QA-12 | Nhập `abc` vào ô vị trí | Must | Lỗi 422, thông báo nằm cạnh đúng ô đó | Thạch | Chưa chạy |  |
| QA-13 | Test hợp đồng tự động, chế độ mock và chế độ thật | Must | Cả hai đều khớp `openapi.yaml` v1 | Đông | Chưa chạy |  |
| QA-14 | So `grid` và `display` giữa các khung | Must | Mọi khung cùng kích thước và cùng `vmin`/`vmax` | Hữu Hoàng | Chưa chạy |  |
| QA-15 | Chạy backend với `API_MODE=mock` | Must | Trên ảnh có nhãn mock | Thạch | Chưa chạy |  |
| QA-16 | Giao diện ở bề rộng 390px và chỉ dùng bàn phím | Must | Không cuộn ngang; Tab đến được mọi nút; nút cao ít nhất 44px; toàn bộ chữ bằng tiếng Anh | Thạch | Chưa chạy |  |
| QA-17 | Mỗi người chạy module của người mình đỡ, chỉ dùng README | Must | Cả 6 module chạy được | Cả nhóm | Chưa chạy |  |
| QA-18 | Đo thời gian trả về của một mục tiêu dựng sẵn | Must | Dưới 2 giây | Đông | Chưa chạy |  |
| QA-19 | Bật ảnh hiệu với Barnard | Should | Thấy một cặp sáng–tối | Hữu Hoàng | Đạt | Đã kiểm thử e2e; ảnh hiệu hiển thị cặp cực sáng–tối do chuyển động riêng, kèm câu kết luận khoa học tiếng Anh cho từng mục tiêu |
| QA-20 | Mở link công khai ở tab ẩn danh trên máy khác | Should | Trang chạy và 5 mục tiêu đều ra khung | Duy Hoàng | Chưa chạy |  |
