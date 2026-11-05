# Bảng tra flags

Bảng dưới đây chọn **14 flags theo yêu cầu bài luyện**. Đã đối chiếu với **Explanatory Supplement v2.0, 25/08/2026, Table 16 trang 31–33**. Tài liệu hiện hành có thêm flags, nên 14 mục này không phải danh sách đầy đủ của mọi release. URL PDF ổn định có thể đổi phiên bản; bản PDF và SHA256 đã lưu trong data/nguyen/official-survey-audit/. Nguồn: https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp_QR.pdf

| Tên          | Bit | Giá trị mask | Nghĩa ngắn                                                                             |
| ------------ | --: | -----------: | -------------------------------------------------------------------------------------- |
| TRANSIENT    |   0 |            1 | Sự kiện nhất thời                                                                      |
| OVERFLOW     |   1 |            2 | Vượt ngưỡng trong xử lý SUR; không đồng nhất với full-well                             |
| SUR_ERROR    |   2 |            4 | Bit chksum_error; khi đi cùng TRANSIENT/OVERFLOW có thể chỉ sự kiện sớm trong exposure |
| NONFUNC      |   6 |           64 | Pixel hỏng                                                                             |
| DICHROIC     |   7 |          128 | Hiệu suất dichroic thấp                                                                |
| MISSING_DATA |   9 |          512 | Thiếu dữ liệu                                                                          |
| HOT          |  10 |         1024 | Pixel nóng                                                                             |
| COLD         |  11 |         2048 | Tín hiệu thấp bất thường                                                               |
| FULLSAMPLE   |  12 |         4096 | Có lịch sử mẫu đầy đủ, cờ thông tin; cần kiểm hướng dẫn khoa học trước khi dùng pixel  |
| PHANMISS     |  14 |        16384 | Thiếu hiệu chỉnh phantom                                                               |
| NONLINEAR    |  15 |        32768 | Phi tuyến chưa sửa được                                                                |
| PERSIST      |  17 |       131072 | Điện tích lưu ảnh                                                                      |
| OUTLIER      |  19 |       524288 | Pixel ngoại lai                                                                        |
| SOURCE       |  21 |      2097152 | Vị trí nguồn đã biết                                                                   |

Đọc `MP_*` từ header `FLAGS` của chính FITS đang dùng. Số trong `MP_*` là **vị trí bit**, nên phải dùng `1 << bit`, không dùng trực tiếp nó làm mask. Ví dụ `2097154` có SOURCE và OVERFLOW. Hàm `decode_flags` trong `science.py` trả cả phần bit chưa biết để tránh âm thầm bỏ qua.

Không che mọi pixel chỉ vì `flags != 0`: SOURCE đánh dấu nguồn, không tự nó là lỗi detector. Với mặt nạ nền thì loại SOURCE là một mục tiêu khác. Mặt nạ cho đo nguồn và mặt nạ cho ước lượng nền cần tách riêng.

OVERFLOW là ngưỡng trong xử lý SUR, không đồng nghĩa chính xác với full-well saturation. Không suy ra “chưa bão hòa” chỉ từ độ sáng J/H/K; kiểm tra flags và hình dạng PSF của ảnh thật.

## Khác biệt với dữ liệu và công cụ mới

Tài liệu Spectrophotometry hiện hành còn liệt kê các bit ảnh CROSSTALK (20), GHOST (22), GHOST_FPA (23, chưa xuất hiện theo bảng), GHOST_EXT (24), STREAK (25), BLOOM (26), SNOWBALL (27), HALO (28), SATELLITE_HALO (29). Bit 32 CONTAINS_BAD_PIXEL và bit 33 FIT_ERROR là cờ đầu ra phép đo phổ, không phải pixel FLAGS của ảnh. Không ép dữ liệu phép đo phổ vào số nguyên 32 bit.

Nguồn cập nhật: https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html

**Bàn giao cho Hữu Hoàng:** chọn mặt nạ theo mục đích và phiên bản; giữ lại mask/weight/coverage sau reproject. Không nội suy bilinear số nguyên bitmask. Những tên bit mới hoặc không có trong bảng phải xuất hiện trong báo cáo kiểm tra, không coi là dữ liệu tốt mặc định.

**Trạng thái cập nhật:** đã đọc MP\_\* từ FITS Barnard D2 tải riêng và đối chiếu các cờ tại pixel lõi. Giá trị 2097158 gồm OVERFLOW + SUR_ERROR + SOURCE; IMAGE và VARIANCE tại đó là NaN. Xem reports/BARNARD-D2-QA.md. Chưa kiểm toàn bộ fixture chính thức của Khôi; chưa xác nhận mọi mục tiêu hoặc release.
