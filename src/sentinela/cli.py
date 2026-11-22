import argparse
import json
from pathlib import Path
import sys

def main(argv=None):
    parser = argparse.ArgumentParser(description="Execução isolada com recomendação supervisionada")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    collect = sub.add_parser("collect")
    collect.add_argument("split", choices=["train", "validation", "test"])
    collect.add_argument("--repeats", type=int, default=3)
    collect.add_argument("--append", action="store_true",
                         help="Acrescenta tarefas ausentes; permitido somente para test")
    sub.add_parser("train")
    evaluate = sub.add_parser("evaluate")
    evaluate.add_argument("split", choices=["validation", "test"])
    sub.add_parser("security")
    run = sub.add_parser("run")
    run.add_argument("script", type=Path)
    run.add_argument("--input", type=Path)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--method", choices=["fixed", "heuristic", "supervised"], default="supervised")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        if args.command == "doctor":
            from .sandbox import doctor
            result = doctor()
        elif args.command == "collect":
            from .data import collect
            if args.repeats <= 0:
                raise ValueError("Repetições precisam ser positivas")
            result = collect(root, args.split, args.repeats, append=args.append)
        elif args.command == "train":
            from .learning import train
            result = train(root)
        elif args.command == "evaluate":
            from .evaluation import evaluate
            result = evaluate(root, args.split)
            result = {k: v for k, v in result.items() if k != "execution"}
        elif args.command == "security":
            from .security import verify
            result = verify(root)
        else:
            from .features import extract
            from .policy import Budget, authorize
            from .sandbox import run
            code = args.script.read_text()
            data = args.input.read_bytes() if args.input else b""
            if args.method == "supervised":
                from .learning import frozen, recommend
                package, config = frozen(root)
                rec = recommend(package, extract(code, len(data)), config["margin"], config["wall_margin"])
            elif args.method == "heuristic":
                from .evaluation import baseline
                rec = baseline({"features": extract(code, len(data)), "input_bytes": len(data)}, "heuristic")
            else:
                rec = {"memory_mb": 128, "wall_seconds": 2, "read_input": True, "write_output": True}
            ceiling = Budget(read_input=args.input is not None)
            result = run(code, data, authorize(rec, ceiling), args.output)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        if result.get("passed") is False or result.get("all_succeeded") is False or ("returncode" in result and result["returncode"] != 0):
            return 1
        return 0
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
