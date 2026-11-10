"""Rodadas sequenciais. Não altera escolhas depois de abrir o teste."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["initial", "development", "final"], required=True)
    args = parser.parse_args()
    from sentinela.data import collect
    from sentinela.sandbox import doctor
    from sentinela.learning import train
    from sentinela.evaluation import evaluate
    from sentinela.security import verify

    if args.phase == "initial":
        print(json.dumps(doctor(), indent=2))
        print(collect(ROOT, "train"))
    elif args.phase == "development":
        print(collect(ROOT, "validation"))
        print(train(ROOT))
        report = evaluate(ROOT, "validation")
        print(json.dumps(report["methods"], indent=2))
    else:
        # Lê configuração já congelada antes de criar o teste.
        from sentinela.learning import frozen
        _, config = frozen(ROOT)
        print("Modelo congelado:", config["model_sha256"])
        print(collect(ROOT, "test"))
        report = evaluate(ROOT, "test")
        print(json.dumps(report["methods"], indent=2))
        report = verify(ROOT)
        print("Ensaios de contenção:", report["passed"])
        if not report["passed"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
