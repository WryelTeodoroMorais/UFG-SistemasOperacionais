"""Implementações equivalentes para consultas sobre CSVs numéricos.

Esta extensão escolhe um algoritmo conhecido; não reescreve scripts arbitrários.
"""
import csv
import io
import math
from pathlib import Path
import time

from .policy import Budget
from .sandbox import run

STRATEGIES = ("memory", "blocks")
ALL_STRATEGIES = (*STRATEGIES, "fused")
FEATURE_NAMES = ("log_bytes", "sample_line_bytes", "columns", "log_passes",
                 "log_chunk_rows", "header", "memory_strategy")
EXECUTION_BUDGET = Budget(memory_mb=512, wall_seconds=20, cpu_seconds=15,
                          output_mb=4, read_input=True, write_output=True)


def validate(passes: int, chunk_rows: int):
    if type(passes) is not int or not 1 <= passes <= 8:
        raise ValueError("passes deve estar entre 1 e 8")
    if type(chunk_rows) is not int or not 1 <= chunk_rows <= 8192:
        raise ValueError("chunk_rows deve estar entre 1 e 8192")


def describe(path: Path, passes=1, chunk_rows=2048, header=False) -> dict:
    validate(passes, chunk_rows)
    path = Path(path)
    size = path.stat().st_size
    if not 0 < size <= 64 * 1024**2:
        raise ValueError("CSV deve ter entre 1 byte e 64 MiB")
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.reader(stream)
        if header:
            next(reader, None)
        widths, count = [], 0
        for row in reader:
            if not row or len(row) > 64:
                raise ValueError("CSV numérico deve ter de 1 a 64 colunas, sem linhas vazias")
            if widths and len(row) != count:
                raise ValueError("Número de colunas inconsistente na amostra")
            for value in row:
                int(value)
            count = len(row)
            widths.append(sum(len(x.encode()) for x in row) + len(row))
            if len(widths) >= 32:
                break
    if not widths:
        raise ValueError("CSV sem registros de dados")
    return {"input_bytes": size, "sample_line_bytes": sum(widths)/len(widths),
            "columns": count, "passes": passes, "chunk_rows": chunk_rows,
            "header": bool(header)}


def features(description: dict, strategy: str) -> list[float]:
    if strategy not in STRATEGIES:
        raise ValueError("Estratégia desconhecida")
    return [math.log1p(description["input_bytes"]), description["sample_line_bytes"],
            description["columns"], math.log1p(description["passes"]),
            math.log1p(description["chunk_rows"]), float(description["header"]),
            float(strategy == "memory")]


def program(strategy: str, passes=1, chunk_rows=2048, header=False) -> str:
    validate(passes, chunk_rows)
    if strategy not in ALL_STRATEGIES:
        raise ValueError("Estratégia desconhecida")
    common = f'''import csv, json
from pathlib import Path
from itertools import islice
PASSES = {passes}
CHUNK = {chunk_rows}
HEADER = {bool(header)!r}

def open_rows():
    stream = open('/input/data.txt', newline='', encoding='utf-8')
    reader = csv.reader(stream)
    if HEADER:
        next(reader, None)
    return stream, reader

def consume(rows, threshold):
    count = total = nrows = 0
    for row in rows:
        value = sum(row)
        nrows += 1
        if value >= threshold:
            count += 1
            total += value
    return nrows, count, total

results = []
'''
    if strategy == "memory":
        body = '''stream, reader = open_rows()
with stream:
    data = [tuple(map(int, row)) for row in reader]
for query in range(PASSES):
    threshold = query * 997
    nrows, count, total = consume(data, threshold)
    results.append(dict(threshold=threshold, count=count, total=total))
'''
    elif strategy == "blocks":
        body = '''for query in range(PASSES):
    threshold = query * 997
    nrows = count = total = 0
    stream, reader = open_rows()
    with stream:
        while True:
            batch = list(islice(reader, CHUNK))
            if not batch:
                break
            a, b, c = consume((tuple(map(int, row)) for row in batch), threshold)
            nrows += a
            count += b
            total += c
    results.append(dict(threshold=threshold, count=count, total=total))
'''
    else:
        # Contagens por intervalo e somas de sufixo resolvem consultas sem reler linhas.
        body = '''counts = [0] * PASSES
totals = [0] * PASSES
nrows = 0
stream, reader = open_rows()
with stream:
    for row in reader:
        nrows += 1
        value = sum(map(int, row))
        if value >= 0:
            bucket = min(PASSES - 1, value // 997)
            counts[bucket] += 1
            totals[bucket] += value
count = total = 0
for query in range(PASSES - 1, -1, -1):
    count += counts[query]
    total += totals[query]
    results.append(dict(threshold=query * 997, count=count, total=total))
results.reverse()
'''
    return common + body + '''payload = dict(rows=nrows, queries=results)
Path('/output/relatorio.json').write_text(json.dumps(payload, sort_keys=True, separators=(',', ':')))
print('csv-summary-ok')
'''


def execute(path: Path, strategy: str, passes=1, chunk_rows=2048, header=False,
            destination: Path | None = None, *, thresholds=None, value_column=None) -> dict:
    started = time.perf_counter()
    code = (aggregation_program(strategy,passes,chunk_rows,header,thresholds,value_column)
            if thresholds is not None or value_column is not None else program(strategy,passes,chunk_rows,header))
    result = run(code, budget=EXECUTION_BUDGET,
                 input_path=path, destination=destination)
    result["execution_total_seconds"] = time.perf_counter() - started
    result["strategy"] = strategy
    return result


def _prepare_csv_jobs(root: Path, paths: list[Path], strategy: str,
                      memory_target_mb: float, passes: int, chunk_rows: int,
                      header: bool, thresholds, value_column):
    if strategy not in ("auto", *ALL_STRATEGIES, "heuristic"):
        raise ValueError("Estratégia desconhecida")
    if not math.isfinite(memory_target_mb) or memory_target_mb <= 0:
        raise ValueError("Meta de RAM deve ser positiva e finita")
    if not paths:
        raise ValueError("Selecione ao menos um CSV")
    custom = thresholds is not None or value_column is not None
    if thresholds is not None:
        thresholds = normalize_thresholds(thresholds)
        passes = len(thresholds)
    if value_column is not None and (type(value_column) is not int or value_column < 0):
        raise ValueError("value_column deve ser índice inteiro não negativo, começando em zero")
    jobs = []
    setup_started = time.perf_counter()
    optimizer = None
    if strategy == "auto" and not custom:
        from .optimizer import load_optimizer
        optimizer = load_optimizer(root)
    setup_seconds = time.perf_counter() - setup_started
    for index, path in enumerate(paths):
        decision_started = time.perf_counter()
        description = describe(path, passes, chunk_rows, header)
        if value_column is not None and value_column >= description["columns"]:
            raise ValueError("Coluna fora do CSV selecionado")
        predictions = None
        if strategy == "auto" and custom:
            selected = "fused"
            predictions = {"selected":"fused","ml_used":False,"reason":"custom_aggregation_single_pass",
                           "note":"Consultas configuráveis não fazem parte do treino; regra algébrica de uma passagem."}
        elif optimizer is not None:
            from .optimizer import decide
            decision = decide(optimizer, description, memory_target_mb)
            selected = decision["selected"]
            predictions = decision
        elif strategy == "heuristic":
            selected = heuristic(description, memory_target_mb)
        else:
            selected = strategy
        decision_seconds = time.perf_counter() - decision_started
        jobs.append({"input": str(path), "strategy": selected,
                     "description": description, "decision_seconds": decision_seconds,
                     "prediction": predictions, "memory_target_mb": memory_target_mb,
                     "query_thresholds": list(thresholds if thresholds is not None else
                                               (index * 997 for index in range(passes))),
                     "value_column": value_column})
    return jobs, setup_seconds, passes, thresholds


def plan_csv(root: Path, paths: list[Path], strategy="auto", memory_target_mb=64.0,
             passes=1, chunk_rows=2048, header=False, thresholds=None,
             value_column=None) -> dict:
    """Descreve a decisão para cada CSV sem iniciar uma execução isolada."""
    started = time.perf_counter()
    jobs, setup_seconds, passes, thresholds = _prepare_csv_jobs(
        root, paths, strategy, memory_target_mb, passes, chunk_rows, header,
        thresholds, value_column)
    return {"mode": strategy, "executed": False,
            "model_setup_seconds": setup_seconds,
            "planning_seconds": time.perf_counter() - started,
            "header": bool(header), "chunk_rows": chunk_rows,
            "jobs": jobs,
            "note": "Plano baseado em metadados e amostra de até 32 linhas. Nenhum sandbox foi iniciado; previsões de RSS e tempo não são garantias."}


def process_csv(root: Path, paths: list[Path], destination: Path, strategy="auto",
                memory_target_mb=64.0, passes=1, chunk_rows=2048, header=False,
                thresholds=None, value_column=None) -> dict:
    started = time.perf_counter()
    if destination.exists():
        raise FileExistsError("Use uma pasta de saída nova")
    jobs, setup_seconds, passes, thresholds = _prepare_csv_jobs(
        root, paths, strategy, memory_target_mb, passes, chunk_rows, header,
        thresholds, value_column)
    results = []
    for job in jobs:
        output = destination / f"{len(results)+1:03d}-{Path(job['input']).stem}"
        result = execute(Path(job["input"]), job["strategy"], passes, chunk_rows,
                         header, output, thresholds=thresholds,
                         value_column=value_column)
        result.update({key: job[key] for key in
                       ("input", "decision_seconds", "prediction", "memory_target_mb")})
        result["memory_target_met"] = (result["peak_rss_mb"] is not None and
                                       result["peak_rss_mb"] <= job["memory_target_mb"])
        result["output_directory"] = str(output)
        results.append(result)
    return {"mode": strategy, "model_setup_seconds": setup_seconds,
            "end_to_end_seconds": time.perf_counter() - started,
            "all_succeeded": all(r["returncode"] == 0 and not r["timed_out"] for r in results),
            "all_memory_targets_met": all(r["memory_target_met"] for r in results),
            "jobs": results,
            "note": "RSS é medido de fato. A meta de RSS orienta a escolha; o limite rígido é 512 MiB de AS por processo."}


def normalize_thresholds(values):
    if isinstance(values,str):
        values = [int(v.strip()) for v in values.split(',')]
    values = tuple(values)
    if not 1 <= len(values) <= 8 or any(type(v) is not int for v in values):
        raise ValueError("Escolha de 1 a 8 limiares inteiros")
    if any(a >= b for a,b in zip(values,values[1:])):
        raise ValueError("Limiares devem estar em ordem crescente, sem repetições")
    return values


def aggregation_program(strategy,passes=1,chunk_rows=2048,header=False,thresholds=None,value_column=None):
    """Operador configurável. O código do benchmark histórico fica inalterado."""
    thresholds = normalize_thresholds(thresholds if thresholds is not None else [q*997 for q in range(passes)])
    passes = len(thresholds)
    validate(passes,chunk_rows)
    if strategy not in ALL_STRATEGIES:
        raise ValueError("Estratégia desconhecida")
    if value_column is not None and (type(value_column) is not int or value_column < 0):
        raise ValueError("Índice de coluna inválido")
    common = f'''import csv, json
from bisect import bisect_right
from itertools import islice
from pathlib import Path
THRESHOLDS = {list(thresholds)!r}
HEADER = {bool(header)!r}
COLUMN = {value_column!r}
CHUNK = {chunk_rows}

def open_rows():
    stream = open('/input/data.txt', newline='', encoding='utf-8')
    reader = csv.reader(stream)
    if HEADER:
        next(reader, None)
    return stream, reader

def score(row):
    return sum(row) if COLUMN is None else row[COLUMN]

def consume(rows,threshold):
    n = count = total = 0
    for row in rows:
        value = score(row)
        n += 1
        if value >= threshold:
            count += 1
            total += value
    return n,count,total

results = []
'''
    if strategy == 'memory':
        body = '''stream,reader = open_rows()
with stream:
    data = [tuple(map(int,row)) for row in reader]
for threshold in THRESHOLDS:
    nrows,count,total = consume(data,threshold)
    results.append(dict(threshold=threshold,count=count,total=total))
'''
    elif strategy == 'blocks':
        body = '''for threshold in THRESHOLDS:
    nrows = count = total = 0
    stream,reader = open_rows()
    with stream:
        while True:
            batch = list(islice(reader,CHUNK))
            if not batch:
                break
            n,c,t = consume((tuple(map(int,row)) for row in batch),threshold)
            nrows += n
            count += c
            total += t
    results.append(dict(threshold=threshold,count=count,total=total))
'''
    else:
        body = '''counts = [0] * len(THRESHOLDS)
totals = [0] * len(THRESHOLDS)
nrows = 0
stream,reader = open_rows()
with stream:
    for row in reader:
        nrows += 1
        value = score(tuple(map(int,row)))
        bucket = bisect_right(THRESHOLDS,value)-1
        if bucket >= 0:
            counts[bucket] += 1
            totals[bucket] += value
count = total = 0
for index in range(len(THRESHOLDS)-1,-1,-1):
    count += counts[index]
    total += totals[index]
    results.append(dict(threshold=THRESHOLDS[index],count=count,total=total))
results.reverse()
'''
    return common + body + '''Path('/output/relatorio.json').write_text(json.dumps(dict(rows=nrows,queries=results),sort_keys=True,separators=(',',':')))
print('csv-summary-ok')
'''


def heuristic(description: dict, target: float) -> str:
    # Regra fixa prévia: 12 MiB de base + 20 vezes o tamanho em disco.
    estimated_rss = 12 + 20 * description["input_bytes"] / 1024**2
    return "memory" if estimated_rss <= target else "blocks"
