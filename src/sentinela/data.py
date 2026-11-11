"""Coleta e leitura das partições medidas."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import statistics

from .features import FEATURE_NAMES, extract
from .policy import Budget
from .sandbox import run
from .tasks import tasks

SPLITS = frozenset({"train", "validation", "test"})


def validate_split(split: str):
    if split not in SPLITS:
        raise ValueError(f"Partição desconhecida: {split}")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(root: Path, split: str) -> list[dict]:
    validate_split(split)
    return [json.loads(line) for line in (root / "data" / f"{split}.jsonl").read_text().splitlines()]


def collect(root: Path, split: str, repeats=3, *, append=False):
    validate_split(split)
    if append and split != "test":
        raise ValueError("A coleta incremental só pode ser usada para ampliar o teste")
    path = root / "data" / f"{split}.jsonl"
    if path.exists() and not append:
        raise FileExistsError(f"Coleta preservada: {path}; use outro diretório para nova rodada")
    existing_lines = path.read_text().splitlines() if append and path.exists() else []
    existing = [json.loads(line) for line in existing_lines]
    existing_ids = {row["id"] for row in existing}
    if len(existing_ids) != len(existing):
        raise ValueError(f"IDs repetidos no conjunto existente: {path}")
    if any(len(row.get("runs", ())) != repeats for row in existing):
        raise ValueError("A repetição solicitada precisa coincidir com os registros já coletados")
    records = []
    for task in tasks(split):
        if task["id"] in existing_ids:
            continue
        runs = [run(task["code"], task["input_data"], Budget()) for _ in range(repeats)]
        if any(r["returncode"] != 0 or r["timed_out"] for r in runs):
            raise RuntimeError(f"Falha no benchmark {task['id']}: {runs}")
        signatures = {(r["stdout"], json.dumps(r["outputs"], sort_keys=True)) for r in runs}
        if len(signatures) != 1:
            raise RuntimeError(f"Benchmark não determinístico: {task['id']}")
        records.append({
            "id": task["id"], "family": task["family"], "seed": task["seed"],
            "split": split,
            "features": extract(task["code"], len(task["input_data"])),
            "feature_names": FEATURE_NAMES, "capabilities": task["capabilities"],
            "code_sha256": hashlib.sha256(task["code"].encode()).hexdigest(),
            "input_sha256": hashlib.sha256(task["input_data"]).hexdigest(),
            "input_bytes": len(task["input_data"]),
            "targets": {
                "memory_mb": max(r["peak_vms_mb"] for r in runs),
                "wall_seconds": max(r["wall_seconds"] for r in runs),
            },
            "runs": runs, "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        })
        print(f"{split}: {task['id']} ({len(records)})", flush=True)
    if append and not records:
        raise FileExistsError(f"Não há tarefas novas para acrescentar a {path}")
    combined = existing + records
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_data = path.with_suffix(path.suffix + ".tmp")
    new_lines = [json.dumps(record, ensure_ascii=False) for record in records]
    temporary_data.write_text("\n".join(existing_lines + new_lines) + "\n")
    temporary_data.replace(path)
    counts = dict(sorted(Counter(r["family"] for r in combined).items()))
    summary = {"split": split, "samples": len(combined), "added_samples": len(records),
               "repeats_per_sample": repeats,
               "families": sorted(counts), "samples_by_family": counts,
               "sha256": digest(path),
               "median_vms_mb": statistics.median(r["targets"]["memory_mb"] for r in combined),
               "median_wall_seconds": statistics.median(r["targets"]["wall_seconds"] for r in combined),
               "platform": platform.platform(), "measurement": "real Linux Bubblewrap execution"}
    summary_path = root / "data" / f"{split}.summary.json"
    temporary_summary = summary_path.with_suffix(summary_path.suffix + ".tmp")
    temporary_summary.write_text(json.dumps(summary, indent=2))
    temporary_summary.replace(summary_path)
    return summary
