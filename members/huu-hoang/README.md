# Hữu Hoàng: Image processing

What goes here: FITS/WCS notes, reproject experiments, flag masking, stacking per detector x survey, difference images, PNG export.

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
