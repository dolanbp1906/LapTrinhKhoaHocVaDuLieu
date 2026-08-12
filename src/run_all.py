"""
Chạy lại pipeline chính (từ dữ liệu đã crawl).
Không crawl lại web mặc định (tránh phụ thuộc mạng); có flag --with-crawl.
Chạy: python src/run_all.py
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def run_step(script: str) -> None:
    path = SRC / script
    print(f"\n===== RUN {script} =====")
    subprocess.run([sys.executable, str(path)], check=True, cwd=str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--with-crawl",
        action="store_true",
        help="Chạy lại crawl HTML practice + DummyJSON/Books",
    )
    args = parser.parse_args()

    steps = []
    if args.with_crawl:
        steps += ["crawl_practice_html.py", "crawl_products.py"]
    steps += [
        "run_buoi4.py",
        "run_buoi5.py",
        "run_numpy_evidence.py",
        "run_buoi6_eda.py",
        "run_buoi7_ml.py",
        "run_buoi8_rfm.py",
    ]

    for s in steps:
        run_step(s)
    print("\n=== PIPELINE COMPLETE ===")


if __name__ == "__main__":
    main()
