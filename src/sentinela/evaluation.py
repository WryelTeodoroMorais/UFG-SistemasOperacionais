"""Comparação por reexecução, com resultados funcionais como oráculo."""
import json
from pathlib import Path
import random
import statistics

import numpy as np

from .data import digest, load
from .learning import frozen, prediction_report, recommend
from .policy import Budget, authorize
from .sandbox import run
from .tasks import make_task


def baseline(row: dict, kind: str) -> dict:
    if kind == "fixed":
        return {"memory_mb": 128, "wall_seconds": 2.0,
                "read_input": True, "write_output": True}
    if kind == "heuristic":
        # Regra definida antes da validação; usa as mesmas entradas prévias.
        f = row["features"]
        return {"memory_mb": min(256, 32 + row["input_bytes"] / 1024**2 * 64),
                "wall_seconds": 1.0 + row["input_bytes"] / 1024**2,
                "read_input": f[7] > 0, "write_output": f[8] > 0}
    raise ValueError(kind)


def evaluate(root: Path, split="validation"):
    rows = load(root, split)
    package, config = frozen(root)
    report_path = root / "reports" / f"{split}.json"
    if report_path.exists():
        raise FileExistsError("Avaliação preservada; use outra cópia para nova rodada")
    if set(package["train_families"]) & {r["family"] for r in rows}:
        raise ValueError("Famílias de avaliação presentes no treino")
    results = []
    for row in rows:
        task = make_task(row["family"], int(row["id"].rsplit("-", 1)[1]))
        methods = ["fixed", "heuristic", "supervised"]
        random.Random(task["seed"]).shuffle(methods)
        for method in methods:
            rec = (recommend(package, row["features"], config["margin"], config["wall_margin"])
                   if method == "supervised" else baseline(row, method))
            budget = authorize(rec, Budget())
            measured = run(task["code"], task["input_data"], budget)
            reference = row["runs"][0]
            success = (measured["returncode"] == 0 and not measured["timed_out"]
                       and measured["stdout"] == reference["stdout"]
                       and measured["outputs"] == reference["outputs"])
            granted = [budget.read_input, budget.write_output]
            results.append({"id": row["id"], "family": row["family"], "method": method,
                            "success": success, "result": measured,
                            "excess_capabilities": sum(bool(g) and not a for g, a in zip(granted, row["capabilities"])),
                            "missing_capabilities": sum(bool(a) and not g for g, a in zip(granted, row["capabilities"]))})
        print(f"evaluate {split}: {row['id']}", flush=True)
    summaries = {}
    for method in ("fixed", "heuristic", "supervised"):
        subset = [r for r in results if r["method"] == method]
        successes = sum(r["success"] for r in subset)
        n = len(subset)
        # Wilson 95%, descritivo: variantes da mesma família não são independentes.
        z = 1.96
        center = (successes / n + z*z/(2*n)) / (1 + z*z/n)
        half = z * np.sqrt(successes/n*(1-successes/n)/n + z*z/(4*n*n))/(1+z*z/n)
        summaries[method] = {
            "n": n, "successes": successes, "success_rate": successes/n,
            "wilson95_descriptive": [float(center-half), float(center+half)],
            "mean_memory_budget_mb": statistics.mean(r["result"]["budget"]["memory_mb"] for r in subset),
            "mean_wall_budget_seconds": statistics.mean(r["result"]["budget"]["wall_seconds"] for r in subset),
            "mean_observed_wall_seconds": statistics.mean(r["result"]["wall_seconds"] for r in subset),
            "excess_capabilities": sum(r["excess_capabilities"] for r in subset),
            "missing_capabilities": sum(r["missing_capabilities"] for r in subset),
            "per_family": {family: {"n": sum(r["family"] == family for r in subset),
                                    "successes": sum(r["success"] for r in subset if r["family"] == family)}
                           for family in sorted({r["family"] for r in subset})}}
    report = {"split": split, "source_sha256": digest(root / "data" / f"{split}.jsonl"),
              "frozen_model_sha256": config["model_sha256"],
              "prediction": prediction_report(root, split), "methods": summaries,
              "execution": results,
              "limits": ["benchmarks autorais controlados; não são tarefas de agentes reais",
                         "limite AS é por processo; orçamento não significa RAM reservada",
                         "um replay por método; três medições de referência por tarefa",
                         "poucas famílias; intervalos de Wilson apenas descritivos"]}
    report_path.parent.mkdir(exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    return report
