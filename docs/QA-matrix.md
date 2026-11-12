# QA matrix – nghiệm thu MVP

> Bản chụp ngày 9/11/2026, **cập nhật ngày 12/11/2026 theo hợp đồng API 0.1** (xem [SRS-MVP.md](SRS-MVP.md), mục 5 và 9). Các phép thử cũ nhắc đến `NO_DATA`, lỗi 422, 502/504, release QR2/QR3 và `API_MODE=mock` đã được viết lại hoặc bỏ vì hợp đồng 0.1 không có chúng. Kết quả chính thức được điền trong tab QA matrix của tài liệu SRS trực tuyến; file này để tra cứu trong repo.

Mỗi dòng là một phép thử có kết quả rõ ràng, lấy từ mục 9 và mục 7 của SRS. Phép thử chính thức chạy trên một máy không phải máy của người viết code. Khi chạy, ghi vào cột Ghi chú: máy nào, ngày nào, commit nào. Nếu không đạt, mở issue cho người sở hữu và dán link issue vào Ghi chú.

**Các giá trị của cột Kết quả:**

| Giá trị | Nghĩa |
| --- | --- |
| Đạt | Người chạy đã thử tay hoặc chạy test trên máy không phải máy người viết code |
| Đạt (tự động) | Test tự động đạt trên máy của Thạch (12/11), bản build mock hoặc backend fixture. **Chưa tính vào Go**; người chạy phải lặp lại trên máy khác |
| Một phần | Một phần tiêu chí đạt, phần còn lại ghi trong Ghi chú |
| Không đạt | Đã chạy và không đạt, hoặc tính năng chưa có |
| Bị chặn | Chưa chạy được vì thiếu dữ liệu, quyền truy cập hoặc phần của người khác |
| Chưa chạy | Chưa ai chạy |

**Luật Go/No-Go (12/11):** Go khi mọi dòng Must đều Đạt. Một dòng Must Không đạt hoặc Bị chặn thì No-Go cho tới khi sửa xong. Dòng "Đạt (tự động)" chưa đủ để Go. Dòng Should không chặn Go.

**Môi trường chạy tự động ngày 12/11:** Windows 11, Node 24.14, Microsoft Edge (`PW_CHANNEL=msedge`), nhánh `thach/integrate-frontend`. Lệnh: `npm run typecheck`, `npm run lint`, `npm test`, `npm run e2e` trong `frontend/`; `npm test` ở thư mục gốc; `pytest members` và `members/dong/scripts/validate_api_samples.py` bằng `.venv`. Mọi lần chạy dùng mock MSW hoặc mẫu tổng hợp của backend fixture; máy này chưa có gói FITS fixture.

| ID | Phép thử | Mức | Đạt khi | Người chạy | Kết quả | Ghi chú |
| --- | --- | --- | --- | --- | --- | --- |
| QA-01 | Nhập `133.7951 -7.2451`, sau đó nhập `08h55m10.831s -07d14m42.53s` | Must | Hai lần nhập hiện cùng RA/Dec | Thạch | Đạt (tự động) | `parseCoordinates` cho 133,7951°/−7,2451° và 133,79513°/−7,24515°: trùng khi làm tròn 4 chữ số (lệch ≈ 0,2″). Test: `coords/*.test.ts`, `e2e/target-input.spec.ts` |
| QA-02 | Nhập tên `Barnard's Star` | Must | Ra đúng mục tiêu Barnard | Thạch | Đạt (tự động) | Nhận ngoại tuyến (`coords/locate.test.ts`); `/api/resolve` mẫu trả `target_key=barnard` (`api/client.test.ts`); e2e nạp Barnard khi mở trang |
| QA-03 | Đổi detector và FOV rồi tải lại trang | Must | URL đổi theo; tải lại vẫn giữ nguyên | Thạch | Không đạt | FR-03 chưa làm: frontend chưa ghi vị trí, FOV, detector vào URL. Chưa có ô chọn FOV (FR-02). Release không còn là tham số |
| QA-04 | Bấm lần lượt 5 nút mục tiêu | Must | Mỗi mục tiêu hiện đủ khung kèm dấu thập; panel photometry không báo lỗi | Nguyên | Đạt (tự động) | `e2e/science.spec.ts` bấm đủ 5 nút trên mock: 3 khung mỗi mục tiêu. Dấu thập đúng ở `predicted_px` (`e2e/blink.spec.ts`). Chưa chạy trên cutout thật |
| QA-05 | WISE 0855, D6 | Must | Ít nhất 2 khung khác thời điểm; mỗi khung ghi ngày và detector; sao nền dịch không quá 1 pixel | Nguyên | Bị chặn | Mẫu tổng hợp có 3 khung và ghi ngày, nhưng phần "sao nền" cần cutout thật (gói FITS fixture hoặc dữ liệu live) |
| QA-06 | Barnard, so các khung | Must | Dịch chuyển khớp bảng kỳ vọng, trong sai số Nguyên đã chốt | Nguyên | Bị chặn | Cần cutout thật; sai số cho phép chưa được chốt |
| QA-07 | Epsilon Indi B (`target_key=epsindib`) | Must | Khung tải được, đúng nguồn B | Nguyên | Bị chặn | Mẫu tổng hợp tải được nhưng không phân biệt A và B; cần cutout thật |
| QA-08 | RW Aurigae (`target_key=rwaur`) | Must | Khung tải được | Thạch | Đạt (tự động) | Chỉ phần tải khung trên mock. Hợp đồng 0.1 không có trường danh sách ảnh nguồn nên tiêu chí "ghi đủ nguồn ảnh" của bản cũ được bỏ |
| QA-09 | R Draconis (`target_key=rdra`) | Must | Khung tải được; panel photometry vẽ 6 điểm D1–D6 và bảng 6 dòng | Thạch | Đạt (tự động) | `e2e/science.spec.ts`. Nếu API trả `SATURATION_POSSIBLE` thì viewer in ra trong dòng `warnings` (phần cảnh báo là Should) |
| QA-10 | Một toạ độ ngoài 5 mục tiêu, gõ tay | Must | Ra khung, hoặc lỗi/cảnh báo rõ ràng (`NO_FRAMES`, `FEW_FRAMES`) | Thạch | Một phần | Mock và mẫu tổng hợp trả 3 khung cho mọi toạ độ hợp lệ (`e2e/target-input.spec.ts`), không có `predicted_px`. Nhánh `NO_FRAMES` (HTTP 404, gói FITS không phủ lưới) chưa chạy. Báo "đang chậm" sau 30 giây của bản cũ không áp dụng cho API đồng bộ |
| QA-11 | Mất mạng | Must | 5 mục tiêu vẫn chạy từ fixture; chỉ bản đồ Aladin và lớp Gaia mất | Khôi | Chưa chạy | Cần gói FITS fixture cục bộ. Với mẫu tổng hợp và mock, viewer và biểu đồ không gọi ra ngoài |
| QA-12 | Nhập `400 10` và `Planet X` vào ô vị trí | Must | Thông báo nằm ngay dưới ô nhập, nêu đúng lý do; ô được đánh dấu `aria-invalid` | Thạch | Đạt (tự động) | `e2e/target-input.spec.ts`. Đây là kiểm tra ở frontend trước khi gọi API. Mã `BAD_COORDS`/`BAD_PARAM` (HTTP 400) từ API được test ở `src/api/client.test.ts`, nhưng giao diện hiện chỉ hiện câu chung, chưa chỉ vào đúng ô |
| QA-13 | Test hợp đồng tự động, mock và fixture | Must | Cả hai khớp `openapi.yaml` | Đông | Đạt (tự động) | `frontend/src/mocks/samples.test.ts` (159 test frontend đạt), `validate_api_samples.py` (6 mẫu đạt), `pytest members` (72 đạt, 1 bỏ qua), `npm run gen:types` không đổi `schema.d.ts` |
| QA-14 | So `grid`, `norm` và kích thước PNG giữa các khung | Must | Cả phản hồi có một `grid` và một `norm`; mọi PNG cùng kích thước | Hữu Hoàng | Chưa chạy | Hợp đồng 0.1 đặt `grid` và `norm` ở mức phản hồi. Cần so kích thước PNG thật khi có cutout thật |
| QA-15 | Dữ liệu tổng hợp luôn có nhãn | Must | Mock: huy hiệu "Mock API"; fixture: PNG ghi `FIX`; biểu đồ photometry có dòng "Fixture data" | Thạch | Đạt (tự động) | Dòng ghi chú dưới biểu đồ đọc `mode` từ `/api/health` và được `e2e/science.spec.ts` kiểm trên mock. Chạy tay với backend fixture thật (`VITE_USE_MOCK=false`) thấy `FIX` trên ảnh; chưa chạy lại tay để xem dòng ghi chú ở chế độ này |
| QA-16 | Giao diện ở bề rộng 390px và chỉ dùng bàn phím | Must | Không cuộn ngang; Tab đến được mọi nút; nút cao ít nhất 44px; toàn bộ chữ bằng tiếng Anh | Thạch | Một phần | Không cuộn ngang ở 390px: Đạt (tự động, `e2e/science.spec.ts`). Tab, chiều cao nút 44px và chữ tiếng Anh chưa kiểm toàn trang; các nút nhỏ của Aladin Lite do thư viện vẽ |
| QA-17 | Mỗi người chạy module của người mình đỡ, chỉ dùng README | Must | Cả 6 module chạy được | Cả nhóm | Chưa chạy |  |
| QA-18 | Đo thời gian trả về của `/api/frames` ở fixture | Must | Dưới 2 giây | Đông | Chưa chạy | Log của backend có `duration_ms` cho từng request |
| QA-19 | Bật ảnh hiệu với Barnard | Should | Thấy một cặp sáng–tối | Hữu Hoàng | Chưa chạy | Nút "Difference" đã có (`e2e/blink.spec.ts` chuyển sang ảnh hiệu); ảnh mẫu là tổng hợp, cần ảnh thật để thấy cặp sáng–tối |
| QA-20 | Mở link công khai ở tab ẩn danh trên máy khác | Should | Trang chạy và 5 mục tiêu đều ra khung | Duy Hoàng | Chưa chạy | Chưa có link công khai (FR-13) |
| QA-21 | Panel photometry: biểu đồ, bảng, bộ lọc | Could | Đường cong ánh sáng và phổ cùng một dữ liệu; lọc detector đổi số dòng; mục tiêu không có số đo thì hiện thông báo thay vì biểu đồ trống | Thạch | Đạt (tự động) | `e2e/science.spec.ts`; quy tắc giới hạn trên 3σ và điểm `flagged` nằm trong `shared/charts/photometry.test.js` (218 test JS ở thư mục gốc đạt). Mock và backend fixture đều chỉ có số đo cho R Draconis |
| QA-22 | Bản đồ Aladin theo vị trí; lớp sao Gaia giả | Could | Bản đồ nằm cạnh viewer, đổi lớp Gaia giữa ba lựa chọn; sao giả hiện không cần mạng | Thạch | Đạt (tự động) | `e2e/science.spec.ts` (chế độ "Synthetic stars"). Ảnh nền HiPS lấy từ CDS nên có thể xám khi mạng chậm |
| QA-23 | Lớp Gaia DR3 thật từ VizieR | Could | Hiện số nguồn Gaia trong khung nhìn của bản đồ | Thạch | Bị chặn | Trên máy của Thạch ngày 12/11, trình duyệt gọi `vizier.unistra.fr` (địa chỉ mặc định của Aladin Lite 3.8.2) và DNS không phân giải được; trang hiện đúng thông báo lỗi "Could not reach VizieR". Cần chạy trên mạng vào được CDS |
