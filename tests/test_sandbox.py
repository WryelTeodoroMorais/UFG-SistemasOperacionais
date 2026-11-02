"""Integração explícita: SENTINELA_INTEGRATION=1 requer namespaces disponíveis."""
import os
from pathlib import Path
import pytest
from policy import Budget
from sandbox import run

pytestmark = pytest.mark.skipif(os.getenv("SENTINELA_INTEGRATION") != "1",
                                reason="ative SENTINELA_INTEGRATION=1 para execução real")


def test_input_readonly_and_output_export(tmp_path):
    result = run("from pathlib import Path\nPath('/output/x.txt').write_text(Path('/input/data.txt').read_text())",
                 b"hello", destination=tmp_path)
    assert result["returncode"] == 0
    assert (tmp_path / "x.txt").read_text() == "hello"
    result = run("open('/input/data.txt','w').write('x')", b"original")
    assert result["returncode"] != 0


def test_no_output_permission():
    assert run("open('/output/x','w')", budget=Budget(write_output=False))["returncode"] != 0


def test_symlinks_never_exported(tmp_path):
    result = run("import os\nos.symlink('/usr/bin/python3','/output/link')", destination=tmp_path)
    assert result["returncode"] == 0
    assert not result["outputs"] and not list(tmp_path.iterdir())


def test_wall_timeout():
    result = run("while True: pass", budget=Budget(wall_seconds=.15))
    assert result["timed_out"] and result["returncode"] != 0


def test_arguments_are_passed_literally(tmp_path):
    import json

    arguments = ["--name", "duas palavras", "$(touch /output/unsafe)", "", "ação"]
    result = run("import json, sys\nprint(json.dumps(sys.argv[1:]))",
                 script_args=arguments, destination=tmp_path)
    assert result["returncode"] == 0
    assert json.loads(result["stdout"]) == arguments
    assert not list(tmp_path.iterdir())


def test_cli_arguments_and_no_write(tmp_path, capsys):
    import json
    from cli import main

    script = Path(__file__).parents[1] / "examples/text_stats.py"
    source = tmp_path / "input.txt"
    source.write_text("hello world\n")
    output = tmp_path / "output"
    common = ["run", str(script), "--input", str(source), "--output", str(output),
              "--method", "fixed", "--no-write"]
    assert main(common) == 0
    result = json.loads(capsys.readouterr().out)
    assert json.loads(result["execution"]["stdout"])["words"] == 2
    assert not result["execution"]["budget"]["write_output"]
    assert not output.exists()

    report = tmp_path / "failure.json"
    assert main([*common, "--arg=--save", "--report", str(report)]) == 1
    result = json.loads(capsys.readouterr().out)
    assert json.loads(report.read_text()) == result
    assert "Read-only file system" in result["execution"]["stderr"]
    assert not output.exists()
