# Hữu Hoàng: Image processing

What goes here: FITS/WCS notes, reproject experiments, flag masking, stacking per detector x survey, difference images, PNG export.

## Tasks ưu tiên ngày 07/11/2026

Xem [TASKS.md](TASKS.md) để đọc từng task, minh chứng, giải thích thuật ngữ và lệnh chạy lại. Đã có lưới TAN mới, benchmark 10/50 cutout, kiểm tra centroid, `make_frames(ra, dec, fov, det)`, median/ảnh hiệu, bộ mẫu năm mục tiêu D1/D3/D6, flags bão hòa và RGB giả.

- [Tổng quan năm mục tiêu](../../data/five_targets/overview.png)
- [Kiểm chứng sản phẩm lưu trên đĩa](../../data/five_targets/verification.json)
- [Minh chứng căn sao nền](../../data/tan_wise0855/alignment_evidence.png)

Sản phẩm trong `data/` chỉ có trên máy đã chạy. Khung là dữ liệu hiển thị từ mẫu quan sát, chưa phải đo quang hoặc bằng chứng biến thiên.

## Task D — 08/11/2026

[TASKS.md](TASKS.md#d-cutout--khung-png-và-ảnh-hiệu--0811) ghi rõ đầu vào thật, kết quả, thời gian chạy máy và phần cần Nguyên/Khôi bàn giao. Chạy `.venv/Scripts/python.exe members/huu-hoang/task_d.py` từ gốc repo khi đã có dữ liệu C; đầu ra ở `data/tasks_def/D/`. Đây là demo kỹ thuật, chưa xác nhận bài tự dựng không chép mã trong 90 phút hoặc mốc của cả sáu người.

## Chuẩn bị E–F — lịch 09–10/11/2026

Xem tiếp E/F trong [TASKS.md](TASKS.md): có lỗi màu vùng thiếu trước/sau, demo photutils tìm cặp trái dấu và đo mẫu theo bước sóng trên FITS Luhman 16 thật. Mã [tasks_def.py](tasks_def.py) nhận `E`, `F`, `F --download`, `F --wide-background`; kết quả ở `data/tasks_def/`. Nền gần cho 0/18 mẫu đạt, thí nghiệm nền xa cho 5 mẫu đo sơ bộ; chưa có phổ được Nguyên kiểm duyệt. Các phần chờ issue/runbook/bàn giao và cách tiếp tục được ghi riêng, không xác nhận thay kết quả diễn tập của nhóm.

## Reproject demo: 2025 / 2026

Hướng dẫn tiếng Việt, giải thích từng file và link PNG/GIF: [ghichu.md](../../ghichu.md).

Chạy tại gốc repo với dữ liệu đã tải:

```powershell
.venv\Scripts\python members/huu-hoang/reproject_demo.py
```

Máy mới: cài môi trường theo README gốc, thêm `--download` để lấy đúng hai cutout IRSA. Sản phẩm tự lưu trong `data/reproject_wise0855/` (gitignored), gồm PNG gốc/sau xử lý, GIF blink, footprint, FITS kết quả, report và log.

Ví dụ căn WCS vùng WISE 0855; chưa xác nhận phát hiện sao lùn nâu, hai ảnh khác bước sóng. Không dùng GIF để kết luận biến thiên.

- Work on a branch named `huu-hoang/<task>` and open a small PR.
- Notebooks: clear outputs before committing (`nbstripout` does it automatically once installed).
- Never commit FITS files, cutouts or databases; put them in `data/` (gitignored) or on the team drive.
- Code that a teammate will import goes in `shared/`, not here.
