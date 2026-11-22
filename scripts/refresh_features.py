"""Recompute cached pre-execution features without recollecting measurements."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sentinela.data import digest
from sentinela.features import FEATURE_NAMES, extract
from sentinela.tasks import make_task


def main():
    for split in ("train", "validation", "test"):
        path = ROOT / "data" / f"{split}.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        for row in rows:
            index = int(row["id"].rsplit("-", 1)[1])
            task = make_task(row["family"], index)
            code_hash = hashlib.sha256(task["code"].encode()).hexdigest()
            input_hash = hashlib.sha256(task["input_data"]).hexdigest()
            if (task["seed"] != row["seed"] or code_hash != row["code_sha256"]
                    or input_hash != row["input_sha256"]
                    or len(task["input_data"]) != row["input_bytes"]):
                raise ValueError(f"Tarefa regenerada diverge do registro: {row['id']}")
            row["features"] = extract(task["code"], row["input_bytes"])
            row["feature_names"] = list(FEATURE_NAMES)

        temporary_data = path.with_suffix(path.suffix + ".tmp")
        temporary_data.write_text("\n".join(
            json.dumps(row, ensure_ascii=False) for row in rows
        ) + "\n")
        temporary_data.replace(path)

        summary_path = ROOT / "data" / f"{split}.summary.json"
        if summary_path.exists():
            summary = json.loads(summary_path.read_text())
        else:
            summary = {"split": split, "samples": len(rows)}
        summary["sha256"] = digest(path)
        summary["feature_schema"] = list(FEATURE_NAMES)
        temporary_summary = summary_path.with_suffix(summary_path.suffix + ".tmp")
        temporary_summary.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
        temporary_summary.replace(summary_path)
        print(f"{split}: {len(rows)} feature vectors refreshed; sha256={summary['sha256']}")


if __name__ == "__main__":
    main()
