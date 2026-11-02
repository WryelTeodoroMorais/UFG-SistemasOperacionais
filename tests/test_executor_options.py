import pytest

import cli
from sandbox import run


@pytest.mark.parametrize("arguments", ["abc", [1], ["x\0y"], ["a"] * 129, ["a" * 32_001]])
def test_invalid_arguments_rejected_before_execution(arguments):
    with pytest.raises(ValueError):
        run("print('never')", script_args=arguments)


def test_existing_report_prevents_execution(tmp_path, monkeypatch, capsys):
    report = tmp_path / "report.json"
    report.write_text("original")

    def unexpected_run(*args, **kwargs):
        pytest.fail("Não deve executar quando o relatório já existe")

    monkeypatch.setattr(cli, "run", unexpected_run)
    assert cli.main(["run", "missing.py", "--output", str(tmp_path / "out"),
                     "--report", str(report)]) == 2
    assert report.read_text() == "original"
    assert "Erro:" in capsys.readouterr().err
