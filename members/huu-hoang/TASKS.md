# Hữu Hoàng — tasks A, B, C, D, E, F

Ngày thực hiện A–C: **07/11/2026**; bổ sung D: **08/11/2026**. Dấu **−** là task chính; dấu **+** là task phụ.

E (lịch 09/11) và F (lịch 10/11) được chuẩn bị/chạy demo trước vào **08/11/2026**. Ngày trong tiêu đề là ngày kế hoạch, không phải bằng chứng nhóm đã diễn tập tích hợp hay đổi vai.

SPHEREx có thể hiểu là một camera chụp bầu trời bằng ánh sáng hồng ngoại. Mạch công việc: **A đặt ảnh lên cùng lưới → B ghép ảnh theo đợt và so sánh → C làm cho năm mục tiêu, thêm ảnh màu giả**.

## A. Đặt các ảnh lên cùng lưới tọa độ

### 1. Thuật ngữ cần hiểu trước

| Từ trong đề                       | Hiểu đơn giản                                                                                                                                                                                                                                |
| --------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Pixel                             | Một ô nhỏ của ảnh, chứa một giá trị đo độ sáng.                                                                                                                                                                                              |
| Cutout                            | Miếng ảnh nhỏ được cắt từ ảnh lớn, chỉ giữ vùng trời cần xem. Cắt xong ảnh vẫn có thể bị xoay hoặc lệch so với ảnh khác.                                                                                                                     |
| RA (Right Ascension — xích kinh)  | Một tọa độ chỉ hướng trên trời, đóng vai trò giống kinh độ trên Trái Đất. Thường ghi bằng giờ góc: 24h = 360°. **RA = 12h không có nghĩa chụp lúc 12 giờ**, cũng không có nghĩa nhìn thẳng lên đầu. Trong mã này RA ghi bằng độ.             |
| Dec (Declination — xích vĩ)       | Tọa độ còn lại, giống vĩ độ nhưng trên trời. Đo từ xích đạo trời: 0° ở xích đạo trời, +90° ở cực Bắc trời, −90° ở cực Nam trời. Xích đạo trời là phần kéo dài mặt phẳng xích đạo Trái Đất ra bầu trời, **không phải mặt đất nơi mình đứng**. |
| FOV (Field of View — trường nhìn) | Độ rộng vùng trời muốn lấy vào ảnh. Trong bài, FOV tính bằng độ, không phải số pixel.                                                                                                                                                        |
| WCS (World Coordinate System)     | Thông tin cho biết mỗi pixel ứng với RA/Dec nào trên trời. Nhờ đó biết hai ảnh đang chụp cùng vị trí dù chúng xoay khác nhau.                                                                                                                |
| TAN (tangent-plane projection)    | Cách biểu diễn vùng trời cong lên một mặt phẳng quanh tâm đã chọn. Dùng **cùng lưới TAN** nghĩa là mọi ảnh dùng cùng tâm, hướng và bước pixel. Chưa phải ghép thành một ảnh.                                                                 |
| Reproject / `reproject_interp`    | Tái chiếu: chuyển số đo từ lưới ảnh gốc sang lưới mới bằng tọa độ trời. Đây là tên hàm thực hiện trong Python.                                                                                                                               |
| Centroid; arcsec                  | Centroid là tâm sáng đo từ một nguồn trong ảnh. Arcsec là giây cung, đơn vị góc nhỏ: 1 arcsec = 1/3600 độ.                                                                                                                                   |

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
| ------ | -------------------------: |
| 10     |                 0,047 giây |
| 50     |                 0,236 giây |

**Ảnh hưởng:** giúp ước lượng người dùng phải chờ bao lâu và có cần tối ưu mã không; không đổi vị trí sao hoặc số đo độ sáng. Chỉ tính reproject lưới 59×59 khi dữ liệu đã trong bộ nhớ, không tính tải mạng, đọc file và xuất ảnh. Thời gian thay đổi theo tải máy, không áp thẳng cho ảnh detector lớn.

**Mã A:** [tan_pipeline.py](tan_pipeline.py).

### 5. Giải đáp sau task A — bổ sung 08/11/2026

**“Ảnh trước/sau đều là 2D, TAN nằm ở đâu?”** TAN là quy tắc gắn tọa độ trời vào ảnh phẳng, không phải một lớp màu hoặc vật thể nhìn thấy trong ảnh. PNG hiện chỉ vẽ độ sáng và trục pixel, chưa vẽ đường tọa độ trời. Thông tin TAN nằm trong WCS của file FITS. Ảnh gốc kiểm tra được đã có `RA---TAN-SIP` / `DEC--TAN-SIP` (TAN kèm mô tả biến dạng SIP); đầu ra có `RA---TAN` / `DEC--TAN`. Vì vậy A không biến ảnh chưa có phép chiếu thành ảnh có phép chiếu: nó đưa các ảnh về **cùng tâm, hướng và bước pixel**, đồng thời tính đến biến dạng ảnh gốc.

**“Tìm tâm tìm kiếm và các thông số ở đâu?”** Có ba nơi, phục vụ ba việc khác nhau:

| Muốn biết gì?                        | Mở đâu?                                                                                                  | Đọc mục nào?                                                                                                                       |
| ------------------------------------ | -------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Mình yêu cầu tâm và trường nhìn nào? | [tan_pipeline.py](tan_pipeline.py)                                                                       | `RA, DEC, FOV, SCALE` ở đầu file.                                                                                                  |
| Lần chạy đã dùng lưới nào?           | [report.json](../../data/tan_wise0855/report.json)                                                       | `grid.ra_deg`, `dec_deg`, `fov_deg`, `scale_arcsec`, `shape`.                                                                      |
| Lưới thực sự lưu trong ảnh là gì?    | [tan_pair.fits](../../data/tan_wise0855/tan_pair.fits), phần thông tin mô tả của `FRAME0` hoặc `FRAME44` | `CTYPE1/2`: phép chiếu; `CRVAL1/2`: tọa độ tâm chiếu; `CRPIX1/2`: pixel mốc; `CDELT1/2`: bước góc mỗi pixel trong lưới đầu ra này. |

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

| Từ trong đề                  | Hiểu đơn giản                                                                                                                                         |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| Detector                     | Cảm biến thu ánh sáng của camera SPHEREx. D1, D3, D6 là ba cảm biến khác nhau.                                                                        |
| LVF (Linear Variable Filter) | Bộ lọc trên cảm biến: ở các vị trí khác nhau, nó cho các khoảng bước sóng khác nhau đi qua. Vì vậy cùng detector chưa chắc là cùng bước sóng.         |
| Đợt quét                     | Nhóm các lần quan sát gần nhau về thời gian. Trong bài này nhóm được suy từ ngày chụp, chưa phải tên đợt chính thức của nhiệm vụ.                     |
| Median                       | Giá trị giữa sau khi sắp các số theo thứ tự. Ví dụ cùng một pixel có số đo 10, 12, 1000 thì median là 12, giúp giảm ảnh hưởng của giá trị bất thường. |
| Khung; FITS; PNG             | Khung là ảnh kết quả của một detector trong một đợt. FITS giữ số đo và thông tin tọa độ để tính toán; PNG là bản hiển thị để xem.                     |
| Stretch / asinh              | Cách ánh xạ số đo thành sáng tối. Asinh nén vùng rất sáng để vùng mờ dễ thấy hơn; không sửa số đo gốc hoặc tạo thêm tín hiệu.                         |
| Ảnh hiệu                     | Ảnh thu được bằng cách lấy số đo của khung sau trừ khung trước tại cùng pixel.                                                                        |
| NaN; NVALID                  | NaN đánh dấu thiếu/bị loại, không có nghĩa độ sáng bằng 0. NVALID ghi số ảnh có dữ liệu tốt đóng góp tại mỗi pixel.                                   |

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

| Đầu vào | Ý nghĩa                                                           |
| ------- | ----------------------------------------------------------------- |
| `ra`    | RA (Right Ascension — xích kinh) của tâm, bằng độ.                |
| `dec`   | Dec (Declination — xích vĩ) của tâm, bằng độ.                     |
| `fov`   | FOV (Field of View — trường nhìn), độ rộng vùng cần xem, bằng độ. |
| `det`   | Detector, số cảm biến từ 1 đến 6.                                 |

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

| Từ trong đề                     | Hiểu đơn giản                                                                                                                                                              |
| ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Mục tiêu                        | Thiên thể hoặc vùng quanh thiên thể muốn khảo sát. Trong bài có năm mục tiêu.                                                                                              |
| Epoch; chuyển động riêng        | Epoch là mốc thời gian của tọa độ. Chuyển động riêng là tốc độ thiên thể đổi vị trí trên trời, nên tọa độ năm 2000 có thể không còn đúng cho năm 2026.                     |
| Bão hòa; phi tuyến              | Bão hòa: ánh sáng quá mạnh khiến cảm biến không ghi đúng độ sáng. Phi tuyến: số đo không còn tăng đúng tỷ lệ với ánh sáng đi vào. Các pixel này không đáng tin để ghép/đo. |
| Flags; bit                      | Flags là các dấu chất lượng đi kèm từng pixel, lưu bằng các bit (giá trị 0/1). Mỗi bit báo một tình trạng, không phải cứ có flag là pixel hỏng.                            |
| Mask                            | Đánh dấu pixel không dùng trong tính toán. Pixel đó có thể hiện thành vùng trống hoặc màu tím; không phải tô lại ngôi sao.                                                 |
| RGB (Red, Green, Blue); màu giả | RGB là ba kênh đỏ, lục, lam của ảnh hiển thị. Màu giả là gán ba bộ dữ liệu hồng ngoại vào ba kênh đó để dễ quan sát.                                                       |

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

**Cách đọc minh chứng R Draconis:** cùng thứ tự ba ô như trên. Tổng trên các cutout đầu vào có **342 lượt pixel** mang cờ OVERFLOW/NONLINEAR. Ô giữa chỉ đánh dấu hai cờ này bằng vàng; nền đen chưa bảo đảm pixel tốt. Vùng tím bên phải là số đo không dùng, gồm dữ liệu thiếu sẵn và pixel bị loại bởi toàn bộ cờ chất lượng đã chọn, nên có thể rộng hơn vùng vàng giữa. Đã kiểm tra pixel mang hai cờ này thực sự thành NaN trước nội suy.

**Bước C4 — xuất khung từng mục tiêu và kiểm tra lại.** Sau mask, chạy lại cùng quy trình căn TAN, median và ảnh hiệu. Đọc lại file kết quả để kiểm tra tâm, đơn vị, số ảnh đóng góp và dấu phép trừ; kết quả trong [verification.json](../../data/five_targets/verification.json).

**Giới hạn:** các số 56/342 là tổng lượt pixel trên toàn cutout qua nhiều ảnh, không phải số pixel trời độc lập hoặc chắc chắn đều thuộc mục tiêu. Mask chỉ tránh dùng số đo xấu, không khôi phục ánh sáng đã bão hòa.

### 4. Task phụ là gì, ảnh hưởng gì?

**+ Ảnh màu giả ghép 3 detector.** Đưa các khung đã có vào ba kênh màu theo quy tắc **R=D6, G=D3, B=D1**: cảm biến bước sóng dài hơn được gán đỏ, ngắn hơn được gán xanh lam.

Ghép các khung cùng nhóm thời gian trên cùng TAN; giữ cùng thang từng kênh qua các đợt. Chỉ hiển thị nơi cả ba kênh có dữ liệu tốt, tím là thiếu/bị mask.

![Ảnh màu giả Barnard, đỏ từ D6, lục từ D3, lam từ D1](../../data/five_targets/barnard/frames/rgb_visit01.png)

**Cách đọc hình:** đây là dữ liệu của ba cảm biến hồng ngoại được tô màu để nhìn chung trong một ảnh. Vùng tím giữa nguồn là phần không có đủ dữ liệu tốt, không phải màu thật của sao.

**Ảnh hưởng:** giúp nhìn vị trí và hình dạng nguồn ở các detector trong một khung; không làm dữ liệu gốc chính xác hơn, không thay đổi phép median/ảnh hiệu. Màu không phải màu mắt người thấy hay thước đo nhiệt độ, vì các kênh không đồng thời và có thể trộn nhiều bước sóng.

**Kết quả bộ C:**

| Mục tiêu       | Cutout | Khung median | Ảnh hiệu |    RGB |
| -------------- | -----: | -----------: | -------: | -----: |
| Barnard        |     12 |            6 |        3 |      2 |
| Epsilon Indi B |     18 |            9 |        6 |      3 |
| WISE 0855      |     18 |            9 |        6 |      3 |
| RW Aurigae     |     12 |            6 |        3 |      2 |
| R Draconis     |     18 |            9 |        6 |      3 |
| Tổng           | **78** |       **39** |   **24** | **13** |

Các cột là đầu vào và sản phẩm ở nhiều bước, không phải các phần chia của tổng cutout. Ví dụ Barnard: 12 cutout → 6 median; cùng 6 median tạo 3 ảnh hiệu và 2 RGB. Vì vậy 6 + 3 + 2 = 11 sản phẩm không có nghĩa thiếu một cutout. `SOURCE`/`FULLSAMPLE` tự nó không khiến pixel bị loại, và không được tô màu riêng trên ảnh độ sáng: pixel vẫn hiện thang xám nếu không có cờ xấu đồng thời. SOURCE chỉ báo vị trí nguồn đã biết, chưa bảo đảm số đo tốt hay phát hiện mục tiêu.

Muốn xem cả năm mục tiêu cạnh nhau, mở [ảnh tổng quan](../../data/five_targets/overview.png): mỗi hàng là một mục tiêu, hai cột đầu là khung D3 đợt đầu/cuối, cột cuối là màu giả đợt cuối.

**Mã C:** [five_targets.py](five_targets.py).

## D. Cutout → khung PNG và ảnh hiệu — 08/11

### 1. Thuật ngữ cần hiểu trước

| Từ trong đề                     | Hiểu đơn giản                                                                                                              |
| ------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| Dựng lại                        | Tự viết lại phần xử lý trong thư mục mới, không chép mã cũ, rồi chạy ra kết quả. Khác với chỉ chạy lại một script đã viết. |
| Thời gian chạy                  | Máy mất bao lâu để đọc dữ liệu, xử lý, lưu sản phẩm và kiểm tra. Không bao gồm thời gian người học viết mã.                |
| PNG (Portable Network Graphics) | Ảnh để xem; đã kéo giãn độ sáng. Không dùng số màu PNG để đo quang hoặc trích phổ.                                         |
| Bàn giao                        | Đưa file và cách dùng cho người nhận; cần phân biệt sản phẩm của mình với phần người khác chưa xác nhận.                   |

### 2. Task chính yêu cầu gì?

**− Cutout → khung PNG + ảnh hiệu, dưới 1,5 giờ.**

Theo lộ trình, đây là bài **tự dựng lại trong thư mục mới, không chép mã cũ và bấm giờ từ lúc bắt đầu dựng**. Ngưỡng 90 phút là thời gian thực hành của Hữu Hoàng, không phải chỉ thời gian chạy Python. Demo dưới đây chứng minh đầu vào thật chạy tới sản phẩm; **chưa chốt đạt bài tự dựng lại 90 phút**.

### 3. Từng thao tác đã làm và minh chứng

**Bước D1 — kiểm tra đầu vào từ nhóm trước.** Đã `git pull --ff-only origin huu-hoang`: nhánh đã cập nhật tại `9c30daf455b3476fe89532aa9e87d212a644de3c`. Đã kiểm tra danh sách nhánh GitHub và tải nhánh `nguyen/day03-04` để đọc, tại commit `9a80481568ef2263fb8027ca579fd9200f379820`; không gộp nhánh này vào mã đang làm.

Nguyên **đã có** bảng mục tiêu, kỳ vọng v0, dự báo chuyển động theo các survey suy ra từ tài liệu, ghi chú flags và hàm chuyển động riêng. **Chưa thấy** runbook trích phổ Luhman 16, checklist cho bài F hoặc bảng kỳ vọng v1 được xác nhận. Không được diễn giải là Nguyên chưa làm khoa học. Trên các nhánh đã công bố **chưa thấy mã tải/DB hay fixture của Khôi**; không kết luận về file riêng hoặc Drive chưa truy cập. Truy vấn issue của repo trả rỗng ở lần kiểm tra này.

Nguồn Nguyên: [ANALYSIS.md](https://github.com/HoangKhoi1704/NASA-space-challenges-PlanetXvsSphereX/blob/9a80481568ef2263fb8027ca579fd9200f379820/members/nguyen/day03-04/ANALYSIS.md), [FLAGS.md](https://github.com/HoangKhoi1704/NASA-space-challenges-PlanetXvsSphereX/blob/9a80481568ef2263fb8027ca579fd9200f379820/members/nguyen/day03-04/FLAGS.md). Bản chụp để đọc offline nằm trong `data/tasks_def/dependencies/`, có commit và đường dẫn gốc trong `source.json`.

**Bước D2 — demo thay đầu vào còn thiếu của Khôi.** Dùng các cutout FITS thật đã tự tải từ IRSA ở C, kèm danh sách `inputs.json` và SHA256 (mã kiểm tra nội dung file). Đây là dữ liệu tải từ kho, không phải ảnh PNG lấy ngược từ demo. Không giả danh fixture chính thức của Khôi, không báo đã có DB của Khôi.

**Bước D3 — xuất vào thư mục riêng và kiểm tra.** [task_d.py](task_d.py) đọc cutout, che flags, đưa về TAN chung, median theo detector × nhóm thời gian, xuất PNG/FITS và ảnh hiệu. Ảnh hiệu = **đợt hiện tại trừ đợt liền trước** trong cùng detector; không mặc định mọi đợt trừ đợt đầu. Script đọc lại FITS để kiểm tra tâm WCS (World Coordinate System — hệ tọa độ ảnh), vùng thiếu theo NVALID (số ảnh hợp lệ đóng góp) và giá trị phép trừ; xác nhận PNG có trên đĩa.

| Mục tiêu  | Cutout đầu vào | Median | Ảnh hiệu | Thời gian chạy đo lần đầu |
| --------- | -------------: | -----: | -------: | ------------------------: |
| WISE 0855 |             18 |      9 |        6 |          khoảng 3,27 giây |
| Barnard   |             12 |      6 |        3 |          khoảng 2,03 giây |

Đây là số lượng ảnh, không phải số nguồn phát hiện. Hai ảnh cùng detector/cùng đợt tạo một median; các median lại được dùng để tạo ảnh hiệu. Không cộng cột median và ảnh hiệu để đối chiếu tổng cutout. WISE có 3 nhóm thời gian, Barnard có 2; nhóm là khoảng quan sát được chia theo ngưỡng gián đoạn 30 ngày của bộ C, **chưa đổi thành nhãn survey chính thức của Nguyên**.

Thời gian trên bao gồm đọc FITS cục bộ, kiểm SHA256, mask, reproject, ghép, lưu PNG/FITS và kiểm tra đầu ra trong script; chưa gồm tải mạng, import/khởi động Python hay người viết mã. Xem số đo lần chạy hiện tại ở [report.json](../../data/tasks_def/D/report.json). Máy/tải hệ thống khác sẽ cho thời gian khác; không cộng vào bảng 6 người như kết quả tự dựng lại.

![Barnard D3 đợt đầu, dựng lại từ cutout thật](../../data/tasks_def/D/barnard/D3_visit00.png)

**Cách đọc:** thang xám là độ sáng MJy/sr (megajansky trên steradian, độ sáng trên một góc khối); tím là pixel thiếu hoặc bị mask, không phải nguồn sáng màu tím. Tâm khung là tọa độ yêu cầu, chưa phải vị trí nguồn đo được.

![Ảnh hiệu Barnard D3, đợt sau trừ đợt trước](../../data/tasks_def/D/barnard/D3_visit01_minus_D3_visit00.png)

**Cách đọc:** đỏ là giá trị hiệu dương, xanh lam là âm; giá trị gần 0 ở giữa thang màu. Trong bản A–D, vùng NaN trên ảnh hiệu có thể hiển thị trắng do colormap mặc định, cần xem FITS/mask để phân biệt; E sẽ sửa màu thiếu cho thống nhất. Khác biệt bước sóng, PSF (Point Spread Function — hình ảnh của nguồn điểm), nền hoặc căn ảnh đều có thể tạo vệt. Chưa dùng ảnh này để khẳng định Barnard chuyển động hoặc biến quang.

**Bước D4 — lộ trình tự dựng lại để chốt 90 phút.** Bắt đầu đồng hồ trước khi tạo thư mục/mã mới; ghi môi trường và đầu vào. Dự kiến 0–15 phút đọc manifest/FITS/flags; 15–40 phút tạo TAN và reproject; 40–60 phút median/NVALID; 60–75 phút PNG cùng thang và ảnh hiệu đúng dấu; 75–90 phút đọc lại kiểm và ghi kết quả. Đây là phân bổ đề xuất, **không phải thời gian đã thực hiện**. Nếu không xong, ghi thời gian thật và lỗi, không đổi tiêu chí thành benchmark máy.

### 4. Task phụ là gì, ảnh hưởng gì?

**+ Vòng 1 học trích phổ từ Nguyên; vòng 2 học tải dữ liệu từ Khôi.**

| Vòng       | Khi người sở hữu bàn giao                                                                                                  | Demo trong lúc chưa có                                                                            | Người học cần tự chạy lại                                                                  |
| ---------- | -------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| 1 — Nguyên | Nhận runbook trích phổ, quy tắc chọn ảnh/bước sóng, mask, nền, đơn vị, sai số và checklist; đối chiếu với ghi chú v0 đã có | Bài F sẽ đọc bước sóng từ WCS phổ và thử đo aperture trên FITS gốc; ghi rõ chưa được Nguyên duyệt | Đổi ảnh đầu vào, kiểm điểm phổ và giải thích vì sao không đo từ PNG/median nhiều bước sóng |
| 2 — Khôi   | Nhận mã SIA2/cutout, manifest/DB, collection và chính sách timeout/retry                                                   | Dùng `five_targets.py --download --target barnard` hoặc `--target wise-0855`; mã tự tải đã có ở C | Tìm ảnh → tải cutout → kiểm HDU/obs_id/detector/đơn vị → lưu nguồn tải và SHA256           |

Theo lộ trình, mỗi vòng 50 phút, mỗi chiều dạy 25 phút; Hữu Hoàng còn dạy Nguyên cộng ảnh và dạy Khôi đọc FITS/che flags. Demo độc lập không thay thế việc hai bên học và tự chạy lại; trạng thái buổi dạy chéo vẫn **chưa xác nhận**.

### 5. Chốt task D: đạt gì, thiếu gì, tiếp theo làm gì?

**Đã đạt phần kỹ thuật độc lập:** PNG thật và ảnh hiệu của WISE 0855/Barnard được dựng từ cutout trong thư mục riêng; các kiểm tra đầu ra của script đạt. Chạy lại bằng:

```powershell
.venv/Scripts/python.exe members/huu-hoang/task_d.py
```

**Chưa đủ để chốt mốc 8/11 của cả nhóm:** chưa có thời gian tự dựng lại của Hữu Hoàng/5 người còn lại; chưa xác nhận PNG do Khôi làm; chưa có xác nhận kỳ vọng v1 và hai vòng dạy chéo. Không ghi kết quả giả tưởng thành kết quả thật.

| Người     | Kết quả cần đưa vào bảng retro                         | Trạng thái kiểm được ở đây                     |
| --------- | ------------------------------------------------------ | ---------------------------------------------- |
| Thạch     | Aladin + Gaia dưới 60 phút                             | Chưa nhận số đo                                |
| Duy Hoàng | Viewer + mock dưới 90 phút                             | Chưa nhận số đo                                |
| Đông      | Mock API + cache dưới 60 phút                          | Chưa nhận số đo                                |
| Khôi      | SIA2 → cutout → DB Barnard dưới 60 phút; PNG thực hành | Chưa nhận số đo/sản phẩm                       |
| Hữu Hoàng | Tự dựng cutout → PNG + ảnh hiệu dưới 90 phút           | Có demo kỹ thuật; chưa đo bài tự dựng          |
| Nguyên    | Kiểm 5 mục tiêu theo kỳ vọng dưới 60 phút; kỳ vọng v1  | Có tài liệu v0 và audit; chưa xác nhận mốc này |

**Sau khi nhận bàn giao:** giữ nguyên dữ liệu demo để đối chiếu, kiểm schema và định danh dữ liệu của Khôi trước khi tạo manifest tương thích; chạy lại D trên đầu vào của Khôi vào thư mục mới. Nhận Nguyên kiểm quy tắc chọn ảnh/bandpass và ghép kết quả theo obs_id; không gán cluster 30 ngày thành survey của Nguyên chỉ bằng tên. Bàn giao cho Khôi/Đông đường dẫn PNG/FITS/report, ngày chụp, detector, thang hiển thị, vùng thiếu và giới hạn khoa học. Tiếp theo E sửa lỗi theo issue thực tế; chưa có issue thì kiểm tra chủ động và ghi rõ đó là lỗi tự phát hiện.

## E. Sửa căn ảnh/kéo giãn và thử tìm cặp sáng–tối — lịch 09/11

### 1. Thuật ngữ cần hiểu trước

| Thuật ngữ          | Hiểu đơn giản                                                                                                                                                                                                |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Issue              | Phiếu lỗi có cách tái hiện, kết quả mong muốn, kết quả thực tế và người phụ trách.                                                                                                                           |
| Stretch / kéo giãn | Đổi cách ánh xạ số đo thành độ sáng/màu để nhìn; không đổi số đo trong FITS.                                                                                                                                 |
| Cặp sáng–tối       | Hai vùng hiệu trái dấu ở gần nhau. Nếu ảnh sau trừ ảnh trước, vị trí mới của nguồn di chuyển có thể dương và vị trí cũ có thể âm; nhiều lỗi cũng tạo hình tương tự.                                          |
| photutils          | Thư viện Python xử lý/đo nguồn thiên văn; ở đây dùng `find_peaks` để tìm cực đại của ảnh hiệu và của ảnh đổi dấu.                                                                                            |
| MAD / sigma        | Median Absolute Deviation — độ lệch tuyệt đối trung vị; `mad_std` quy đổi thành ước lượng độ phân tán kiểu sigma. Đây là ngưỡng phát hiện thực hành, không phải sai số đo flux hoặc xác suất phát hiện đúng. |

### 2. Task chính yêu cầu gì?

**− Sửa lỗi căn ảnh, kéo giãn theo issue.**

Task này cần issue từ buổi tích hợp của Thạch/Nguyên và app của nhóm để nghiệm thu. Lần kiểm GitHub 08/11 trả rỗng; vì vậy **chưa có căn cứ ghi đã sửa xong các issue tích hợp ngày 09/11**. Phần độc lập làm được ngay là chạy kiểm tra tọa độ đã có và kiểm tra cách hiển thị dữ liệu thiếu.

### 3. Từng thao tác đã làm và minh chứng

**Bước E1 — giữ kiểm tra căn ảnh và thang màu.** Các kiểm tra A/B tiếp tục kiểm tâm/hướng tọa độ, ảnh xoay/lệch và phép median/trừ. Demo dữ liệu thật ở A đo lệch tương đối các nguồn nền; không ép mục tiêu chuyển động về giữa. `frames.py` đã dùng chung ngưỡng percentile 2/99,5 và asinh cho các đợt của một detector, dùng thang hiệu đối xứng ±percentile 99 của trị tuyệt đối. Đây là tham số hiển thị thực hành đã dùng, chưa phải tham số cuối được cả nhóm duyệt. Không tự dịch ảnh thật khi chưa có bằng chứng lỗi căn từ issue.

**Bước E2 — sửa lỗi tự phát hiện: màu của vùng không có số đo trên ảnh hiệu.** Bản A–D dùng `RdBu_r` mặc định: NaN (Not a Number — không có số đo hữu hạn) có thể hiện trong suốt/trắng, dễ bị hiểu nhầm thành hiệu gần 0. Đã sửa trong [frames.py](frames.py) để NaN hiện tím `#703090`, thống nhất với ảnh median. Chỉ đổi hiển thị; không điền số 0 và không đổi phép trừ FITS.

![Cùng một ảnh hiệu trước/sau sửa màu vùng thiếu](../../data/tasks_def/E/missing_before_after.png)

**Cách đọc:** hai ô dùng cùng mảng số đo và cùng giới hạn thang. Bên trái là cách vẽ cũ, bên phải tô tím nơi không có dữ liệu. Trắng ở thang đỏ–lam có thể là hiệu gần 0; tím ở ô phải mới là số đo không dùng. Không được hiểu nhiều tím hơn là nguồn tối đi hoặc sửa xong căn ảnh.

**Bước E3 — khi có issue thật.** Nhận obs_id, detector, ngày, PNG/FITS gốc, tâm/FOV, cách tái hiện và ảnh trước/sau mong đợi. Nếu sao nền nhảy: đối chiếu WCS, mask, bước sóng và centroid trên cùng cặp ảnh, kiểm lại bằng nguồn nền độc lập trước khi đổi phép căn. Nếu nhấp nháy do thang màu: kiểm cùng thang qua các đợt, outlier, vùng thiếu và ngày chụp. Lưu minh chứng trước/sau và ngưỡng kiểm; chạy lại cặp gây lỗi rồi nhờ người báo lỗi nghiệm thu trên app. Không đóng issue chỉ vì PNG nhìn đẹp hơn.

### 4. Task phụ là gì, ảnh hưởng gì?

**+ Thử tự phát hiện cặp sáng–tối trên ảnh hiệu bằng photutils.**

[tasks_def.py](tasks_def.py), nhánh chạy `E`: đọc **FITS hiệu chưa stretch**, lấy median nền và MAD từ pixel hữu hạn; tìm đỉnh dương trên ảnh và đỉnh âm trên ảnh đổi dấu. Loại lân cận vùng NaN bằng phép nở mask 2 pixel, bỏ mép 2 pixel; cửa sổ tìm đỉnh 5×5, ngưỡng 5 sigma. Ghép hai đỉnh trái dấu cách nhau trên 0 đến 8 pixel, ưu tiên khoảng cách nhỏ, mỗi đỉnh chỉ dùng một lần. Đây là cấu hình để thử thuật toán; chưa được tối ưu cho PSF hoặc khoảng dịch chuyển từng mục tiêu. Khoảng cách là giữa pixel cực trị, chưa phải centroid nguồn chính xác.

**Kết quả lần chạy:** 9 ảnh hiệu thật của bộ D (6 WISE + 3 Barnard) cho tổng **58 cặp ứng viên** trên toàn các khung. Đây là số cặp do thuật toán ghép, không phải 58 vật thể mới, không phải 58 lần phát hiện hai mục tiêu. Cùng nguồn có thể lặp qua detector/đợt. Bộ ảnh chưa khớp PSF/bandpass/nền nên các ứng viên chưa có nhãn đúng/sai và chưa có đánh giá precision/recall.

![Ca giả lập đã biết chuyển động và ảnh hiệu thật](../../data/tasks_def/E/dipoles.png)

**Cách đọc:** trái là dữ liệu tự tạo, có một nguồn âm ở (26,29) và dương ở (31,29), dịch 5 pixel; thuật toán tìm được một cặp đúng vị trí. Phải là ảnh hiệu thật, các đoạn xanh lá nối ứng viên âm/dương, chưa chỉ ra danh tính mục tiêu. Đỏ/lam biểu diễn hiệu dương/âm; tím là dữ liệu thiếu. Giả lập chỉ kiểm thuật toán có chạy đúng với tình huống đã biết, không chứng minh ảnh thật có chuyển động.

Kiểm tra tự động bổ sung: ca không có dịch chuyển chỉ có nhiễu không tạo cặp ở seed thử; đỉnh cạnh NaN không trở thành ứng viên. Đây là vài ca kiểm soát, không phải đo tỷ lệ báo giả trên mọi dữ liệu. Tham số và từng cặp lưu trong [report.json](../../data/tasks_def/E/report.json).

**Ảnh hưởng:** trợ giúp khoanh vùng để người xem kiểm tra; chưa thay thế kết luận của Nguyên và chưa nối thành tính năng trên app.

### 5. Chốt task E: đạt gì, thiếu gì, tiếp theo làm gì?

**Đã đạt:** sửa nhất quán màu dữ liệu thiếu, có hình trước/sau; chạy thử tìm cặp trái dấu trên FITS thật và ca giả lập, có kiểm tra chống dùng vùng mask. **Chưa đạt:** sửa/đóng issue tích hợp thực tế, xác nhận tham số cuối với Nguyên, xác nhận ứng viên thuộc mục tiêu và nghiệm thu viewer. Sau khi có issue/bảng kỳ vọng, đối chiếu vị trí/hướng/khoảng dịch dự báo, loại sai khác PSF/bước sóng/nền và chốt tham số vào runbook cùng người báo lỗi.

```powershell
# D phải chạy trước để có FITS hiệu. Nếu đã có, chỉ cần lệnh E.
.venv/Scripts/python.exe members/huu-hoang/task_d.py
.venv/Scripts/python.exe members/huu-hoang/tasks_def.py E
```

## F. Trích phổ và kiểm khoa học Luhman 16 — lịch 10/11

### 1. Thuật ngữ cần hiểu trước

| Thuật ngữ             | Hiểu đơn giản                                                                                                                        |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Phổ                   | Độ sáng theo bước sóng; cần nhiều số đo tương thích. Ba detector được tô RGB không tự trở thành phổ.                                 |
| WCS phổ               | Thông tin đổi vị trí pixel thành bước sóng và độ rộng dải đo. Ở FITS này là WCS thay thế khóa `W`, dùng bảng `WCS-WAVE`.             |
| Aperture / khẩu độ đo | Vùng tròn gom tín hiệu quanh tọa độ mục tiêu; không phải lỗ mở vật lý của kính.                                                      |
| Annulus / vành đo nền | Vành tròn bên ngoài khẩu độ để ước lượng nền cần trừ. Pixel nền phải phù hợp, không lấy nguồn lân cận làm nền.                       |
| Flux; mJy             | Mật độ thông lượng nhận từ nguồn; mJy là millijansky. IMAGE dùng MJy/sr là độ sáng bề mặt, cần nhân góc khối pixel trước khi ra mJy. |
| Forced photometry     | Đo tại vị trí dự đoán ngay cả khi chưa tìm thấy nguồn rõ; ra số đo chưa có nghĩa xác nhận phát hiện đúng nguồn.                      |

### 2. Task chính yêu cầu gì?

**− Trích phổ + kiểm theo checklist khoa học cho Luhman 16, làm mảnh của Nguyên.**

Luồng ngày đổi vai: **Đông tải cutout theo mảnh của Khôi → Khôi dựng PNG/ảnh hiệu theo mảnh của Hữu Hoàng; Hữu Hoàng dùng FITS gốc và runbook của Nguyên để thử trích phổ → Nguyên kiểm kết quả**. Nhánh ảnh và nhánh phổ dùng chung FITS; không trích phổ từ PNG của Khôi hay từ median trộn nhiều bước sóng.

Theo lộ trình, tự làm trong 90 phút, người sở hữu chỉ quan sát, sau đó sửa runbook. Demo AI chuẩn bị trước không xác nhận Hữu Hoàng đã vượt bài đổi vai hoặc đã quan sát Khôi.

### 3. Từng thao tác đã làm và minh chứng

**Bước F1 — xử lý bàn giao còn thiếu bằng demo riêng.** Chưa thấy cutout Luhman của Đông, sản phẩm xử lý ảnh của Khôi hoặc runbook trích phổ của Nguyên trên các nhánh đã kiểm. Đã dùng `resolve`/`acquire_target` của mã C để tự truy vấn SIMBAD và tải cutout IRSA QR2 cho `WISE J104915.57-531906.1` (Luhman 16). Đây là dữ liệu thiên văn thật, không phải phổ giả dùng thay kết quả thật. Bộ này chọn **18 cutout: 3 nhóm thời gian × 3 detector D1/D3/D6 × tối đa 2 ảnh**, chưa lấy đủ detector hoặc đủ kênh phổ.

Tâm tìm kiếm J2026 khoảng RA **162,295356°**, Dec **−53,316884°**, FOV **0,1°**. Tâm tìm kiếm giữ cố định cho bộ ảnh; khi đo từng FITS, vị trí dự đoán được đẩy từ J2000 tới MJD của bản ghi. Chưa tính thị sai/quỹ đạo hệ đôi/vận tốc xuyên tâm; vị trí này chưa phải centroid đo từ ảnh. Luhman là hệ đôi: phép đo thực hành không tuyên bố phân giải hay tách phổ từng thành phần.

Nguồn và dấu kiểm file: [target.json](../../data/five_targets/luhman-16/target.json), [inputs.json](../../data/five_targets/luhman-16/inputs.json), `catalog.xml`, `simbad.txt` trong cùng thư mục. File đầu vào tự tải không có nghĩa đã hoàn thành DB của Đông/Khôi.

**Bước F2 — thử trích từng mẫu trên FITS gốc.** Kiểm SHA256, obs_id, detector, đơn vị IMAGE và VARIANCE (phương sai số đo). Đọc WCS không gian và WCS phổ tại vị trí dự đoán; giữ `SOURCE`/`FULLSAMPLE` khi đo nguồn, loại các cờ chất lượng đã chọn. Đo khẩu độ tròn bán kính 2 pixel bằng trọng số diện tích của photutils; đòi toàn bộ khẩu độ có số đo/phương sai hợp lệ và nằm trong ảnh. Không điền lõi mất số đo hay sửa bằng tỷ lệ diện tích còn lại.

Nền thử bằng median trong vành 4–7 pixel, bỏ pixel xấu **và pixel có SOURCE**, cần ít nhất 20 pixel nền dùng được. Khác với đo nguồn, loại `SOURCE` khỏi mẫu nền giúp tránh gom nguồn khác vào nền. Các bán kính/ngưỡng là lựa chọn demo, chưa được Nguyên duyệt theo PSF/crowding (nguồn chen chúc).

Nếu mẫu đạt, tính tổng có trọng số sau trừ nền, nhân diện tích pixel chiếu xấp xỉ theo WCS: `mJy = tổng(MJy/sr × trọng số) × diện tích_pixel(sr) × 10^9`. Sai số gồm VARIANCE gốc với bình phương trọng số và ước lượng sai số median nền; chưa có hiệu chỉnh PSF/aperture, sai số hiệu chuẩn, biến thiên nền hoặc mô hình hệ đôi. Không lấy error này làm toàn bộ sai số khoa học. Script giữ bước sóng/độ rộng dải/thời điểm từng ảnh, không nối đường qua các khoảng bước sóng không đo.

**Bước F3 — kết quả thật và lý do không có phổ dùng được.**

| Trạng thái mẫu đầu vào                                   | Số cutout | Ý nghĩa                                                                                            |
| -------------------------------------------------------- | --------: | -------------------------------------------------------------------------------------------------- |
| Thiếu nền hợp lệ (`insufficient_background`)             |        11 | Sau loại SOURCE và pixel xấu, vành thử không đủ 20 pixel nền; các mẫu này có 0 pixel nền dùng được |
| Khẩu độ bị mask/không đầy đủ (`masked_or_edge_aperture`) |         6 | Không đủ diện tích có số đo hợp lệ trong khẩu độ; không tự bù phần mất                             |
| Không có khẩu độ chồng lên ảnh (`outside_image`)         |         1 | Không có vùng khẩu độ đo được trong mảng ảnh trả về; cần kiểm footprint/cutout                     |
| Đạt điều kiện demo (`ok`)                                |     **0** | **Chưa có điểm phổ thật đủ điều kiện để vẽ/diễn giải**                                             |
| Tổng đầu vào                                             |    **18** | Mỗi ảnh được phân loại theo lý do dừng đầu tiên; không cộng nhiều lỗi của một ảnh                  |

Điều này không chứng minh Luhman 16 không tồn tại hoặc không có phổ. Nó cho thấy **bộ chọn ảnh và cách đo nền demo hiện chưa đủ**. Không giảm tiêu chí hoặc dùng pixel SOURCE làm nền chỉ để có đường phổ. File [samples.ecsv](../../data/tasks_def/F/samples.ecsv) vẫn lưu các lần thử/bước sóng/trạng thái; [report.json](../../data/tasks_def/F/report.json) có số đo kiểm tra và giới hạn. Bước sóng được đọc thành công không đồng nghĩa flux tại đó hợp lệ.

![Minh chứng khẩu độ và mặt nạ nguồn ở cutout đầu tiên](../../data/tasks_def/F/background_qa.png)

**Cách đọc:** ô trái là ảnh gốc; vòng xanh lá là khẩu độ đo, hai vòng cam giới hạn vành nền. Ô phải tô **đen** nơi mang SOURCE, **trắng** nơi không mang SOURCE; đây là bản đồ cờ, không phải thang độ sáng hay bản đồ pixel lỗi. Vành nền trong ví dụ nằm trong vùng SOURCE nên không còn pixel phù hợp với quy tắc nền thử. Một cờ hữu ích cho nhận diện nguồn vẫn có thể cần loại khỏi phép **đo nền**.

**Bước F4 — ca kiểm soát khi chưa đo được ảnh thật.** `synthetic_control.json` chứa nguồn Gaussian giả lập trên nền hằng 10, phương sai 1; không đặt tên là phổ Luhman. Phép đo trả trạng thái `ok`, trừ đúng nền; kiểm thử riêng tiêm thêm tín hiệu 100 vào một pixel thu lại tổng 100, và loại phép đo nếu lõi thành NaN hoặc khẩu độ chạm biên. Ca này giúp học công thức và kiểm mã, không thay thế 18 mẫu thật bị loại.

**Bước F5 — thử phương án độc lập khi nền gần không dùng được.** Giữ nguyên kết quả cơ sở ở `F/`; chạy thí nghiệm riêng `F_wide/` với vành nền **12–25 pixel**, vẫn bỏ SOURCE/pixel xấu, đòi tối thiểu 20 pixel nền và toàn khẩu độ hợp lệ. Không điền pixel thiếu, không hạ ngưỡng. Vành xa hơn giúp thử lấy nền ở khoảng trống ngoài vùng SOURCE gần mục tiêu; đổi lại nền có thể không đại diện vùng nguồn và bị ảnh hưởng gradient/bước sóng LVF, nên cần Nguyên kiểm lại.

Thí nghiệm này cho **5/18 mẫu đạt điều kiện số học**: 3 D1 và 2 D6; 6 mẫu thiếu nền, 6 khẩu độ không đầy đủ, 1 không có khẩu độ trên ảnh. Không có mẫu D3 đạt. Xem [report.json thí nghiệm](../../data/tasks_def/F_wide/report.json) và [samples.ecsv](../../data/tasks_def/F_wide/samples.ecsv). Hai kết quả 0/18 và 5/18 dùng **cùng 18 đầu vào nhưng khác vùng đo nền**, không cộng thành 36 ảnh hay 5 phát hiện khoa học.

![Năm mẫu đo thử trên FITS thật, vành nền rộng](../../data/tasks_def/F_wide/spectrum.png)

**Cách đọc:** trục ngang là bước sóng tại vị trí dự đoán, trục đứng là flux khẩu độ chưa hiệu chỉnh, đơn vị mJy. Chấm xanh lam từ D1, xanh lá từ D6; có thanh sai số tính từ mô hình demo nhưng nhỏ ở tỷ lệ hình này. Không nối đường vì các điểm khác thời gian và có khoảng phổ trống lớn. Chưa có PSF/aperture correction và kiểm nguồn/nền nên **đây là mẫu đo thử theo bước sóng, chưa phải phổ chuẩn của Luhman 16**. Việc đổi cách đo nền tạo ra điểm đo là lý do phải bàn giao cả hai cấu hình cho Nguyên, không chọn cấu hình chỉ vì đường nhìn hợp lý hơn.

### 4. Task phụ là gì, ảnh hưởng gì?

**+ Xem Khôi làm mảnh xử lý ảnh.** Chưa có buổi thực hành/sản phẩm của Khôi để quan sát, nên chưa đánh dấu hoàn tất. Trong lúc chờ, Hữu Hoàng đã có [task_d.py](task_d.py) làm demo cutout → mask → TAN → median/NVALID → PNG/ảnh hiệu. Khi Đông bàn giao cutout, Khôi chạy mảnh đó; Hữu Hoàng ghi chỗ thiếu trong runbook: hiểu cờ, tâm/hướng, nhóm thời gian, giữ cùng thang, dấu ảnh hiệu, metadata và vùng thiếu. Không sửa hộ trong lúc bấm 90 phút; sau bài diễn tập mới bổ sung runbook theo lộ trình.

### 5. Checklist khoa học tạm, bàn giao và bước tiếp theo

Đây là **checklist đề xuất dựa trên tài liệu đã có của Nguyên và hướng dẫn IRSA**, chưa gắn nhãn “checklist của Nguyên đã duyệt”.

| Cần kiểm                                    | Kết quả demo                                                     | Việc còn lại                                                                             |
| ------------------------------------------- | ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Danh tính, epoch và vị trí theo thời gian   | Có SIMBAD, dự báo tới thời điểm ảnh                              | Nguyên xác nhận đúng hệ/thành phần, thị sai/quỹ đạo và tâm đo                            |
| Dữ liệu truy nguồn được, không đo từ PNG    | Có 18 FITS QR2, manifest, SHA256, obs_id/detector                | Thay bằng manifest chính thức của Đông/Khôi khi có; kiểm release và bản ghi trùng        |
| Bước sóng/bandwidth từng ảnh                | Đọc từ WCS phổ tại tọa độ đo                                     | Chọn thêm detector/ảnh, kiểm biến thiên bandpass trong aperture                          |
| Mask chất lượng và coverage                 | Có kiểm toàn khẩu độ; có mẫu bị loại                             | Kiểm footprint, chọn ảnh tránh phần mất dữ liệu; không khôi phục lõi bão hòa             |
| Nền không bị nguồn chi phối                 | Demo phát hiện không đủ nền ở 11 mẫu                             | Nguyên chọn nền xa hơn/FOV lớn hơn hoặc mô hình PSF+nền phù hợp trường chen chúc         |
| Đơn vị và bất định                          | Có công thức MJy/sr → mJy và variance gốc, kiểm số học           | Xác nhận pixel solid angle, PSF/aperture correction, hiệu chuẩn và hệ đôi                |
| Có điểm phổ thật đủ điều kiện               | Cơ sở 0/18; thí nghiệm nền rộng có 5/18 mẫu đạt điều kiện số học | Chưa qua kiểm khoa học; Nguyên kiểm nền/nguồn/phương pháp trước khi dùng các điểm này    |
| Kiểm phổ tham chiếu, đồng thời và đặc trưng | Chưa làm                                                         | Nguyên đối chiếu công cụ phổ IRSA, thời điểm, sai số; không suy nhiệt độ/phân tử từ demo |
| Bài đổi vai 90 phút và quan sát Khôi        | Chưa xác nhận                                                    | Hữu Hoàng tự làm theo runbook, ghi thời gian thật; Khôi/Nguyên ghi nhận và sửa runbook   |

**Sau khi nhận kết quả của họ:** Đông/Khôi đưa manifest/FITS và metadata collection, thời điểm, detector, footprint, flags, variance; Hữu Hoàng đối chiếu nguồn/đơn vị/SHA256 rồi dùng FITS gốc. Nguyên đưa runbook và quy tắc nền/khẩu độ/bước sóng, tiêu chí loại mẫu và chuẩn đối chiếu; Hữu Hoàng chạy lại trong thư mục mới, trả bảng mẫu có trạng thái, hình khẩu độ/nền và báo cáo kiểm cho Nguyên. Chỉ khi có điểm đo đạt kiểm và Nguyên duyệt mới chốt hoàn thành trích phổ khoa học. Nếu bị chặn quá 30 phút, ghi rõ chặn và làm demo/secondary theo lộ trình; không báo đã có kết quả của người khác.

**Chốt F:** đã chạy đường trích mẫu từ FITS thật cho mục tiêu mới, phát hiện cấu hình nền gần không dùng được, thử nền rộng và xuất 5 mẫu đo sơ bộ kèm phân loại lý do loại, ca kiểm soát và danh sách việc bàn giao. **Chưa có phổ được kiểm khoa học, chưa hoàn thành phần duyệt của Nguyên hoặc bài đổi vai của nhóm.** Hành động tiếp theo cụ thể là kiểm footprint mẫu không có khẩu độ, chọn ảnh ít mask và nhờ Nguyên đánh giá mẫu nền gần/xa, PSF và định danh nguồn trước khi tải thêm hàng loạt.

```powershell
# Lần đầu tự tải dữ liệu Luhman 16 khi chưa có cutout bàn giao:
.venv/Scripts/python.exe members/huu-hoang/tasks_def.py F --download
# Khi đã có dữ liệu demo trên máy, chạy lại không dùng mạng:
.venv/Scripts/python.exe members/huu-hoang/tasks_def.py F
# Thí nghiệm nền xa, xuất riêng vào data/tasks_def/F_wide/:
.venv/Scripts/python.exe members/huu-hoang/tasks_def.py F --wide-background
# Kiểm số học, mask, ứng viên và các kiểm tra A/B:
.venv/Scripts/python.exe -m pytest members/huu-hoang/test_pipeline.py members/huu-hoang/test_tasks_def.py -q
```

Tham khảo cách đọc ảnh/WCS phổ: [IRSA Introduction to SPHEREx Spectral Images](https://caltech-ipac.github.io/irsa-tutorials/spherex-intro/); cách dùng trọng số khẩu độ và sai số: [photutils aperture photometry](https://docs.astropy.org/projects/photutils/en/stable/user_guide/aperture.html). Phương pháp demo có các lựa chọn riêng nêu trên, không coi đó là quy trình chuẩn chính thức IRSA.

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
