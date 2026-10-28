"""Supervisor de medição em ambiente isolado, usando apenas stdlib.

RLIMIT_AS é espaço de endereçamento por processo, não RSS/cgroup.
Esta implementação não promete limite agregado de RAM ou de processos.
"""
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time


def main():
    settings = json.loads(Path("/app/settings.json").read_text())

    def limits():
        for kind, value in (
            (resource.RLIMIT_AS, settings["memory_mb"] * 1024**2),
            (resource.RLIMIT_CPU, settings["cpu_seconds"]),
            (resource.RLIMIT_FSIZE, settings["output_mb"] * 1024**2),
            (resource.RLIMIT_NOFILE, 64), (resource.RLIMIT_CORE, 0),
        ):
            resource.setrlimit(kind, (value, value))

    started = time.monotonic()
    with open("/tmp/stdout.log", "wb") as out, open("/tmp/stderr.log", "wb") as err:
        child = subprocess.Popen(["/usr/bin/python3", "-I", "/app/task.py"],
                                 stdout=out, stderr=err, preexec_fn=limits)
        peak_vms_kb = 0
        timed_out = False
        while True:
            try:
                for line in Path(f"/proc/{child.pid}/status").read_text().splitlines():
                    if line.startswith("VmPeak:"):
                        peak_vms_kb = max(peak_vms_kb, int(line.split()[1]))
            except (OSError, ValueError):
                pass
            pid, status, usage = os.wait4(child.pid, os.WNOHANG)
            if pid:
                child.returncode = os.waitstatus_to_exitcode(status)
                break
            if time.monotonic() - started > settings["wall_seconds"]:
                timed_out = True
                child.kill()
            time.sleep(0.002)
    result = {
        "returncode": child.returncode, "timed_out": timed_out,
        "wall_seconds": time.monotonic() - started,
        "cpu_seconds": usage.ru_utime + usage.ru_stime,
        "peak_rss_mb": usage.ru_maxrss / 1024,
        "peak_vms_mb": peak_vms_kb / 1024,
        "stdout": Path("/tmp/stdout.log").read_bytes()[:4096].decode(errors="replace"),
        "stderr": Path("/tmp/stderr.log").read_bytes()[:4096].decode(errors="replace"),
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
