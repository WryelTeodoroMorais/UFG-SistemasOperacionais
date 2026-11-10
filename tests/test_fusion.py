import json
import os
from pathlib import Path
import random

import pytest

from sentinela.optimizer import decide, load_optimizer, train_optimizer
from sentinela.strategies import execute, normalize_thresholds, process_csv


def test_auto_does_not_require_ml_artifacts_when_no_model_was_promoted(tmp_path):
    optimizer=load_optimizer(tmp_path)
    result=decide(optimizer,{},64)
    assert result['selected']=='fused' and result['ml_used'] is False


def test_validation_rejects_ml_without_advantage_over_strong_baseline(tmp_path):
    base=tmp_path/'evolution/fusion'
    base.mkdir(parents=True)
    (base/'protocol.json').write_text('{}')
    for split in ('train','validation'):
        records=[]
        for index in range(8):
            meta={'input_bytes':(index+1)*1000,'sample_line_bytes':8,'columns':2,
                  'passes':6,'chunk_rows':2048,'header':False}
            for strategy,seconds,rss in (('memory',.1,60),('blocks',.3,14),('fused',.03,12)):
                records.append({'dataset_id':f'{split}-{index}','description':meta,'strategy':strategy,
                                'rss_mb':rss,'total_seconds':seconds})
        (base/f'{split}.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))
    policy=train_optimizer(base)
    assert policy['ml_enabled'] is False and policy['test_used'] is False
    # Sem benefício comprovado, as árvores sequer são necessárias no runtime.
    (base/'model.json').unlink()
    optimizer=load_optimizer(tmp_path)
    assert optimizer['model'] is None
    assert decide(optimizer,{},64)['selected']=='fused'
    with pytest.raises(FileExistsError):
        train_optimizer(base)


@pytest.mark.skipif(os.getenv('SENTINELA_INTEGRATION')!='1',reason='requer namespaces')
@pytest.mark.parametrize('passes',[1,6,8])
@pytest.mark.parametrize('header',[False,True])
def test_fusion_exact_at_threshold_boundaries_and_negative_values(tmp_path,passes,header):
    values=[-100000,-1,0,996,997,998,1993,1994,4984,4985,4986,6978,6979,100000]
    rng=random.Random(337)
    values += [rng.randrange(-20000,20001) for _ in range(70)]
    path=tmp_path/'input.csv'
    path.write_text(('a,b\n' if header else '')+''.join(f'{v},0\n' for v in values))
    expected={'rows':len(values),'queries':[
        {'threshold':q*997,'count':sum(v>=q*997 for v in values),
         'total':sum(v for v in values if v>=q*997)} for q in range(passes)]}
    hashes=[]
    for strategy in ('memory','blocks','fused'):
        destination=tmp_path/strategy
        result=execute(path,strategy,passes,chunk_rows=3,header=header,destination=destination)
        assert result['returncode']==0
        assert json.loads((destination/'relatorio.json').read_text())==expected
        hashes.append(result['outputs']['relatorio.json']['sha256'])
    assert len(set(hashes))==1


@pytest.mark.parametrize('values',[(2,1),(1,1),(),tuple(range(9)),(True,2)])
def test_rejects_ambiguous_custom_thresholds(values):
    with pytest.raises(ValueError):
        normalize_thresholds(values)


@pytest.mark.skipif(os.getenv('SENTINELA_INTEGRATION')!='1',reason='requer namespaces')
def test_custom_column_and_negative_thresholds_have_same_results(tmp_path):
    path=tmp_path/'input.csv'
    path.write_text('100,-10\n200,0\n300,20\n400,997\n')
    expected={'rows':4,'queries':[{'threshold':-10,'count':4,'total':1007},
                                {'threshold':0,'count':3,'total':1017},
                                {'threshold':997,'count':1,'total':997}]}
    for strategy in ('memory','blocks','fused'):
        output=tmp_path/strategy
        result=execute(path,strategy,destination=output,thresholds=[-10,0,997],value_column=1)
        assert result['returncode']==0
        assert json.loads((output/'relatorio.json').read_text())==expected
    result=process_csv(tmp_path,[path],tmp_path/'auto',thresholds='-10,0,997',value_column=1)
    assert result['all_succeeded']
    assert result['jobs'][0]['prediction']['ml_used'] is False
    assert json.loads((tmp_path/'auto/001-input/relatorio.json').read_text())==expected
