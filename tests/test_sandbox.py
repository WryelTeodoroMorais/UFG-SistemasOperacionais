"""Integração explícita: SENTINELA_INTEGRATION=1 requer namespaces disponíveis."""
import os
from pathlib import Path
import pytest
from sentinela.policy import Budget
from sentinela.sandbox import run

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
