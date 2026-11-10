import json
import os
from pathlib import Path

import pytest

from sentinela import cli, security


@pytest.mark.skipif(os.getenv("SENTINELA_INTEGRATION") != "1",
                    reason="ative SENTINELA_INTEGRATION=1 para execução real")
def test_functional_containment(tmp_path):
    report = security.verify(tmp_path)
    assert report["passed"], report
    assert len(report["cases"]) == 9
    saved = tmp_path / "reports" / "security.json"
    assert json.loads(saved.read_text()) == report


@pytest.mark.parametrize("passed, expected_status", [(True, 0), (False, 1)])
def test_security_cli_report(monkeypatch, tmp_path, capsys, passed, expected_status):
    report = {"cases": [], "passed": passed}
    roots = []

    def fake_verify(root):
        roots.append(Path(root))
        return report

    monkeypatch.setattr(security, "verify", fake_verify)
    assert cli.main(["--root", str(tmp_path), "security"]) == expected_status
    assert roots == [tmp_path.resolve()]
    assert json.loads(capsys.readouterr().out) == report
