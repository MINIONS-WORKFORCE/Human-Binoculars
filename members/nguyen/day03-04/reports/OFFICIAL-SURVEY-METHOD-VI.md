# Phân loại survey SPHEREx theo tài liệu và header thật

## Kết quả kiểm chứng

- Đọc đủ **792 header exposure**, đại diện **1545 bản ghi QR2**, không còn lỗi tải header.
- Dùng HTTP Range từ IRSA và mirror AWS công khai; không tải toàn bộ ảnh phổ chỉ để đọc header.
- **1413 bản ghi có số survey suy ra theo quy tắc tài liệu; 132 bản ghi giữ chưa phân loại** do chính sách bảo thủ ở mốc chuyển giai đoạn.
- Survey 1: 685; Survey 2: 624; Survey 3: 0; Survey 4: 104. Số 0 chỉ nói về tập đã phân loại này, không phải toàn kho.
- Có **42 cặp dự báo giữa các survey suy ra**, chọn quan sát trung vị theo thời gian cho từng mục tiêu/detector/release/survey.
- Sai lệch lớn nhất giữa DATE-OBS trong header và t_min của metadata: 0.043400 giây, đều trong ngưỡng kiểm 2 giây.

## Căn cứ và cách áp dụng

Nguồn chính: [SPHEREx Explanatory Supplement](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp_QR.pdf), **v2.0 ngày 25/08/2026**, đã tải và đọc trực tiếp. Mục 1.4 trang 8–9 định nghĩa survey; Image Header Description trang 14 nhắc lại quy tắc. Phần diễn giải dùng SPS_PA_ECL, bảng header và FITS thật dùng SPS_EPA. SHA256 PDF được ghi trong manifest.json. Kết quả web trước đó hiển thị v1.3 đã được thay thế bằng đối chiếu này. [Trang Data Tools của nhiệm vụ](https://spherex.caltech.edu/page/data-tools) nêu ngày bắt đầu science survey là 01/05/2025.

Quy tắc: PA 0/180 độ trong pha 0–12,5 tháng tương ứng Survey 1/2; PA 0/180 trong pha 12,5–25 tháng tương ứng Survey 3/4. Thông tin planned boresight giống nhau ở sáu band của cùng OBSID nên dùng một header đã kiểm cho mỗi exposure/release, giữ URL và SHA256.

Đây là **nhãn suy ra bằng quy tắc chính thức**, không phải cột survey ID nguyên bản do archive cấp. Vì vậy cột tên derived_survey_number, không giả là nhãn lấy trực tiếp từ kho.

## Những lựa chọn bảo thủ được công bố rõ

- Chỉ xét dữ liệu có token all_sky và NON_SURVEY=false. all_sky,downlink vẫn có membership all_sky, nhưng giữ cờ gốc cho QA ảnh riêng.
- Đọc SPS_PA_ECL hoặc SPS_EPA; nếu cả hai có nhưng mâu thuẫn thì từ chối. Dung sai PA 0,1 độ là tham số của chương trình, được ghi rõ.
- Tài liệu nói 12,5 tháng nhưng nguồn đã kiểm ở đây chưa cho giờ UTC chuyển pha chính xác. **Để trống toàn bộ tháng 5/2026 là lựa chọn bảo thủ của chương trình, không phải lịch chuyển survey chính thức do IRSA công bố.** Không tự bịa ngày bằng cách làm tròn nửa tháng.
- Khoảng chắc chắn dùng cho pha đầu: 01/05/2025 đến trước 01/05/2026; pha sau: 01/06/2026 đến trước 01/05/2027. Đây là suy luận có công bố từ ngày bắt đầu science và quy tắc trong Supplement. Các ngày ngoài khoảng đó cần thêm thông tin pha có thẩm quyền.
- Không gán nhãn còn trống bằng ngưỡng 7 ngày, mã tuần, QR2/QR3 hoặc survey gần nhất.
- Cặp được xếp theo ngày chụp thật. Survey 1/2 không tự nói thứ tự trước/sau vì có thể nằm trong cùng pha thời gian.

## File dùng khi bàn giao

- reports/official-survey/survey_classification.csv: 1545 bản ghi với góc PA, thời gian, cờ, số survey suy ra/trạng thái và provenance header.
- reports/official-survey/expected_motion_between_surveys.csv: 42 cặp dự báo theo survey suy ra.
- reports/official-survey/manifest.json: SHA256 đầu vào và chính sách.
- data/nguyen/official-survey-audit/header-cache/: block header gốc và JSON trích xuất, chỉ lưu local/Drive.
- audit_official_surveys.py, test_official_surveys.py: mã tái lập và 15 test mới đạt; Ruff đạt.

## Đính chính trạng thái

30 cặp đầu-cuối cũ là dự báo theo thời gian. 31 nhóm 7 ngày và 84 cặp là phân tích thăm dò. Không dùng chúng làm nhãn survey. Ưu tiên bảng mới cho so sánh theo survey và giữ nguyên tập chưa phân loại.

Nhận định trước rằng phải chờ Khôi cho mọi ánh xạ scan không còn áp dụng cho những trường hợp nay đã có header và quy tắc tài liệu. Riêng mốc chuyển pha vẫn để chưa xác định. Chưa kiểm bandpass/phát hiện nguồn hay đo chuyển động trên ảnh. Mô hình chỉ có proper motion góc, chưa có thị sai năm/quỹ đạo/gia tốc phối cảnh; chưa chấp nhận cặp Barnard D2 để đo.

Chỉ cập nhật cục bộ, không commit, push, tạo PR hoặc gửi tin.
