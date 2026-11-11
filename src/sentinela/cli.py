import argparse
import json
from pathlib import Path
import sys

CSV_STRATEGIES = ("auto", "fused")
CSV_STRATEGY_HELP = (
    "auto: padrão, usa a política promovida; fused: uma passagem explícita"
)


def _add_csv_arguments(
    command: argparse.ArgumentParser, *, include_output: bool = False
) -> None:
    command.add_argument("inputs", type=Path, nargs="+")
    if include_output:
        command.add_argument("--output", type=Path, required=True)
    command.add_argument("--strategy", choices=CSV_STRATEGIES, default="auto",
                         help=CSV_STRATEGY_HELP)
    command.add_argument("--memory-target-mb", type=float, default=64)
    command.add_argument("--passes", type=int, default=1)
    command.add_argument("--chunk-rows", type=int, default=2048)
    command.add_argument("--header", action="store_true")
    command.add_argument("--thresholds",
                         help="Limiares inteiros crescentes separados por vírgula; substitui --passes")
    command.add_argument("--value-column", type=int,
                         help="Coluna numérica por índice a partir de zero; padrão: soma das colunas")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Sentinela ML: execução isolada com recomendação supervisionada")
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
    plan = sub.add_parser("plan-csv", help="Mostra a estratégia prevista sem iniciar o sandbox")
    _add_csv_arguments(plan)
    process = sub.add_parser(
        "process-csv",
        help="Processa CSV isolado com a política atual; mede RSS e tempo reais",
    )
    _add_csv_arguments(process, include_output=True)
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
        elif args.command == "plan-csv":
            from .strategies import plan_csv
            result = plan_csv(root, args.inputs, args.strategy, args.memory_target_mb,
                              args.passes, args.chunk_rows, args.header,
                              args.thresholds, args.value_column)
        elif args.command == "process-csv":
            from .strategies import process_csv
            result = process_csv(root, args.inputs, args.output, args.strategy,
                                 args.memory_target_mb, args.passes, args.chunk_rows, args.header,
                                 args.thresholds,args.value_column)
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
