"""Coleta medida dentro da sandbox, com linhagem de dados."""
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


def collect(root: Path, split: str, repeats=3):
    validate_split(split)
    path = root / "data" / f"{split}.jsonl"
    if path.exists():
        raise FileExistsError(f"Coleta preservada: {path}; use outro diretório para nova rodada")
    records = []
    for task in tasks(split):
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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records))
    counts = dict(sorted(Counter(r["family"] for r in records).items()))
    summary = {"split": split, "samples": len(records), "repeats_per_sample": repeats,
               "families": sorted(counts), "samples_by_family": counts,
               "sha256": digest(path),
               "median_vms_mb": statistics.median(r["targets"]["memory_mb"] for r in records),
               "median_wall_seconds": statistics.median(r["targets"]["wall_seconds"] for r in records),
               "platform": platform.platform(), "measurement": "real Linux Bubblewrap execution"}
    (root / "data" / f"{split}.summary.json").write_text(json.dumps(summary, indent=2))
    return summary
