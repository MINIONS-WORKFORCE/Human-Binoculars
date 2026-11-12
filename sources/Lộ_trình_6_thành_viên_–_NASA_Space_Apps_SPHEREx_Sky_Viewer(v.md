**Làm sao để mọi thứ theo như kế hoạch trong docs?**
**Rule:**
*  Task không kéo quá 2 ngày
*  Vô meet thì mở mic (khuyến khích mở cam)
*  Không được leak src code
**Hình phạt:**
*  Vi phạm 1 trong rule trên (trừ leak code) thì:
*  Một lần nhắc nhở riêng
*  Hai lần lên meet chung nói chuyện (leak source thì kích mẹ luôn)
**Thái độ/ tinh thần:**
*   **Chủ động**
*   **Có trách nhiệm:**
*  Đảm bảo chất lượng (70%) trong công việc và hiểu đúng công mình đang làm gì!
*  Sai thì nhận sai và rút kinh nghiệm ko trốn tránh
*   **Luôn chia sẻ kiến thức:**
**Cách thức làm việc:**
1.  **Các buổi họp:**
2.  **Mục đích là gì (What)?**
*  Cập nhật tiến độ: Báo cáo những công việc đã làm (cập nhật tiến độ công việc) -> thất bại / thành công -> bài học để chuẩn bị cho hackathon
*  Báo cáo những sai sót -> Fixing như thế nào
*  Chia sẻ kiến thức cho nhau (Vô meet thì phải mở mic) -> Học được điều mới
2.  **Tổ chức buổi họp (How)?**
*  Thời lượng: 1h30
*  Mỗi người báo cáo 10’:
*  Những việc đã làm
*  Gặp vấn đề gì? Đạt được gì? Cần ai hỗ trợ không?
*  Bước đi tiếp theo
**2. Giao việc và dl**
*  Mỗi ngày đều là DL: 223h59 của ngày hôm đó là dl
*  Mỗi ngày 8h sáng Thạch sẽ thông báo task của ngày hôm đó
*  Mọi người phải đọc và ước lượng task có thể hoàn thành trong ngày không?  **DL cho việc này là 13h mỗi ngày**  Nếu không:
*  Ưu tiên: Nhờ người ai đó.
*  Thì bàn lại task đó cần bao lâu? Có cần phân tách nhỏ ra nữa, để mỗi ngày đều có cái để hoàn thành
###  **Lộ trình 6 thành viên – NASA Space Apps: SPHEREx Sky Viewer**
1. ####  **Đề bài & mục tiêu sản phẩm**
Nhóm 6 người có khoảng 39 giờ, từ 09:00 thứ Bảy 14/11 đến 23:59 Chủ nhật 15/11 theo giờ điểm thi, để làm và nộp một web tool công khai: nhập toạ độ RA/Dec → xem chuỗi ảnh SPHEREx của vùng trời đó chạy như video (blink) để phát hiện vật thể di chuyển hoặc đổi độ sáng. Sản phẩm chỉ được làm trong hai ngày này; 11 ngày chuẩn bị (3–13/11) chỉ để học và luyện. Khung giờ lấy theo [Project Submission Guide](https://www.spaceappschallenge.org/resources/project-submission-guide/), trang này hiện vẫn ghi ngày của năm 2025.
**Sản phẩm:**
*   **Đầu vào:**  RA/Dec (độ thập phân hoặc giờ–phút–giây), trường nhìn (FOV), detector.
*   **MVP bắt buộc:**  blink các khung ảnh theo thời gian, nhãn ngày chụp, play/pause/tốc độ, toạ độ nằm trong URL, 5 nút mục tiêu mẫu.
*   **Điểm cộng theo gợi ý của đề:**  cộng ảnh theo từng detector, trừ ảnh hai thời điểm, chọn FOV, overlay Gaia/WISE, cờ lỗi (flags), phổ tạo ngay trên web.
**Bài nộp phải có**  (bản hướng dẫn 2026 ra ngày 13/11 theo [Participant FAQs](https://www.spaceappschallenge.org/resources/participant-faqs/), kiểm tra lại hôm đó):
*  Toàn bộ nội dung bằng tiếng Anh.
*  Link demo công khai: 7 slide hoặc video tối đa 30 giây.
*  Link sản phẩm công khai, mô tả chi tiết, dữ liệu NASA đã dùng.
*  Danh sách mọi code, thư viện, hình ảnh và công cụ AI đã dùng; tick "Confirm All Work is Original"; bấm "Submit for Judging" trước hạn.
**5 mục tiêu kiểm thử bắt buộc**  (số liệu chuyển động là ước lượng, Nguyên kiểm lại trên SIMBAD):
| Mục tiêu | Loại | Cần thấy trong tool | Lưu ý kỹ thuật |
| ------ | ------ | ------ | ------ |
| WISE 0855 (08h55m10.831s, −07°14′42.53″ ≈ 133.7951°, −7.2451°) | Sao lùn nâu rất lạnh, chuyển động nhanh | Chấm sáng dịch chuyển giữa các đợt quét 6 tháng | Rất mờ ở bước sóng ngắn; kỳ vọng rõ nhất ở D5–D6 và cần cộng ảnh (cần kiểm chứng) |
| Barnard’s Star | Sao gần, chuyển động riêng ~10″/năm | Dịch khoảng 2 pixel SPHEREx (6,15″/pixel) qua ~1,5 năm | Sao sáng → coi chừng bão hoà (flag OVERFLOW); toạ độ J2000 phải đẩy theo chuyển động riêng |
| Epsilon Indi B | Cặp sao lùn nâu quay quanh sao Epsilon Indi A | Chuyển động chung với sao chủ | Chọn FOV đủ rộng để thấy cả A và B |
| RW Aurigae | Sao trẻ, biến quang bất thường | Độ sáng đổi giữa các khung | Cần thêm đường cong ánh sáng, blink thôi là chưa đủ |
| R Draconis | Sao biến quang kiểu Mira, chu kỳ ~8 tháng | Sáng/tối rõ theo mùa quan sát | Sao sáng → bão hoà, xem flags |

2. ####  **Kiến trúc kỹ thuật & tech stack**
Một backend Python làm toàn bộ phần nặng (tìm ảnh, cắt, ghép, cộng), trình duyệt chỉ nhận PNG và JSON để hiển thị. Đây là bản thiết kế để cả nhóm hiểu chung trước ngày thi; code viết mới từ giờ 0 trong repo dự thi.
kiến trúc đề xuất · 3 vùng, 10 khối
Trình duyệt gửi toạ độ; backend tìm ảnh qua SIA2, cắt cutout, đưa về lưới chung, cộng theo detector × đợt quét rồi trả PNG; riêng Aladin Lite tự tải nền và catalog Gaia từ CDS.
**Vì sao dễ cập nhật khi có dữ liệu mới**  ([IRSA Data Access](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access)):
*  Không lưu cứng danh sách ảnh: mỗi yêu cầu hỏi lại SIA2, nên dữ liệu nạp hàng tuần tự xuất hiện (SIA2 trễ khoảng một ngày so với thư mục duyệt).
*  Hiện có 4 collection: spherex_qr3, spherex_qr3_deep, spherex_qr2, spherex_qr2_deep; tên collection để trong file cấu hình.
*  Cutout lấy bằng cách thêm ?center=ra,dec&size=độ vào access_url, không bao giờ tải file gốc.
| Lớp | Công cụ | Người phụ trách |
| ------ | ------ | ------ |
| Pipeline dữ liệu | Python 3.11, astropy, numpy, reproject, photutils | Hữu Hoàng, Nguyên |
| Truy cập IRSA + database | astroquery, pyvo, SQLite cho metadata quan sát | Khôi |
| Backend | FastAPI + uvicorn, diskcache, Pillow | Đông |
| Frontend | React + Vite, Canvas 2D | Duy Hoàng |
| Bản đồ trời + biểu đồ | Aladin Lite v3, Chart.js hoặc Plotly | Thạch |
| Thiết kế + thuyết trình | Figma, công cụ slide của nhóm | Thạch |
| Deploy | Backend: Render, Fly.io hoặc Hugging Face Spaces; frontend: Vercel hoặc Netlify | Duy Hoàng, Đông |

Không dùng Next.js, Redis hay CI/CD như bản Gemini: chúng thêm việc cài đặt mà 39 giờ không có chỗ.
3. ####  **Phân vai 6 thành viên**
Vai chia theo chuyên ngành thật của 6 người. Primary, secondary, vòng dự phòng và task từng ngày nằm ở tab Task từng ngày.
| Người | Nền | Vai chính |
| ------ | ------ | ------ |
| Thạch | Fullstack | Frontend B + UI/UX + điều phối |
| Duy Hoàng | Fullstack | Frontend A + DevOps + testing |
| Đông | Backend | Backend API + cache |
| Khôi | Backend | Dữ liệu IRSA + database |
| Hữu Hoàng | AI | Xử lý ảnh |
| Nguyên | Computer science | Khoa học + phổ |

####  **Lộ trình chung 11 ngày (3–13/11)**
Timeline dưới đây là các giai đoạn chung; task từng người từng ngày nằm ở tab Task từng ngày. Cuối tuần 7–8/11 là lúc luyện nhiều nhất.
lộ trình 3–15/11 · 7 giai đoạn, 4 mốc
Mọi thứ trước 14/11 nằm trong repo đào tạo; repo dự thi tạo mới ở giờ 0.
**Mốc kiểm tra:**
*  [ ]  **4/11:**  6 máy chạy được dữ liệu SPHEREx; fixture pack v1 và hợp đồng API v0 đã lên drive
*  [ ]  **8/11:**  Khôi và Hữu Hoàng có PNG thật của WISE 0855 và Barnard; Nguyên có bảng kết quả kỳ vọng v1; đủ bảng thời gian dựng lại của 6 người
*  [ ]  **10/11:**  ngày đổi vai, cả 6 mảnh do người dự phòng làm ra kết quả trong 90 phút
*  [ ]  **13/11:**  checklist trước ngày thi hoàn tất, bảng Go/No-Go có xác nhận của cả 6 người
Trượt mốc 8/11 → Đông vào pair với Khôi, Nguyên vào pair với Hữu Hoàng, Duy Hoàng tiếp tục với mock. Trượt mốc 10/11 → mảnh nào chưa đạt thì người sở hữu bổ sung runbook và dạy lại ngay trong tối đó.
4. ####  **Rủi ro, dự phòng và checklist trước ngày thi**
Rủi ro lớn nhất là lần đầu chạy trọn chuỗi dữ liệu trong giờ thi bị lỗi hoặc IRSA chậm. Vì vậy nhóm phải luyện notebook trên dữ liệu thật từ trước và tạo bộ ảnh dự phòng ngay ở giờ 9–15.
| Rủi ro | Dấu hiệu sớm | Phương án |
| ------ | ------ | ------ |
| Chuỗi dữ liệu lỗi ở lần chạy đầu tiên trong giờ thi | Giờ 9 chưa có cutout | Dùng lại code notebook IRSA (ghi nguồn); Khôi + Hữu Hoàng cùng gỡ, Duy Hoàng tiếp tục với PNG thử |
| Thiếu giờ (39 giờ, không phải 48) | Giờ 24 chưa có MVP trên link công khai | Không mở điểm cộng; cắt theo luật ở phần kịch bản thi |
| Local Lead không cho mang wireframe hoặc ghi chú chuẩn bị | Hỏi trước 11/11 | Chỉ mang design system chung; vẽ lại wireframe ở giờ 0–3 |
| IRSA chậm hoặc sập lúc demo | Truy vấn trên 30 giây | Bộ ảnh dựng sẵn 5 mục tiêu (tạo ở giờ 9–15), video dự phòng |
| Quá nhiều ảnh cho một vị trí | Lần tải đầu trên 2 phút | Lọc theo detector, giới hạn số ảnh mỗi đợt, FOV mặc định theo bảng thời gian tải của Khôi |
| Lỗi CORS khi trình duyệt gọi IRSA trực tiếp | Lỗi CORS trong console | Mọi lệnh gọi IRSA đi qua backend |
| Sao sáng bị bão hoà (Barnard, R Draconis) | Lõi sao phẳng, flag OVERFLOW | Hiện lớp flags, giải thích trong app, gợi ý detector khác |
| Ảnh lệch nhau khi blink | Sao đứng yên vẫn “nhảy” | Kiểm tra bước reproject; Nguyên đối chiếu với Gaia |
| Bài nộp sai yêu cầu | Video dài hơn 30 giây, còn nội dung tiếng Việt | Thạch soát form theo mục “Bài nộp phải có” từ giờ 33 |
| Bản phát hành dữ liệu mới đổi tên collection | Truy vấn trả rỗng | Tên collection nằm trong file cấu hình; mặc định spherex_qr3, lùi về spherex_qr2 |
| Mạng yếu tại địa điểm thi | Tải cutout chậm bất thường | Phát 4G dự phòng |
| Kiệt sức | Lỗi ngớ ngẩn tăng sau nửa đêm | Ngủ 2 ca bắt buộc |

**Checklist hoàn thành trước tối 13/11:**
*  [ ] Đã đọc thể lệ và hướng dẫn nộp bài 2026; biết giờ bắt đầu và hạn nộp của điểm thi
*  [ ] Đã hỏi Local Lead về wireframe và ghi chú chuẩn bị
*  [ ] 6 máy chạy được notebook Introduction to SPHEREx Spectral Images
*  [ ] Repo đào tạo tách riêng; chưa tạo repo dự thi
*  [ ] Tài khoản deploy backend và frontend đã tạo, đã deploy thử bằng app học tập
*  [ ] Bảng kết quả kỳ vọng (Nguyên) và bảng số ảnh + thời gian tải (Khôi) cho 5 mục tiêu đã duyệt
*  [ ] Runbook của cả 3 người đã in hoặc lưu offline
*  [ ] Design system chung, bộ test case, dàn ý 7 slide và kịch bản video 30 giây (để trống)
*  [ ] Phân ca ngủ, đồ ăn, sạc, ổ cắm nối dài, 4G dự phòng
5. ####  **Tài liệu & nguồn tham khảo**
**Lộ trình gốc được gộp:**  bản Cẩm nang (Lo_trinh_NASA_SPHEREx_2026.docx), bản Gemini (GEMINI_PLANNING.docx) và bản 1/11 của tài liệu của Claude.
**Trang đã đọc để viết tài liệu này:**
*  [Project Submission Guide – NASA Space Apps](https://www.spaceappschallenge.org/resources/project-submission-guide/): khung giờ nộp bài và yêu cầu bài nộp (trang hiện ghi ngày của năm 2025)
*  [Participant FAQs – NASA Space Apps](https://www.spaceappschallenge.org/resources/participant-faqs/): sự kiện 14–15/11/2026, hướng dẫn nộp bài 2026 ra ngày 13/11
*  [SPHEREx Quick Release Overview – IRSA](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_qr.html): QR3 bắt đầu từ 9/2026, DOI 10.26131/IRSA662
*  [SPHEREx Data Access – SPHEREx Archive at IRSA](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access) (cập nhật 28/9/2026): SIA2, collection QR3/QR2, cutout, pyvo/astroquery, Data Explorer
*  [Introduction to SPHEREx Spectral Images](https://caltech-ipac.github.io/irsa-tutorials/spherex-intro): cấu trúc file, 6 detector, LVF, flags
*  [SPHEREx Tutorial Notebooks](https://caltech-ipac.github.io/irsa-tutorials/spherex): danh sách notebook chính thức
**Tài liệu học và tra cứu:**
*  [SPHEREx Spectral Image Cutouts](https://caltech-ipac.github.io/irsa-tutorials/spherex-cutouts) · [SPHEREx Cutout Capabilities](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/cutout_tool.html) · [SPHEREx Mosaic Cube](https://caltech-ipac.github.io/irsa-tutorials/spherex-mosaic)
*  [SPHEREx Explanatory Supplement (PDF)](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp_QR.pdf) · [SPHEREx Data Explorer](https://irsa.ipac.caltech.edu/applications/spherex) · [Trang SPHEREx tại IRSA](https://irsa.ipac.caltech.edu/Missions/spherex.html)
*  [Aladin Lite](https://aladin.cds.unistra.fr/AladinLite/doc) · [SIMBAD](https://simbad.cds.unistra.fr) · [Backyard Worlds](https://backyardworlds.org)
*  [Astropy Learn](https://learn.astropy.org) · [reproject](https://reproject.readthedocs.io) · [photutils](https://photutils.readthedocs.io) · [FastAPI](https://fastapi.tiangolo.com/tutorial/) · [React](https://react.dev/learn)
### Task từng ngày 3–13/11
*Mỗi người có một vai chính; mỗi ngày có task primary (phải xong) và secondary (làm khi xong sớm hoặc bị chặn). Bị chặn quá 30 phút thì chuyển sang secondary hoặc gọi một trong hai người đứng cạnh mình trong vòng dự phòng, không ai ngồi chờ. Mặc định: standup 19:30, bàn giao trước 22:30, Thạch điều phối (đổi nếu nhóm đã có trưởng nhóm), khoảng 3 giờ/ngày thường và 6 giờ/ngày cuối tuần. Mọi task là bài luyện trong repo đào tạo; sản phẩm chỉ làm trong 14–15/11.*
####  **Vai trò và vòng dự phòng**
Vai chia theo chuyên ngành thật: hai người frontend, hai người backend, hai người dữ liệu. Sáu người xếp thành một vòng; mỗi người đỡ hai người đứng cạnh, một người cùng mảng và một người khác mảng, nên mảng nào cũng có hai người biết làm.
| Người | Nền | Vai chính | Primary (sở hữu, phải xong) | Secondary (khi xong sớm hoặc bị chặn) | Đỡ cho |
| ------ | ------ | ------ | ------ | ------ | ------ |
| Thạch | Fullstack | Frontend B + UI/UX + điều phối | Figma, design system; Aladin Lite + overlay Gaia; biểu đồ phổ và đường cong ánh sáng; standup, quyết định cắt tính năng; slide và video | Kiểm thử thủ công theo QA matrix; nội dung giải thích tiếng Anh | Duy Hoàng (giao diện), Nguyên (nội dung khoa học) |
| Duy Hoàng | Fullstack | Frontend A + DevOps + testing | Viewer blink, form toạ độ, điều khiển, trạng thái tải/lỗi; repo, nhánh, deploy frontend và backend; smoke test tự động | Endpoint API mỏng | Thạch (Aladin, biểu đồ), Đông (API) |
| Đông | Backend | Backend API + cache | Hợp đồng API, FastAPI, job nền, cache, log; deploy backend cùng Duy Hoàng | Tải cutout song song, retry | Duy Hoàng (fetch phía frontend), Khôi (dữ liệu IRSA) |
| Khôi | Backend | Dữ liệu IRSA + database | Truy vấn SIA2, tải cutout, SQLite metadata, fixture pack, benchmark thời gian tải | Đọc FITS, che flags, xuất PNG từng ảnh | Đông (API, cache), Hữu Hoàng (xử lý ảnh) |
| Hữu Hoàng | AI | Xử lý ảnh | Căn ảnh về lưới chung, che flags, cộng ảnh theo detector × đợt quét, ảnh hiệu, kéo giãn, PNG | Tự phát hiện cặp sáng–tối trên ảnh hiệu (điểm cộng) | Khôi (đọc FITS), Nguyên (phổ) |
| Nguyên | Computer vision | Khoa học + phổ | Bảng 5 mục tiêu và kết quả kỳ vọng; quy tắc chọn ảnh so sánh được; trích phổ; đường cong ánh sáng; kiểm chứng | Tối ưu tốc độ pipeline (xử lý song song, theo lô) | Hữu Hoàng (căn ảnh, cộng ảnh), Thạch (nội dung) |

vòng dự phòng · 6 người, 6 cặp đỡ nhau
Ví dụ: Hữu Hoàng trễ xử lý ảnh thì Khôi (đọc FITS) hoặc Nguyên (ảnh, phổ) vào giúp; Khôi trễ dữ liệu thì Đông hoặc Hữu Hoàng vào giúp.
####  **Luật vận hành để không ai phải chờ**
Không ai chờ code thật của người khác: mọi người làm trên dữ liệu mẫu và hợp đồng đã chốt, rồi thay bằng phần thật khi có.
1.  **Hợp đồng trước, code sau.**  Tối 4/11 chốt hợp đồng API (Đông) và cấu trúc thư mục dữ liệu mẫu (Khôi). Frontend gọi mock, xử lý ảnh đọc dữ liệu mẫu, không đợi phần thật.
2.  **Fixture pack (bộ cutout mẫu).**  Khôi phát hành v1 tối 4/11 (Barnard, WISE 0855) và v2 tối 7/11 (đủ 5 mục tiêu), để trên drive chung, không đưa vào Git. Trễ quá 21:00 thì ai cần cứ tự tải bằng notebook Spectral Image Cutouts của IRSA.
3.  **Luật 30 phút.**  Bị chặn quá 30 phút: đổi trạng thái task thành “Bị chặn”, nhắn kênh chung một dòng (chặn ở đâu, cần ai), rồi chuyển ngay sang secondary hoặc backlog.
4.  **Luật vào giúp.**  Ai trễ bàn giao quá nửa buổi, một trong hai người đỡ cho họ bỏ secondary của mình để vào pair. Thạch chốt ai vào trong standup; giữa buổi thì người bị chặn gọi thẳng.
5.  **Bàn giao trước 22:30:**  link, ảnh chụp kết quả, một dòng “người nhận dùng thế nào”. Cột “Bàn giao” trong bảng từng ngày ghi rõ giao cho ai.
6.  **Standup 19:30, 15 phút:**  hôm qua xong gì, hôm nay làm gì, đang chặn ở đâu. Cập nhật cột trạng thái trước standup.
7.  **Mỗi task một nhánh, PR nhỏ.**  Duy Hoàng giữ nhánh main của repo đào tạo luôn chạy được.

--------------------------------------------------------------------------------

####  **Giai đoạn 1 – Nền tảng (3–4/11)**
**Mục tiêu:**  6 máy chạy được dữ liệu SPHEREx thật, có hợp đồng API v0 và fixture pack v1 để từ 5/11 không ai phải chờ ai. Vì cả nhóm đã có nền lập trình, bỏ các bài nhập môn của bản Cẩm nang (Python cơ bản, HTML/CSS, Git cơ bản).
#####  **3/11 (T3) – Môi trường + thiên văn 101**
Cả nhóm 19:30–20:15: đọc đề, đọc phần Kiến thức ở tab chính, chốt vai.
| Người | Primary | Secondary | Bàn giao (cho ai) | Trạng thái |
| ------ | ------ | ------ | ------ | ------ |
| Thạch | Tạo bảng việc trên GitHub Projects theo tab này; kênh chat chung; chốt giờ standup | Tạo file Figma; nhúng thử Aladin Lite v3, bay tới 5 mục tiêu | Link bảng việc → cả nhóm | Chưa làm |
| Duy Hoàng | Repo đào tạo spaceapps-training: thư mục theo người, .gitignore chặn file FITS, requirements.txt + package.json chung, README cài đặt | Hỗ trợ cả nhóm cài Python 3.11 + Node 20 | Repo + lệnh cài → cả nhóm | Chưa làm |
| Đông | Đọc trang SPHEREx Data Access; gọi SIA2 bằng curl cho WISE 0855, ghi nghĩa ~10 cột quan trọng (access_url, t_min, energy_bandpassname…) | FastAPI /health trong repo đào tạo | Ghi chú cột SIA2 → Khôi, Hữu Hoàng | Chưa làm |
| Khôi | Chạy hết notebook Introduction to SPHEREx Spectral Images | Nháp schema bảng observations từ các cột SIA2 | Ghi chú 6 HDU → Hữu Hoàng | Chưa làm |
| Hữu Hoàng | Đọc LVF, 6 HDU, WCS không gian và WCS phổ (mục 8 của notebook Introduction) | Chạy ví dụ reproject trên 2 ảnh mẫu | Tóm tắt WCS 1 trang → Nguyên | Chưa làm |
| Nguyên | Bảng 5 mục tiêu từ SIMBAD: toạ độ, chuyển động riêng, độ sáng J/H/K | Đổi toạ độ sang độ bằng SkyCoord | Bảng 5 mục tiêu → cả nhóm | Chưa làm |

Xong khi: 6 máy import được astropy, astroquery, pyvo, reproject, photutils.
#####  **4/11 (T4) – Dữ liệu thật đầu tiên + fixture pack v1**
Cả nhóm 30 phút đầu: Hữu Hoàng và Nguyên dạy lại LVF và quy tắc “một khung blink = ảnh cộng của một detector trong một đợt quét”.
| Người | Primary | Secondary | Bàn giao (cho ai) | Trạng thái |
| ------ | ------ | ------ | ------ | ------ |
| Thạch | Wireframe low-fi 3 màn (nhập toạ độ, viewer, panel phổ) + design tokens màu, chữ, khoảng cách | QA matrix v0: 12 test case | Tokens → Duy Hoàng | Chưa làm |
| Duy Hoàng | React + Vite; viewer canvas chạy 3 PNG bất kỳ: play/pause, tốc độ, thanh trượt khung | Hàm đọc toạ độ hai dạng (độ thập phân và 08h55m10.831s -07d14m42.53s) + unit test Vitest | Viewer → Thạch | Chưa làm |
| Đông | Hợp đồng API v0 (OpenAPI) cho /api/frames, /api/spectrum, /api/lightcurve, tên trường theo cột SIA2 thật | Mock server trả JSON tĩnh theo hợp đồng | Hợp đồng v0 → Duy Hoàng, Thạch, Hữu Hoàng | Chưa làm |
| Khôi | Chạy notebook Spectral Image Cutouts cho Barnard và WISE 0855 (size 0,05°) → fixture pack v1: tối đa 10 cutout mỗi mục tiêu + metadata.csv | Script đếm ảnh theo detector × tháng chụp | Fixture pack v1 → Hữu Hoàng, Nguyên | Chưa làm |
| Hữu Hoàng | Đọc IMAGE, FLAGS của cutout; xuất PNG kéo giãn asinh | Hàm che flags (OVERFLOW, NONFUNC, HOT, COLD…) | PNG thật đầu tiên → Duy Hoàng | Chưa làm |
| Nguyên | Đẩy toạ độ 5 mục tiêu tới ngày chụp (apply_space_motion); tính dịch chuyển kỳ vọng (pixel) giữa các đợt quét | Cheat sheet 14 flags từ Explanatory Supplement | Bảng kết quả kỳ vọng v0 → Hữu Hoàng, Thạch | Chưa làm |

Xong khi (mốc 4/11): fixture pack v1 và hợp đồng API v0 đã lên drive; ai cũng giải thích được LVF trong một câu.

--------------------------------------------------------------------------------

####  **Giai đoạn 2 – Công cụ và dữ liệu thật (5–8/11)**
Mục tiêu: mỗi người làm chắc mảnh của mình trên dữ liệu thật, rồi nối thành một chuỗi chạy được cho cả 5 mục tiêu trong repo đào tạo. Ai chưa có đầu vào thật thì dùng fixture pack hoặc mock, không chờ.
#####  **5/11 (T5) – Công cụ chuyên sâu, mỗi người một mảnh**
| Người | Primary | Secondary | Bàn giao (cho ai) | Trạng thái |
| ------ | ------ | ------ | ------ | ------ |
| Thạch | Hi-fi màn viewer + điều khiển; Aladin overlay Gaia DR3 bằng A.catalogFromVizieR (catalog I/355/gaiadr3) | Viết test case từ bảng kết quả kỳ vọng của Nguyên | Hi-fi → Duy Hoàng | Chưa làm |
| Duy Hoàng | Gọi mock API của Đông; trạng thái tải/rỗng/lỗi; tải trước ảnh; đồng bộ ?ra=&dec=&fov=&det= | Deploy thử frontend đào tạo lên Vercel | URL frontend thử → cả nhóm | Chưa làm |
| Đông | Mock API phục vụ PNG + JSON từ fixture pack; CORS; log thời gian từng request | Thiết kế khoá cache (ra, dec làm tròn, fov, detector, release) | Mock API → Duy Hoàng, Thạch | Chưa làm |
| Khôi | Truy vấn SIA2 bằng code (Irsa.query_sia, collection spherex_qr3); tải cutout song song, timeout 120 giây, retry 3 lần | Tạo SQLite observations, nạp kết quả SIA2 | fetch.py + DB mẫu → Đông, Hữu Hoàng | Chưa làm |
| Hữu Hoàng | reproject_interp các cutout về lưới TAN chung, tâm là mục tiêu; kiểm tra sao đứng yên không nhảy | Đo thời gian reproject 10 và 50 ảnh | Ảnh đã căn → Nguyên | Chưa làm |
| Nguyên | Quy tắc nhóm ảnh: gán đợt quét từ t_min, gán detector; định nghĩa “cặp ảnh so sánh được” | Kiểm ảnh đã căn của Hữu Hoàng với vị trí Gaia | Quy tắc nhóm → Hữu Hoàng, Khôi | Chưa làm |

#####  **6/11 (T6) – Chuỗi đầu–cuối trên Barnard’s Star**
| Người | Primary | Secondary | Bàn giao (cho ai) | Trạng thái |
| ------ | ------ | ------ | ------ | ------ |
| Thạch | Biểu đồ phổ + đường cong ánh sáng (Plotly) từ JSON mẫu của Nguyên | Usability test bản Figma với 2 người ngoài nhóm | Component biểu đồ → Duy Hoàng | Chưa làm |
| Duy Hoàng | Viewer gọi API đào tạo thật của Đông; nút bật/tắt ảnh hiệu | Deploy thử backend cùng Đông (Render hoặc Fly.io) | URL app đào tạo → Thạch kiểm | Chưa làm |
| Đông | Bọc hàm của Khôi và Hữu Hoàng thành /api/frames thật (job nền, cache đĩa) | Log thời gian từng bước | API thật → Duy Hoàng | Chưa làm |
| Khôi | Lấy toàn bộ ảnh Barnard bằng code, nạp DB, lưu cutout | Làm lại cho WISE 0855 | Dữ liệu Barnard → Hữu Hoàng | Chưa làm |
| Hữu Hoàng | Cộng median theo detector × đợt quét → khung PNG cùng thang kéo giãn; ảnh hiệu đợt sau trừ đợt trước | Gói thành hàm make_frames(ra, dec, fov, det) | Khung Barnard → Đông, Duy Hoàng | Chưa làm |
| Nguyên | Xác nhận dịch chuyển Barnard khớp kỳ vọng; trích phổ: đo flux tại vị trí trên nhiều cutout, lấy bước sóng từ WCS phổ | Phương án đường cong ánh sáng cho R Draconis | JSON phổ mẫu → Thạch | Chưa làm |

Nếu Khôi trễ, Hữu Hoàng chạy trên fixture pack v1; nếu Đông trễ, Duy Hoàng tiếp tục với mock.
#####  **7/11 (T7, ~6 giờ) – Mở rộng ra cả 5 mục tiêu**
| Người | Primary | Secondary | Bàn giao (cho ai) | Trạng thái |
| ------ | ------ | ------ | ------ | ------ |
| Thạch | Aladin: mũi tên chuyển động riêng từ pmra/pmdec của Gaia; nối biểu đồ với API | Usability test lần 2 trên app đào tạo | Trang Aladin → Duy Hoàng | Chưa làm |
| Duy Hoàng | Viewer chạy 5 mục tiêu + 5 nút chọn nhanh; chọn detector D1–D6 | Smoke test Playwright: nhập toạ độ → có khung | App 5 mục tiêu → Thạch, Nguyên kiểm | Chưa làm |
| Đông | Cache + xử lý nhiều yêu cầu cùng lúc; /api/spectrum, /api/lightcurve bọc hàm của Nguyên | Pair với Khôi tối ưu tải song song | API đủ 3 endpoint → Duy Hoàng, Thạch | Chưa làm |
| Khôi | Dữ liệu 5 mục tiêu vào DB; bảng benchmark: số ảnh, thời gian tải ở size 0,05° / 0,1° / 0,2° | Thử đường tải bản AWS qua cột cloud_access cho 1 mục tiêu | Fixture pack v2 + benchmark → cả nhóm | Chưa làm |
| Hữu Hoàng | Khung cho 5 mục tiêu; xử lý sao bão hoà (Barnard, R Draconis) bằng flags | Ảnh màu giả ghép 3 detector | Khung 5 mục tiêu → Đông | Chưa làm |
| Nguyên | Đường cong ánh sáng RW Aurigae và R Draconis bằng photutils; bảng kết quả kỳ vọng v1 | So phổ R Draconis với tab Spectrophotometry của SPHEREx Data Explorer | Bảng kỳ vọng v1 → Thạch, Duy Hoàng | Chưa làm |

#####  **8/11 (CN, ~6 giờ) – Bấm giờ dựng lại + dạy chéo**
Sáng 3 giờ: mỗi người dựng lại phần của mình trong thư mục mới, không chép code cũ, bấm giờ; con số này dùng để chia việc giờ 0–9 ngày thi. Chiều 2 giờ: dạy chéo 2 vòng, mỗi vòng 50 phút, hai người trong cặp dạy nhau mỗi chiều 25 phút và người học tự chạy lại một lần. Vòng 1: Thạch–Duy Hoàng, Đông–Khôi, Hữu Hoàng–Nguyên. Vòng 2: Duy Hoàng–Đông, Khôi–Hữu Hoàng, Nguyên–Thạch. Cuối buổi 1 giờ: retro và cập nhật tab này.
| Người | Primary (bấm giờ dựng lại) | Secondary (dạy chéo) | Bàn giao (cho ai) | Trạng thái |
| ------ | ------ | ------ | ------ | ------ |
| Thạch | Aladin + overlay Gaia, mục tiêu dưới 1 giờ | Vòng 1 học viewer từ Duy Hoàng; vòng 2 học kiểm chứng khoa học từ Nguyên | Thời gian dựng lại → bảng retro | Chưa làm |
| Duy Hoàng | Viewer + gọi mock, dưới 1,5 giờ | Vòng 1 học Aladin từ Thạch; vòng 2 học endpoint FastAPI từ Đông | Thời gian dựng lại → bảng retro | Chưa làm |
| Đông | Mock API + cache, dưới 1 giờ | Vòng 1 học tải dữ liệu IRSA từ Khôi; vòng 2 học fetch phía frontend từ Duy Hoàng | Thời gian dựng lại → bảng retro | Chưa làm |
| Khôi | SIA2 → cutout → DB cho Barnard, dưới 1 giờ | Vòng 1 học API + cache từ Đông; vòng 2 học đọc FITS + che flags từ Hữu Hoàng | Thời gian dựng lại → bảng retro | Chưa làm |
| Hữu Hoàng | Cutout → khung PNG + ảnh hiệu, dưới 1,5 giờ | Vòng 1 học trích phổ từ Nguyên; vòng 2 học tải dữ liệu từ Khôi | Thời gian dựng lại → bảng retro | Chưa làm |
| Nguyên | Kiểm 5 mục tiêu theo bảng kỳ vọng, dưới 1 giờ | Vòng 1 học cộng ảnh từ Hữu Hoàng; vòng 2 học Aladin + nội dung từ Thạch | Thời gian dựng lại → bảng retro | Chưa làm |

Xong khi (mốc 8/11): Khôi và Hữu Hoàng có PNG thật của WISE 0855 và Barnard; Nguyên có bảng kỳ vọng v1; bảng thời gian dựng lại đủ 6 người.

--------------------------------------------------------------------------------

####  **Giai đoạn 3 – Diễn tập và đổi vai (9–11/11)**
Mục tiêu: chứng minh mảng nào cũng có hai người làm được, và mọi sự cố thường gặp đều đã được tập xử lý một lần.
#####  **9/11 (T2) – Diễn tập tích hợp trên app đào tạo**
| Người | Primary | Secondary | Bàn giao (cho ai) | Trạng thái |
| ------ | ------ | ------ | ------ | ------ |
| Thạch | Kiểm thử theo QA matrix và bảng kỳ vọng trên app đào tạo; ghi issue cho đúng người sở hữu | Chốt design system bản cuối | Danh sách lỗi → người sở hữu | Chưa làm |
| Duy Hoàng | Ghép viewer, Aladin và biểu đồ trên một trang; deploy cả frontend và backend | Smoke test tự chạy sau mỗi lần deploy | URL app đào tạo đầy đủ → Thạch | Chưa làm |
| Đông | Sửa lỗi API theo issue; đo thời gian trả lời từng endpoint | Endpoint health + trạng thái job | Bảng thời gian API → Khôi | Chưa làm |
| Khôi | Mô phỏng IRSA chậm hoặc lỗi: timeout, retry, trả “không có ảnh” rõ ràng | Script nạp lại DB khi đổi bản phát hành (đổi collection) | Ghi chú xử lý lỗi → Đông | Chưa làm |
| Hữu Hoàng | Sửa lỗi căn ảnh, kéo giãn theo issue | Thử tự phát hiện cặp sáng–tối trên ảnh hiệu bằng photutils | Tham số cuối → runbook | Chưa làm |
| Nguyên | Kiểm 5 mục tiêu trên app đào tạo theo bảng kỳ vọng | Viết nội dung “What am I looking at?” bằng tiếng Anh | Báo cáo kiểm chứng → cả nhóm | Chưa làm |

#####  **10/11 (T3) – Ngày đổi vai**
Mỗi người làm một mảnh của người mình đỡ, một mình, trong 90 phút, chỉ dùng runbook và ghi chú dạy chéo; người sở hữu chỉ ngồi xem và ghi chỗ runbook còn thiếu. Dùng một mục tiêu mới ngoài 5 mục tiêu của đề, ví dụ sao lùn nâu Luhman 16 (không có ảnh thì chọn sao lùn nâu khác trên SIMBAD), để chắc chuỗi không chỉ chạy với dữ liệu đã quen. 60 phút còn lại: hai người sửa runbook.
| Người | Primary (mảnh của người khác) | Secondary | Bàn giao (cho ai) | Trạng thái |
| ------ | ------ | ------ | ------ | ------ |
| Thạch | Thanh trượt khung + nút ảnh hiệu trong viewer (mảnh của Duy Hoàng) | Xem Nguyên làm mảnh Aladin, ghi chỗ thiếu | Ghi chú runbook → Duy Hoàng | Chưa làm |
| Duy Hoàng | Endpoint /api/targets trả danh sách mục tiêu mẫu (mảnh của Đông) | Xem Thạch làm mảnh viewer | Ghi chú runbook → Đông | Chưa làm |
| Đông | Tải ảnh Luhman 16 qua SIA2 + cutout vào DB (mảnh của Khôi) | Xem Duy Hoàng làm mảnh endpoint | Cutout Luhman 16 → Khôi | Chưa làm |
| Khôi | Khung PNG + ảnh hiệu Luhman 16 từ cutout của Đông (mảnh của Hữu Hoàng); 30 phút chưa có cutout thì tập trên fixture pack v2 | Xem Đông làm mảnh tải dữ liệu | Khung Luhman 16 → Hữu Hoàng | Chưa làm |
| Hữu Hoàng | Trích phổ + kiểm theo checklist khoa học cho Luhman 16 (mảnh của Nguyên) | Xem Khôi làm mảnh xử lý ảnh | Kết quả kiểm → Nguyên | Chưa làm |
| Nguyên | Overlay Gaia trong Aladin cho Luhman 16 + 3 câu giải thích tiếng Anh (mảnh của Thạch) | Xem Hữu Hoàng làm mảnh khoa học | Ghi chú runbook → Thạch | Chưa làm |

Xong khi (mốc 10/11): cả 6 mảnh ra kết quả trong 90 phút; mảnh nào chưa được thì bổ sung runbook ngay trong tối.
#####  **11/11 (T4) – Runbook, thẻ nhiệm vụ giờ 0–9, diễn tập sự cố**
| Người | Primary | Secondary (diễn tập sự cố) | Bàn giao (cho ai) | Trạng thái |
| ------ | ------ | ------ | ------ | ------ |
| Thạch | Thẻ nhiệm vụ giờ 0–9 cho cả nhóm; luật cắt tính năng; dàn ý 7 slide + kịch bản video 30 giây bằng tiếng Anh (để trống) | Hỏi Local Lead: wireframe và ghi chú có được mang vào không | Thẻ nhiệm vụ → cả nhóm | Chưa làm |
| Duy Hoàng | Runbook deploy: từ repo trống tới frontend + backend online trong 30 phút | Deploy hỏng → rollback | Runbook deploy → Đông | Chưa làm |
| Đông | Runbook API + cache | API sập → frontend chuyển sang JSON tĩnh | Runbook API → Duy Hoàng | Chưa làm |
| Khôi | Runbook dữ liệu + danh sách obs_id/URL của 5 mục tiêu | IRSA chậm → chuyển sang cache hoặc bản AWS | Runbook dữ liệu → Đông, Hữu Hoàng | Chưa làm |
| Hữu Hoàng | Runbook xử lý ảnh 5 bước + tham số đã thử | Máy hết RAM khi reproject → giảm FOV, xử lý theo lô | Runbook xử lý → Khôi, Nguyên | Chưa làm |
| Nguyên | Science brief 1 trang tiếng Anh + checklist kiểm chứng | 10 cặp hỏi–đáp khoa học cho giám khảo | Science brief → Thạch | Chưa làm |

####  **Giai đoạn 4 – Mini-hackathon và sẵn sàng (12–13/11)**
Mục tiêu: tập phối hợp đúng như ngày thi trên một đề khác, rồi vào ngày 14/11 với máy sẵn sàng và sức còn đầy.
#####  **12/11 (T5) – Mini-hackathon đề khác (3–4 giờ)**
Làm một app nhỏ không liên quan SPHEREx, ví dụ trang theo dõi vị trí Trạm Vũ trụ Quốc tế (ISS) từ một API công khai, đúng vai như ngày thi. Luyện ba thứ: chốt hợp đồng trong 20 phút đầu, luật 30 phút, deploy trước phút 150. Retro 30 phút cuối.
| Người | Primary | Secondary | Bàn giao (cho ai) | Trạng thái |
| ------ | ------ | ------ | ------ | ------ |
| Thạch | Điều phối, bấm giờ, chốt phạm vi phút 0–20; giao diện phụ | Ghi decision log + chủ trì retro | Retro 3 tốt / 3 lỗi / 3 đổi → cả nhóm | Chưa làm |
| Duy Hoàng | Repo mới, trang chính, deploy trước phút 150 | Smoke test | URL app → Thạch | Chưa làm |
| Đông | Hợp đồng API trong 20 phút đầu; backend gọi API công khai | Cache | Hợp đồng → Duy Hoàng | Chưa làm |
| Khôi | Lớp lấy dữ liệu từ API công khai + lưu SQLite | Pair với Đông khi xong | Dữ liệu mẫu → Đông | Chưa làm |
| Hữu Hoàng | Xử lý dữ liệu (ví dụ quỹ đạo theo thời gian) | Pair với Khôi khi xong | Dữ liệu đã xử lý → Đông | Chưa làm |
| Nguyên | Kiểm số liệu; viết mô tả tiếng Anh như form nộp bài thật | Đo thời gian từng lần bàn giao | Bản mô tả → Thạch | Chưa làm |

#####  **13/11 (T6) – Sẵn sàng, nghỉ sớm**
Không học kỹ thuật mới. Hướng dẫn nộp bài 2026 ra hôm nay; Thạch đọc và cập nhật mục “Bài nộp phải có” ở tab chính. Cả nhóm ngủ trước 23:00.
| Người | Primary | Secondary | Bàn giao (cho ai) | Trạng thái |
| ------ | ------ | ------ | ------ | ------ |
| Thạch | Đọc thể lệ và hướng dẫn nộp bài 2026; chốt bảng Go/No-Go; chia ca ngủ ngày thi | Đọc lại runbook của Duy Hoàng và Nguyên | Go/No-Go có xác nhận 6 người | Chưa làm |
| Duy Hoàng | Kiểm tài khoản deploy, quyền GitHub, máy, sạc, ổ cắm, 4G dự phòng | Đọc lại runbook của Thạch và Đông | Checklist thiết bị → Thạch | Chưa làm |
| Đông | Lưu offline runbook backend; cài lại môi trường Python sạch từ requirements.txt | Đọc lại runbook của Duy Hoàng và Khôi | Máy sẵn sàng → Thạch | Chưa làm |
| Khôi | Kiểm IRSA còn chạy; ghi collection hiện hành (QR3 hay mới hơn) | Đọc lại runbook của Đông và Hữu Hoàng | Ghi chú collection → cả nhóm | Chưa làm |
| Hữu Hoàng | Cài lại môi trường xử lý ảnh trên máy sạch, chạy thử 1 cutout | Đọc lại runbook của Khôi và Nguyên | Máy sẵn sàng → Thạch | Chưa làm |
| Nguyên | In hoặc lưu offline science brief + bảng kỳ vọng | Đọc lại runbook của Hữu Hoàng và Thạch | Tài liệu offline → cả nhóm | Chưa làm |

####  **Task dự phòng khi gặp pain point**
Mỗi pain point có sẵn người vào giúp và việc cụ thể của họ, nên không cần họp mới quyết. Hàng thứ hai là tình huống Hữu Hoàng trễ xử lý ảnh trong khi Khôi đang rảnh vì database chờ dữ liệu.
| Pain point | Dấu hiệu | Ai vào giúp | Người vào giúp làm gì | Người bị chặn làm gì trong lúc chờ |
| ------ | ------ | ------ | ------ | ------ |
| Khôi trễ dữ liệu IRSA | 21:00 chưa có cutout | Đông | Pair viết phần tải song song + retry; IRSA lỗi thì thử bản AWS qua cloud_access | Hữu Hoàng, Nguyên chạy trên fixture pack hoặc tự tải bằng notebook Cutouts |
| Hữu Hoàng trễ xử lý ảnh | Khôi đã nạp xong dữ liệu nhưng chưa có khung PNG | Khôi + Nguyên | Khôi: đọc FITS, che flags, xuất PNG từng ảnh chưa cộng. Nguyên: gom nhóm detector × đợt quét và cộng median | Hữu Hoàng giữ phần khó nhất (reproject); Duy Hoàng tạm dùng PNG từng ảnh |
| Đông trễ API | Frontend chưa gọi được endpoint thật | Duy Hoàng | Viết endpoint mỏng đọc thẳng thư mục PNG + JSON | Đông tập trung job nền và cache; frontend chạy trên mock |
| Duy Hoàng trễ viewer | Chưa có trang để ghép | Thạch | Tạm dừng Aladin (không thuộc MVP), làm thanh trượt và điều khiển | Duy Hoàng giữ phần canvas và tải trước ảnh |
| Thạch trễ thiết kế hoặc Aladin | Chưa có hi-fi hoặc overlay | Duy Hoàng (giao diện), Nguyên (nội dung) | Duy Hoàng dùng design tokens đã chốt 4/11; Aladin dời xuống điểm cộng; Nguyên viết nội dung giải thích | Thạch giữ điều phối và kiểm thử |
| Nguyên trễ phần khoa học | Chưa có bảng kỳ vọng hoặc phổ khi cần kiểm | Hữu Hoàng (phổ), Thạch (nội dung) | Hữu Hoàng trích phổ bằng WCS phổ; Thạch soạn phần giải thích từ mục Kiến thức ở tab chính | Nguyên giữ việc kiểm 5 mục tiêu |
| IRSA chậm hoặc sập | Truy vấn trên 30 giây | Khôi + Đông | Chuyển sang cache và fixture pack; thử bản AWS | Mọi người làm tiếp trên fixture pack |
| Một người vắng cả ngày | Báo trước standup | Hai người đứng cạnh trong vòng | Chia đôi primary của người vắng, bỏ secondary của mình | — |
| Repo rối, conflict kéo dài | PR mở quá 1 ngày | Duy Hoàng | Gộp PR nhỏ, khoá nhánh main, hướng dẫn rebase | Người có PR tách task nhỏ hơn |
| Máy hết RAM khi reproject | Notebook chết giữa chừng | Nguyên | Xử lý theo lô, giảm FOV, chạy trên máy mạnh nhất nhóm | Hữu Hoàng chuyển sang secondary |
| Một người xong sớm | Hết primary và secondary | — | — | Lấy task từ backlog bên dưới, hoặc hỏi một trong hai người mình đỡ có cần pair không |

####  **Backlog kéo khi rảnh**
Ai xong sớm hoặc đang bị chặn thì nhận một task dưới đây: ghi tên vào cuối dòng rồi làm.
*  [ ] Unit test cho hàm đổi toạ độ (frontend hoặc Python)
*  [ ] Đo thời gian tải cutout ở 3 size cho một mục tiêu thứ 6
*  [ ] Tooltip tiếng Anh cho 14 flags, dựa trên cheat sheet của Nguyên
*  [ ] Ảnh màu giả ghép 3 detector
*  [ ] Smoke test Playwright cho 5 nút mục tiêu
*  [ ] Đo RAM khi reproject 50 ảnh, ghi vào runbook
*  [ ] Ghi danh sách obs_id/URL của 5 mục tiêu vào runbook
*  [ ] Dịch science brief sang tiếng Anh
*  [ ] Thử Moving Object Search Tool của IRSA với một tiểu hành tinh
*  [ ] Tự trả lời 5 câu hỏi từ mục Kiến thức ở tab chính rồi nhờ Nguyên chấm
####  **Kiến thức thiên văn tối thiểu cả nhóm phải nắm**
Điều quan trọng nhất: SPHEREx không chụp ảnh màu như máy ảnh. Mỗi detector nằm sau bộ lọc LVF có bước sóng thay đổi dọc một trục của chip, nên một ngôi sao trong một ảnh chỉ được đo ở một bước sóng; phổ đầy đủ có được nhờ chụp lại ở nhiều vị trí ([IRSA](https://caltech-ipac.github.io/irsa-tutorials/spherex-intro)). Vì vậy blink phải so ảnh cùng detector, hoặc cộng nhiều ảnh cùng detector trong một đợt quét thành một khung.
| Detector | Bước sóng (µm) | Độ phân giải phổ R |
| ------ | ------ | ------ |
| D1 | 0,75–1,09 | 39 |
| D2 | 1,10–1,62 | 41 |
| D3 | 1,63–2,41 | 41 |
| D4 | 2,42–3,82 | 35 |
| D5 | 3,83–4,41 | 112 |
| D6 | 4,42–5,00 | 128 |

Nguồn: [Introduction to SPHEREx Spectral Images](https://caltech-ipac.github.io/irsa-tutorials/spherex-intro). “102 màu” là các kênh phổ cắt từ dải bước sóng liên tục của 6 detector này.
*   **RA/Dec:**  RA đo bằng giờ (0–24h, 1h = 15°), Dec bằng độ (−90° đến +90°). Ví dụ 08h55m10.831s = 133,7951°. Trong Python: SkyCoord('08h55m10.831s -07d14m42.53s').
*   **FITS và HDU:**  file ảnh thiên văn gồm nhiều lớp. Ảnh SPHEREx có 6 lớp: IMAGE (MJy/sr), FLAGS, VARIANCE, ZODI (nền bụi hoàng đạo, chưa trừ khỏi IMAGE), PSF, WCS-WAVE.
*   **WCS:**  quy tắc đổi pixel ↔ toạ độ trời. Mỗi ảnh SPHEREx xoay một góc khác, nên phải đưa về lưới chung (reproject) trước khi blink.
*   **Kích thước:**  chip 2040×2040 pixel, ~6,15″/pixel, tức mỗi ảnh phủ khoảng 3,5° mỗi chiều. Một file gốc nặng hàng trăm MB, nên luôn dùng cutout.
*   **Chuyển động riêng và thị sai:**  sao gần trôi dần (″/năm) và lắc qua lại theo quỹ đạo Trái Đất. Toạ độ catalog gắn với một epoch (thường J2000 hoặc J2016), phải đẩy tới ngày chụp.
*   **Đợt quét:**  SPHEREx bắt đầu quan sát khoa học 1/5/2025 và quét toàn trời mỗi ~6 tháng, nên đến tháng 11/2026 có khoảng 3 đợt (ước lượng; Nguyên xác nhận từ cột t_min).
*   **Sao biến quang:**  độ sáng đổi theo thời gian; đo bằng aperture photometry để vẽ đường cong ánh sáng.
*   **Cộng ảnh:**  cộng N ảnh thì nhiễu giảm theo √N, nên 16 ảnh cho tín hiệu/nhiễu tốt hơn khoảng 4 lần.
*   **Ảnh hiệu:**  lấy đợt sau trừ đợt trước; vật đứng yên biến mất, vật di chuyển thành cặp sáng–tối.
*   **Flags:**  mỗi pixel có một bitmask, ví dụ OVERFLOW (bão hoà), HOT, COLD, NONFUNC, PERSIST, SOURCE; định nghĩa nằm ngay trong header lớp FLAGS.
*   **HiPS và catalog:**  HiPS là ảnh toàn trời cắt tile cho Aladin Lite; Gaia DR3 cho vị trí và chuyển động riêng chính xác để đối chiếu.
**Tài liệu học và tra cứu:**
*  [SPHEREx Spectral Image Cutouts](https://caltech-ipac.github.io/irsa-tutorials/spherex-cutouts) · [SPHEREx Cutout Capabilities](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/cutout_tool.html) · [SPHEREx Mosaic Cube](https://caltech-ipac.github.io/irsa-tutorials/spherex-mosaic)
*  [SPHEREx Explanatory Supplement (PDF)](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp_QR.pdf) · [SPHEREx Data Explorer](https://irsa.ipac.caltech.edu/applications/spherex) · [Trang SPHEREx tại IRSA](https://irsa.ipac.caltech.edu/Missions/spherex.html)
*  [Aladin Lite](https://aladin.cds.unistra.fr/AladinLite/doc) · [SIMBAD](https://simbad.cds.unistra.fr) · [Backyard Worlds](https://backyardworlds.org)
*  [Astropy Learn](https://learn.astropy.org) · [reproject](https://reproject.readthedocs.io) · [photutils](https://photutils.readthedocs.io) · [FastAPI](https://fastapi.tiangolo.com/tutorial/) · [React](https://react.dev/learn)
####  **Kịch bản 39 giờ thi (09:00 14/11 → 23:59 15/11)**
Mốc quan trọng nhất là giờ 24 (09:00 Chủ nhật): link công khai chạy MVP với cả 5 mục tiêu; chưa đạt thì không mở tính năng cộng điểm nào. Giờ 0 = giờ BTC địa phương cho bắt đầu; dời cả bảng nếu khác 09:00 thứ Bảy.
| Giờ | Thời điểm | Việc | Ai | Xong khi |
| ------ | ------ | ------ | ------ | ------ |
| 0–2 | T7 09:00–11:00 | Đọc lại đề và tab Resources (có thể có dữ liệu mới); chốt MVP; tạo repo dự thi mới; chia issue trên GitHub | Cả nhóm, Thạch điều phối | Mỗi issue có người nhận |
| 2–9 | 11:00–18:00 | Khôi: tìm ảnh, cutout, SQLite. Hữu Hoàng: căn ảnh, cộng ảnh, PNG. Nguyên: quy tắc chọn ảnh + kiểm. Đông: API + cache. Duy Hoàng: repo, deploy bản rỗng, viewer với PNG thử. Thạch: vẽ lại wireframe trong giờ 0–3, rồi Aladin | Từng người | **Giờ 9:**  có ít nhất 1 cutout SPHEREx thật qua API |
| 9–15 | 18:00–24:00 | Ghép lần 1 với WISE 0855 và Barnard; chạy đủ 5 mục tiêu; Khôi tạo bộ ảnh dựng sẵn cho 5 mục tiêu | Đông, Khôi, Hữu Hoàng, Duy Hoàng; Nguyên kiểm | **Giờ 15:**  chuỗi ≥2 khung cho ít nhất 3/5 mục tiêu |
| 15–19,5 | CN 00:00–04:30 | Ca A (Thạch, Nguyên, Hữu Hoàng) ngủ. Ca B (Duy Hoàng, Đông, Khôi): deploy bản đầu, sửa lỗi dữ liệu | Ca B | Có link công khai |
| 19,5–24 | 04:30–09:00 | Ca B ngủ. Ca A: thử trên máy thứ hai, sửa lỗi ảnh và giao diện, nháp slide | Ca A | **Giờ 24 (09:00):**  MVP chạy trên link công khai với cả 5 mục tiêu |
| 24–30 | 09:00–15:00 | Điểm cộng theo thứ tự bên dưới | Đông, Khôi, Hữu Hoàng, Nguyên, Duy Hoàng; Thạch kiểm thử | **Giờ 30:**  dừng mở tính năng mới |
| 30–33 | 15:00–18:00 | Đóng băng tính năng; sửa lỗi chặn demo; kiểm lại 5 mục tiêu; README tiếng Anh | Nguyên, Đông, Khôi, Hữu Hoàng | Không còn lỗi chặn demo |
| 33–36 | 18:00–21:00 | 7 slide hoặc video 30 giây; điền form nộp bài bằng tiếng Anh, liệt kê code và công cụ AI đã dùng | Thạch + Nguyên, dev hỗ trợ | Đủ mọi trường bắt buộc |
| 36–37,5 | 21:00–22:30 | Bấm "Submit for Judging"; mở thử mọi link ở tab ẩn danh | Thạch + Duy Hoàng | **Đã nộp trước 22:30** |
| 37,5–39 | 22:30–23:59 | Dự phòng | — | — |

Ai bị chặn trong giờ thi thì dùng đúng vòng dự phòng và bảng task dự phòng ở tab Task từng ngày.
**MVP (bắt buộc trước giờ 24):**
*  [ ] Nhập RA/Dec ở cả hai định dạng + chọn FOV
*  [ ] Blink theo thời gian: mỗi khung = ảnh cộng của một detector trong một đợt quét, có nhãn ngày
*  [ ] Chọn detector D1–D6
*  [ ] Toạ độ nằm trong URL
*  [ ] 5 nút chọn nhanh 5 mục tiêu kiểm thử
*  [ ] Hiển thị nguồn ảnh: bản phát hành, detector, thời điểm chụp
*  [ ] Báo lỗi rõ khi không có ảnh hoặc IRSA chậm
**Cộng điểm (làm theo thứ tự, dừng ở giờ 30):**
1. Ảnh hiệu giữa hai đợt quét (vật thể di chuyển hiện thành cặp đen–trắng).
2. Overlay Gaia DR3 + vị trí dự đoán theo chuyển động riêng.
3. Lớp flags bật/tắt.
4. Đường cong ánh sáng cho RW Aurigae và R Draconis.
5. Phổ tại vị trí click, gom từ nhiều ảnh (không phải từ một pixel).
6. Ảnh màu giả ghép 3 detector thành RGB.
7. Mã nhúng iframe; nút đánh dấu vật thể nghi vấn.
Thiếu giờ thì cắt điểm cộng từ dưới lên, giữ nguyên MVP và nộp trước 22:30.
**Record**
1.  **Phổ biến lại role, task cho từng người và kế hoạch thực hiện (tab tổng quan)**
2.  **Phổ biến rule làm việc, hình phạt (tab CÁCH THỨC LÀM VIỆC)**
3.  **Phổ biến nội dung của các cuộc meeting.**
4.  **Thứ 6 (6/11) meeting trình bày task (từ 3-6/11)**
Hiện tại trên màn hình tài liệu, mình chỉ thấy được bảng phân công công việc của ngày 6/11. Dưới đây là nội dung task ngày 6/11 được tổng hợp theo đúng format bạn yêu cầu. Bạn hãy cuộn trang lên phần ngày 5/11 để mình bổ sung thêm nhé:
1. Thạch
*  Biểu đồ phổ + đường cong ánh sáng (Plotly) từ JSON mẫu của Nguyên
*  Usability test bản Figma với 2 người ngoài nhóm
2. Duy Hoàng
*  Viewer gọi API đào tạo thật của Đông; nút bật/tắt ảnh hiệu
*  Deploy thử backend cùng Đông (Render hoặc Fly.io)
3. Đông
*  Bọc hàm của Khôi và Hữu Hoàng thành /api/frames thật (job nền, cache đĩa)
*  Log thời gian từng bước
4. Khôi
*  Lấy toàn bộ ảnh Barnard bằng code, nạp DB, lưu cutout
*  Làm lại cho WISE 0855
5. Hữu Hoàng
*  Cộng median theo detector x đợt quét -> khung PNG cùng thang kéo giãn; ảnh hiệu đợt sau trừ đợt trước
*  Gói thành hàm make_frames(ra, dec, fov, det)
