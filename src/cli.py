import argparse
import json
from pathlib import Path
import sys
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("sentinela-ml")
except PackageNotFoundError:
    __version__ = "0.1.0"

from policy import Budget, authorize
from recommendation import recommend
from sandbox import doctor, run


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


def _recommendation_for(args, code: str, input_bytes: int, ceiling: Budget) -> dict:
    if args.method == "heuristic":
        return recommend(code, input_bytes, ceiling)
    suggestion = {"memory_mb": min(128, ceiling.memory_mb),
                  "wall_seconds": min(2.0, ceiling.wall_seconds),
                  "read_input": ceiling.read_input,
                  "write_output": ceiling.write_output}
    budget = authorize(suggestion, ceiling)
    return {"method": "fixed", "trained_model": False,
            "suggestion": suggestion, "authorized_budget": budget.to_dict(),
            "note": "Perfil fixo de referência; não foi aprendido a partir de dados."}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Sentinela ML: planejamento e execução isolada de scripts Python")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="Exibe o nome e a versão do pacote")
    sub.add_parser("doctor", help="Verifica Bubblewrap e executa uma prova inofensiva de isolamento")

    def add_limits(command):
        command.add_argument("--max-memory-mb", type=int, default=256)
        command.add_argument("--max-wall-seconds", type=float, default=5.0)
        command.add_argument("--cpu-seconds", type=int, default=3)
        command.add_argument("--output-mb", type=int, default=4)

    plan = sub.add_parser("plan", help="Analisa o script e sugere um orçamento heurístico")
    plan.add_argument("script", type=Path)
    plan.add_argument("--input", type=Path)
    plan.add_argument("--allow-write", action="store_true", help="Inclui escrita de saída no teto autorizado")
    add_limits(plan)

    execute = sub.add_parser("run", help="Executa um script dentro de Bubblewrap")
    execute.add_argument("script", type=Path)
    execute.add_argument("--input", type=Path)
    execute.add_argument("--output", type=Path, required=True)
    execute.add_argument("--method", choices=("fixed", "heuristic"), default="heuristic")
    add_limits(execute)

    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            result = {"name": "Sentinela ML", "version": __version__,
                      "capabilities": ["status", "doctor", "plan", "run"]}
        elif args.command == "doctor":
            result = doctor()
        elif args.command == "plan":
            code = _script(args.script)
            input_bytes = _input_size(args.input)
            ceiling = _ceiling(args, read_input=args.input is not None,
                               write_output=args.allow_write)
            result = {"script": str(args.script), **recommend(code, input_bytes, ceiling)}
        else:
            code = _script(args.script)
            input_bytes = _input_size(args.input)
            ceiling = _ceiling(args, read_input=args.input is not None, write_output=True)
            profile = _recommendation_for(args, code, input_bytes, ceiling)
            budget = Budget(**profile["authorized_budget"])
            measured = run(code, budget=budget, destination=args.output,
                           input_path=args.input)
            result = {"script": str(args.script), "method": profile["method"],
                      "profile": profile, "execution": measured}
        print(json.dumps(result, indent=2, ensure_ascii=False))
        if args.command == "run" and (result["execution"].get("timed_out")
                                      or result["execution"].get("returncode") != 0):
            return 1
        if result.get("passed") is False:
            return 1
        return 0
    except (ValueError, RuntimeError, OSError, SyntaxError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
