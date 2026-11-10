from pathlib import Path
import csv
import json

with open('/input/data.txt') as stream:
    rows = list(csv.reader(stream))
total = sum(int(row[1]) for row in rows)
Path('/output/relatorio.json').write_text(json.dumps({'linhas': len(rows), 'total': total}))
print('Relatório gerado')
