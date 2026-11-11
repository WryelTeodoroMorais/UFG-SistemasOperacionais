"""Workloads determinísticos atualmente presentes na partição de validação."""
import hashlib
import json
import random
_VALIDATION_FAMILIES = ('list_filter_v3', 'tuple_set_v3', 'json_nested_v3', 'text_token_index_v3', 'matrix_transpose_v3')
VALIDATION_FAMILIES = _VALIDATION_FAMILIES
_VALIDATION_FILE_COUNTS = (1000, 2500, 5000, 10000, 15000, 20000, 30000, 40000, 50000, 60000)
_VALIDATION_LIST_COUNTS = (100000, 200000, 300000, 400000, 500000, 650000, 800000, 1000000, 1200000, 1400000)
_VALIDATION_SIDES = (40, 60, 80, 100, 140, 180, 220, 280, 360, 440)
_VALIDATION_WORDS = ('amber', 'birch', 'cobalt', 'dawn', 'ember', 'fjord', 'grove', 'harbor', 'indigo', 'juniper', 'kernel', 'linen')

def _validation_csv(rng, count):
    return ''.join((f'{rng.randrange(10000)},{rng.randrange(-5000, 50001)}\n' for _ in range(count))).encode()

def _validation_json_rows(rng, count):
    rows = [{'id': i, 'group': f'g{rng.randrange(96)}', 'value': rng.randrange(-100000, 100001), 'active': bool(rng.randrange(2))} for i in range(count)]
    return json.dumps(rows, separators=(',', ':')).encode()

def _validation_text(rng, count):
    return ('\n'.join((' '.join((rng.choice(_VALIDATION_WORDS) for _ in range(6))) for _ in range(count))) + '\n').encode()

def make_task(family: str, index: int) -> dict:
    if family not in _VALIDATION_FAMILIES:
        raise ValueError(f'Família desconhecida: {family}')
    if type(index) is not int or not 0 <= index < 100:
        raise ValueError('Índice de tarefa deve ficar entre 0 e 99')
    seed = int(hashlib.sha256(f'sentinela-refinement-v3:{family}:{index}'.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    data = b''
    read = write = False
    if family == 'list_filter_v3':
        size = _VALIDATION_LIST_COUNTS[index % len(_VALIDATION_LIST_COUNTS)]
        stride = (2, 3, 5, 7)[index % 4]
        code = f'values = [i for i in range({size}) if i % {stride}]\nprint(len(values), sum(values))\n'
    elif family == 'tuple_set_v3':
        data = _validation_csv(rng, _VALIDATION_FILE_COUNTS[index % len(_VALIDATION_FILE_COUNTS)])
        read = True
        code = "import csv\nwith open('/input/data.txt', newline='') as source:\n    pairs = {(int(row[0]), int(row[1])) for row in csv.reader(source)}\nprint(len(pairs))\n"
    elif family == 'json_nested_v3':
        data = _validation_json_rows(rng, _VALIDATION_FILE_COUNTS[index % len(_VALIDATION_FILE_COUNTS)])
        read = True
        code = "import json\nfrom collections import defaultdict\ngroups = defaultdict(list)\nfor row in json.load(open('/input/data.txt')):\n    groups[row['group']].append(row['value'])\nprint(len(groups), sum(map(len, groups.values())))\n"
    elif family == 'text_token_index_v3':
        data = _validation_text(rng, _VALIDATION_FILE_COUNTS[index % len(_VALIDATION_FILE_COUNTS)])
        read = True
        code = "from collections import Counter\nfrom pathlib import Path\ncounts = Counter(Path('/input/data.txt').read_text().split())\nprint(len(counts), sum(counts.values()))\n"
    elif family == 'matrix_transpose_v3':
        side = _VALIDATION_SIDES[index % len(_VALIDATION_SIDES)]
        code = f'side = {side}\nmatrix = [[(row * 13 + col) % 97 for col in range(side)] for row in range(side)]\ntransposed = [list(column) for column in zip(*matrix)]\nprint(len(transposed), sum(map(sum, transposed)))\n'
    else:
        raise ValueError(f'Implementação ausente para {family}')
    code += '\nimport time\ntime.sleep(0.04)\n'
    return {'id': f'{family}-{index:03d}', 'family': family, 'seed': seed, 'code': code, 'input_data': data, 'capabilities': [int(read), int(write)]}
SAMPLES_PER_FAMILY = {family: 20 for family in _VALIDATION_FAMILIES}
