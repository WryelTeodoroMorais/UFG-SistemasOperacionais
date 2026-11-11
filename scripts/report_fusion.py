"""Gera o resumo e o gráfico da avaliação da fusão CSV."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "evolution/fusion"
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".build/matplotlib"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    evaluation = json.loads((BASE / "evaluation.json").read_text())
    demo = json.loads((BASE / "demo.json").read_text())
    policy = evaluation["policy"]
    names = {
        "memory": "Sempre memória",
        "blocks": "Sempre blocos",
        "heuristic": "Heurística",
        "fused": "Uma passagem",
        "learned": "ML experimental",
        "auto": "Auto atual",
        "oracle": "Oráculo medido",
    }
    demo_methods = ("memory", "blocks", "heuristic", "fused", "auto")

    report = [
        "# Avaliação da agregação CSV",
        "",
        "fused lê e converte cada linha uma vez. auto usa ML somente se a validação aprovar a promoção.",
        "",
        "## Promoção de ML",
        "A regra exige pelo menos 5% menos tempo que fused, sem mais violações das metas de RSS em 24, 64 e 128 MiB.",
        "",
        "| Meta | ML na validação (s) | Fusão (s) | Variação ML |",
        "|---:|---:|---:|---:|",
    ]
    for target, row in sorted(policy["validation"].items(), key=lambda item: int(item[0])):
        report.append(
            f"| {target} MiB | {row['ml_seconds']:.5f} | {row['fused_seconds']:.5f} | {row['relative_gain'] * 100:.2f}% |"
        )
    if policy["ml_enabled"]:
        report.append("\nML foi promovido pela validação.")
    else:
        report.append("\nML não foi promovido; auto usa fused sem carregar as árvores.")

    report.extend([
        "",
        "## Teste reservado",
        "O teste contém 18 tarefas em seis arquivos; cada método teve três repetições. As saídas foram comparadas com um oráculo independente.",
        "",
        "| Método | Tempo do lote (s) | RSS médio (MiB) | Maior RSS (MiB) | Metas de 64 MiB |",
        "|---|---:|---:|---:|---:|",
    ])
    for method, row in evaluation["comparison"]["64"].items():
        report.append(
            f"| {names[method]} | {row['total_seconds']:.4f} | {row['mean_peak_rss_mb']:.3f} | {row['max_peak_rss_mb']:.3f} | {row['targets_met']}/{row['jobs']} |"
        )
    report.append(
        f"\nOráculo: {evaluation['correct_reference_executions']} execuções corretas. Replay automático: {evaluation['replay_correct']}/{evaluation['replay_jobs']} saídas e {evaluation['replay_targets_met']}/{evaluation['replay_jobs']} metas atendidas; árvores carregadas: {evaluation['auto_loads_model_trees']}."
    )
    report.append("Os tempos pareados somam medianas das alternativas e custos de decisão; a CLI completa é medida abaixo.")

    report.extend([
        "",
        "## Replay da CLI",
        "Dois CSVs de 100.000 linhas, seis consultas e três repetições. O tempo inclui amostragem, decisão, cópia, sandbox e exportação.",
        "",
        "| Método | Tempo mediano (s) | RSS médio mediano (MiB) | Maior RSS (MiB) | Metas atendidas |",
        "|---|---:|---:|---:|---:|",
    ])
    for method in demo_methods:
        row = demo["summary"][method]
        report.append(
            f"| {names[method]} | {row['median_end_to_end_seconds']:.4f} | {row['median_mean_peak_rss_mb']:.3f} | {row['max_peak_rss_mb']:.3f} | {row['targets_met']}/{row['jobs']} |"
        )
    report.extend([
        "",
        "## Limites",
        "O benchmark usa CSVs sintéticos, um operador conhecido, uma máquina, cache aquecido e três repetições. Os resultados não se estendem a programas arbitrários; RSS é por processo.",
        "",
        "Protocolo: protocol.json. Os arquivos detalhados da avaliação ficam locais. Contexto: docs/FUSAO_E_JUSTIFICATIVA.md.",
        "",
    ])
    (BASE / "REPORT.md").write_text("\n".join(report))

    methods = demo_methods
    labels = ["Memória", "Blocos", "Heurística", "Uma passagem", "Auto atual"]
    colors = ["#96a6b6", "#c49642", "#657fa3", "#327b59", "#137d89"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), layout="constrained")
    charts = (
        (axes[0], "median_end_to_end_seconds", "Lote completo", "Segundos"),
        (axes[1], "median_mean_peak_rss_mb", "Picos de RAM", "MiB RSS por processo"),
    )
    for axis, key, title, unit in charts:
        values = [demo["summary"][method][key] for method in methods]
        bars = axis.bar(labels, values, color=colors)
        axis.bar_label(bars, labels=[f"{value:.2f}" for value in values], padding=4)
        axis.set_ylim(0, max(values) * 1.2)
        axis.set_ylabel(unit)
        axis.set_title(title)
        axis.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Fusão em uma passagem é a estratégia padrão após a validação.", fontsize=10)
    fig.savefig(BASE / "comparison.png", dpi=180)
    plt.close(fig)
    print(BASE / "REPORT.md")


if __name__ == "__main__":
    main()
