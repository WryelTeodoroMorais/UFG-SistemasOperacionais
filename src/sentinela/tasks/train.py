"""Workloads determinísticos atualmente presentes na partição de treino."""
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
    """Return a deterministic, executable task with explicit I/O capabilities."""
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
TRAIN_FAMILIES = (
    *_CORE_TRAIN_FAMILIES,
    *_GENERAL_TRAIN_FAMILIES,
    *_LARGE_TRAIN_FAMILIES,
    *_RESOURCE_TRAIN_FAMILIES,
)
SAMPLES_PER_FAMILY = {
    **{family: 12 for family in _CORE_TRAIN_FAMILIES},
    **{family: 40 for family in _GENERAL_TRAIN_FAMILIES},
    **{family: 100 for family in _LARGE_TRAIN_FAMILIES},
    **{family: 100 for family in _RESOURCE_TRAIN_FAMILIES},
}
_TRAIN_GENERATORS = {
    **{family: _make_core_train_task for family in _CORE_TRAIN_FAMILIES},
    **{family: _make_general_train_task for family in _GENERAL_TRAIN_FAMILIES},
    **{family: _make_large_train_task for family in _LARGE_TRAIN_FAMILIES},
    **{family: _make_resource_train_task for family in _RESOURCE_TRAIN_FAMILIES},
}

def make_task(family: str, index: int) -> dict:
    generator = _TRAIN_GENERATORS.get(family)
    if generator is None:
        raise ValueError(f'Família de treino desconhecida: {family}')
    return generator(family, index)
