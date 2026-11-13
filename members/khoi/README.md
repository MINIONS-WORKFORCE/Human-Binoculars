# Khôi: IRSA Data & Database Specialist

Module và tài liệu thuộc trách nhiệm của Khôi trong dự án **NASA Space Apps SPHEREx Sky Viewer**:

- **Module truy cập dữ liệu chính:** `shared/pipeline/irsa.py` (truy vấn SIA2, TAP ADQL fallback, tải cutout song song, chuyển đổi chế độ live/fixture).
- **Runbook dữ liệu chi tiết:** [RUNBOOK_DATA.md](RUNBOOK_DATA.md) (Kiến trúc pipeline, danh mục ObsID của 5 mục tiêu, quy trình xử lý sự cố IRSA).
- **Bảng đo đạc Benchmark:** [BENCHMARKS.md](BENCHMARKS.md) (Số lượng ảnh và thời gian tải thực tế trên `spherex_qr3` ở các kích thước 0.05°, 0.1°, 0.2°).
- **Thông báo bàn giao Collection (13/11/2026):** [../../docs/team/collection_notice_20261113.md](../../docs/team/collection_notice_20261113.md).
- **Bộ dữ liệu mẫu Offline:** Lưu tại `data/fixtures/` và `data/fixtures_spherex_5targets.zip` (không commit FITS lên Git).
- **Tình trạng kiểm thử:** Backend tests pass 64/65 (1 skipped khi chạy offline không có mạng).
