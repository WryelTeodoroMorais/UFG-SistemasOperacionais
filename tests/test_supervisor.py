import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

from sentinela import supervisor


def test_child_exits_between_wait_and_timeout_signal(monkeypatch, tmp_path, capsys):
    (tmp_path / "settings.json").write_text(json.dumps({"wall_seconds": 0.5}))
    monkeypatch.setattr(supervisor, "Path", lambda path: tmp_path / Path(path).name)
    monkeypatch.setattr(
        supervisor, "open", lambda path, mode: (tmp_path / Path(path).name).open(mode),
        raising=False,
    )

    # The child stays alive until the supervisor has made its first wait4 call.
    with subprocess.Popen(
        [sys.executable, "-c", "import sys; sys.stdin.buffer.read(1)"],
        stdin=subprocess.PIPE,
    ) as child:
        monkeypatch.setattr(
            supervisor, "subprocess", SimpleNamespace(Popen=lambda *args, **kwargs: child),
        )
        readings = iter((0.0, 1.0))

        def monotonic():
            elapsed = next(readings, 1.0)
            if elapsed and not child.stdin.closed:
                child.stdin.close()
                # Observe the exit without consuming the status or usage.
                os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOWAIT)
            return elapsed

        monkeypatch.setattr(
            supervisor, "time", SimpleNamespace(monotonic=monotonic, sleep=lambda _: None),
        )
        supervisor.main()

    result = json.loads(capsys.readouterr().out)
    assert result["timed_out"] is True
    assert result["returncode"] == 0
    assert result["peak_rss_mb"] > 0
