from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".build/matplotlib"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    methods = ["Fixo", "Heurística", "Supervisionado"]
    colors = ["#758195", "#e69f00", "#2878b5"]
    panels = [
        ("Conclusão correta", [100.0, 90.6, 91.9], "%", ["100,0%", "90,6%", "91,9%"]),
        ("Limite médio de memória", [128.0, 50.65, 39.56], "MiB", ["128,00", "50,65", "39,56"]),
        ("Limite médio de parede", [2.000, 1.286, 0.246], "segundos", ["2,000", "1,286", "0,246"]),
        ("Tempo observado médio", [0.122, 0.115, 0.114], "segundos", ["0,122", "0,115", "0,114"]),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(11, 7), layout="constrained")
    fig.suptitle("Comparação dos métodos no teste final", fontsize=17, fontweight="bold")

    for axis, (title, values, unit, labels) in zip(axes.flat, panels):
        bars = axis.bar(methods, values, color=colors, width=0.62)
        axis.set_title(title, loc="left", fontweight="bold")
        axis.set_ylabel(unit)
        axis.set_ylim(0, max(values) * 1.28)
        axis.yaxis.grid(True, color="#d9dee7", linewidth=0.8)
        axis.set_axisbelow(True)
        axis.spines[["top", "right"]].set_visible(False)
        axis.tick_params(axis="x", labelsize=9, length=0)
        axis.bar_label(bars, labels=labels, padding=3, fontsize=9)

    fig.savefig(ROOT / "docs/figures/method-comparison.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
