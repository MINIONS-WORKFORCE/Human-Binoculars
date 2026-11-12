# Issue #36 — bàn giao khoa học cho nhóm

Đối chiếu ngày 12/11/2026 với issue #36, wiki API và 13 README trên `main`
`f8541d106894b6e921eb8a165cb7fbcadfe66908`. Đây là mã đào tạo.
Nguyên tự rebase nhánh; gói này không thực hiện rebase, commit, push hay nối route.

## Tiêu chí và bằng chứng

| Yêu cầu | Kết quả |
| --- | --- |
| `astrometry()` tìm tâm Barnard từng khung, khớp chuyển động | Đã có Gaussian centroid trên IMAGE gốc, đổi WCS sang ICRS, hồi quy có trọng số |
| `fit.pmdec` đúng dấu Gaia | FITS thật: +8745.199 ±571.065 mas/năm; Gaia +10362.394. 8 điểm, 196.558 ngày |
| `photometry()` đo R Dra trong khẩu độ | Đã có phép đo, trừ ZODI/nền và truyền sai số; có bảng CSV giữ cả điểm bị loại |
| Chốt `aperture_arcsec` | 12.3 giây cung, **bán kính**; đường kính 24.6; vành nền 49.2–86.1 |
| R Dra có bảng điểm đo | Mock: 20 điểm nguồn hợp lệ +40 điểm của hai sao kiểm soát. Thật: 32 dòng, 0 flux hợp lệ |
| Rebase lên main | **Nguyên thực hiện sau**; chưa xác nhận hoàn thành |

Bảng thật ở `evidence/issue36/observational/rdra/points.csv`: 31 SATURATED,
1 APERTURE_OR_ANNULUS_OUTSIDE_IMAGE. Ô flux trống biểu diễn null, không phải 0.
Nếu team yêu cầu các **flux thật hợp lệ**, tiêu chí đó vẫn chờ dữ liệu không bão hòa
hoặc một phương pháp khác đã kiểm chứng. Không dùng bảng mock để đóng yêu cầu này.
Barnard pmra thật +4107.620 ±487.099 khác Gaia −801.551; giữ cảnh báo này khi trình bày.
Đúng dấu pmdec là tiêu chí demo, không chứng minh nghiệm hai chiều đã chính xác.

## Chạy trên máy của bạn

Chạy từ gốc repo sau khi copy các file trong gói theo đúng cấu trúc. Dùng Python 3.12
và môi trường của README gốc. Có thể cài tập thư viện nhỏ đã dùng trong bài:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r members/nguyen/requirements-science.txt
.venv\Scripts\python.exe -m pytest members/nguyen/tests -q
.venv\Scripts\python.exe members/dong/scripts/validate_api_samples.py
.venv\Scripts\python.exe members/nguyen/build_samples.py
.venv\Scripts\python.exe members/nguyen/issue36.py data/science_acceptance_mock/rdra-manifest.json --output data/issue36/rdra
.venv\Scripts\python.exe members/nguyen/issue36.py data/science_acceptance_mock/barnard-manifest.json --output data/issue36/barnard
```

Kết quả mỗi lần chạy: `points.csv`, `diagnostics.json`, `summary.json`, và
`api_payload.json` nếu metadata đáp ứng API 0.1. Mock R Dra có chi2_reduced ≈10.059,
mock Barnard pmdec ≈+10362.391. Kết quả có `data_kind=mock` trong báo cáo;
API 0.1 không có trường này, nên luôn gửi API payload kèm chẩn đoán/nhãn mode.
`build_samples.py` chỉ ghi mẫu mới vào `data/science_acceptance_mock/api_samples`,
không thay bộ `api_samples/` mà frontend hiện sử dụng.

Linux/Colab: dùng `python` thay `.venv\Scripts\python.exe`. Không dùng đường dẫn C:
trong Colab. Notebook Colab cũ chứa snapshot bài #16/#23, không tự cập nhật theo gói #36.

## Chạy lại dữ liệu thật

```powershell
.venv\Scripts\python.exe members/nguyen/validate_irsa.py --data-dir data/science_validation --output data/issue36/replay --download
.venv\Scripts\python.exe members/nguyen/issue36.py --from-diagnostics data/issue36/replay/r-dra.json --output data/issue36/rdra-real
.venv\Scripts\python.exe members/nguyen/issue36.py --from-diagnostics data/issue36/replay/barnard.json --output data/issue36/barnard-real
```

Lần sau bỏ `--download` nếu đã có cache. Khoảng 0.25 GB, 40 cutout và 2 file hiệu
chuẩn, có URL/SHA-256 trong `evidence/irsa_snapshot.json`. Lượt kiểm tra 12/11 đã đọc
lại FITS cache local và kiểm hash, không chỉ đọc báo cáo cũ. `--from-diagnostics`
chỉ chuyển báo cáo đã đo thành bảng, không đo FITS lần nữa. Có thể dùng dữ liệu ở
checkout khác bằng `--data-dir "đường/dẫn/data/science_validation"`.

Snapshot thật chưa có `survey` dạng số nguyên theo quy ước visit của team. Vì API
0.1 bắt buộc số nguyên, bảng R Dra vẫn xuất đủ nhưng không xuất E6 thật nếu thiếu
metadata này. Ghi `api_payload_status=not_exportable` cùng lý do; không đoán survey.
Nhận visit index từ Khôi/Hữu Hoàng, thêm vào manifest rồi đo lại. Đây không phải
số survey vật lý được suy ra tùy tiện từ khoảng trống 30 ngày.

## Đông import gì?

```python
from shared.science import photometry, astrometry

photo = photometry(cutouts, target, aperture_arcsec=12.3)
astro = astrometry(cutouts, target)
# photo/astro: đúng trường của models Photometry/Astrometry trên main đã kiểm tra.
photo_diagnostics = photometry(cutouts, target, 12.3, diagnostics=True)
astro_diagnostics = astrometry(cutouts, target, diagnostics=True)
```

Hàm không gọi mạng. Đầu vào rỗng trả points rỗng, fit/variability null. Target nhận
các khóa wiki `ra/dec/epoch/pmra/pmdec`, fixture J2016, hoặc mục `astrometry` lồng
trong bảng `shared/targets.json` J2000 hiện tại. Không đổi epoch khi đổi schema.
`pmra` là mu_alpha*cos(delta), mas/năm. `pmdec` dương là về Bắc thiên cầu.

Cutout cần `path`, `mjd` UTC MJD, `detector` D1–D6 hoặc số, `release`, `data_kind`.
Để xuất E6, cần bước sóng micromet và `survey` số nguyên có nguồn/quy ước của nhóm.
Các khóa tùy chọn `spectral_wcs_path`, `sapm_path` cung cấp hiệu chuẩn; `png_wcs_header`
và `png_shape=[height,width]` chỉ cung cấp khi đúng PNG sẽ hiển thị.
Đường dẫn trong manifest tính tương đối với file manifest, không theo thư mục chạy.
Xem `examples/issue36/manifest.schema.json` và `observations_template.csv`.

`diagnostics=True` giữ loại dữ liệu, lý do loại điểm, khẩu độ, nhóm bước sóng và cờ
kiểm tra Gaia. Mặc định chỉ trả các trường E6/E7 có sẵn, không tự thay OpenAPI.
Thông tin ngoài schema không bị lén thêm vào response. Public E6 báo TypeError khi
thiếu survey số nguyên; báo ValueError khi thiếu bước sóng. FITS hỏng/mất có thể báo
OSError/KeyError. Đông ánh xạ thành lỗi API theo owner; gói này chưa nối HTTP routes.
Các phép đo bị loại do chất lượng vẫn có dòng với null, cờ/warnings trong chẩn đoán.

`measured_px=null` khi chưa có WCS của PNG: pixel ảnh FITS gốc không nhất thiết trùng
PNG đã reproject. Khi có đúng lưới, y_PNG=height−1−y_FITS (gốc 0).
Đã sửa ghép nhầm frame khi nhiều ảnh có cùng MJD; thứ tự ổn định giữ danh tính khung.

## Giải thích để trình bày

Photometry trả lời “nguồn sáng bao nhiêu”: lấy tổng pixel trong hình tròn, trừ nền,
đổi MJy/sr sang mJy bằng góc khối pixel và truyền phương sai với bình phương trọng số.
Không thể đổi pixel sáng bề mặt thành thông lượng mà quên diện tích góc.
SOURCE đánh dấu nguồn có sẵn, không đồng nghĩa pixel hỏng; loại SOURCE khỏi vành nền.
OVERFLOW làm phép đo khẩu độ bị loại. Chỉ so chi-square trong các dải bước sóng tương
thích; phổ đỏ khác nhau theo bước sóng không tự chứng minh biến thiên theo thời gian.

Astrometry trả lời “nguồn nằm đâu và dịch chuyển thế nào”: dự đoán vị trí từ epoch,
fit Gaussian trên ảnh tại vùng gần vị trí đó, chuyển tâm pixel qua WCS, khớp độ lệch
Đông/Bắc theo năm. Không dùng chiều tăng/giảm pixel y để kết luận dấu pmdec vì WCS có
thể xoay hoặc lật. Ít nhất 3 điểm và baseline 30 ngày mới trả fit.

Đây là mô hình tối thiểu: chưa fit thị sai năm, chưa đăng ký bằng sao nền, Gaussian
là xấp xỉ PSF. Sai số có sàn 100 mas giả định và được tăng theo scatter; không coi đó
là hiệu chuẩn đã xác nhận. Photometry chưa hiệu chỉnh khẩu độ tuyệt đối, sai số mô
hình ZODI, tương quan pixel hay hệ thống hiệu chuẩn. Bán kính 12.3 là mặc định kỹ
thuật; không được giới thiệu là khẩu độ tối ưu đã chứng minh trên R Dra bão hòa.

## File và cách nộp

Gói có danh sách file/SHA-256 và patch so với main đã đọc. Copy phần `files/` theo
đúng đường dẫn. Nếu nhánh đã có bài #16/#23, **so diff rồi áp dụng thay đổi**, tránh
ghi đè các chỉnh sửa riêng. Không copy thư mục work, môi trường, data, FITS hay .env.
Bảng mục tiêu `shared/targets.json`, OpenAPI, JSON mẫu frontend và route của Đông được
giữ nguyên từ main trong bài kiểm tra; gói không yêu cầu thay những file đó.
Sau khi bạn tự rebase, chạy lại hai lệnh kiểm thử trên và xem diff trước khi commit.
Mẫu nội dung PR: `ISSUE36_PR.md`; giữ `Refs #36` tới khi xong rebase và owner xác nhận
ý nghĩa “bảng điểm đo” với R Dra. Không tự đánh dấu toàn issue hoàn thành.

## Nguồn đối chiếu

- [Issue #36](https://github.com/MINIONS-WORKFORCE/Human-Binoculars/issues/36).
- [API wiki, mục E6/E7 và 6](https://github.com/MINIONS-WORKFORCE/Human-Binoculars/wiki/The-API-contract).
- [Quy trình bàn giao](../../docs/team/handoff.md), [README gốc](../../README.md).
- [Sản phẩm SPHEREx/hiệu chuẩn](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/).
- [IRSA: photometry và FLAGS](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html).
- [IRSA: cutouts](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/cutouts.html).
- [Gaia DR3](https://www.cosmos.esa.int/web/gaia/dr3); bản ghi Gaia của Barnard
  4472832130942575872 và truy vấn có nguồn trong `fixtures/targets.json`.

Phương pháp khẩu độ của bài là lựa chọn triển khai của nhóm; không phải tuyên bố
đã tái tạo toàn bộ thuật toán spectrophotometry chính thức của IRSA.
