import argparse
import json
from pathlib import Path
import sys
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("sentinela-ml")
except PackageNotFoundError:
    __version__ = "0.1.0"

from artifacts import check_destination, write_json
from policy import Budget
from recommendation import METHODS, profile
from sandbox import doctor, run
from security import verify


def _script(path: Path) -> str:
    code = path.read_text(encoding="utf-8")
    if len(code.encode("utf-8")) > 128_000:
        raise ValueError("Código máximo: 128 kB")
    return code


def _input_size(path: Path | None) -> int:
    if path is None:
        return 0
    if not path.is_file():
        raise ValueError(f"Arquivo de entrada não encontrado: {path}")
    size = path.stat().st_size
    if size > 64 * 1024**2:
        raise ValueError("Entrada máxima: 64 MiB")
    return size


def _ceiling(args, *, read_input: bool, write_output: bool) -> Budget:
    return Budget(memory_mb=args.max_memory_mb, wall_seconds=args.max_wall_seconds,
                  cpu_seconds=args.cpu_seconds, output_mb=args.output_mb,
                  read_input=read_input, write_output=write_output)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Sentinela ML: planejamento e execução isolada de scripts Python")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="Exibe o nome e a versão do pacote")
    sub.add_parser("doctor", help="Verifica Bubblewrap e executa uma prova inofensiva de isolamento")
    security = sub.add_parser("security", help="Executa nove ensaios funcionais de contenção")
    security.add_argument("--output", type=Path, help="Salva o relatório JSON em um arquivo novo")
    collect = sub.add_parser("collect", help="Coleta 32 tarefas autorais em Bubblewrap para o ML inicial")
    collect.add_argument("--output", type=Path, required=True, help="Arquivo JSON novo para as medições")
    train = sub.add_parser("train", help="Treina uma árvore de recursos a partir de medições")
    train.add_argument("--data", type=Path, required=True)
    train.add_argument("--output", type=Path, required=True, help="Arquivo JSON novo para o modelo")
    evaluate = sub.add_parser("evaluate", help="Compara fixo, heurística e ML no teste reservado")
    evaluate.add_argument("--data", type=Path, required=True)
    evaluate.add_argument("--model", type=Path, required=True)
    evaluate.add_argument("--output", type=Path, required=True)

    def add_method(command):
        command.add_argument("--method", choices=METHODS, default="heuristic")
        command.add_argument("--model", type=Path, help="Modelo JSON obrigatório para --method ml")

    def add_limits(command):
        command.add_argument("--max-memory-mb", type=int, default=256)
        command.add_argument("--max-wall-seconds", type=float, default=5.0)
        command.add_argument("--cpu-seconds", type=int, default=3)
        command.add_argument("--output-mb", type=int, default=4)

    plan = sub.add_parser("plan", help="Sugere um orçamento fixo, heurístico ou aprendido")
    plan.add_argument("script", type=Path)
    plan.add_argument("--input", type=Path)
    plan.add_argument("--allow-write", action="store_true", help="Inclui escrita de saída no teto autorizado")
    add_limits(plan)
    add_method(plan)

    execute = sub.add_parser("run", help="Executa um script dentro de Bubblewrap")
    execute.add_argument("script", type=Path)
    execute.add_argument("--input", type=Path)
    execute.add_argument("--output", type=Path, required=True)
    execute.add_argument("--arg", action="append", default=[], help="Argumento do script; pode ser repetido (use --arg=--opcao para opções)")
    execute.add_argument("--no-write", action="store_true", help="Bloqueia escrita em /output, inclusive no perfil fixo")
    execute.add_argument("--report", type=Path, help="Salva o resultado JSON em um arquivo novo no host")
    add_method(execute)
    add_limits(execute)

    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            result = {"name": "Sentinela ML", "version": __version__,
                      "capabilities": ["status", "doctor", "plan", "run", "security", "collect", "train", "evaluate"],
                      "methods": list(METHODS)}
        elif args.command == "doctor":
            result = doctor()
        elif args.command == "collect":
            from ml_data import collect
            result = collect(args.output)
        elif args.command == "train":
            from learning import train
            result = train(args.data, args.output)
        elif args.command == "evaluate":
            from learning import evaluate
            result = evaluate(args.data, args.model, args.output)
        elif args.command == "security":
            if args.output:
                check_destination(args.output)
            result = verify()
            if args.output:
                write_json(args.output, result)
        else:
            executing = args.command == "run"
            if executing and args.report:
                check_destination(args.report)
            code = _script(args.script)
            input_bytes = _input_size(args.input)
            ceiling = _ceiling(args, read_input=args.input is not None,
                               write_output=not args.no_write if executing else args.allow_write)
            recommendation = profile(args.method, code, input_bytes, ceiling, args.model)
            if executing:
                measured = run(code, budget=Budget(**recommendation["authorized_budget"]),
                               destination=args.output, input_path=args.input, script_args=args.arg)
                result = {"script": str(args.script), "method": args.method, "script_args": args.arg,
                          "profile": recommendation, "execution": measured}
                if args.report:
                    write_json(args.report, result)
            else:
                result = {"script": str(args.script), **recommendation}
        print(json.dumps(result, indent=2, ensure_ascii=False))
        if args.command == "run" and (result["execution"].get("timed_out")
                                      or result["execution"].get("returncode") != 0):
            return 1
        if result.get("passed") is False:
            return 1
        return 0
    except (ValueError, RuntimeError, OSError, SyntaxError, ImportError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
