# Hữu Hoàng — tasks A, B, C, D

Ngày thực hiện A–C: **07/11/2026**; bổ sung D: **08/11/2026**. Dấu **−** là task chính; dấu **+** là task phụ.

SPHEREx có thể hiểu là một camera chụp bầu trời bằng ánh sáng hồng ngoại. Mạch công việc: **A đặt ảnh lên cùng lưới → B ghép ảnh theo đợt và so sánh → C làm cho năm mục tiêu, thêm ảnh màu giả**.

## A. Đặt các ảnh lên cùng lưới tọa độ

### 1. Thuật ngữ cần hiểu trước

| Từ trong đề | Hiểu đơn giản |
| --- | --- |
| Pixel | Một ô nhỏ của ảnh, chứa một giá trị đo độ sáng. |
| Cutout | Miếng ảnh nhỏ được cắt từ ảnh lớn, chỉ giữ vùng trời cần xem. Cắt xong ảnh vẫn có thể bị xoay hoặc lệch so với ảnh khác. |
| RA (Right Ascension — xích kinh) | Một tọa độ chỉ hướng trên trời, đóng vai trò giống kinh độ trên Trái Đất. Thường ghi bằng giờ góc: 24h = 360°. **RA = 12h không có nghĩa chụp lúc 12 giờ**, cũng không có nghĩa nhìn thẳng lên đầu. Trong mã này RA ghi bằng độ. |
| Dec (Declination — xích vĩ) | Tọa độ còn lại, giống vĩ độ nhưng trên trời. Đo từ xích đạo trời: 0° ở xích đạo trời, +90° ở cực Bắc trời, −90° ở cực Nam trời. Xích đạo trời là phần kéo dài mặt phẳng xích đạo Trái Đất ra bầu trời, **không phải mặt đất nơi mình đứng**. |
| FOV (Field of View — trường nhìn) | Độ rộng vùng trời muốn lấy vào ảnh. Trong bài, FOV tính bằng độ, không phải số pixel. |
| WCS (World Coordinate System) | Thông tin cho biết mỗi pixel ứng với RA/Dec nào trên trời. Nhờ đó biết hai ảnh đang chụp cùng vị trí dù chúng xoay khác nhau. |
| TAN (tangent-plane projection) | Cách biểu diễn vùng trời cong lên một mặt phẳng quanh tâm đã chọn. Dùng **cùng lưới TAN** nghĩa là mọi ảnh dùng cùng tâm, hướng và bước pixel. Chưa phải ghép thành một ảnh. |
| Reproject / `reproject_interp` | Tái chiếu: chuyển số đo từ lưới ảnh gốc sang lưới mới bằng tọa độ trời. Đây là tên hàm thực hiện trong Python. |
| Centroid; arcsec | Centroid là tâm sáng đo từ một nguồn trong ảnh. Arcsec là giây cung, đơn vị góc nhỏ: 1 arcsec = 1/3600 độ. |

### 2. Task chính yêu cầu gì?

**− reproject_interp các cutout về lưới TAN chung, tâm là mục tiêu; kiểm tra sao đứng yên không nhảy.**

Nghĩa là: lấy các lần chụp cùng vùng trời, đưa chúng về cùng hệ ô pixel, rồi kiểm tra nguồn nền có giữ gần cùng vị trí hay không. Mục đích là tránh nhầm ảnh bị xoay/lệch thành chuyển động của sao khi so sánh ở B. Sao thực sự chuyển động vẫn phải được giữ chuyển động đó.

### 3. Từng thao tác đã làm và minh chứng

**Bước A1 — lấy cutout quanh vùng cần xem.** Cắt trước để tải và xử lý ít dữ liệu hơn; cutout chưa tự căn ảnh. Danh sách ảnh, địa chỉ tải và mã kiểm tra file được lưu trong [inputs.json](../../data/tan_wise0855/inputs.json), giúp biết chính xác đã dùng ảnh nào.

**Bước A2 — tạo lưới TAN chung.** Demo WISE 0855 dùng RA (Right Ascension — xích kinh) **133,7951°**, Dec (Declination — xích vĩ) **−7,2451°**, FOV (Field of View — trường nhìn) **0,1°**, bước pixel **6,2 arcsec**. Làm tròn thành lưới 59×59 để tâm nằm đúng ô giữa; Bắc ở trên, Đông bên trái. Đây là **tâm tìm kiếm đã thống nhất**, chưa phải vị trí đo được của WISE 0855. Bộ C dùng tâm dự đoán theo thời gian cho từng mục tiêu.

**Bước A3 — chuyển từng ảnh sang lưới ấy.** Đọc WCS của ảnh gốc, loại pixel có vấn đề theo cờ chất lượng (giải thích ở C), rồi gọi `reproject_interp`. Với mỗi pixel đích, tìm vị trí tương ứng trong ảnh gốc và nội suy bilinear, tức ước lượng giá trị từ các pixel lân cận. Không chỉ phóng to/thu nhỏ ảnh; cũng không thay đổi cờ chất lượng bằng nội suy này. Hai ảnh vẫn là hai khung riêng sau bước này.

**Bước A4 — đo xem nguồn nền còn nhảy không.** Tìm và đo centroid độc lập trên từng ảnh, ghép các nguồn gần nhau ở hai ảnh, rồi tính độ lệch pixel. Chọn cặp cùng detector (cảm biến) D3 và gần bước sóng tại tâm để giảm khác biệt hình dạng do màu nguồn. Không dịch thêm ảnh để ép nguồn khớp.

![Hai ảnh trên cùng TAN và độ lệch tâm sáng của các nguồn nền](../../data/tan_wise0855/alignment_evidence.png)

**Cách đọc hình:** hai ô trái là ảnh ngày 05/05/2025 và 11/05/2026, các vòng đỏ đánh dấu 7 nguồn ghép được. Ô phải vẽ độ lệch, mũi tên phóng đại 10 lần để dễ nhìn. Trung vị lệch **0,057 pixel ≈ 0,35 arcsec**; lớn nhất **0,166 pixel ≈ 1,03 arcsec**.

Khi so thêm 44 ảnh D3 với ảnh mốc, **43 ảnh đạt**, **1 ảnh thiếu nguồn để kết luận**. Điều kiện đạt là ít nhất 3 nguồn ghép được và độ lệch trung vị dưới 0,5 pixel. Kiểm tra đổi tọa độ, ảnh có giá trị hằng và đọc lại WCS sau lưu cũng đạt. Số liệu nằm trong [report.json](../../data/tan_wise0855/report.json); số đo và tọa độ cặp ảnh nằm trong [tan_pair.fits](../../data/tan_wise0855/tan_pair.fits).

**Giới hạn:** đây là kiểm tra tương đối giữa các nguồn ghép được; chưa đối chiếu danh sách sao độc lập. Nguồn lệch quá lớn có thể không được ghép. Không tự suy ra D6 cũng đạt, mọi sao đứng yên tuyệt đối, hoặc đã phát hiện WISE 0855.

### 4. Task phụ là gì, ảnh hưởng gì?

**+ Đo thời gian reproject 10 và 50 ảnh.** Đây là đo tốc độ xử lý, không phải thêm một bước làm ảnh đẹp hơn.

Dùng các cutout khác nhau, đo ba lần sau một lần chạy khởi động. Bộ 50 ảnh gồm 45 D3 và 5 D6:

| Số ảnh | Thời gian trung vị, xấp xỉ |
| --- | ---: |
| 10 | 0,047 giây |
| 50 | 0,236 giây |

**Ảnh hưởng:** giúp ước lượng người dùng phải chờ bao lâu và có cần tối ưu mã không; không đổi vị trí sao hoặc số đo độ sáng. Chỉ tính reproject lưới 59×59 khi dữ liệu đã trong bộ nhớ, không tính tải mạng, đọc file và xuất ảnh. Thời gian thay đổi theo tải máy, không áp thẳng cho ảnh detector lớn.

**Mã A:** [tan_pipeline.py](tan_pipeline.py).

### 5. Giải đáp sau task A — bổ sung 08/11/2026

**“Ảnh trước/sau đều là 2D, TAN nằm ở đâu?”** TAN là quy tắc gắn tọa độ trời vào ảnh phẳng, không phải một lớp màu hoặc vật thể nhìn thấy trong ảnh. PNG hiện chỉ vẽ độ sáng và trục pixel, chưa vẽ đường tọa độ trời. Thông tin TAN nằm trong WCS của file FITS. Ảnh gốc kiểm tra được đã có `RA---TAN-SIP` / `DEC--TAN-SIP` (TAN kèm mô tả biến dạng SIP); đầu ra có `RA---TAN` / `DEC--TAN`. Vì vậy A không biến ảnh chưa có phép chiếu thành ảnh có phép chiếu: nó đưa các ảnh về **cùng tâm, hướng và bước pixel**, đồng thời tính đến biến dạng ảnh gốc.

**“Tìm tâm tìm kiếm và các thông số ở đâu?”** Có ba nơi, phục vụ ba việc khác nhau:

| Muốn biết gì? | Mở đâu? | Đọc mục nào? |
| --- | --- | --- |
| Mình yêu cầu tâm và trường nhìn nào? | [tan_pipeline.py](tan_pipeline.py) | `RA, DEC, FOV, SCALE` ở đầu file. |
| Lần chạy đã dùng lưới nào? | [report.json](../../data/tan_wise0855/report.json) | `grid.ra_deg`, `dec_deg`, `fov_deg`, `scale_arcsec`, `shape`. |
| Lưới thực sự lưu trong ảnh là gì? | [tan_pair.fits](../../data/tan_wise0855/tan_pair.fits), phần thông tin mô tả của `FRAME0` hoặc `FRAME44` | `CTYPE1/2`: phép chiếu; `CRVAL1/2`: tọa độ tâm chiếu; `CRPIX1/2`: pixel mốc; `CDELT1/2`: bước góc mỗi pixel trong lưới đầu ra này. |

RA (Right Ascension — xích kinh) = 133,7951° và Dec (Declination — xích vĩ) = −7,2451° là tâm tìm kiếm được chọn từ ví dụ trước, không phải do đo tâm sáng tìm ra. FOV (Field of View — trường nhìn) = 0,1° là độ rộng yêu cầu; lưới 59 pixel × 6,2 arcsec sau làm tròn rộng khoảng 0,10161°. Trong FITS, pixel mốc là (30,30) vì đếm từ 1; trong Python là (29,29) vì đếm từ 0. Không nhầm tâm chiếu của WCS ảnh gốc với tâm cutout: pixel mốc của ảnh gốc có thể nằm ngoài miếng cắt.

**“D3 là gì? Vì sao chọn D3/D6, không phải detector khác?”** D là detector (cảm biến); D3 là cảm biến số 3, không phải ảnh thứ 3 hoặc ảnh 3D. Mã chủ động ưu tiên D3 cho bài đo nguồn nền, lấy hết 45 cutout D3 trong catalog, rồi lấy thêm 5 D6 để đủ 50 ảnh benchmark. D6 cũng là detector của demo hai ảnh trước đó. Đây là lựa chọn bộ mẫu, chưa phải kết quả so sánh chứng minh D3/D6 tốt nhất hoặc các detector khác không dùng được.

**“Vì sao chỉ 7 nguồn mà 43 ảnh đạt? Có 45 D3 sao chỉ kiểm tra 44?”** Hai loại số đếm khác nhau:

- **7 nguồn**: số đốm sáng ghép được giữa **một cặp ảnh minh họa**, không phải số ảnh. Nguồn chưa được xác minh từng đối tượng bằng catalogue độc lập.
- **45 ảnh D3 = 1 ảnh mốc + 44 ảnh đem so với mốc**. Không cần so ảnh mốc với chính nó.
- **44 phép so = 43 đạt + 1 thiếu nguồn**. Mỗi phép so tìm nguồn riêng; thực tế số nguồn ghép được từ 0 đến 13, không cố định là 7. Ảnh thiếu nguồn có 0 nguồn ghép được theo bộ lọc hiện tại, không có nghĩa vùng trời hoàn toàn không có sao.
- **50 ảnh benchmark = 45 D3 + 5 D6**. Cả 50 được reproject và đo thời gian, nhưng 5 D6 chưa có kiểm chứng nguồn nền tương ứng trong A.

**“Vì sao dùng arcsec thay vì độ?”** Không bắt buộc: 0,35 arcsec ≈ 0,0000972°. Dùng arcsec để số nhỏ dễ đọc và dễ so với bước pixel 6,2 arcsec; đổi đơn vị không tăng độ chính xác. Giây cung là đơn vị góc, không phải giây thời gian.

**“Kiểm tra nhảy để làm gì? Nhảy là tốt hay xấu?”** Nếu nhiều nguồn nền cùng lệch có hệ thống, ảnh có thể chưa căn đúng; ghép median sẽ làm nguồn nhòe, ảnh hiệu sẽ sinh vệt sáng/tối giả. Khi đó cần tìm lỗi tọa độ, chọn nguồn, chất lượng ảnh hoặc nội suy trước khi dùng kết quả. Sai lệch nhỏ do nhiễu là bình thường. Nếu nền đã ổn mà chỉ mục tiêu đổi vị trí, đó có thể là chuyển động thật, nhưng phải kiểm tra thêm; không phải cứ nhảy là lỗi hay phát hiện tốt. Ngưỡng 0,5 pixel là tiêu chí thực hành đã chọn, không phải chuẩn đúng cho mọi bài khoa học.

**“Vậy cần tối ưu mã chưa? Khi nào mới gọi là chậm?”** Kết luận hiện tại: **chưa có lý do tối ưu riêng bước reproject cho bộ mẫu 50 ảnh 59×59**. Khoảng 0,236 giây là đủ nhỏ cho bài thực hành; số ảnh tăng 5 lần thì thời gian đo tăng khoảng 5 lần. Chưa đo thời gian toàn luồng nên không kết luận toàn ứng dụng nhanh.

Muốn quyết định tối ưu, trước tiên đặt giới hạn chờ cho nhu cầu thật. Ví dụ minh họa: nếu dành tối đa 1 giây cho reproject 50 ảnh, chỉ xem là chậm khi đo lặp trên máy và dữ liệu dự kiến thường xuyên vượt mức đó. Đây là mục tiêu ví dụ, chưa phải yêu cầu nhóm đã chốt. Cũng cần xem bộ ảnh lớn hơn có gây thiếu bộ nhớ, treo hoặc thời gian tăng bất thường không. Đo riêng tải mạng, đọc FITS, reproject và xuất PNG; chỉ tối ưu phần chiếm nhiều thời gian khiến vượt giới hạn. Tải mạng chậm không phải lý do tự động sửa thuật toán reproject.

## B. Ghép ảnh theo cảm biến và đợt quét

### 1. Thuật ngữ cần hiểu trước

| Từ trong đề | Hiểu đơn giản |
| --- | --- |
| Detector | Cảm biến thu ánh sáng của camera SPHEREx. D1, D3, D6 là ba cảm biến khác nhau. |
| LVF (Linear Variable Filter) | Bộ lọc trên cảm biến: ở các vị trí khác nhau, nó cho các khoảng bước sóng khác nhau đi qua. Vì vậy cùng detector chưa chắc là cùng bước sóng. |
| Đợt quét | Nhóm các lần quan sát gần nhau về thời gian. Trong bài này nhóm được suy từ ngày chụp, chưa phải tên đợt chính thức của nhiệm vụ. |
| Median | Giá trị giữa sau khi sắp các số theo thứ tự. Ví dụ cùng một pixel có số đo 10, 12, 1000 thì median là 12, giúp giảm ảnh hưởng của giá trị bất thường. |
| Khung; FITS; PNG | Khung là ảnh kết quả của một detector trong một đợt. FITS giữ số đo và thông tin tọa độ để tính toán; PNG là bản hiển thị để xem. |
| Stretch / asinh | Cách ánh xạ số đo thành sáng tối. Asinh nén vùng rất sáng để vùng mờ dễ thấy hơn; không sửa số đo gốc hoặc tạo thêm tín hiệu. |
| Ảnh hiệu | Ảnh thu được bằng cách lấy số đo của khung sau trừ khung trước tại cùng pixel. |
| NaN; NVALID | NaN đánh dấu thiếu/bị loại, không có nghĩa độ sáng bằng 0. NVALID ghi số ảnh có dữ liệu tốt đóng góp tại mỗi pixel. |

### 2. Task chính yêu cầu gì?

**− Cộng median theo detector × đợt quét → khung PNG cùng thang kéo giãn; ảnh hiệu đợt sau trừ đợt trước.**

Nghĩa là: các ảnh đã căn ở A được ghép riêng theo từng cảm biến và từng đợt. Sau đó xem các khung với cùng quy tắc sáng tối và trừ chúng để tìm chỗ khác nhau. “Cộng median” ở đây là **ghép bằng median**, không phải cộng tổng độ sáng.

### 3. Từng thao tác đã làm và minh chứng

**Bước B1 — chia ảnh thành các nhóm detector × đợt.** Ví dụ D3 đợt 1 là một nhóm, D3 đợt 2 là nhóm khác; không ghép lẫn D3 và D6. Tách đợt khi hai quan sát liên tiếp cách nhau **hơn 30 ngày**, để giữ các ngày quét gần nhau và tách những lượt cách nhiều tháng. Một đợt có thể dài hơn 30 ngày nếu các lần chụp bên trong vẫn nối tiếp gần nhau. Bộ C xác định nhóm trên toàn danh sách quan sát trước khi lấy mẫu, lưu ranh giới vào file nguồn; bộ A chỉ suy nhóm từ 50 ảnh đã chọn.

**Bước B2 — lấy median tại từng pixel.** Sau khi ảnh cùng lưới, gom số đo tốt tại cùng một ô rồi lấy median; bỏ qua NaN. Lưu cả MEDIAN và NVALID trong FITS để biết mỗi ô dựa trên bao nhiêu ảnh. Nếu không còn số đo tốt thì để NaN; nhóm chỉ một ảnh vẫn xuất khung nhưng không có lợi ích ghép nhiều ảnh.

**Bước B3 — xuất PNG cùng thang kéo giãn.** Dùng chung giới hạn sáng tối và cùng phép asinh cho mọi đợt của **cùng mục tiêu và detector**. Như vậy phần mềm không tự làm từng ảnh sáng lên/tối đi theo một thang khác nhau. Detector khác có thang riêng.

![Khung median D3 đợt đầu của vùng WISE 0855](../../data/tan_wise0855/frames/D3_visit00.png)

![Khung median D3 đợt kế tiếp, dùng cùng thang hiển thị](../../data/tan_wise0855/frames/D3_visit01.png)

**Cách đọc hai hình:** đây là hai khung D3 ở hai đợt liên tiếp, dùng cùng thang sáng tối. Nhãn ghi ngày và số ảnh được ghép; tím là vùng thiếu/bị loại. Khung đầu ghép 3 ảnh, khung tiếp ghép 21 ảnh; số ảnh đóng góp tại từng pixel có thể ít hơn vì mask.

**Bước B4 — tạo ảnh hiệu đợt sau trừ đợt trước.** Trừ số đo gốc trước khi áp dụng cách hiển thị; chỉ có kết quả nơi cả hai khung đều có dữ liệu. Dùng màu đỏ cho hiệu dương (sau sáng hơn), xanh cho hiệu âm (sau tối hơn), gần trắng cho hiệu gần 0. Thang màu đối xứng quanh 0 và chung giới hạn giữa các cặp của detector đó.

![Ảnh hiệu D3: đợt kế tiếp trừ đợt đầu](../../data/tan_wise0855/frames/D3_visit01_minus_D3_visit00.png)

**Cách đọc hình:** tên `visit01_minus_visit00` cho biết thứ tự trừ. Vùng trống do thiếu dữ liệu không được hiểu là hiệu bằng 0. Một vùng đỏ/xanh chỉ cho biết hai số đo khác nhau; chưa chứng minh sao biến thiên.

**Kết quả B:** demo WISE có 3 khung D3 từ 3/21/21 ảnh, và 2 khung D6 từ phần mẫu còn lại. Xem [D3 report](../../data/tan_wise0855/frames/D3_report.json) và [D6 report](../../data/tan_wise0855/frames/D6_report.json).

**Giới hạn:** LVF có thể làm các ảnh thu bước sóng khác nhau. Chưa làm cho hình nguồn điểm giống nhau giữa các ảnh (khớp PSF — Point Spread Function), cân mức nền hoặc tính đầy đủ sai số. Vì vậy đây là khung khảo sát, chưa dùng để kết luận biến thiên hoặc đo độ sáng chính xác của sao.

### 4. Task phụ là gì, ảnh hưởng gì?

**+ Gói thành hàm `make_frames(ra, dec, fov, det)`.** Nghĩa là gom chuỗi xử lý trên vào một lệnh gọi, để không phải chép và chạy thủ công từng bước.

| Đầu vào | Ý nghĩa |
| --- | --- |
| `ra` | RA (Right Ascension — xích kinh) của tâm, bằng độ. |
| `dec` | Dec (Declination — xích vĩ) của tâm, bằng độ. |
| `fov` | FOV (Field of View — trường nhìn), độ rộng vùng cần xem, bằng độ. |
| `det` | Detector, số cảm biến từ 1 đến 6. |

```python
from frames import make_frames
report = make_frames(133.7951, -7.2451, 0.1, 3)
# Thêm manifest=... (file danh sách ảnh) và output=... (thư mục kết quả)
# khi muốn dùng bộ dữ liệu khác.
```

**Ảnh hưởng:** giúp tái sử dụng, chạy lại cùng quy tắc và áp dụng cho nhiều mục tiêu ở C; bản thân việc gói hàm không tăng độ chính xác hay khôi phục dữ liệu mất. Mặc định hàm đọc bộ A đã tải, không tự gọi mạng. Mã hiện là thực hành cá nhân, chưa tích hợp giao diện lập trình dùng chung của nhóm.

**Mã B:** [frames.py](frames.py).

## C. Áp dụng cho năm mục tiêu và ghép màu giả

### 1. Thuật ngữ cần hiểu trước

| Từ trong đề | Hiểu đơn giản |
| --- | --- |
| Mục tiêu | Thiên thể hoặc vùng quanh thiên thể muốn khảo sát. Trong bài có năm mục tiêu. |
| Epoch; chuyển động riêng | Epoch là mốc thời gian của tọa độ. Chuyển động riêng là tốc độ thiên thể đổi vị trí trên trời, nên tọa độ năm 2000 có thể không còn đúng cho năm 2026. |
| Bão hòa; phi tuyến | Bão hòa: ánh sáng quá mạnh khiến cảm biến không ghi đúng độ sáng. Phi tuyến: số đo không còn tăng đúng tỷ lệ với ánh sáng đi vào. Các pixel này không đáng tin để ghép/đo. |
| Flags; bit | Flags là các dấu chất lượng đi kèm từng pixel, lưu bằng các bit (giá trị 0/1). Mỗi bit báo một tình trạng, không phải cứ có flag là pixel hỏng. |
| Mask | Đánh dấu pixel không dùng trong tính toán. Pixel đó có thể hiện thành vùng trống hoặc màu tím; không phải tô lại ngôi sao. |
| RGB (Red, Green, Blue); màu giả | RGB là ba kênh đỏ, lục, lam của ảnh hiển thị. Màu giả là gán ba bộ dữ liệu hồng ngoại vào ba kênh đó để dễ quan sát. |

### 2. Task chính yêu cầu gì?

**− Khung cho 5 mục tiêu; xử lý sao bão hoà (Barnard, R Draconis) bằng flags.**

Nghĩa là: áp dụng A và B cho Barnard, Epsilon Indi B, WISE 0855, RW Aurigae và R Draconis. Với nguồn quá sáng, phải nhận biết và loại số đo không đáng tin trước khi ghép; không cố vá lõi sáng thành dữ liệu tốt.

### 3. Từng thao tác đã làm và minh chứng

**Bước C1 — chọn đúng mục tiêu và tâm theo thời gian.** Lấy tọa độ, chuyển động riêng từ SIMBAD (cơ sở dữ liệu thiên thể), dự đoán vị trí tại mốc J2026, rồi giữ một lưới cố định qua các đợt. Nếu cứ kéo mục tiêu về tâm ở từng ảnh, sao nền có thể trông như đang chạy. Riêng Epsilon Indi B được xác minh bằng định danh 2MASS để tránh nhầm với hành tinh có tên gần giống.

Trong bộ C, RA (Right Ascension — xích kinh) và Dec (Declination — xích vĩ) của tâm thay đổi theo mục tiêu; FOV (Field of View — trường nhìn) vẫn là **0,1°**. WISE ở bộ C dùng tâm dự đoán J2026, khác tâm tìm kiếm của demo A. Dự đoán chưa tính đầy đủ chuyển động do vị trí người quan sát thay đổi, quỹ đạo hệ đôi và chuyển động về phía/ra xa người quan sát; chưa phải vị trí đo từ ảnh.

**Bước C2 — tải bộ mẫu rồi chạy A và B.** Chọn ba detector D1/D3/D6, tối đa hai ảnh đầu/cuối mỗi detector trong mỗi nhóm quan sát. File danh sách ảnh giữ ngày chụp, nhóm thời gian, tọa độ yêu cầu và nguồn tải. Bộ mẫu giúp chạy hoàn chỉnh luồng xử lý mà chưa cần tải mọi ảnh sẵn có.

**Bước C3 — đọc flags và mask trước khi reproject.** Đọc ý nghĩa và vị trí bit từ header (phần thông tin mô tả) của từng file. Loại các bit chất lượng đã chọn, giữ `SOURCE` (đánh dấu có nguồn) và `FULLSAMPLE` (thông tin lấy mẫu). Không dùng điều kiện “flags phải bằng 0” vì sẽ loại cả pixel có nguồn tốt. Theo dõi riêng `OVERFLOW` (cảnh báo gần bão hòa) và `NONLINEAR` (phi tuyến).

![Barnard: ảnh gốc, cờ liên quan bão hòa và ảnh sau mask](../../data/five_targets/barnard/saturation_evidence.png)

**Cách đọc minh chứng Barnard:** trái là số đo gốc; giữa là vị trí có cờ OVERFLOW/NONLINEAR; phải là ảnh sau khi loại toàn bộ các cờ chất lượng đã chọn. Tím là dữ liệu thiếu/bị loại; ảnh gốc cũng có thể đã có pixel thiếu. Tổng trên các cutout đầu vào có **56 lượt pixel** mang cờ OVERFLOW/NONLINEAR.

![R Draconis: ảnh gốc, cờ liên quan bão hòa và ảnh sau mask](../../data/five_targets/r-dra/saturation_evidence.png)

**Cách đọc minh chứng R Draconis:** cùng thứ tự ba ô như trên. Tổng trên các cutout đầu vào có **342 lượt pixel** mang cờ OVERFLOW/NONLINEAR. Vùng bị loại bên phải có thể lớn hơn vùng giữa vì còn các cờ chất lượng khác. Đã kiểm tra pixel mang hai cờ này thực sự thành NaN trước nội suy.

**Bước C4 — xuất khung từng mục tiêu và kiểm tra lại.** Sau mask, chạy lại cùng quy trình căn TAN, median và ảnh hiệu. Đọc lại file kết quả để kiểm tra tâm, đơn vị, số ảnh đóng góp và dấu phép trừ; kết quả trong [verification.json](../../data/five_targets/verification.json).

**Giới hạn:** các số 56/342 là tổng lượt pixel trên toàn cutout qua nhiều ảnh, không phải số pixel trời độc lập hoặc chắc chắn đều thuộc mục tiêu. Mask chỉ tránh dùng số đo xấu, không khôi phục ánh sáng đã bão hòa.

### 4. Task phụ là gì, ảnh hưởng gì?

**+ Ảnh màu giả ghép 3 detector.** Đưa các khung đã có vào ba kênh màu theo quy tắc **R=D6, G=D3, B=D1**: cảm biến bước sóng dài hơn được gán đỏ, ngắn hơn được gán xanh lam.

Ghép các khung cùng nhóm thời gian trên cùng TAN; giữ cùng thang từng kênh qua các đợt. Chỉ hiển thị nơi cả ba kênh có dữ liệu tốt, tím là thiếu/bị mask.

![Ảnh màu giả Barnard, đỏ từ D6, lục từ D3, lam từ D1](../../data/five_targets/barnard/frames/rgb_visit01.png)

**Cách đọc hình:** đây là dữ liệu của ba cảm biến hồng ngoại được tô màu để nhìn chung trong một ảnh. Vùng tím giữa nguồn là phần không có đủ dữ liệu tốt, không phải màu thật của sao.

**Ảnh hưởng:** giúp nhìn vị trí và hình dạng nguồn ở các detector trong một khung; không làm dữ liệu gốc chính xác hơn, không thay đổi phép median/ảnh hiệu. Màu không phải màu mắt người thấy hay thước đo nhiệt độ, vì các kênh không đồng thời và có thể trộn nhiều bước sóng.

**Kết quả bộ C:**

| Mục tiêu | Cutout | Khung median | Ảnh hiệu | RGB |
| --- | ---: | ---: | ---: | ---: |
| Barnard | 12 | 6 | 3 | 2 |
| Epsilon Indi B | 18 | 9 | 6 | 3 |
| WISE 0855 | 18 | 9 | 6 | 3 |
| RW Aurigae | 12 | 6 | 3 | 2 |
| R Draconis | 18 | 9 | 6 | 3 |
| Tổng | **78** | **39** | **24** | **13** |

Muốn xem cả năm mục tiêu cạnh nhau, mở [ảnh tổng quan](../../data/five_targets/overview.png): mỗi hàng là một mục tiêu, hai cột đầu là khung D3 đợt đầu/cuối, cột cuối là màu giả đợt cuối.

**Mã C:** [five_targets.py](five_targets.py).

## D. Cutout → khung PNG và ảnh hiệu — 08/11

### 1. Thuật ngữ cần hiểu trước

| Từ trong đề | Hiểu đơn giản |
| --- | --- |
| Dựng lại | Tự viết lại phần xử lý trong thư mục mới, không chép mã cũ, rồi chạy ra kết quả. Khác với chỉ chạy lại một script đã viết. |
| Thời gian chạy | Máy mất bao lâu để đọc dữ liệu, xử lý, lưu sản phẩm và kiểm tra. Không bao gồm thời gian người học viết mã. |
| PNG (Portable Network Graphics) | Ảnh để xem; đã kéo giãn độ sáng. Không dùng số màu PNG để đo quang hoặc trích phổ. |
| Bàn giao | Đưa file và cách dùng cho người nhận; cần phân biệt sản phẩm của mình với phần người khác chưa xác nhận. |

### 2. Task chính yêu cầu gì?

**− Cutout → khung PNG + ảnh hiệu, dưới 1,5 giờ.**

Theo lộ trình, đây là bài **tự dựng lại trong thư mục mới, không chép mã cũ và bấm giờ từ lúc bắt đầu dựng**. Ngưỡng 90 phút là thời gian thực hành của Hữu Hoàng, không phải chỉ thời gian chạy Python. Demo dưới đây chứng minh đầu vào thật chạy tới sản phẩm; **chưa chốt đạt bài tự dựng lại 90 phút**.

### 3. Từng thao tác đã làm và minh chứng

**Bước D1 — kiểm tra đầu vào từ nhóm trước.** Đã `git pull --ff-only origin huu-hoang`: nhánh đã cập nhật tại `9c30daf455b3476fe89532aa9e87d212a644de3c`. Đã kiểm tra danh sách nhánh GitHub và tải nhánh `nguyen/day03-04` để đọc, tại commit `9a80481568ef2263fb8027ca579fd9200f379820`; không gộp nhánh này vào mã đang làm.

Nguyên **đã có** bảng mục tiêu, kỳ vọng v0, dự báo chuyển động theo các survey suy ra từ tài liệu, ghi chú flags và hàm chuyển động riêng. **Chưa thấy** runbook trích phổ Luhman 16, checklist cho bài F hoặc bảng kỳ vọng v1 được xác nhận. Không được diễn giải là Nguyên chưa làm khoa học. Trên các nhánh đã công bố **chưa thấy mã tải/DB hay fixture của Khôi**; không kết luận về file riêng hoặc Drive chưa truy cập. Truy vấn issue của repo trả rỗng ở lần kiểm tra này.

Nguồn Nguyên: [ANALYSIS.md](https://github.com/HoangKhoi1704/NASA-space-challenges-PlanetXvsSphereX/blob/9a80481568ef2263fb8027ca579fd9200f379820/members/nguyen/day03-04/ANALYSIS.md), [FLAGS.md](https://github.com/HoangKhoi1704/NASA-space-challenges-PlanetXvsSphereX/blob/9a80481568ef2263fb8027ca579fd9200f379820/members/nguyen/day03-04/FLAGS.md). Bản chụp để đọc offline nằm trong `data/tasks_def/dependencies/`, có commit và đường dẫn gốc trong `source.json`.

**Bước D2 — demo thay đầu vào còn thiếu của Khôi.** Dùng các cutout FITS thật đã tự tải từ IRSA ở C, kèm danh sách `inputs.json` và SHA256 (mã kiểm tra nội dung file). Đây là dữ liệu tải từ kho, không phải ảnh PNG lấy ngược từ demo. Không giả danh fixture chính thức của Khôi, không báo đã có DB của Khôi.

**Bước D3 — xuất vào thư mục riêng và kiểm tra.** [task_d.py](task_d.py) đọc cutout, che flags, đưa về TAN chung, median theo detector × nhóm thời gian, xuất PNG/FITS và ảnh hiệu. Ảnh hiệu = **đợt hiện tại trừ đợt liền trước** trong cùng detector; không mặc định mọi đợt trừ đợt đầu. Script đọc lại FITS để kiểm tra tâm WCS (World Coordinate System — hệ tọa độ ảnh), vùng thiếu theo NVALID (số ảnh hợp lệ đóng góp) và giá trị phép trừ; xác nhận PNG có trên đĩa.

| Mục tiêu | Cutout đầu vào | Median | Ảnh hiệu | Thời gian chạy đo lần đầu |
| --- | ---: | ---: | ---: | ---: |
| WISE 0855 | 18 | 9 | 6 | khoảng 3,27 giây |
| Barnard | 12 | 6 | 3 | khoảng 2,03 giây |

Đây là số lượng ảnh, không phải số nguồn phát hiện. Hai ảnh cùng detector/cùng đợt tạo một median; các median lại được dùng để tạo ảnh hiệu. Không cộng cột median và ảnh hiệu để đối chiếu tổng cutout. WISE có 3 nhóm thời gian, Barnard có 2; nhóm là khoảng quan sát được chia theo ngưỡng gián đoạn 30 ngày của bộ C, **chưa đổi thành nhãn survey chính thức của Nguyên**.

Thời gian trên bao gồm đọc FITS cục bộ, kiểm SHA256, mask, reproject, ghép, lưu PNG/FITS và kiểm tra đầu ra trong script; chưa gồm tải mạng, import/khởi động Python hay người viết mã. Xem số đo lần chạy hiện tại ở [report.json](../../data/tasks_def/D/report.json). Máy/tải hệ thống khác sẽ cho thời gian khác; không cộng vào bảng 6 người như kết quả tự dựng lại.

![Barnard D3 đợt đầu, dựng lại từ cutout thật](../../data/tasks_def/D/barnard/D3_visit00.png)

**Cách đọc:** thang xám là độ sáng MJy/sr (megajansky trên steradian, độ sáng trên một góc khối); tím là pixel thiếu hoặc bị mask, không phải nguồn sáng màu tím. Tâm khung là tọa độ yêu cầu, chưa phải vị trí nguồn đo được.

![Ảnh hiệu Barnard D3, đợt sau trừ đợt trước](../../data/tasks_def/D/barnard/D3_visit01_minus_D3_visit00.png)

**Cách đọc:** đỏ là giá trị hiệu dương, xanh lam là âm; giá trị gần 0 ở giữa thang màu. Trong bản A–D, vùng NaN trên ảnh hiệu có thể hiển thị trắng do colormap mặc định, cần xem FITS/mask để phân biệt; E sẽ sửa màu thiếu cho thống nhất. Khác biệt bước sóng, PSF (Point Spread Function — hình ảnh của nguồn điểm), nền hoặc căn ảnh đều có thể tạo vệt. Chưa dùng ảnh này để khẳng định Barnard chuyển động hoặc biến quang.

**Bước D4 — lộ trình tự dựng lại để chốt 90 phút.** Bắt đầu đồng hồ trước khi tạo thư mục/mã mới; ghi môi trường và đầu vào. Dự kiến 0–15 phút đọc manifest/FITS/flags; 15–40 phút tạo TAN và reproject; 40–60 phút median/NVALID; 60–75 phút PNG cùng thang và ảnh hiệu đúng dấu; 75–90 phút đọc lại kiểm và ghi kết quả. Đây là phân bổ đề xuất, **không phải thời gian đã thực hiện**. Nếu không xong, ghi thời gian thật và lỗi, không đổi tiêu chí thành benchmark máy.

### 4. Task phụ là gì, ảnh hưởng gì?

**+ Vòng 1 học trích phổ từ Nguyên; vòng 2 học tải dữ liệu từ Khôi.**

| Vòng | Khi người sở hữu bàn giao | Demo trong lúc chưa có | Người học cần tự chạy lại |
| --- | --- | --- | --- |
| 1 — Nguyên | Nhận runbook trích phổ, quy tắc chọn ảnh/bước sóng, mask, nền, đơn vị, sai số và checklist; đối chiếu với ghi chú v0 đã có | Bài F sẽ đọc bước sóng từ WCS phổ và thử đo aperture trên FITS gốc; ghi rõ chưa được Nguyên duyệt | Đổi ảnh đầu vào, kiểm điểm phổ và giải thích vì sao không đo từ PNG/median nhiều bước sóng |
| 2 — Khôi | Nhận mã SIA2/cutout, manifest/DB, collection và chính sách timeout/retry | Dùng `five_targets.py --download --target barnard` hoặc `--target wise-0855`; mã tự tải đã có ở C | Tìm ảnh → tải cutout → kiểm HDU/obs_id/detector/đơn vị → lưu nguồn tải và SHA256 |

Theo lộ trình, mỗi vòng 50 phút, mỗi chiều dạy 25 phút; Hữu Hoàng còn dạy Nguyên cộng ảnh và dạy Khôi đọc FITS/che flags. Demo độc lập không thay thế việc hai bên học và tự chạy lại; trạng thái buổi dạy chéo vẫn **chưa xác nhận**.

### 5. Chốt task D: đạt gì, thiếu gì, tiếp theo làm gì?

**Đã đạt phần kỹ thuật độc lập:** PNG thật và ảnh hiệu của WISE 0855/Barnard được dựng từ cutout trong thư mục riêng; các kiểm tra đầu ra của script đạt. Chạy lại bằng:

```powershell
.venv/Scripts/python.exe members/huu-hoang/task_d.py
```

**Chưa đủ để chốt mốc 8/11 của cả nhóm:** chưa có thời gian tự dựng lại của Hữu Hoàng/5 người còn lại; chưa xác nhận PNG do Khôi làm; chưa có xác nhận kỳ vọng v1 và hai vòng dạy chéo. Không ghi kết quả giả tưởng thành kết quả thật.

| Người | Kết quả cần đưa vào bảng retro | Trạng thái kiểm được ở đây |
| --- | --- | --- |
| Thạch | Aladin + Gaia dưới 60 phút | Chưa nhận số đo |
| Duy Hoàng | Viewer + mock dưới 90 phút | Chưa nhận số đo |
| Đông | Mock API + cache dưới 60 phút | Chưa nhận số đo |
| Khôi | SIA2 → cutout → DB Barnard dưới 60 phút; PNG thực hành | Chưa nhận số đo/sản phẩm |
| Hữu Hoàng | Tự dựng cutout → PNG + ảnh hiệu dưới 90 phút | Có demo kỹ thuật; chưa đo bài tự dựng |
| Nguyên | Kiểm 5 mục tiêu theo kỳ vọng dưới 60 phút; kỳ vọng v1 | Có tài liệu v0 và audit; chưa xác nhận mốc này |

**Sau khi nhận bàn giao:** giữ nguyên dữ liệu demo để đối chiếu, kiểm schema và định danh dữ liệu của Khôi trước khi tạo manifest tương thích; chạy lại D trên đầu vào của Khôi vào thư mục mới. Nhận Nguyên kiểm quy tắc chọn ảnh/bandpass và ghép kết quả theo obs_id; không gán cluster 30 ngày thành survey của Nguyên chỉ bằng tên. Bàn giao cho Khôi/Đông đường dẫn PNG/FITS/report, ngày chụp, detector, thang hiển thị, vùng thiếu và giới hạn khoa học. Tiếp theo E sửa lỗi theo issue thực tế; chưa có issue thì kiểm tra chủ động và ghi rõ đó là lỗi tự phát hiện.

## Chạy lại theo đúng task

Chạy tại gốc repo, PowerShell. Các lệnh có `--download` dùng mạng; bỏ tùy chọn này khi đã tải đủ dữ liệu.

```powershell
# A: căn TAN, kiểm tra nguồn nền và đo thời gian.
.venv/Scripts/python.exe members/huu-hoang/tan_pipeline.py --download
# B: ghép median và ảnh hiệu từ bộ A, không tải mạng.
.venv/Scripts/python.exe members/huu-hoang/frames.py
# C: tải bộ năm mục tiêu và tạo các khung, mask, RGB.
.venv/Scripts/python.exe members/huu-hoang/five_targets.py --download
# Kiểm tra file kết quả C và tạo ảnh tổng quan.
.venv/Scripts/python.exe members/huu-hoang/verify_products.py
```

Bốn ca kiểm tra tự động đã đạt: tâm/hướng WCS; vị trí nguồn qua lưới xoay/lệch; median loại ngoại lệ và ảnh hiệu đúng dấu; giữ nhóm thời gian khi lấy mẫu thưa. Kiểm chứng ảnh thật nằm trong các report riêng.

```powershell
.venv/Scripts/python.exe -m pytest members/huu-hoang/test_pipeline.py -q
.venv/Scripts/ruff.exe check members/huu-hoang
```

Sản phẩm trong `data/` bị gitignore, nghĩa là không được đưa vào Git. Link ảnh chỉ mở được trên máy có dữ liệu; file FITS dùng cho tính toán, không mở như văn bản.

Nguồn: [ghi chú ban đầu](../../ghichu.md) · [reproject_interp](https://reproject.readthedocs.io/en/latest/api/reproject.reproject_interp.html) · [IRSA cutout](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/cutout_tool.html) · [IRSA flags](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html) · [SIMBAD Barnard](https://simbad.cfa.harvard.edu/simbad/sim-id?Ident=GJ+699) · [SIMBAD Epsilon Indi B](https://simbad.cfa.harvard.edu/simbad/sim-id?Ident=2MASS+J22041052-5646577).

## Cách trình bày dành cho Hữu Hoàng ở các lần tiếp theo

- Mở đầu nói rõ đang giải thích task chính hay phụ nào; giải nghĩa từ mới trước khi dùng và ghi tên đầy đủ cạnh chữ viết tắt.
- Với RA/Dec, nói rõ đó là tọa độ góc trên trời, không phải giờ chụp hoặc hướng so với mặt đất. Phân biệt tâm yêu cầu, tâm chiếu, pixel giữa ảnh và vị trí nguồn đo được.
- Với bước không nhìn thấy trực tiếp như TAN/WCS, chỉ rõ nó nằm ở đâu trong file; phân biệt thay đổi số đo, thay đổi lưới tọa độ và chỉ thay đổi hiển thị.
- Với mỗi con số, nêu đơn vị, đếm ảnh hay đếm nguồn, ảnh mốc có nằm trong tổng không, phạm vi đã kiểm tra và phần chưa đủ bằng chứng.
- Giải thích vì sao chọn dữ liệu, ngưỡng và phương pháp; phân biệt lựa chọn thực hành với kết luận đã kiểm chứng hoặc chuẩn bắt buộc.
- Mỗi thao tác cần có mục đích, cách thực hiện, ảnh minh chứng đúng chỗ và hướng dẫn đọc; không để người đọc tự đoán ý nghĩa hình.
- Kết thúc mỗi task bằng kết luận cụ thể: đã đạt gì, còn thiếu gì, cần hành động tiếp không. Với hiệu năng, phân biệt thời gian một bước và toàn luồng, đặt tiêu chí trước khi gọi nhanh/chậm hoặc đề nghị tối ưu.
