"""Ensaios funcionais de contenção; não certificam resistência a ataques."""
import hashlib

from policy import Budget, authorize
from sandbox import run


def verify() -> dict:
    cases = [
        ("legitimate", "from pathlib import Path\nx=Path('/input/data.txt').read_text()\nPath('/output/result.txt').write_text(x.upper())\nprint('ok')", Budget(), None),
        ("input_write", "open('/input/data.txt','w').write('changed')", Budget(), "Read-only file system"),
        ("host_files", "open('/home/sentinel-secret.txt').read()", Budget(), "No such file or directory"),
        ("network", "import socket\ns=socket.socket()\ns.settimeout(.2)\ns.connect(('1.1.1.1',443))", Budget(), "Network is unreachable"),
        ("output_denied", "open('/output/result.txt','w').write('x')", Budget(write_output=False), "Read-only file system"),
        ("input_denied", "open('/input/data.txt').read()", Budget(read_input=False), "No such file or directory"),
        ("memory", "x=bytearray(200*1024*1024)", Budget(memory_mb=32), "MemoryError"),
        ("wall_time", "while True: pass", Budget(wall_seconds=.2), "timeout"),
        ("file_size", "open('/output/big.bin','wb').write(b'x'*(2*1024**2))", Budget(output_mb=1), "File too large"),
    ]
    results = []
    for name, code, budget, expected_error in cases:
        measured = run(code, b"example", budget)
        if expected_error is None:
            passed = (measured["returncode"] == 0 and not measured["timed_out"]
                      and measured["stdout"].strip() == "ok"
                      and measured["outputs"].get("result.txt", {}).get("sha256")
                      == hashlib.sha256(b"EXAMPLE").hexdigest())
        elif expected_error == "timeout":
            passed = measured["timed_out"] and measured["returncode"] != 0
        else:
            passed = (measured["returncode"] != 0 and not measured["timed_out"]
                      and expected_error in measured["stderr"])
        results.append({"case": name, "passed": passed, "result": measured})
    try:
        authorize({"network": True}, Budget())
        policy_passed = False
    except ValueError:
        policy_passed = True
    return {"cases": results, "policy_rejects_network": policy_passed,
            "passed": all(case["passed"] for case in results) and policy_passed,
            "scope": "Contenção funcional em casos controlados; não certifica segurança contra escapes."}
