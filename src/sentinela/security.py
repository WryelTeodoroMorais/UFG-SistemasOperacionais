"""Ensaios limitados de contenção. Não constituem certificação de segurança."""
import json
from pathlib import Path
import tempfile

from .policy import Budget, authorize
from .sandbox import run


def verify(root: Path):
    cases = [
        ("legitimate", "from pathlib import Path\nx=Path('/input/data.txt').read_text()\nPath('/output/result.txt').write_text(x.upper())\nprint('ok')", Budget(), True),
        ("input_write", "open('/input/data.txt','w').write('changed')", Budget(), False),
        ("host_files", "open('/home/sentinel-secret.txt').read()", Budget(), False),
        ("network", "import socket\ns=socket.socket()\ns.settimeout(.2)\ns.connect(('1.1.1.1',443))", Budget(), False),
        ("output_denied", "open('/output/result.txt','w').write('x')", Budget(write_output=False), False),
        ("input_denied", "open('/input/data.txt').read()", Budget(read_input=False), False),
        ("memory", "x=bytearray(200*1024*1024)", Budget(memory_mb=32), False),
        ("wall_time", "while True: pass", Budget(wall_seconds=.2), False),
        ("file_size", "open('/output/big.bin','wb').write(b'x'*(2*1024**2))", Budget(output_mb=1), False),
    ]
    results = []
    for name, code, budget, should_succeed in cases:
        if name == "host_files":
            # Usa um arquivo existente no host para testar o mount seletivo.
            with tempfile.NamedTemporaryFile(mode="w", prefix="sentinela-host-proof-") as proof:
                proof.write("host-only-marker")
                proof.flush()
                assert Path(proof.name).read_text() == "host-only-marker"
                measured = run(f"open({proof.name!r}).read()", b"example", budget)
                measured["host_fixture_existed"] = True
        else:
            measured = run(code, b"example", budget)
        succeeded = measured["returncode"] == 0 and not measured["timed_out"]
        results.append({"case": name, "passed": succeeded == should_succeed, "result": measured})
    try:
        authorize({"network": True}, Budget())
        policy_passed = False
    except ValueError:
        policy_passed = True
    report = {"cases": results, "policy_rejects_network": policy_passed,
              "passed": all(r["passed"] for r in results) and policy_passed,
              "scope": "isolamento e limites funcionais em casos controlados; não prova resistência a escapes"}
    (root / "reports").mkdir(exist_ok=True)
    (root / "reports/security.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    return report
