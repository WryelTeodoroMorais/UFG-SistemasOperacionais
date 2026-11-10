"""Lotes completos por meio da função usada pela CLI, sem retreino."""
import json
from pathlib import Path
import random
import statistics
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from sentinela.strategies import process_csv

BASE=ROOT/'evolution/fusion'
destination=BASE/'demo'
destination.mkdir(exist_ok=False)
METHODS=('memory','blocks','heuristic','fused','auto')
paths=[BASE/'inputs'/f'test-100000-{c}.csv' for c in (8,16)]
expected={r['dataset_id']:r['output_sha256'] for r in map(json.loads,(BASE/'test.jsonl').read_text().splitlines()) if r['description']['passes']==6}
measurements=[]
for repeat in range(3):
    methods=list(METHODS)
    random.Random(337+repeat).shuffle(methods)
    for method in methods:
        result=process_csv(ROOT,paths,destination/f'{repeat}-{method}',method,64,6)
        assert result['all_succeeded']
        for job in result['jobs']:
            assert job['outputs']['relatorio.json']['sha256']==expected[Path(job['input']).stem]
        measurements.append({'method':method,'repeat':repeat,'result':result})
        print(method,repeat,round(result['end_to_end_seconds'],4),flush=True)
summary={}
for method in METHODS:
    runs=[r['result'] for r in measurements if r['method']==method]
    summary[method]={'median_end_to_end_seconds':statistics.median(r['end_to_end_seconds'] for r in runs),
                    'median_mean_peak_rss_mb':statistics.median(statistics.mean(j['peak_rss_mb'] for j in r['jobs']) for r in runs),
                    'max_peak_rss_mb':max(j['peak_rss_mb'] for r in runs for j in r['jobs']),
                    'targets_met':sum(j['memory_target_met'] for r in runs for j in r['jobs']),
                    'jobs':sum(len(r['jobs']) for r in runs),
                    'median_setup_seconds':statistics.median(r['model_setup_seconds'] for r in runs)}
(BASE/'demo.json').write_text(json.dumps({'summary':summary,'measurements':measurements,
    'scope':'2 CSVs, 100000 rows, 8/16 columns, 6 queries each, 3 repeats; demonstration reuses test inputs without retraining'},indent=2))
print(json.dumps(summary,indent=2))
