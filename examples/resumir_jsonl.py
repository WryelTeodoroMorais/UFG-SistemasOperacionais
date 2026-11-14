import json
from pathlib import Path

counts = {}
records = 0
with open('/input/data.txt') as stream:
    for line in stream:
        if not line.strip():
            continue
        family = json.loads(line)['family']
        counts[family] = counts.get(family, 0) + 1
        records += 1

report = {'registros': records, 'tarefas_por_familia': dict(sorted(counts.items()))}
Path('/output/resumo.json').write_text(json.dumps(report, indent=2))
print(f"{records} tarefas em {len(counts)} famílias")
