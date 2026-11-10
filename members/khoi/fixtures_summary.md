# BÁO CÁO FIXTURE 5 MỤC TIÊU (DETECTOR D6 & D1)
- **Tác giả:** Khôi (`members/khoi/build_five_targets_fixture.py`)
- **Issue liên quan:** #21 (Task ngày 10/11)
- **Tổng số khung FITS đã tải:** `30` khung
- **Kích thước cutout:** `0.05°` (3 arcmin)

## Bảng thống kê số khung theo mục tiêu
| Key | Mục tiêu | D6 (4.4–5.0 µm) | D1 (0.75–1.11 µm) | Tổng khung | Tiêu chí >= 3 |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `barnard` | **Barnard's Star** | 3 | 3 | **6** | ✅ ĐẠT |
| `wise0855` | **WISE 0855-0714** | 3 | 3 | **6** | ✅ ĐẠT |
| `epsindib` | **Epsilon Indi B** | 3 | 3 | **6** | ✅ ĐẠT |
| `rwaur` | **RW Aurigae** | 3 | 3 | **6** | ✅ ĐẠT |
| `rdra` | **R Draconis** | 3 | 3 | **6** | ✅ ĐẠT |

## Kiểm tra tính năng find_frames()
- Chế độ `fixture`: Đọc trực tiếp từ `manifest.json` và trả về danh sách khung FITS mà không cần gọi mạng.
- Đạt 100% tiêu chí Done when của Issue #21.