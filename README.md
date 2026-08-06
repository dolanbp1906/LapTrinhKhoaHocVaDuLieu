# Chuyên đề 6 — Phân tích bán hàng, quản lý tồn kho và phân nhóm khách hàng

Dự án cuối kỳ môn **Lập trình cho Khoa học dữ liệu**.  
Thực hiện **1 mình**. Cửa hàng: **Nhà sách và văn phòng phẩm**.

## Mục tiêu

1. Hệ thống quản lý kho OOP (nhập / xuất / điều chỉnh) có nhật ký
2. Phân tích doanh thu, sản phẩm bán chạy, cặp mua cùng nhau
3. Phân nhóm khách hàng RFM + K-Means
4. Dự đoán giá trị đơn hàng và cảnh báo tồn kho thấp

## Nguồn dữ liệu

| Nguồn | Vai trò |
|---|---|
| `data/raw/products_lecturer.*` (60 SP) | Dữ liệu khởi đầu do giảng viên cung cấp |
| HTML mẫu / Mock API trong `practice/` | Thực hành thu thập (không tính SP mới) |
| [DummyJSON Products](https://dummyjson.com/docs/products) | Crawl bổ sung (15 SP) |
| [Books to Scrape](https://books.toscrape.com/) | Crawl bổ sung (15 SP) |

Catalog cuối: **90 sản phẩm** = 60 GV + 30 crawl.

## Cài đặt

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Xem giao diện hệ thống

```bash
python -m streamlit run src/app_dashboard.py
```

Mở [http://localhost:8501](http://localhost:8501)

UI bám đúng bối cảnh chuyên đề:

1. **Nghiệp vụ kho** — nhập / xuất / điều chỉnh, chặn âm kho, nhật ký trước/sau  
2. **Bán hàng** — tạo đơn trừ kho, rollback nếu thiếu hàng  
3. **Phân tích** — doanh thu, SP bán chạy/chậm, cặp mua cùng nhau  
4. **RFM** — phân nhóm + chiến lược  
5. **Học máy** — dự đoán giá trị đơn / cảnh báo dưới reorder  
6. **Nhật ký** — `inventory_log` + `error_log` runtime

(Trên máy này dùng `python -m streamlit` vì `streamlit.exe` có thể bị policy chặn.)

## Chạy lại toàn bộ pipeline

```bash
# Từ dữ liệu đã crawl (khuyến nghị)
python src/run_all.py

# Kèm crawl lại web
python src/run_all.py --with-crawl
```

Hoặc từng buổi: `demo_buoi2.py`, `crawl_products.py`, `run_buoi4.py` … `run_buoi8_rfm.py`.

## Tiến độ (đã hoàn thành 8/8)

| Buổi | Trạng thái | Hồ sơ |
|---|---|---|
| 1. Khởi động & thiết kế | ✅ | `reports/01_hoso_buoi_1.md` |
| 2. OOP kho | ✅ | `reports/02_hoso_buoi_2.md` |
| 3. Thu thập / crawl | ✅ | `reports/03_hoso_buoi_3.md` |
| 4. Clean + sinh giao dịch | ✅ | `reports/04_hoso_buoi_4.md` |
| 5. Merge / Pivot | ✅ | `reports/05_hoso_buoi_5.md` |
| 6. EDA | ✅ | `reports/06_hoso_buoi_6.md` |
| 7. ML | ✅ | `reports/07_hoso_buoi_7.md` |
| 8. RFM + hoàn thiện | ✅ | `reports/08_hoso_buoi_8.md` |

## Sản phẩm nộp chính

- Báo cáo Word 27 trang: [`reports/BAO_CAO_CHUYEN_DE_6.docx`](reports/BAO_CAO_CHUYEN_DE_6.docx)
- Báo cáo PDF: [`reports/BAO_CAO_CHUYEN_DE_6.pdf`](reports/BAO_CAO_CHUYEN_DE_6.pdf)
- Bản tóm tắt Markdown: [`reports/BAO_CAO_TONG_HOP.md`](reports/BAO_CAO_TONG_HOP.md)
- Slide thuyết trình: [`reports/SLIDE_CHUYEN_DE_6.pptx`](reports/SLIDE_CHUYEN_DE_6.pptx)
- Slide outline: [`reports/SLIDE_OUTLINE.md`](reports/SLIDE_OUTLINE.md)
- Nhật ký AI: [`logs/ai_usage_log.md`](logs/ai_usage_log.md)
- Đóng góp: [`reports/bang_dong_gop.md`](reports/bang_dong_gop.md)
- Nguồn dữ liệu: [`source_information.txt`](source_information.txt)
- Notebooks bắt buộc: `01_problem_and_data.ipynb`, `02_collection_and_cleaning.ipynb`, `03_eda.ipynb`, `04_machine_learning.ipynb`
- Minh chứng NumPy/dictionary: `reports/03_numpy_dictionary_evidence.*`
- Figures: `reports/figures/`

## Kết quả nổi bật (tóm tắt)

- DecisionTree dự đoán giá trị đơn: **R² ≈ 0.79**
- DecisionTree cảnh báo tồn kho: **F1 ≈ 0.98**
- RFM k=4 (`reference_date=2026-01-01`): Champions / Loyal / Potential / At Risk
- Offline ~42% doanh thu; tháng đỉnh 2025-04; 77/90 SP dưới reorder

## Lưu ý

- Không trình bày trường mô phỏng như dữ liệu thu thập từ website.
- Khi sinh customers/orders: random seed cố định (42) và đã công bố quy tắc.
- Không vượt CAPTCHA; có timeout và nghỉ giữa các request khi crawl.
