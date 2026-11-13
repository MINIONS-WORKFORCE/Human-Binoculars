# Thông báo Kỹ thuật & Bàn giao Collection IRSA – Ngày 13/11/2026

> **Người gửi:** Khôi (Backend / IRSA Data & Database)  
> **Người nhận:** Thạch, Đông, Hữu Hoàng, Duy Hoàng, Nguyên  
> **Thời điểm gửi:** 13/11/2026 (Chuẩn bị trước giờ G Hackathon)  
> **Trạng thái sẵn sàng cá nhân (Go/No-Go):** **GO (100% SẴN SÀNG)**

---

### 1. Chốt tên Collection IRSA SPHEREx
- **Collection chính thức:** **`spherex_qr3`** (Quick Release 3).
- **Collection cũ (`spherex_qr2`):** Đã hết hiệu lực trên hệ thống IRSA; kết quả truy vấn hiện trả về 0 ảnh.
- **Hành động cấu hình:** Mọi người hãy đảm bảo file `.env` cá nhân và production có cấu hình:
  ```ini
  SPHEREX_COLLECTION=spherex_qr3
  SPHEREX_COLLECTION_FALLBACK=spherex_qr2
  ```

---

### 2. Cảnh báo dữ liệu đối với WISE 0855-0714
- **Hiện tượng:** Kiểm tra trực tiếp trên IRSA SIA2 cho thấy bản phát hành `spherex_qr3` **chưa phủ sóng** tọa độ của WISE 0855-0714 (`133.8189°`, `-7.2470°`).
- **Phương án thống nhất:**
  - Khi người dùng chọn mục tiêu **WISE 0855-0714**, backend sẽ tự động fallback đọc dữ liệu FITS từ bộ fixture pack offline tại [data/fixtures/wise0855/](file:///d:/Roy/NASA.ShereX/data/fixtures/wise0855/).
  - Bộ fixture pack này gồm đủ 6 ảnh FITS (3 ảnh detector D1 và 3 ảnh detector D6) cùng manifest đã được kiểm chứng tính nhất quán.

---

### 3. Khuyến nghị Kích thước Cutout (FOV) & Timeout cho Backend (Bàn giao Đông)
- **Kích thước mặc định (Default FOV):** Đặt `size = 0.05°`.
  - Ở `0.05°`, thời gian truy vấn IRSA SIA2 chỉ mất từ **2.4 giây đến 7.5 giây**.
  - Ở `0.10°` và `0.20°`, thời gian truy vấn có thể kéo dài lên tới **57 giây** (đối với vùng cực bắc như R Draconis).
- **Timeout của Backend HTTP Client:** Đặt tối thiểu **90 giây** khi gọi IRSA để tránh bị timeout trên các mục tiêu có mật độ ảnh cao.

---

### 4. Tài liệu & Tài nguyên đã hoàn tất
- **Runbook dữ liệu chi tiết:** [members/khoi/RUNBOOK_DATA.md](file:///d:/Roy/NASA.ShereX/members/khoi/RUNBOOK_DATA.md)
- **Bảng đo đạc Benchmark chi tiết:** [members/khoi/BENCHMARKS.md](file:///d:/Roy/NASA.ShereX/members/khoi/BENCHMARKS.md)
- **Bộ mẫu FITS offline:** Đầy đủ 30 file tại [data/fixtures/](file:///d:/Roy/NASA.ShereX/data/fixtures/) và bản nén zip [data/fixtures_spherex_5targets.zip](file:///d:/Roy/NASA.ShereX/data/fixtures_spherex_5targets.zip).
- **Kiểm thử tự động:** Test suite backend [members/dong/tests/](file:///d:/Roy/NASA.ShereX/members/dong/tests/) đạt **64 passed, 1 skipped, 0 failed**.
