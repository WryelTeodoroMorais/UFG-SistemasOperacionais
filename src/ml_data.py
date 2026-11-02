"""Coleta pequena e real em Bubblewrap; nenhum rótulo de recurso é inventado."""
from datetime import datetime, timezone
from pathlib import Path
import platform

from artifacts import check_destination, write_json
from policy import Budget
from sandbox import doctor, run


def collect(output: Path) -> dict:
    check_destination(output)
    environment = doctor()
    tasks = []
    for variant, size in enumerate((1, 2, 3, 4, 6, 8, 10, 12)):
        programs = [
            ("allocate", f"x=bytearray({size}*1024*1024)\nprint(sum(x))", ""),
            ("compute", f"print(sum(i*i for i in range({size}*100000)))", ""),
            ("read", "from pathlib import Path\nx=Path('/input/data.txt').read_text()\nprint(len(x.upper()))", "word line\n" * (size * 512)),
            ("write", f"from pathlib import Path\nPath('/output/data.txt').write_text('x'*({size}*32768))\nprint('ok')", ""),
        ]
        for family, code, text in programs:
            measurements = []
            for _ in range(2):
                measured = run(code, text.encode(), Budget(read_input=bool(text)))
                if (measured["returncode"] != 0 or measured["timed_out"]
                        or not measured.get("peak_vms_mb") or measured["peak_vms_mb"] <= 0):
                    raise RuntimeError(f"Coleta incompleta: {family}/{variant}: {measured}")
                measurements.append(measured)
            if any((m["stdout"], m["outputs"]) != (measurements[0]["stdout"], measurements[0]["outputs"]) for m in measurements):
                raise RuntimeError("Saída instável entre repetições")
            tasks.append({"id": f"{family}-{variant}", "family": family,
                          "split": "test" if variant in (2, 6) else "train",
                          "code": code, "input_text": text,
                          "measurements": measurements})
    data = {"schema": "sentinela-measurements-v1", "created_at": datetime.now(timezone.utc).isoformat(),
            "platform": platform.platform(), "environment": environment,
            "scope": "32 tarefas autorais, 2 execuções cada; variantes reservadas das mesmas 4 famílias, sem generalização por família.",
            "tasks": tasks}
    write_json(output, data)
    return {"dataset": str(output), "tasks": len(tasks), "executions": 2 * len(tasks), "scope": data["scope"]}
