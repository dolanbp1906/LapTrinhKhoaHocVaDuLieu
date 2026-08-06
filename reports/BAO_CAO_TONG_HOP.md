# BÁO CÁO TỔNG HỢP
## Chuyên đề 6 — Phân tích bán hàng, quản lý tồn kho và phân nhóm khách hàng

**Môn:** Lập trình cho Khoa học dữ liệu  
**Hình thức:** Thực hiện 1 mình  
**Cửa hàng:** Nhà sách và văn phòng phẩm  
**Ngày hoàn thành pipeline:** 2026-07-23

---

## 1. Giới thiệu và mục tiêu

Dự án xây dựng một quy trình khoa học dữ liệu hoàn chỉnh cho cửa hàng nhà sách – văn phòng phẩm, kết hợp:

1. Hệ thống quản lý kho hướng đối tượng (nhập/xuất/điều chỉnh) có nhật ký và chặn tồn kho âm.
2. Thu thập và chuẩn hóa dữ liệu sản phẩm từ nhiều nguồn.
3. Phân tích doanh thu, sản phẩm, kênh bán và tồn kho.
4. Học máy: dự đoán giá trị đơn hàng và cảnh báo tồn kho thấp.
5. Phân nhóm khách hàng theo RFM + K-Means kèm chiến lược tiếp cận.

### 1.1. Câu hỏi nghiên cứu

1. Danh mục và kênh bán nào tạo doanh thu lớn nhất?
2. Sản phẩm nào bán chạy/bán chậm; cặp nào thường mua cùng nhau?
3. Thời điểm nào doanh thu cao nhất?
4. Khách hàng chia thành những nhóm RFM nào?
5. Dự đoán giá trị đơn hàng đạt sai số bao nhiêu?
6. Sản phẩm nào nguy cơ dưới `reorder_level`?

### 1.2. Phạm vi và nguyên tắc

- Không vượt CAPTCHA / chống bot.
- Ghi rõ trường thu thập vs mô phỏng.
- Dữ liệu giao dịch là **synthetic** (seed=42), phục vụ học tập.
- Có phương án dự phòng: HTML mẫu / mock API nếu nguồn online lỗi.

---

## 2. Nguồn dữ liệu và từ điển dữ liệu

### 2.1. Nguồn

| Nguồn | Số SP | Vai trò |
|---|---|---|
| `products_lecturer` (GV) | 60 | Khởi đầu |
| DummyJSON Products API | 15 | Crawl bổ sung (`public_api`) |
| Books to Scrape | 15 | Crawl bổ sung (`public_website`) |
| HTML mẫu 2 trang | 60 | Thực hành (không tính SP mới) |

**Catalog cuối:** 90 sản phẩm (`data/processed/products_final.csv`).

### 2.2. Chuẩn hóa tiền tệ

- DummyJSON: USD × 25.000 = VND  
- Books to Scrape: GBP × 33.000 = VND  

### 2.3. Các bảng giao dịch (đã sinh)

| Bảng | Số bản ghi |
|---|---|
| customers | 220 |
| orders | 1.200 |
| order_details | 3.274 |
| inventory_transactions | 3.396 |

Quy tắc sinh: xem `reports/04_generation_rules.json`.

### 2.4. Từ điển sản phẩm (rút gọn)

`product_id`, `product_name`, `category`, `brand`, `unit`, `unit_price`, `initial_quantity`, `reorder_level`, `popularity_weight`, `paired_product_id`, `source_type`, `source_reference`, …

---

## 3. Phương pháp

### 3.1. OOP quản lý kho

Các lớp: `Product`, `Customer`, `Order`, `OrderItem`, `InventoryTransaction`, `InventoryManager`, `SalesManager`.

- Từ chối giao dịch làm âm kho; ghi `inventory_log.csv`, `error_log.txt`.
- Đơn hàng thiếu hàng: rollback các dòng đã trừ.

### 3.2. Làm sạch và ghép

- Chuẩn hóa text/kiểu số; bỏ trùng `product_id`; sửa `reorder_level` nếu không hợp lệ.
- Merge lecturer ưu tiên khi trùng ID; giữ cột nguồn.

### 3.3. Phân tích

- Fact table: `order_details ⋈ orders ⋈ customers ⋈ products`.
- Groupby/Pivot theo tháng, danh mục, thành phố, kênh, thanh toán.
- EDA ≥ 8 biểu đồ.

### 3.4. Học máy

**A. Hồi quy giá trị đơn**

- Features: số dòng, số lượng, giá TB, discount, tháng, dow, kênh, thành phố, loại KH, thanh toán.
- Models: DummyRegressor, LinearRegression, DecisionTreeRegressor.
- Metric: MAE, RMSE, R² trên tập test.

**B. Phân lớp cảnh báo tồn kho**

- Nhãn: `current_quantity <= reorder_level`.
- Features: thuộc tính đầu kỳ + bán/nhập **nửa đầu năm 2025** (tránh rò rỉ sold cả kỳ).
- Models: DummyClassifier, LogisticRegression, DecisionTreeClassifier.
- Metric: Accuracy, Precision, Recall, F1.

### 3.5. RFM + K-Means

- `reference_date = 2026-01-01` (cố định).
- Features: recency_days, frequency, log1p(monetary); StandardScaler.
- Chọn k ∈ {4,5} theo silhouette; gán nhãn Champions / Loyal / Potential / At Risk / Hibernating.

---

## 4. Kết quả chính

### 4.1. Doanh thu và vận hành

- Danh mục doanh thu cao nhất: **Thiết bị văn phòng** (ảnh hưởng giá laptop DummyJSON).
- Kênh lớn nhất: **offline (~42%)**.
- Thành phố lớn nhất: **TP. Hồ Chí Minh**.
- Tháng đỉnh: **2025-04**.
- **77/90** sản phẩm dưới hoặc bằng `reorder_level` — áp lực tồn kho cao trong dữ liệu mô phỏng.

### 4.2. Học máy

| Bài toán | Baseline | Model tốt nhất | Chỉ số nổi bật |
|---|---|---|---|
| Giá trị đơn | Dummy MAE ~44M | DecisionTree | R² ≈ 0.79; MAE ≈ 10.8M |
| Cảnh báo tồn kho | Dummy F1 0.92 | DecisionTree | F1 ≈ 0.98 |

Phân tích ≥ 10 case sai: `reports/07_order_value_top10_errors.csv`, `reports/07_stock_alert_error_cases.csv`.

### 4.3. Phân nhóm khách hàng

Chi tiết số liệu từng segment: `reports/08_hoso_buoi_8.md`, `08_rfm_segment_summary.csv`.

Chiến lược rút gọn:

- **Champions:** ưu đãi VIP, giữ chân.
- **Loyal:** upsell/cross-sell.
- **Potential:** coupon kích hoạt.
- **At Risk:** win-back.
- **Hibernating:** campaign chi phí thấp.

---

## 5. Thảo luận giới hạn

1. Giao dịch synthetic không phản ánh hành vi mua thật.
2. FX cố định làm giá thiết bị/sách chiếm tỷ trọng doanh thu lớn.
3. Lớp `low_stock` mất cân bằng → Accuracy dễ cao; cần nhìn F1/Recall.
4. Mô hình chỉ mang tính minh họa quy trình; chưa đủ để tự động đặt hàng.
5. Crawl phụ thuộc mạng; đã có HTML/API dự phòng.

---

## 6. Kết luận

Dự án đã hoàn thành đủ quy trình KHDL theo đề cương Chuyên đề 6: thu thập → làm sạch → phân tích → mô hình → phân cụm → báo cáo, kèm hệ thống OOP kho có kiểm soát tồn kho. Pipeline có thể chạy lại bằng:

```bash
python src/run_all.py
# hoặc kèm crawl:
python src/run_all.py --with-crawl
```

---

## 7. Phụ lục — Danh mục sản phẩm nộp

### Mã nguồn chính

- `src/models.py`, `inventory_manager.py`, `sales_manager.py`, `demo_buoi2.py`
- `src/crawl_practice_html.py`, `crawl_dummyjson.py`, `crawl_books_toscrape.py`, `crawl_products.py`
- `src/clean_products.py`, `merge_products.py`, `validate_products.py`, `generate_transactions.py`, `run_buoi4.py`
- `src/run_buoi5.py`, `run_buoi6_eda.py`, `run_buoi7_ml.py`, `run_buoi8_rfm.py`, `run_all.py`

### Notebook

- `01_problem_and_data.ipynb`
- `02b_merge_groupby_pivot.ipynb`
- `03_eda.ipynb`
- `04_machine_learning.ipynb`

### Dữ liệu

- `data/raw/` — lecturer, crawled, HTML practice  
- `data/processed/` — products_final, customers, orders, order_details, inventory, fact_sales, rfm_*

### Báo cáo / minh chứng

- `reports/01` … `08` hồ sơ buổi  
- `reports/figures/`  
- `reports/SLIDE_OUTLINE.md`  
- `logs/ai_usage_log.md`  
- `reports/bang_dong_gop.md`  
- `source_information.txt`

---

*Báo cáo này là bản markdown tổng hợp nội dung chuyên đề. Khi nộp Word/PDF, sinh viên có thể chuyển định dạng và bổ sung họ tên, MSSV, trang bìa theo mẫu nhà trường.*
