import os

import pytest

import cli
from security import verify


@pytest.mark.skipif(os.getenv("SENTINELA_INTEGRATION") != "1",
                    reason="ative SENTINELA_INTEGRATION=1 para execução real")
def test_functional_containment():
    report = verify()
    assert report["passed"], report
    assert len(report["cases"]) == 9


@pytest.mark.parametrize("passed, expected_status", [(True, 0), (False, 1)])
def test_security_cli_report(monkeypatch, tmp_path, capsys, passed, expected_status):
    import json

    report = {"cases": [], "passed": passed}
    monkeypatch.setattr(cli, "verify", lambda: report)
    target = tmp_path / "security.json"
    assert cli.main(["security", "--output", str(target)]) == expected_status
    assert json.loads(target.read_text()) == report
    assert json.loads(capsys.readouterr().out) == report
    assert cli.main(["security", "--output", str(target)]) == 2
    assert json.loads(target.read_text()) == report
