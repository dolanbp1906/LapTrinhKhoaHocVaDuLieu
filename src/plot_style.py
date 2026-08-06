"""Bảng màu và style dùng chung cho biểu đồ, khớp tông báo cáo và slide."""
from __future__ import annotations

import matplotlib as mpl
import seaborn as sns

PRIMARY = "#00969E"
PRIMARY_DARK = "#046E76"
INK = "#0F2033"
ACCENT = "#2E6F9E"
POSITIVE = "#0E7C66"
WARNING = "#C0703B"
DANGER = "#B4342A"
NEUTRAL = "#687A8E"
GRID = "#DCE3EA"
SEQUENTIAL_CMAP = "YlGnBu"
CATEGORICAL = [PRIMARY, ACCENT, WARNING, POSITIVE, "#7A5EA7", NEUTRAL]


def apply_style() -> None:
    sns.set_theme(style="whitegrid", context="notebook")
    sns.set_palette(CATEGORICAL)
    mpl.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": GRID,
            "axes.labelcolor": NEUTRAL,
            "axes.labelsize": 10.5,
            "axes.titlesize": 13,
            "axes.titleweight": "bold",
            "axes.titlecolor": INK,
            "axes.titlepad": 12,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "grid.color": GRID,
            "grid.linewidth": 0.8,
            "xtick.color": NEUTRAL,
            "ytick.color": NEUTRAL,
            "xtick.labelsize": 9.5,
            "ytick.labelsize": 9.5,
            "legend.frameon": False,
            "legend.fontsize": 9.5,
            "savefig.facecolor": "white",
        }
    )
