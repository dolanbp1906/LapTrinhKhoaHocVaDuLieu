# DANH SÁCH HỒ SƠ NỘP — CHUYÊN ĐỀ 6

Thư mục này chỉ giữ các sản phẩm cần thiết để giảng viên chấm và chạy lại dự án (theo đề cương *Chuyên đề cho KHDL*).

## Sản phẩm chính

| Nhóm | Nội dung |
|---|---|
| Báo cáo | `reports/BAO_CAO_CHUYEN_DE_6.pdf`, `.docx` |
| Slide | `reports/SLIDE_CHUYEN_DE_6.pptx` |
| Notebook | `notebooks/` — 04 notebook bắt buộc |
| Mã nguồn | `src/` — module/lớp Python |
| Dữ liệu | `data/raw/`, `data/processed/` |
| Nhật ký | `logs/` — crawl, lỗi, kho, AI |
| Minh chứng | `reports/figures/`, metric ML, case sai, NumPy |

## Chạy lại

```bash
pip install -r requirements.txt
python src/run_all.py
python -m streamlit run src/app_dashboard.py
```

**Tổng số tệp (không tính manifest):** 95  
**Dung lượng:** ~4.6 MB

## Danh sách tệp

- `.streamlit/config.toml`
- `data/processed/customers.csv`
- `data/processed/fact_sales.csv`
- `data/processed/inventory_transactions.csv`
- `data/processed/order_details.csv`
- `data/processed/orders.csv`
- `data/processed/products_final.csv`
- `data/processed/rfm_raw.csv`
- `data/processed/rfm_segments.csv`
- `data/processed/summaries/low_stock_alert.csv`
- `data/processed/summaries/numpy_revenue_matrix.csv`
- `data/processed/summaries/numpy_revenue_standardized.csv`
- `data/processed/summaries/pivot_category_payment.csv`
- `data/processed/summaries/pivot_month_channel.csv`
- `data/processed/summaries/revenue_by_category.csv`
- `data/processed/summaries/revenue_by_channel.csv`
- `data/processed/summaries/revenue_by_city.csv`
- `data/processed/summaries/revenue_by_month.csv`
- `data/processed/summaries/stock_vs_reorder.csv`
- `data/processed/summaries/top_products.csv`
- `data/raw/products_crawled.csv`
- `data/raw/products_from_html_practice.csv`
- `data/raw/products_lecturer.csv`
- `data/raw/products_lecturer.xlsx`
- `data/raw/products_sample.csv`
- `data/raw/products_sample.json`
- `data/raw/products_sample.xlsx`
- `logs/ai_usage_log.md`
- `logs/buoi1_kiem_tra_products.txt`
- `logs/buoi3_so_sanh_html_excel.txt`
- `logs/buoi4_cleaning_report.txt`
- `logs/buoi5_merge_checks.txt`
- `logs/crawl_log.txt`
- `logs/error_log.txt`
- `logs/inventory_log.csv`
- `notebooks/01_problem_and_data.ipynb`
- `notebooks/02_collection_and_cleaning.ipynb`
- `notebooks/03_eda.ipynb`
- `notebooks/04_machine_learning.ipynb`
- `practice/html_sample/products_page_1.html`
- `practice/html_sample/products_page_2.html`
- `practice/PUBLIC_SOURCES.md`
- `README.md`
- `reports/03_numpy_dictionary_evidence.json`
- `reports/03_numpy_dictionary_evidence.md`
- `reports/04_generation_rules.json`
- `reports/07_ml_metrics.json`
- `reports/07_order_value_top10_errors.csv`
- `reports/07_stock_alert_error_cases.csv`
- `reports/08_rfm_meta.json`
- `reports/08_rfm_segment_summary.csv`
- `reports/bang_dong_gop.md`
- `reports/BAO_CAO_CHUYEN_DE_6.docx`
- `reports/BAO_CAO_CHUYEN_DE_6.pdf`
- `reports/BAO_CAO_TONG_HOP.md`
- `reports/figures/01_revenue_by_month.png`
- `reports/figures/02_revenue_by_category.png`
- `reports/figures/03_top_slow_products.png`
- `reports/figures/04_revenue_by_channel.png`
- `reports/figures/05_order_value_dist.png`
- `reports/figures/06_pair_heatmap.png`
- `reports/figures/07_stock_vs_reorder.png`
- `reports/figures/08_rfm_raw_dist.png`
- `reports/figures/09_revenue_by_city.png`
- `reports/figures/10_order_value_by_channel.png`
- `reports/figures/11_rfm_clusters.png`
- `reports/figures/12_rfm_segment_counts.png`
- `reports/SLIDE_CHUYEN_DE_6.pptx`
- `requirements.txt`
- `source_information.txt`
- `src/__init__.py`
- `src/app_dashboard.py`
- `src/clean_products.py`
- `src/crawl_books_toscrape.py`
- `src/crawl_dummyjson.py`
- `src/crawl_practice_html.py`
- `src/crawl_products.py`
- `src/demo_buoi2.py`
- `src/generate_transactions.py`
- `src/inventory_manager.py`
- `src/merge_products.py`
- `src/models.py`
- `src/plot_style.py`
- `src/read_excel.py`
- `src/run_all.py`
- `src/run_buoi4.py`
- `src/run_buoi5.py`
- `src/run_buoi6_eda.py`
- `src/run_buoi7_ml.py`
- `src/run_buoi8_rfm.py`
- `src/run_numpy_evidence.py`
- `src/sales_manager.py`
- `src/validate_products.py`
