"""Execução real com Bubblewrap. Falha fechada se namespaces indisponíveis."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile

from policy import Budget


class SandboxUnavailable(RuntimeError):
    pass


def run(code: str, input_data: bytes = b"", budget: Budget | None = None,
        destination: Path | None = None, *, input_path: Path | None = None) -> dict:
    budget = budget or Budget()
    bwrap = shutil.which("bwrap")
    if not bwrap:
        raise SandboxUnavailable("Instale bubblewrap. Não existe execução insegura de fallback.")
    if len(code.encode()) > 128_000 or len(input_data) > 8 * 1024**2:
        raise ValueError("Código máximo 128 kB; entrada máxima 8 MiB")
    if input_path is not None and input_data:
        raise ValueError("Use input_data ou input_path, não ambos")
    with tempfile.TemporaryDirectory(prefix="sentinela-") as temp:
        root = Path(temp)
        app, inputs, outputs = (root / p for p in ("app", "input", "output"))
        for p in (app, inputs, outputs):
            p.mkdir()
        (app / "task.py").write_text(code)
        (app / "supervisor.py").write_text(Path(__file__).with_name("supervisor.py").read_text())
        (app / "settings.json").write_text(json.dumps(budget.to_dict()))
        if input_path is None:
            (inputs / "data.txt").write_bytes(input_data)
        else:
            # Copia com memória limitada também no controlador. Evita read_bytes
            # do arquivo inteiro antes de iniciar a estratégia em blocos.
            with Path(input_path).open("rb") as source, (inputs / "data.txt").open("wb") as target:
                total = 0
                while chunk := source.read(1024**2):
                    total += len(chunk)
                    if total > 64 * 1024**2:
                        raise ValueError("Entrada por arquivo excede 64 MiB")
                    target.write(chunk)
        args = [bwrap, "--unshare-all", "--unshare-user", "--die-with-parent", "--new-session",
                "--disable-userns", "--cap-drop", "ALL", "--clearenv",
                "--setenv", "PATH", "/usr/bin", "--setenv", "HOME", "/tmp",
                "--ro-bind", "/usr", "/usr"]
        for p in ("/lib", "/lib64"):
            if Path(p).exists():
                args += ["--ro-bind", p, p]
        args += ["--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
                 "--ro-bind", str(app), "/app", "--dir", "/input", "--dir", "/output"]
        if budget.read_input:
            args += ["--ro-bind", str(inputs), "/input"]
        if budget.write_output:
            args += ["--bind", str(outputs), "/output"]
        else:
            args += ["--ro-bind", str(outputs), "/output"]
        args += ["--chdir", "/tmp", "/usr/bin/python3", "-I", "/app/supervisor.py"]
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   start_new_session=True)
        try:
            stdout, stderr = process.communicate(timeout=budget.wall_seconds + 3)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            return {"returncode": -9, "timed_out": True, "wall_seconds": budget.wall_seconds + 3,
                    "peak_rss_mb": None, "peak_vms_mb": None,
                    "stderr": "Timeout externo: ambiente encerrado", "stdout": "",
                    "outputs": {}, "budget": budget.to_dict()}
        except BaseException:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            raise
        if process.returncode:
            raise SandboxUnavailable(stderr.decode(errors="replace")[:2000])
        try:
            result = json.loads(stdout)
        except (ValueError, UnicodeError) as exc:
            raise SandboxUnavailable("Supervisor sem resposta válida") from exc
        result["outputs"] = {}
        for p in outputs.iterdir():
            # Nunca seguir symlinks produzidos por código não confiável.
            if p.is_symlink() or not p.is_file():
                continue
            if p.stat().st_size <= budget.output_mb * 1024**2:
                result["outputs"][p.name] = {"bytes": p.stat().st_size,
                                              "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                if destination:
                    destination.mkdir(parents=True, exist_ok=True)
                    target = destination / p.name
                    if target.exists() or target.is_symlink():
                        raise FileExistsError(target)
                    with target.open("xb") as stream:
                        stream.write(p.read_bytes())
        result["budget"] = budget.to_dict()
        return result


def doctor() -> dict:
    result = run("print('sandbox-ok')", budget=Budget(memory_mb=64))
    if result["returncode"] != 0 or result["stdout"].strip() != "sandbox-ok":
        raise SandboxUnavailable(str(result))
    return {"bubblewrap": shutil.which("bwrap"), "isolation": "verified", "probe": result}
