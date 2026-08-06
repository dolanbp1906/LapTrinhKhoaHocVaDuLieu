"""Tạo thư mục chỉ chứa các tệp cần nộp cho giảng viên."""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT.parent / "NOP_GIAO_VIEN_CHUYEN_DE_6"


def copy_file(source: Path, relative_destination: str | Path) -> None:
    if not source.exists():
        raise FileNotFoundError(f"Thiếu tệp bắt buộc: {source}")
    target = DEST / relative_destination
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def copy_matching(source_dir: Path, pattern: str, destination_dir: str | Path) -> None:
    for source in sorted(source_dir.glob(pattern)):
        if source.is_file():
            copy_file(source, Path(destination_dir) / source.name)


def build_manifest() -> None:
    files = sorted(path for path in DEST.rglob("*") if path.is_file())
    total_bytes = sum(path.stat().st_size for path in files)
    lines = [
        "# DANH SÁCH HỒ SƠ NỘP — CHUYÊN ĐỀ 6",
        "",
        "Thư mục này chỉ giữ các sản phẩm cần thiết để giảng viên chấm và chạy lại dự án.",
        "",
        "## Sản phẩm chính",
        "",
        "- `reports/BAO_CAO_CHUYEN_DE_6.pdf` — báo cáo chính.",
        "- `reports/BAO_CAO_CHUYEN_DE_6.docx` — bản Word có thể chỉnh sửa.",
        "- `reports/SLIDE_CHUYEN_DE_6.pptx` — slide bảo vệ.",
        "- `notebooks/` — đúng 04 notebook bắt buộc.",
        "- `src/` — mã nguồn theo module/lớp.",
        "- `data/raw/`, `data/processed/` — dữ liệu gốc và dữ liệu sạch.",
        "- `logs/` — nhật ký crawl, lỗi, kho và sử dụng AI.",
        "- `reports/figures/`, metric và case sai — minh chứng kết quả.",
        "",
        "## Chạy lại",
        "",
        "```bash",
        "pip install -r requirements.txt",
        "python src/run_all.py",
        "python -m streamlit run src/app_dashboard.py",
        "```",
        "",
        "## Việc cần điền trước khi gửi",
        "",
        "- Họ tên, mã học viên và tên giảng viên trong báo cáo/slide.",
        "",
        f"**Tổng số tệp (không tính manifest):** {len(files)}  ",
        f"**Dung lượng:** {total_bytes / (1024 * 1024):.2f} MB",
        "",
        "## Danh sách tệp",
        "",
    ]
    lines.extend(f"- `{path.relative_to(DEST).as_posix()}`" for path in files)
    (DEST / "DANH_SACH_FILE_NOP.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True)

    # Tệp gốc để cài đặt, hiểu nguồn và chạy lại.
    for filename in ["README.md", "requirements.txt", "source_information.txt"]:
        copy_file(ROOT / filename, filename)
    copy_file(ROOT / ".streamlit" / "config.toml", ".streamlit/config.toml")

    # Dữ liệu gốc: giữ bản CSV/JSON và bổ sung đúng bản Excel giảng viên.
    copy_matching(ROOT / "data" / "raw", "*", "data/raw")
    lecturer_xlsx = ROOT.parent / "products_sample.xlsx"
    if lecturer_xlsx.exists():
        copy_file(lecturer_xlsx, "data/raw/products_lecturer.xlsx")

    # Dữ liệu đã xử lý cần cho phân tích, ML, RFM và dashboard.
    processed_files = [
        "products_final.csv",
        "customers.csv",
        "orders.csv",
        "order_details.csv",
        "inventory_transactions.csv",
        "fact_sales.csv",
        "rfm_raw.csv",
        "rfm_segments.csv",
    ]
    for filename in processed_files:
        copy_file(ROOT / "data" / "processed" / filename, f"data/processed/{filename}")
    copy_matching(
        ROOT / "data" / "processed" / "summaries",
        "*.csv",
        "data/processed/summaries",
    )

    # Đúng 04 notebook bắt buộc theo đề cương.
    notebooks = [
        "01_problem_and_data.ipynb",
        "02_collection_and_cleaning.ipynb",
        "03_eda.ipynb",
        "04_machine_learning.ipynb",
    ]
    for filename in notebooks:
        copy_file(ROOT / "notebooks" / filename, f"notebooks/{filename}")

    # Toàn bộ mã nguồn chính; không kèm cache, môi trường ảo hoặc Git.
    copy_matching(ROOT / "src", "*.py", "src")

    # Snapshot HTML tối thiểu để bước thu thập thực hành chạy lại được.
    copy_matching(
        ROOT / "practice" / "html_sample",
        "*.html",
        "practice/html_sample",
    )
    copy_file(ROOT / "practice" / "PUBLIC_SOURCES.md", "practice/PUBLIC_SOURCES.md")

    # Nhật ký bắt buộc, loại bỏ logs/ui_runtime của phiên demo.
    log_files = [
        "ai_usage_log.md",
        "crawl_log.txt",
        "error_log.txt",
        "inventory_log.csv",
        "buoi1_kiem_tra_products.txt",
        "buoi3_so_sanh_html_excel.txt",
        "buoi4_cleaning_report.txt",
        "buoi5_merge_checks.txt",
    ]
    for filename in log_files:
        copy_file(ROOT / "logs" / filename, f"logs/{filename}")

    # Báo cáo và slide chính.
    submission_reports = [
        "BAO_CAO_CHUYEN_DE_6.pdf",
        "BAO_CAO_CHUYEN_DE_6.docx",
        "SLIDE_CHUYEN_DE_6.pptx",
        "BAO_CAO_TONG_HOP.md",
        "bang_dong_gop.md",
        "DEMO_FLOW.md",
    ]
    for filename in submission_reports:
        copy_file(ROOT / "reports" / filename, f"reports/{filename}")

    # Minh chứng cho EDA, NumPy, mô hình, phân tích lỗi và RFM.
    evidence_reports = [
        "03_numpy_dictionary_evidence.md",
        "03_numpy_dictionary_evidence.json",
        "04_generation_rules.json",
        "07_ml_metrics.json",
        "07_order_value_top10_errors.csv",
        "07_stock_alert_error_cases.csv",
        "08_rfm_meta.json",
        "08_rfm_segment_summary.csv",
    ]
    for filename in evidence_reports:
        copy_file(ROOT / "reports" / filename, f"reports/evidence/{filename}")
    copy_matching(ROOT / "reports" / "figures", "*.png", "reports/figures")

    build_manifest()
    files = [path for path in DEST.rglob("*") if path.is_file()]
    size_mb = sum(path.stat().st_size for path in files) / (1024 * 1024)
    print(f"Created: {DEST}")
    print(f"Files: {len(files)}")
    print(f"Size: {size_mb:.2f} MB")


if __name__ == "__main__":
    main()
