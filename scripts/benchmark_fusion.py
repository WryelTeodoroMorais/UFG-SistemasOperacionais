"""Rodada independente: referência forte, ganho real e promoção opcional de ML."""
import argparse
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path
import platform
import random
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from sentinela.strategies import ALL_STRATEGIES, describe, execute, heuristic, program
from sentinela.optimizer import candidate_decision, decide, load_optimizer, sha, train_optimizer

BASE = ROOT/'evolution/fusion'


def protocol():
    return {"version":1,"seed":337,"repeats":3,"passes":[1,6],"test_passes":[1,3,6],
            "columns":[2,8,16],"rows":{"train":[700,7000,45000],"validation":[2500,22000],"test":[11000,100000]},
            "memory_targets_mb":[24,64,128],"chunk_rows":2048,
            "promotion_min_relative_gain":.05,
            "promotion":"ML must beat always fused by >=5% total time with no extra RSS-target violations at every validation target; otherwise auto uses fused without loading trees",
            "split_unit":"physical file; all queries and strategies of that file stay together",
            "labels":"median of 3 real sandbox executions: total request duration and peak RSS",
            "scope":"Known additive numeric CSV queries, integer thresholds q*997; same output for all strategies",
            "sources_sha256":{f'{s}:{p}':hashlib.sha256(program(s,p).encode()).hexdigest() for s in ALL_STRATEGIES for p in (1,3,6)},
            "platform":platform.platform(),"prepared_at_utc":datetime.now(timezone.utc).isoformat()}


def make_input(split,n,columns):
    identity=f'{split}-{n}-{columns}'
    path=BASE/'inputs'/f'{identity}.csv'
    path.parent.mkdir(exist_ok=True)
    rng=random.Random(hashlib.sha256((identity+':337').encode()).hexdigest())
    counts=[0]*6
    totals=[0]*6
    boundaries=(-1,0,996,997,998,1993,1994,4984,4985,4986,100000,-100000)
    with path.open('x') as stream:
        for i in range(n):
            row=[rng.randrange(-8000,8001) for _ in range(columns)]
            if i<len(boundaries):
                row=[boundaries[i]]+[0]*(columns-1)
            stream.write(','.join(map(str,row))+'\n')
            total=sum(row)
            for q in range(6):
                if total>=q*997:
                    counts[q]+=1
                    totals[q]+=total
    oracles={}
    for passes in (1,3,6):
        payload={'rows':n,'queries':[{'threshold':q*997,'count':counts[q],'total':totals[q]} for q in range(passes)]}
        oracles[passes]=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return path,oracles


def collect(split):
    config=json.loads((BASE/'protocol.json').read_text())
    destination=BASE/f'{split}.jsonl'
    if destination.exists():
        raise FileExistsError('Coleta preservada')
    if split=='test' and not (BASE/'frozen.json').exists():
        raise ValueError('Congele a decisão antes de abrir o teste')
    rows=[]
    for n,columns in itertools.product(config['rows'][split],config['columns']):
        path,oracles=make_input(split,n,columns)
        for passes in config['test_passes'] if split=='test' else config['passes']:
            metadata=describe(path,passes)
            runs={s:[] for s in ALL_STRATEGIES}
            for repeat in range(config['repeats']):
                order=list(ALL_STRATEGIES)
                random.Random(f'{path.stem}:{passes}:{repeat}:337').shuffle(order)
                for strategy in order:
                    result=execute(path,strategy,passes)
                    correct=(result['returncode']==0 and not result['timed_out'] and
                             result['outputs'].get('relatorio.json',{}).get('sha256')==oracles[passes])
                    if not correct:
                        raise RuntimeError(f'{path.stem}/{passes}/{strategy}: {result}')
                    runs[strategy].append(result)
            for strategy,results in runs.items():
                rows.append({'dataset_id':path.stem,'split':split,'input_sha256':sha(path),
                             'description':metadata,'strategy':strategy,'runs':results,
                             'total_seconds':statistics.median(r['execution_total_seconds'] for r in results),
                             'rss_mb':statistics.median(r['peak_rss_mb'] for r in results),
                             'output_sha256':oracles[passes],
                             'observed_at_utc':datetime.now(timezone.utc).isoformat()})
            print(split,path.stem,'consultas',passes,flush=True)
    destination.write_text(''.join(json.dumps(r)+'\n' for r in rows))


def evaluate():
    if (BASE/'evaluation.json').exists():
        raise FileExistsError('Avaliação preservada')
    policy=json.loads((BASE/'frozen.json').read_text())
    started=time.perf_counter()
    optimizer=load_optimizer(ROOT)
    auto_setup=time.perf_counter()-started
    experimental=json.loads((BASE/'model.json').read_text())
    train=[json.loads(x) for x in (BASE/'train.jsonl').read_text().splitlines()]
    val=[json.loads(x) for x in (BASE/'validation.jsonl').read_text().splitlines()]
    test=[json.loads(x) for x in (BASE/'test.jsonl').read_text().splitlines()]
    assert not {r['dataset_id'] for r in test}&{r['dataset_id'] for r in train+val}
    groups={}
    for row in test:
        groups.setdefault((row['dataset_id'],row['description']['passes']),{})[row['strategy']]=row
    reports={}
    replay=[]
    for target in (24,64,128):
        entries={s:[] for s in (*ALL_STRATEGIES,'heuristic','learned','auto','oracle')}
        for (dataset_id,passes),candidates in groups.items():
            metadata=candidates['fused']['description']
            started=time.perf_counter()
            automatic=decide(optimizer,metadata,target)
            auto_cost=time.perf_counter()-started
            started=time.perf_counter()
            learned=candidate_decision(experimental,metadata,target)
            learned_cost=time.perf_counter()-started
            feasible=[s for s in ALL_STRATEGIES if candidates[s]['rss_mb']<=target]
            oracle=min(feasible,key=lambda s:candidates[s]['total_seconds']) if feasible else min(ALL_STRATEGIES,key=lambda s:candidates[s]['rss_mb'])
            choices={s:s for s in ALL_STRATEGIES}
            choices.update(heuristic=heuristic(metadata,target),learned=learned['selected'],auto=automatic['selected'],oracle=oracle)
            for method,selected in choices.items():
                row=candidates[selected]
                overhead=auto_cost if method=='auto' else learned_cost if method=='learned' else 0
                entries[method].append({'dataset_id':dataset_id,'passes':passes,'selected':selected,
                    'seconds':row['total_seconds']+overhead,'rss_mb':row['rss_mb'],
                    'target_met':row['rss_mb']<=target})
            if target==64:
                result=execute(BASE/'inputs'/f'{dataset_id}.csv',automatic['selected'],passes)
                correct=result['returncode']==0 and result['outputs'].get('relatorio.json',{}).get('sha256')==candidates['fused']['output_sha256']
                replay.append({'dataset_id':dataset_id,'passes':passes,'decision':automatic,'result':result,
                               'correct':correct,'target_met':result['peak_rss_mb']<=target})
        reports[str(target)]={}
        for method,records in entries.items():
            setup=auto_setup if method=='auto' else policy['setup_seconds'] if method=='learned' else 0
            reports[str(target)][method]={'jobs':len(records),'targets_met':sum(r['target_met'] for r in records),
                'total_seconds':sum(r['seconds'] for r in records)+setup,
                'mean_peak_rss_mb':statistics.mean(r['rss_mb'] for r in records),
                'max_peak_rss_mb':max(r['rss_mb'] for r in records),
                'choices':{s:sum(r['selected']==s for r in records) for s in ALL_STRATEGIES},'records':records}
    result={'comparison':reports,'policy':policy,'test_sha256':sha(BASE/'test.jsonl'),
            'auto_setup_seconds':auto_setup,'auto_loads_model_trees':optimizer['model'] is not None,
            'correct_reference_executions':len(test)*3,
            'replay_correct':sum(r['correct'] for r in replay),'replay_jobs':len(replay),
            'replay_targets_met':sum(r['target_met'] for r in replay),'replay':replay,
            'limits':['numeric CSV additive queries only','one machine','3 repetitions','warm filesystem cache',
                      'test sizes differ; same operator','RSS goal is not hard RSS enforcement',
                      'improvement credited to fusion, not to ML when promotion is rejected']}
    (BASE/'evaluation.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ('comparison','replay','policy')},indent=2))
    print(json.dumps({m:{k:v for k,v in r.items() if k!='records'} for m,r in reports['64'].items()},indent=2))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--phase',choices=['fit','final'],required=True)
    args=parser.parse_args()
    BASE.mkdir(parents=True,exist_ok=True)
    if args.phase=='fit':
        if (BASE/'protocol.json').exists():
            raise FileExistsError('Rodada iniciada: use outra pasta para novo estudo')
        (BASE/'protocol.json').write_text(json.dumps(protocol(),indent=2))
        collect('train')
        collect('validation')
        print(json.dumps(train_optimizer(BASE),indent=2))
    else:
        config=json.loads((BASE/'protocol.json').read_text())
        policy=json.loads((BASE/'frozen.json').read_text())
        for key,file in (('model_sha256','model.json'),('train_sha256','train.jsonl'),('validation_sha256','validation.jsonl'),('protocol_sha256','protocol.json')):
            if sha(BASE/file)!=policy[key]:
                raise ValueError('Artefato alterado antes do teste: '+file)
        for strategy in ALL_STRATEGIES:
            for passes in (1,3,6):
                if hashlib.sha256(program(strategy,passes).encode()).hexdigest()!=config['sources_sha256'][f'{strategy}:{passes}']:
                    raise ValueError('Código de execução alterado depois do protocolo')
        collect('test')
        evaluate()


if __name__=='__main__':
    main()
