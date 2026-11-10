import json
import os
from pathlib import Path

import pytest

from sentinela.strategies import describe, execute, features, program


def test_metadata_uses_bounded_sample(tmp_path):
    path=tmp_path/'x.csv'
    path.write_text('1,2\n'*40+'not,numeric\n')
    result=describe(path,passes=3)
    assert result['columns']==2 and result['passes']==3
    assert result['input_bytes']==path.stat().st_size
    assert len(features(result,'memory'))==7


@pytest.mark.parametrize('passes,chunk',[(0,2),(9,2),(1,0),(1,8193)])
def test_invalid_execution_parameters(passes,chunk):
    with pytest.raises(ValueError):
        program('memory',passes,chunk)


@pytest.mark.skipif(os.getenv('SENTINELA_INTEGRATION')!='1',reason='requer namespaces')
@pytest.mark.parametrize('header',[False,True])
def test_algorithms_produce_identical_verified_results(tmp_path,header):
    path=tmp_path/'input.csv'
    path.write_text(('a,b\n' if header else '')+'1,2\n-3,10\n2000,3000\n')
    output=[]
    for strategy in ('memory','blocks'):
        destination=tmp_path/strategy
        result=execute(path,strategy,passes=3,chunk_rows=1,header=header,destination=destination)
        assert result['returncode']==0
        output.append((destination/'relatorio.json').read_bytes())
    assert output[0]==output[1]
    payload=json.loads(output[0])
    assert payload['rows']==3
    assert payload['queries'][0]['total']==5010
    assert payload['queries'][1]['count']==1


@pytest.mark.skipif(os.getenv('SENTINELA_INTEGRATION')!='1',reason='requer namespaces')
def test_large_input_uses_file_copy_without_reading_whole_file(tmp_path,monkeypatch):
    from sentinela.sandbox import run
    path=tmp_path/'large.csv'
    with path.open('wb') as out:
        for _ in range(9):
            out.write(b'x'*1024**2)
    original=Path.read_bytes
    def guarded_read(self):
        if self==path:
            raise AssertionError('Entrada inteira carregada no controlador')
        return original(self)
    monkeypatch.setattr(Path,'read_bytes',guarded_read)
    result=run("import os\nprint(os.stat('/input/data.txt').st_size)",input_path=path)
    assert result['returncode']==0 and int(result['stdout'])==9*1024**2
