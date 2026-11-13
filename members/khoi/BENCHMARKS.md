# Bảng Benchmark Dữ liệu IRSA SPHEREx – Khôi (13/11/2026)

> **Mục đích:** Đo đạc thực tế số lượng ảnh và thời gian phản hồi của dịch vụ IRSA SIA2 với bản phát hành **SPHEREx Quick Release 3 (`spherex_qr3`)** cho 5 mục tiêu thách thức khoa học ở 3 kích thước vùng trời (`0.05°`, `0.10°`, `0.20°`).  
> **Người thực hiện:** Khôi (Backend / IRSA Data & Database)  
> **Người nhận bàn giao:** Đông (Backend API / Cache), Thạch (Captain / UI-UX), Hữu Hoàng (Xử lý ảnh).

---

## 1. Bảng số ảnh và thời gian tải (Benchmark Table)

Được đo kiểm trực tiếp qua IVOA SIA2 endpoint (`https://irsa.ipac.caltech.edu/SIA`) vào ngày 13/11/2026:

| STT | Mục tiêu | Tọa độ RA / Dec (J2000) | Bán kính / FOV | Số ảnh QR3 | Thời gian truy vấn (s) | Đánh giá & Khuyến nghị |
| :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **1** | **Barnard's Star**<br>*(Sao Barnard - Chuyển động riêng)* | `269.4521°`, `+4.6934°` | 0.05°<br>0.10°<br>0.20° | **126**<br>132<br>141 | **7.50s**<br>29.95s<br>33.46s | Rất nhiều ảnh trên 6 detector và nhiều epoch. Đủ dữ liệu làm blink/motion và difference image. |
| **2** | **WISE 0855-0714**<br>*(Sao lùn nâu lạnh -7°)* | `133.8189°`, `-7.2470°` | 0.05°<br>0.10°<br>0.20° | **0**<br>0<br>0 | **1.31s**<br>25.22s<br>16.06s | ⚠️ **LƯU Ý QUAN TRỌNG:** Bản `spherex_qr3` hiện chưa phủ sóng tọa độ này. **Bắt buộc fallback về bộ fixture offline** (`data/fixtures/wise0855/`). |
| **3** | **Epsilon Indi B**<br>*(Hệ sao lùn nâu đôi)* | `331.0441°`, `-56.7828°` | 0.05°<br>0.10°<br>0.20° | **120**<br>120<br>134 | **6.06s**<br>32.78s<br>16.89s | Đủ ảnh trên D1 và D6. Truy vấn 0.05° phản hồi cực nhanh (6s). |
| **4** | **RW Aurigae**<br>*(Sao trẻ biến quang)* | `76.9565°`, `+30.4014°` | 0.05°<br>0.10°<br>0.20° | **114**<br>139<br>161 | **2.43s**<br>20.31s<br>21.58s | Thời gian truy vấn nhanh nhất (~2.4s ở 0.05°). Rất tốt để demo trực tiếp. |
| **5** | **R Draconis**<br>*(Sao biến quang Mira)* | `248.1676°`, `+66.7550°` | 0.05°<br>0.10°<br>0.20° | **127**<br>133<br>209 | **3.22s**<br>57.53s<br>25.90s | Vùng cực bắc chứa lượng ảnh lớn (209 ảnh ở 0.2°). Truy vấn 0.1° có thể mất tới 57s. |

---

## 2. Kết luận & Khuyến nghị kỹ thuật cho Backend (Đông)

1. **Khuyến nghị Default FOV (Kích thước cutout mặc định):**
   - Đặt `size = 0.05°` làm mặc định trên giao diện và API.
   - **Lý do:** Tại `0.05°`, thời gian truy vấn IRSA chỉ mất **2.4s – 7.5s**, vừa đủ bao quát nguồn mục tiêu (~30×30 pixel) và nguồn nền để căn chỉnh astrometry, vừa giảm thiểu tối đa độ trễ cho người dùng.
   - Khi tăng lên `0.10°` hay `0.20°`, thời gian truy vấn nhảy vọt lên **25s – 58s**, dễ chạm ngưỡng timeout của trình duyệt hoặc proxy.

2. **Cấu hình Timeout & Retry:**
   - Client HTTP Backend (`httpx` / `requests`) gọi IRSA SIA2 cần đặt `timeout = 90s` (không để mặc định 30s vì R Draconis 0.1° mất 57s).
   - Số lần thử lại: `retries = 3` với `backoff_factor = 1.5s`.

3. **Cơ chế Cache SQLite & DiskCache:**
   - Mọi kết quả truy vấn SIA2 sau khi lấy về cần được nạp ngay vào SQLite `spherex_sia2.db` hoặc bộ nhớ đệm `diskcache`.
   - Nếu IRSA chậm (> 15s) hoặc gặp lỗi 502/504, tự động trả dữ liệu từ cache cục bộ hoặc fixture pack.
