"""Geradores determinísticos das tarefas de treino."""
import hashlib
import json
import random
_CORE_TRAIN_FAMILIES = (
    'csv_sum', 'line_sort', 'hash', 'allocate', 'compute', 'write',
    'csv_transform', 'stream_copy',
)
SUFFIX = '\nimport time\ntime.sleep(0.04)\n'

def _make_core_train_task(family: str, index: int) -> dict:
    if family not in _CORE_TRAIN_FAMILIES:
        raise ValueError(f'Família desconhecida: {family}')
    seed = int(hashlib.sha256(f'{family}:{index}:2026'.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    rows = rng.choice((200, 1000, 4000, 12000, 30000, 60000))
    data = ''.join((f'{rng.randrange(1000)},{rng.randrange(10000)}\n' for _ in range(rows))).encode()
    read, write = (True, False)
    code = 'from pathlib import Path\n'
    if family == 'csv_sum':
        code += "import csv\nwith open('/input/data.txt') as f:\n    values = list(csv.reader(f))\nresult = sum(int(r[1]) for r in values)\nprint(result)\n"
    elif family == 'line_sort':
        code += "lines = Path('/input/data.txt').read_text().splitlines()\nlines.sort()\nprint(len(lines))\n"
    elif family == 'hash':
        code += "import hashlib\ndata = Path('/input/data.txt').read_bytes()\nprint(hashlib.sha256(data).hexdigest())\n"
    elif family == 'allocate':
        read = False
        size = rng.choice((1, 4, 8, 16, 32, 48, 64)) * 1024 ** 2
        code += f'buffer = bytearray({size})\nprint(len(buffer))\n'
    elif family == 'compute':
        read = False
        n = rng.choice((50000, 100000, 300000, 600000))
        code += f'result = sum(i*i for i in range({n}))\nprint(result)\n'
    elif family == 'write':
        read, write = (False, True)
        n = rng.choice((1000, 10000, 100000, 500000))
        code += f"result = 'x' * {n}\nPath('/output/result.txt').write_text(result)\nprint(len(result))\n"
    elif family == 'csv_transform':
        write = True
        code += "import csv\nwith open('/input/data.txt') as f:\n    values = list(csv.reader(f))\nresult = '\\n'.join(str(int(r[0])+int(r[1])) for r in values)\nPath('/output/result.txt').write_text(result)\nprint(len(values))\n"
    elif family == 'stream_copy':
        write = True
        code += "data = Path('/input/data.txt').read_bytes()\nPath('/output/result.txt').write_bytes(data)\nprint(len(data))\n"
    else:
        raise ValueError(f'Família desconhecida: {family}')
    code += SUFFIX
    return {'id': f'{family}-{index:03d}', 'family': family, 'seed': seed, 'code': code, 'input_data': data if read else b'', 'capabilities': [int(read), int(write)]}
_GENERAL_TRAIN_FAMILIES = ('csv_mean', 'csv_filter', 'csv_histogram', 'csv_sort', 'text_frequency', 'text_unique', 'text_search', 'json_select', 'jsonl_count', 'compute_primes', 'allocate_buffer', 'write_report')
_GENERAL_ROWS = (100, 300, 1000, 3000, 7000, 15000, 30000, 60000)
_GENERAL_TOKENS = ('alpha', 'beta', 'gamma', 'delta', 'epsilon', 'zeta', 'eta', 'theta', 'iota', 'kappa', 'needle', 'lambda')

def _general_csv_data(rng: random.Random, count: int) -> bytes:
    rows = []
    for index in range(count):
        rows.append(f'{index},{rng.randrange(-5000, 50001)}\n')
    return ''.join(rows).encode()

def _general_text_data(rng: random.Random, count: int) -> bytes:
    lines = []
    for _ in range(count):
        width = rng.randrange(3, 9)
        lines.append(' '.join((rng.choice(_GENERAL_TOKENS) for _ in range(width))))
    return ('\n'.join(lines) + '\n').encode()

def _general_json_data(rng: random.Random, count: int) -> bytes:
    rows = [{'id': index, 'group': f'g{rng.randrange(32)}', 'score': rng.randrange(10000), 'active': bool(rng.randrange(2))} for index in range(count)]
    return json.dumps(rows, separators=(',', ':')).encode()

def _general_jsonl_data(rng: random.Random, count: int) -> bytes:
    return ''.join((json.dumps({'group': f'g{rng.randrange(32)}', 'value': rng.randrange(10000), 'flag': bool(rng.randrange(2))}, separators=(',', ':')) + '\n' for _ in range(count))).encode()

def _make_general_train_task(family: str, index: int) -> dict:
    """Gera uma tarefa de treino e suas capacidades de leitura/escrita."""
    if family not in _GENERAL_TRAIN_FAMILIES:
        raise ValueError(f'Família desconhecida: {family}')
    if type(index) is not int or index < 0:
        raise ValueError('Índice de tarefa inválido')
    seed = int(hashlib.sha256(f'sentinela-expansion-v1:{family}:{index}'.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    count = _GENERAL_ROWS[index % len(_GENERAL_ROWS)]
    read = write = False
    data = b''
    if family in {'csv_mean', 'csv_filter', 'csv_histogram', 'csv_sort'}:
        read = True
        data = _general_csv_data(rng, count)
    if family in {'text_frequency', 'text_unique', 'text_search'}:
        read = True
        data = _general_text_data(rng, count)
    if family == 'json_select':
        read = write = True
        data = _general_json_data(rng, count)
    elif family == 'jsonl_count':
        read = True
        data = _general_jsonl_data(rng, count)
    code = ''
    if family == 'csv_mean':
        code = "import csv\nwith open('/input/data.txt', newline='') as stream:\n    values = [int(row[1]) for row in csv.reader(stream)]\nprint(sum(values) // len(values))\n"
    elif family == 'csv_filter':
        threshold = rng.randrange(1000, 25000)
        write = True
        code = f"import csv\nrows = []\nwith open('/input/data.txt', newline='') as stream:\n    rows = [row for row in csv.reader(stream) if int(row[1]) >= {threshold}]\nwith open('/output/result.csv', 'w', newline='') as stream:\n    csv.writer(stream).writerows(rows)\nprint(len(rows))\n"
    elif family == 'csv_histogram':
        width = rng.choice((250, 500, 1000, 2500))
        write = True
        code = f"import csv, json\nfrom collections import Counter\ncounts = Counter()\nwith open('/input/data.txt', newline='') as stream:\n    for row in csv.reader(stream):\n        counts[int(row[1]) // {width}] += 1\nopen('/output/result.json', 'w').write(json.dumps(dict(sorted(counts.items()))))\nprint(len(counts))\n"
    elif family == 'csv_sort':
        code = "import csv, json\nwith open('/input/data.txt', newline='') as stream:\n    values = sorted(int(row[0]) for row in csv.reader(stream))\nprint(json.dumps([values[0], values[len(values) // 2], values[-1]]))\n"
    elif family == 'text_frequency':
        top = rng.choice((5, 10, 20))
        code = f"from collections import Counter\nfrom pathlib import Path\ncounts = Counter(Path('/input/data.txt').read_text().split())\nprint(counts.most_common({top}))\n"
    elif family == 'text_unique':
        write = True
        code = "from pathlib import Path\nlines = Path('/input/data.txt').read_text().splitlines()\nunique = list(dict.fromkeys(lines))\nPath('/output/result.txt').write_text('\\n'.join(unique) + '\\n')\nprint(len(unique))\n"
    elif family == 'text_search':
        needle = rng.choice(_GENERAL_TOKENS)
        code = f"from pathlib import Path\ntext = Path('/input/data.txt').read_text()\nprint(text.count({needle!r}))\n"
    elif family == 'json_select':
        threshold = rng.randrange(1000, 9000)
        code = f"import json\nrows = json.load(open('/input/data.txt'))\nselected = [row for row in rows if row['active'] and row['score'] >= {threshold}]\njson.dump(selected, open('/output/result.json', 'w'), separators=(',', ':'))\nprint(len(selected))\n"
    elif family == 'jsonl_count':
        code = "import json\nfrom collections import Counter\ncounts = Counter()\nwith open('/input/data.txt') as stream:\n    for line in stream:\n        counts[json.loads(line)['group']] += 1\nprint(json.dumps(dict(sorted(counts.items()))))\n"
    elif family == 'compute_primes':
        limit = (1000, 3000, 7000, 12000, 20000, 30000, 45000, 60000)[index % 8]
        code = f'import math\ndef is_prime(value):\n    if value < 2:\n        return False\n    for divisor in range(2, math.isqrt(value) + 1):\n        if value % divisor == 0:\n            return False\n    return True\nprint(sum(is_prime(value) for value in range({limit})))\n'
    elif family == 'allocate_buffer':
        size_mb = (1, 2, 4, 8, 12, 16, 24, 32)[index % 8]
        code = f'size = {size_mb} * 1024 * 1024\nbuffer = bytearray(size)\nfor offset in range(0, size, 4096):\n    buffer[offset] = 1\nprint(len(buffer))\n'
    elif family == 'write_report':
        size_bytes = (1024, 4096, 16384, 65536, 131072, 262144, 524288, 1048576)[index % 8]
        write = True
        code = f"from pathlib import Path\npayload = b'resource-report\\n' * ({size_bytes} // len(b'resource-report\\n'))\nPath('/output/report.bin').write_bytes(payload)\nprint(len(payload))\n"
    code += '\nimport time\ntime.sleep(0.04)\n'
    return {'id': f'{family}-{index:03d}', 'family': family, 'seed': seed, 'code': code, 'input_data': data, 'capabilities': [int(read), int(write)]}
_LARGE_TRAIN_FAMILIES = ('csv_group_mean_v2', 'csv_topk_v2', 'csv_scale_write_v2', 'text_replace_v2', 'text_sort_unique_v2', 'json_filter_v2', 'jsonl_rewrite_v2', 'array_sort_v2', 'prime_count_v2', 'allocate_buffer_v2')
_LARGE_ROWS = (100, 300, 1000, 3000, 7000, 12000, 20000, 30000, 45000, 60000)
_LARGE_JSONL_ROWS = (100, 300, 1000, 3000, 7000, 12000, 16000, 20000, 24000, 30000)
_LARGE_TOKENS = ('amber', 'birch', 'cobalt', 'dawn', 'ember', 'fjord', 'grove', 'harbor', 'indigo', 'juniper', 'kernel', 'linen')

def _large_csv(rng, count, grouped=False):
    return ''.join((f'{(rng.randrange(max(10, count // 8)) if grouped else i)},{rng.randrange(-5000, 50001)}\n' for i in range(count))).encode()

def _large_text(rng, count):
    return ('\n'.join((' '.join((rng.choice(_LARGE_TOKENS) for _ in range(rng.randrange(3, 9)))) for _ in range(count))) + '\n').encode()

def _large_json(rng, count):
    rows = [{'id': i, 'group': f'g{rng.randrange(64)}', 'score': rng.randrange(100000), 'active': bool(rng.randrange(2))} for i in range(count)]
    return json.dumps(rows, separators=(',', ':')).encode()

def _large_jsonl(rng, count):
    return ''.join((json.dumps({'group': f'g{rng.randrange(64)}', 'value': rng.randrange(100000), 'flag': bool(rng.randrange(2))}, separators=(',', ':')) + '\n' for _ in range(count))).encode()

def _make_large_train_task(family: str, index: int) -> dict:
    if family not in _LARGE_TRAIN_FAMILIES:
        raise ValueError(f'Família desconhecida: {family}')
    if type(index) is not int or index < 0:
        raise ValueError('Índice de tarefa inválido')
    seed = int(hashlib.sha256(f'sentinela-expansion-1000-v1:{family}:{index}'.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    count = _LARGE_ROWS[index % len(_LARGE_ROWS)]
    read = write = False
    data = b''
    csv_families = {'csv_group_mean_v2', 'csv_topk_v2', 'csv_scale_write_v2'}
    text_families = {'text_replace_v2', 'text_sort_unique_v2'}
    if family in csv_families:
        read = True
        data = _large_csv(rng, count, grouped=family == 'csv_group_mean_v2')
    elif family in text_families:
        read = True
        data = _large_text(rng, count)
    elif family in {'json_filter_v2'}:
        read = True
        data = _large_json(rng, count)
    elif family in {'jsonl_rewrite_v2'}:
        read = True
        data = _large_jsonl(rng, _LARGE_JSONL_ROWS[index % len(_LARGE_JSONL_ROWS)])
    elif family == 'array_sort_v2':
        read = True
        data = ''.join((f'{rng.randrange(-1000000, 1000001)}\n' for _ in range(count))).encode()
    code = ''
    if family == 'csv_group_mean_v2':
        write = True
        code = "import csv, json\nfrom collections import defaultdict\ngroups = defaultdict(lambda: [0, 0])\nwith open('/input/data.txt', newline='') as source:\n    for key, value in csv.reader(source):\n        groups[key][0] += int(value)\n        groups[key][1] += 1\nmeans = {key: total / amount for key, (total, amount) in groups.items()}\njson.dump(means, open('/output/means.json', 'w'), sort_keys=True)\nprint(len(means))\n"
    elif family == 'csv_topk_v2':
        top = rng.choice((5, 10, 20, 50))
        code = f"import csv, json\nwith open('/input/data.txt', newline='') as source:\n    rows = list(csv.reader(source))\nrows.sort(key=lambda row: int(row[1]), reverse=True)\nprint(json.dumps(rows[:{top}]))\n"
    elif family == 'csv_scale_write_v2':
        factor = rng.choice((2, 3, 5, 10))
        write = True
        code = f"import csv\nwith open('/input/data.txt', newline='') as source, open('/output/scaled.csv', 'w', newline='') as target:\n    writer = csv.writer(target)\n    count = 0\n    for key, value in csv.reader(source):\n        writer.writerow((key, int(value) * {factor}))\n        count += 1\nprint(count)\n"
    elif family == 'text_replace_v2':
        needle = rng.choice(_LARGE_TOKENS)
        replacement = rng.choice(tuple((word for word in _LARGE_TOKENS if word != needle)))
        write = True
        code = f"from pathlib import Path\ntext = Path('/input/data.txt').read_text()\nupdated = text.replace({needle!r}, {replacement!r})\nPath('/output/replaced.txt').write_text(updated)\nprint(len(updated))\n"
    elif family == 'text_sort_unique_v2':
        write = True
        code = "from pathlib import Path\nlines = Path('/input/data.txt').read_text().splitlines()\nunique = sorted(set(lines))\nPath('/output/unique.txt').write_text('\\n'.join(unique) + '\\n')\nprint(len(unique))\n"
    elif family == 'json_filter_v2':
        threshold = rng.randrange(10000, 90000)
        write = True
        code = f"import json\nrows = json.load(open('/input/data.txt'))\nselected = [row for row in rows if row['active'] and row['score'] >= {threshold}]\njson.dump(selected, open('/output/filtered.json', 'w'), separators=(',', ':'))\nprint(len(selected))\n"
    elif family == 'jsonl_rewrite_v2':
        write = True
        code = "import json\nwith open('/input/data.txt') as source, open('/output/enriched.jsonl', 'w') as target:\n    count = 0\n    for line in source:\n        row = json.loads(line)\n        row['bucket'] = row['value'] // 10000\n        target.write(json.dumps(row, separators=(',', ':')) + '\\n')\n        count += 1\nprint(count)\n"
    elif family == 'array_sort_v2':
        code = "from pathlib import Path\nvalues = sorted(map(int, Path('/input/data.txt').read_text().splitlines()))\nprint(values[0], values[len(values) // 2], values[-1])\n"
    elif family == 'prime_count_v2':
        limit = count
        code = f'import math\ndef prime(value):\n    return value >= 2 and all(value % d for d in range(2, math.isqrt(value) + 1))\nprint(sum(prime(value) for value in range({limit})))\n'
    elif family == 'allocate_buffer_v2':
        size_mb = (1, 2, 4, 8, 12, 16, 24, 32, 48, 64)[index % 10]
        code = f'size = {size_mb} * 1024 * 1024\nbuffer = bytearray(size)\nfor offset in range(0, size, 4096):\n    buffer[offset] = 1\nprint(len(buffer))\n'
    else:
        raise ValueError(f'Implementação ausente para {family}')
    code += '\nimport time\ntime.sleep(0.04)\n'
    return {'id': f'{family}-{index:03d}', 'family': family, 'seed': seed, 'code': code, 'input_data': data, 'capabilities': [int(read), int(write)]}
_RESOURCE_TRAIN_FAMILIES = ('int_list_comp_v3', 'dict_records_v3', 'nested_lists_v3', 'csv_sort_v3', 'bytearray_chunks_v3')
_RESOURCE_COUNTS = (1000, 2500, 5000, 10000, 20000, 40000, 80000, 150000, 300000, 600000)
_RESOURCE_FILE_COUNTS = (1000, 2500, 5000, 10000, 15000, 20000, 30000, 40000, 50000, 60000)
_RESOURCE_LIST_COUNTS = (100000, 200000, 300000, 400000, 500000, 650000, 800000, 1000000, 1200000, 1400000)
_RESOURCE_WORDS = ('amber', 'birch', 'cobalt', 'dawn', 'ember', 'fjord', 'grove', 'harbor', 'indigo', 'juniper', 'kernel', 'linen')

def _resource_csv(rng, count):
    return ''.join((f'{rng.randrange(10000)},{rng.randrange(-5000, 50001)}\n' for _ in range(count))).encode()

def _resource_json_rows(rng, count):
    rows = [{'id': i, 'group': f'g{rng.randrange(96)}', 'value': rng.randrange(-100000, 100001), 'active': bool(rng.randrange(2))} for i in range(count)]
    return json.dumps(rows, separators=(',', ':')).encode()

def _resource_text(rng, count):
    return ('\n'.join((' '.join((rng.choice(_RESOURCE_WORDS) for _ in range(6))) for _ in range(count))) + '\n').encode()

def _make_resource_train_task(family: str, index: int) -> dict:
    if family not in _RESOURCE_TRAIN_FAMILIES:
        raise ValueError(f'Família desconhecida: {family}')
    if type(index) is not int or not 0 <= index < 100:
        raise ValueError('Índice de tarefa deve ficar entre 0 e 99')
    seed = int(hashlib.sha256(f'sentinela-refinement-v3:{family}:{index}'.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    count = _RESOURCE_COUNTS[index % len(_RESOURCE_COUNTS)]
    data = b''
    read = write = False
    if family == 'int_list_comp_v3':
        size = _RESOURCE_LIST_COUNTS[index % len(_RESOURCE_LIST_COUNTS)]
        code = f'values = [(i * 19) % 65521 for i in range({size})]\nprint(len(values), sum(values))\n'
    elif family == 'dict_records_v3':
        data = _resource_json_rows(rng, _RESOURCE_FILE_COUNTS[index % len(_RESOURCE_FILE_COUNTS)])
        read = True
        code = "import json\nrows = json.load(open('/input/data.txt'))\nindex = {row['id']: (row['group'], row['value']) for row in rows}\nprint(len(index), sum(value for _, value in index.values()))\n"
    elif family == 'nested_lists_v3':
        size = _RESOURCE_COUNTS[index % len(_RESOURCE_COUNTS)]
        data = ''.join((f'{rng.randrange(-1000, 1001)}\n' for _ in range(size))).encode()
        read = True
        width = (8, 16, 32, 64)[index % 4]
        code = f"from pathlib import Path\nvalues = [int(item) for item in Path('/input/data.txt').read_text().splitlines()]\nrows = [values[pos:pos + {width}] for pos in range(0, len(values), {width})]\nprint(len(rows), sum(map(sum, rows)))\n"
    elif family == 'csv_sort_v3':
        data = _resource_csv(rng, _RESOURCE_FILE_COUNTS[index % len(_RESOURCE_FILE_COUNTS)])
        read = True
        code = "import csv\nwith open('/input/data.txt', newline='') as source:\n    values = [int(row[1]) for row in csv.reader(source)]\nvalues.sort()\nprint(len(values), values[len(values) // 2])\n"
    elif family == 'bytearray_chunks_v3':
        total_mb = (2, 4, 8, 12, 16, 24, 32, 40, 48, 64)[index % 10]
        chunk_mb = (1, 2, 4, 8)[index % 4]
        parts = total_mb // chunk_mb
        code = f'chunk = {chunk_mb} * 1024 * 1024\nblocks = [bytearray(chunk) for _ in range({parts})]\nprint(sum(map(len, blocks)))\n'
    else:
        raise ValueError(f'Implementação ausente para {family}')
    code += '\nimport time\ntime.sleep(0.04)\n'
    return {'id': f'{family}-{index:03d}', 'family': family, 'seed': seed, 'code': code, 'input_data': data, 'capabilities': [int(read), int(write)]}

_GENERAL_WORKLOAD_FAMILIES = (
    "word_count", "normalize",
    "csv_median", "csv_group_extrema", "json_rank", "jsonl_status_summary",
    "text_run_length", "text_wrap", "subarray_sum", "interval_merge",
    "graph_degree", "coordinate_grid", "json_tree_depth",
    "base_convert_report", "matrix_rotate",
)
_LOW_VOLUME_GENERAL_WORKLOADS = {"word_count", "normalize"}
_GENERAL_WORKLOAD_ROWS = (200, 1_000, 4_000, 12_000, 30_000, 60_000)
_GENERAL_WORKLOAD_WORDS = ("amber", "birch", "cobalt", "dawn", "ember", "fjord", "grove", "harbor")
_GENERAL_WORKLOAD_SUFFIX = "\nimport time\ntime.sleep(0.04)\n"
_GENERAL_WORKLOAD_SAMPLE_COUNTS = {
    **{family: 12 for family in _LOW_VOLUME_GENERAL_WORKLOADS},
    **{family: 40 for family in _GENERAL_WORKLOAD_FAMILIES if family not in _LOW_VOLUME_GENERAL_WORKLOADS},
}


def _general_workload_csv_data(rng: random.Random, count: int, *, groups: bool = False) -> bytes:
    rows = []
    for index in range(count):
        key = rng.randrange(min(512, max(8, count // 10))) if groups else index
        rows.append(f"{key},{rng.randrange(-100_000, 100_001)}\n")
    return "".join(rows).encode()


def _general_workload_json_rows(rng: random.Random, count: int) -> bytes:
    rows = [{"id": index, "score": rng.randrange(-10_000, 100_001),
             "group": f"g{rng.randrange(128)}"} for index in range(count)]
    return json.dumps(rows, separators=(",", ":")).encode()


def _general_workload_jsonl_status_rows(rng: random.Random, count: int) -> bytes:
    statuses = ("queued", "ready", "running", "done", "failed")
    return "".join(
        json.dumps({"status": rng.choice(statuses), "amount": rng.randrange(10_000)},
                   separators=(",", ":")) + "\n"
        for _ in range(count)
    ).encode()


def _general_workload_text_rows(rng: random.Random, count: int, *, repeated: bool = False) -> bytes:
    lines = []
    for _ in range(count):
        if repeated:
            token = rng.choice(_GENERAL_WORKLOAD_WORDS)
            width = rng.randrange(1, 5)
            words = [token] * width + [rng.choice(_GENERAL_WORKLOAD_WORDS) for _ in range(rng.randrange(1, 5))]
        else:
            words = [rng.choice(_GENERAL_WORKLOAD_WORDS) for _ in range(rng.randrange(3, 10))]
        lines.append(" ".join(words))
    return ("\n".join(lines) + "\n").encode()


def _general_workload_json_tree(rng: random.Random, depth: int) -> dict:
    node = {"value": rng.randrange(100_000), "children": []}
    if depth > 0:
        node["children"] = [_general_workload_json_tree(rng, depth - 1), _general_workload_json_tree(rng, depth - 1)]
    return node


def _make_count_normalize_task(family: str, index: int) -> dict:
    seed = int(hashlib.sha256(f"{family}:{index}:2026".encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    rows = rng.choice((200, 1_000, 4_000, 12_000, 30_000, 60_000))
    data = "".join(f"{rng.randrange(1000)},{rng.randrange(10000)}\n" for _ in range(rows)).encode()
    read, write = True, False
    code = "from pathlib import Path\n"
    if family == "word_count":
        code += "from collections import Counter\ntext = Path('/input/data.txt').read_text()\ncounts = Counter(text.replace(',', ' ').split())\nprint(sum(counts.values()))\n"
    elif family == "normalize":
        write = True
        code += "lines = Path('/input/data.txt').read_text().splitlines()\nresult = '\\n'.join(';'.join(str(int(x)) for x in line.split(',')) for line in lines)\nPath('/output/result.txt').write_text(result)\nprint(len(lines))\n"
    else:
        raise ValueError(f"Família original desconhecida: {family}")
    code += _GENERAL_WORKLOAD_SUFFIX
    return {"id": f"{family}-{index:03d}", "family": family, "seed": seed,
            "code": code, "input_data": data, "capabilities": [int(read), int(write)]}


def _make_general_workload_task(family: str, index: int) -> dict:
    seed = int(hashlib.sha256(
        f"sentinela-test-expansion-v1:{family}:{index}".encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    count = _GENERAL_WORKLOAD_ROWS[index % len(_GENERAL_WORKLOAD_ROWS)]
    data = b""
    read = write = False

    if family == "csv_median":
        data = _general_workload_csv_data(rng, count)
        read = True
        code = "from pathlib import Path\nvalues = [int(line.split(',')[1]) for line in Path('/input/data.txt').read_text().splitlines()]\nvalues.sort()\nmid = len(values) // 2\nmedian = values[mid] if len(values) % 2 else (values[mid - 1] + values[mid]) // 2\nprint(median)\n"
    elif family == "csv_group_extrema":
        data = _general_workload_csv_data(rng, count, groups=True)
        read = write = True
        code = "from collections import defaultdict\nfrom pathlib import Path\ngroups = defaultdict(list)\nfor line in Path('/input/data.txt').read_text().splitlines():\n    key, value = line.split(',')\n    groups[key].append(int(value))\nresult = '\\n'.join(f'{key},{min(values)},{max(values)}' for key, values in sorted(groups.items()))\nPath('/output/extrema.csv').write_text(result + '\\n')\nprint(len(groups), sum(len(values) for values in groups.values()))\n"
    elif family == "json_rank":
        data = _general_workload_json_rows(rng, count)
        read = True
        top = (5, 10, 20, 50)[index % 4]
        code = f"import json\nfrom pathlib import Path\nrows = json.loads(Path('/input/data.txt').read_text())\nrows.sort(key=lambda row: (row['score'], row['id']))\nselected = rows[-{top}:]\nprint(len(selected), sum(row['score'] for row in selected))\n"
    elif family == "jsonl_status_summary":
        data = _general_workload_jsonl_status_rows(rng, count)
        read = True
        code = "import json\nfrom pathlib import Path\nsummary = {}\nfor line in Path('/input/data.txt').read_text().splitlines():\n    row = json.loads(line)\n    totals = summary.setdefault(row['status'], [0, 0])\n    totals[0] += 1\n    totals[1] += row['amount']\nprint(json.dumps(summary, sort_keys=True))\n"
    elif family == "text_run_length":
        data = _general_workload_text_rows(rng, count, repeated=True)
        read = True
        code = "from pathlib import Path\nlongest = current = 0\nprevious = None\nfor word in Path('/input/data.txt').read_text().split():\n    current = current + 1 if word == previous else 1\n    longest = max(longest, current)\n    previous = word\nprint(longest)\n"
    elif family == "text_wrap":
        data = _general_workload_text_rows(rng, count)
        read = write = True
        width = rng.choice((40, 60, 80, 100))
        code = f"from pathlib import Path\nwords = Path('/input/data.txt').read_text().split()\nlines = []\nline = ''\nfor word in words:\n    if line and len(line) + len(word) + 1 > {width}:\n        lines.append(line)\n        line = word\n    else:\n        line = word if not line else line + ' ' + word\nif line:\n    lines.append(line)\nPath('/output/wrapped.txt').write_text('\\n'.join(lines) + '\\n')\nprint(len(lines))\n"
    elif family == "subarray_sum":
        size = (20_000, 50_000, 100_000, 200_000, 300_000, 400_000)[index % 6]
        target = rng.randrange(-25, 26)
        code = f"size = {size}\ntarget = {target}\nvalues = [((i * 17 + 11) % 101) - 50 for i in range(size)]\nseen = {{0: 1}}\nprefix = matches = 0\nfor value in values:\n    prefix += value\n    matches += seen.get(prefix - target, 0)\n    seen[prefix] = seen.get(prefix, 0) + 1\nprint(matches)\n"
    elif family == "interval_merge":
        size = (1_000, 5_000, 10_000, 20_000, 50_000, 80_000)[index % 6]
        code = f"intervals = [(i * 3, i * 3 + 4 + (i % 5)) for i in range({size})]\nintervals.sort()\nmerged = []\nfor start, end in intervals:\n    if not merged or start > merged[-1][1]:\n        merged.append([start, end])\n    else:\n        merged[-1][1] = max(merged[-1][1], end)\nprint(len(merged), sum(end - start for start, end in merged))\n"
    elif family == "graph_degree":
        node_count = min(10_000, max(100, count // 4))
        data = "".join(f"{rng.randrange(node_count)},{rng.randrange(node_count)}\n" for _ in range(count)).encode()
        read = True
        code = "from pathlib import Path\ndegree = {}\nfor line in Path('/input/data.txt').read_text().splitlines():\n    left, right = line.split(',')\n    degree[left] = degree.get(left, 0) + 1\n    degree[right] = degree.get(right, 0) + 1\nprint(len(degree), max(degree.values(), default=0), sum(degree.values()))\n"
    elif family == "coordinate_grid":
        data = "".join(f"{rng.randrange(1_000_000)},{rng.randrange(1_000_000)}\n" for _ in range(count)).encode()
        read = True
        width = rng.choice((10, 25, 50, 100))
        code = f"from pathlib import Path\ncells = {{}}\nfor line in Path('/input/data.txt').read_text().splitlines():\n    x, y = map(int, line.split(','))\n    cell = (x // {width}, y // {width})\n    cells[cell] = cells.get(cell, 0) + 1\nprint(len(cells), max(cells.values(), default=0))\n"
    elif family == "json_tree_depth":
        depth = 2 + index % 9
        data = json.dumps(_general_workload_json_tree(rng, depth), separators=(",", ":")).encode()
        read = True
        code = "import json\nfrom pathlib import Path\nroot = json.loads(Path('/input/data.txt').read_text())\nstack = [(root, 1)]\ncount = maximum = 0\nwhile stack:\n    node, depth = stack.pop()\n    count += 1\n    maximum = max(maximum, depth)\n    stack.extend((child, depth + 1) for child in node['children'])\nprint(count, maximum)\n"
    elif family == "base_convert_report":
        values = [rng.randrange(-10**9, 10**9) for _ in range(count)]
        data = ("\n".join(map(str, values)) + "\n").encode()
        read = write = True
        code = "from pathlib import Path\nvalues = Path('/input/data.txt').read_text().splitlines()\nconverted = [f'{int(value)}:{int(value):x}' for value in values]\nPath('/output/base16.txt').write_text('\\n'.join(converted) + '\\n')\nprint(len(converted))\n"
    elif family == "matrix_rotate":
        side = (20, 40, 60, 80, 120, 160, 220, 280)[index % 8]
        code = f"side = {side}\nmatrix = [[(row * 17 + column * 31) % 997 for column in range(side)] for row in range(side)]\nrotated = [list(row) for row in zip(*matrix[::-1])]\nprint(len(rotated), sum(map(sum, rotated)))\n"
    else:
        raise ValueError(f"Implementação ausente para {family}")

    code += _GENERAL_WORKLOAD_SUFFIX
    return {"id": f"{family}-{index:03d}", "family": family, "seed": seed,
            "code": code, "input_data": data, "capabilities": [int(read), int(write)]}


def _make_general_workload_family(family: str, index: int) -> dict:
    if family not in _GENERAL_WORKLOAD_FAMILIES:
        raise ValueError(f"Família desconhecida: {family}")
    if type(index) is not int or not 0 <= index < _GENERAL_WORKLOAD_SAMPLE_COUNTS[family]:
        raise ValueError(f"Índice inválido para a família {family}: {index}")
    if family in _LOW_VOLUME_GENERAL_WORKLOADS:
        return _make_count_normalize_task(family, index)
    return _make_general_workload_task(family, index)

_DIVERSE_WORKLOAD_FAMILIES = (
    "csv_variance_stream", "csv_frequency_report", "csv_ranked_rows",
    "json_group_report", "jsonl_score_filter", "text_line_stats",
    "text_replace_report", "text_unique_sorted", "graph_components",
    "point_nearest", "activity_schedule", "matrix_product", "prime_sieve",
    "fibonacci_tail", "page_buffer", "nested_json_scan",
    "csv_rolling_mean",
)
_DIVERSE_WORKLOAD_SAMPLE_COUNTS = {family: 40 for family in _DIVERSE_WORKLOAD_FAMILIES}
_DIVERSE_WORKLOAD_ROWS = (200, 1_000, 4_000, 12_000, 30_000, 60_000, 90_000, 120_000)
_DIVERSE_WORKLOAD_TOKENS = ("amber", "birch", "cobalt", "dawn", "ember", "fjord", "grove", "harbor",
           "indigo", "juniper", "kernel", "linen", "maple", "nectar", "onyx", "prairie")
_DIVERSE_WORKLOAD_STATUSES = ("queued", "ready", "running", "done", "failed")
_DIVERSE_WORKLOAD_SUFFIX = "\nimport time\ntime.sleep(0.04)\n"


def _diverse_workload_csv(rng: random.Random, count: int, *, grouped: bool = False) -> bytes:
    return "".join(
        f"{rng.randrange(64) if grouped else index},{rng.randrange(-100_000, 100_001)}\n"
        for index in range(count)
    ).encode()


def _diverse_workload_text(rng: random.Random, count: int, *, repeated: bool = False) -> bytes:
    lines = []
    for _ in range(count):
        if repeated:
            token = rng.choice(_DIVERSE_WORKLOAD_TOKENS)
            lines.append(" ".join([token] * rng.randrange(2, 6) + [rng.choice(_DIVERSE_WORKLOAD_TOKENS)]))
        else:
            lines.append(" ".join(rng.choice(_DIVERSE_WORKLOAD_TOKENS) for _ in range(rng.randrange(4, 10))))
    return ("\n".join(lines) + "\n").encode()


def _diverse_workload_json_rows(rng: random.Random, count: int) -> bytes:
    rows = [{"group": f"g{rng.randrange(64)}", "score": rng.randrange(100_000),
             "active": bool(rng.randrange(2))} for _ in range(count)]
    return json.dumps(rows, separators=(",", ":")).encode()


def _diverse_workload_jsonl_rows(rng: random.Random, count: int) -> bytes:
    return "".join(json.dumps({"status": rng.choice(_DIVERSE_WORKLOAD_STATUSES), "score": rng.randrange(100_000)},
                               separators=(",", ":")) + "\n" for _ in range(count)).encode()


def _make_diverse_workload_task(family: str, index: int) -> dict:
    if family not in _DIVERSE_WORKLOAD_FAMILIES:
        raise ValueError(f"Família desconhecida: {family}")
    if type(index) is not int or not 0 <= index < _DIVERSE_WORKLOAD_SAMPLE_COUNTS[family]:
        raise ValueError(f"Índice inválido para a família {family}: {index}")

    seed = int(hashlib.sha256(
        f"sentinela-final-test-v1:{family}:{index}".encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    rows = _DIVERSE_WORKLOAD_ROWS[index % len(_DIVERSE_WORKLOAD_ROWS)]
    data = b""
    read = write = False

    if family == "csv_variance_stream":
        data, read = _diverse_workload_csv(rng, rows), True
        code = (
            "from pathlib import Path\ncount = total = squares = 0\n"
            "for line in Path('/input/data.txt').open():\n"
            "    value = int(line.rstrip().split(',')[1])\n"
            "    count += 1\n    total += value\n    squares += value * value\n"
            "print(count, total, squares)\n"
        )
    elif family == "csv_frequency_report":
        data, read, write = _diverse_workload_csv(rng, rows, grouped=True), True, True
        code = (
            "import json\nfrom collections import Counter\nfrom pathlib import Path\n"
            "counts = Counter()\nwith Path('/input/data.txt').open() as source:\n"
            "    for line in source:\n        counts[line.split(',', 1)[0]] += 1\n"
            "Path('/output/counts.json').write_text(json.dumps(dict(sorted(counts.items()))))\n"
            "print(len(counts), sum(counts.values()))\n"
        )
    elif family == "csv_ranked_rows":
        data, read = _diverse_workload_csv(rng, rows), True
        limit = (5, 10, 20, 50)[index % 4]
        code = (
            "from pathlib import Path\nrows = []\n"
            "for line in Path('/input/data.txt').read_text().splitlines():\n"
            "    key, value = line.split(',')\n    rows.append((int(value), int(key)))\n"
            f"rows.sort(reverse=True)\nprint(rows[:{limit}])\n"
        )
    elif family == "json_group_report":
        row_count = min(rows, 30_000)
        data, read, write = _diverse_workload_json_rows(rng, row_count), True, True
        code = (
            "import json\nfrom pathlib import Path\n"
            "items = json.loads(Path('/input/data.txt').read_text())\nsummary = {}\n"
            "for row in items:\n    totals = summary.setdefault(row['group'], [0, 0])\n"
            "    totals[0] += 1\n    totals[1] += row['score']\n"
            "Path('/output/summary.json').write_text(json.dumps(summary, sort_keys=True))\n"
            "print(len(items), len(summary))\n"
        )
    elif family == "jsonl_score_filter":
        row_count = min(rows, 60_000)
        data, read, write = _diverse_workload_jsonl_rows(rng, row_count), True, True
        threshold = rng.randrange(20_000, 80_001)
        code = (
            "import json\nfrom pathlib import Path\nselected = []\n"
            "for line in Path('/input/data.txt').open():\n    row = json.loads(line)\n"
            f"    if row['score'] >= {threshold}: selected.append(row)\n"
            "Path('/output/selected.jsonl').write_text(''.join(json.dumps(row) + '\\n' for row in selected))\n"
            "print(len(selected))\n"
        )
    elif family == "text_line_stats":
        data, read = _diverse_workload_text(rng, min(rows, 60_000)), True
        code = (
            "from pathlib import Path\nlines = Path('/input/data.txt').read_text().splitlines()\n"
            "lengths = [len(line) for line in lines]\n"
            "print(len(lines), max(lengths, default=0), sum(lengths))\n"
        )
    elif family == "text_replace_report":
        data, read, write = _diverse_workload_text(rng, min(rows, 60_000), repeated=True), True, True
        source, target = rng.choice(_DIVERSE_WORKLOAD_TOKENS), rng.choice(_DIVERSE_WORKLOAD_TOKENS)
        code = (
            "from pathlib import Path\ntext = Path('/input/data.txt').read_text()\n"
            f"changed = text.replace({source!r}, {target!r})\n"
            "Path('/output/replaced.txt').write_text(changed)\n"
            "print(len(text), text.count(" + repr(source) + "))\n"
        )
    elif family == "text_unique_sorted":
        data, read, write = _diverse_workload_text(rng, min(rows, 60_000)), True, True
        code = (
            "from pathlib import Path\nwords = Path('/input/data.txt').read_text().split()\n"
            "unique = sorted(set(words))\n"
            "Path('/output/unique.txt').write_text('\\n'.join(unique) + '\\n')\n"
            "print(len(words), len(unique))\n"
        )
    elif family == "graph_components":
        nodes = max(20, min(10_000, rows // 3))
        data = "".join(f"{rng.randrange(nodes)},{rng.randrange(nodes)}\n" for _ in range(rows)).encode()
        read = True
        code = (
            "from pathlib import Path\nadjacency = {}\n"
            "for line in Path('/input/data.txt').open():\n"
            "    left, right = line.rstrip().split(',')\n"
            "    adjacency.setdefault(left, set()).add(right)\n"
            "    adjacency.setdefault(right, set()).add(left)\n"
            "seen = set()\ncomponents = 0\n"
            "for start in adjacency:\n    if start in seen: continue\n"
            "    components += 1\n    stack = [start]\n    seen.add(start)\n"
            "    while stack:\n        node = stack.pop()\n"
            "        for neighbor in adjacency[node] - seen:\n"
            "            seen.add(neighbor)\n            stack.append(neighbor)\n"
            "print(len(adjacency), components)\n"
        )
    elif family == "point_nearest":
        data = "".join(f"{rng.randrange(1_000_000)},{rng.randrange(1_000_000)}\n" for _ in range(rows)).encode()
        read = True
        code = (
            "from pathlib import Path\npoints = []\n"
            "for line in Path('/input/data.txt').open():\n"
            "    x, y = map(int, line.split(','))\n    points.append((x, y))\n"
            "points.sort(key=lambda point: point[0] * point[0] + point[1] * point[1])\n"
            "print(len(points), points[:3])\n"
        )
    elif family == "activity_schedule":
        count = min(rows, 60_000)
        code = (
            f"intervals = [((i * 17) % {count * 2}, (i * 17) % {count * 2} + 1 + i % 37) for i in range({count})]\n"
            "intervals.sort(key=lambda item: item[1])\nselected = []\nend = -1\n"
            "for start, finish in intervals:\n"
            "    if start >= end:\n        selected.append((start, finish))\n        end = finish\n"
            "print(len(selected), sum(finish - start for start, finish in selected))\n"
        )
    elif family == "matrix_product":
        side = (8, 12, 16, 20, 24, 28, 32, 36)[index % 8]
        code = (
            f"side = {side}\na = [[(r * 7 + c * 3) % 97 for c in range(side)] for r in range(side)]\n"
            "b = [[(r * 5 + c * 11) % 89 for c in range(side)] for r in range(side)]\n"
            "product = [[sum(a[r][k] * b[k][c] for k in range(side)) for c in range(side)] for r in range(side)]\n"
            "print(side, sum(map(sum, product)))\n"
        )
    elif family == "prime_sieve":
        limit = (10_000, 20_000, 35_000, 50_000, 70_000, 90_000, 120_000, 150_000)[index % 8]
        code = (
            f"limit = {limit}\nflags = bytearray(b'\\x01') * (limit + 1)\n"
            "flags[:2] = b'\\x00\\x00'\n"
            "for value in range(2, int(limit ** 0.5) + 1):\n"
            "    if flags[value]: flags[value * value:limit + 1:value] = b'\\x00' * (((limit - value * value) // value) + 1)\n"
            "print(sum(flags))\n"
        )
    elif family == "fibonacci_tail":
        steps = (5_000, 10_000, 20_000, 40_000, 60_000, 80_000, 120_000, 160_000)[index % 8]
        code = (
            f"steps = {steps}\na, b = 0, 1\n"
            "for _ in range(steps): a, b = b, a + b\n"
            "print(steps, a.bit_length())\n"
        )
    elif family == "page_buffer":
        megabytes = (2, 4, 8, 12, 16, 24, 32, 48)[index % 8]
        code = (
            f"size = {megabytes} * 1024 * 1024\nbuffer = bytearray(size)\n"
            "for offset in range(0, size, 4096): buffer[offset] = 1\n"
            "print(len(buffer), sum(buffer[::4096]))\n"
        )
    elif family == "nested_json_scan":
        row_count = min(rows, 30_000)
        values = [{"id": i, "meta": {"group": rng.randrange(128), "flags": [bool(rng.randrange(2)) for _ in range(4)]},
                   "measurements": [rng.randrange(100_000) for _ in range(5)]} for i in range(row_count)]
        data, read = json.dumps(values, separators=(",", ":")).encode(), True
        code = (
            "import json\nfrom pathlib import Path\n"
            "records = json.loads(Path('/input/data.txt').read_text())\n"
            "active = sum(any(record['meta']['flags']) for record in records)\n"
            "total = sum(sum(record['measurements']) for record in records)\n"
            "print(len(records), active, total)\n"
        )
    elif family == "csv_rolling_mean":
        data, read = _diverse_workload_csv(rng, rows), True
        window = (10, 25, 50, 100, 250, 500, 750, 1000)[index % 8]
        code = (
            "from collections import deque\nfrom pathlib import Path\n"
            f"window = {window}\nvalues = deque()\ntotal = count = 0\n"
            "for line in Path('/input/data.txt').open():\n"
            "    value = int(line.rstrip().split(',')[1])\n    values.append(value)\n"
            "    total += value\n    if len(values) > window: total -= values.popleft()\n"
            "    if len(values) == window: count += 1\n"
            "print(count, total)\n"
        )
    else:
        raise ValueError(f"Implementação ausente para {family}")

    code += _DIVERSE_WORKLOAD_SUFFIX
    return {"id": f"{family}-{index:03d}", "family": family, "seed": seed,
            "code": code, "input_data": data,
            "capabilities": [int(read), int(write)]}

TRAIN_FAMILIES = (
    *_CORE_TRAIN_FAMILIES,
    *_GENERAL_TRAIN_FAMILIES,
    *_LARGE_TRAIN_FAMILIES,
    *_RESOURCE_TRAIN_FAMILIES,
    *_GENERAL_WORKLOAD_FAMILIES,
    *_DIVERSE_WORKLOAD_FAMILIES,
)
SAMPLES_PER_FAMILY = {
    **{family: 12 for family in _CORE_TRAIN_FAMILIES},
    **{family: 40 for family in _GENERAL_TRAIN_FAMILIES},
    **{family: 100 for family in _LARGE_TRAIN_FAMILIES},
    **{family: 100 for family in _RESOURCE_TRAIN_FAMILIES},
    **_GENERAL_WORKLOAD_SAMPLE_COUNTS,
    **_DIVERSE_WORKLOAD_SAMPLE_COUNTS,
}
_TRAIN_GENERATORS = {
    **{family: _make_core_train_task for family in _CORE_TRAIN_FAMILIES},
    **{family: _make_general_train_task for family in _GENERAL_TRAIN_FAMILIES},
    **{family: _make_large_train_task for family in _LARGE_TRAIN_FAMILIES},
    **{family: _make_resource_train_task for family in _RESOURCE_TRAIN_FAMILIES},
    **{family: _make_general_workload_family for family in _GENERAL_WORKLOAD_FAMILIES},
    **{family: _make_diverse_workload_task for family in _DIVERSE_WORKLOAD_FAMILIES},
}

def make_task(family: str, index: int) -> dict:
    generator = _TRAIN_GENERATORS.get(family)
    if generator is None:
        raise ValueError(f'Família de treino desconhecida: {family}')
    return generator(family, index)
