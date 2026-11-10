"""Workloads determinísticos atualmente presentes na partição de teste."""
import hashlib
import random
TEST_FAMILIES = ('word_count', 'normalize')
SUFFIX = '\nimport time\ntime.sleep(0.04)\n'

def make_task(family: str, index: int) -> dict:
    if family not in TEST_FAMILIES:
        raise ValueError(f'Família desconhecida: {family}')
    seed = int(hashlib.sha256(f'{family}:{index}:2026'.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    rows = rng.choice((200, 1000, 4000, 12000, 30000, 60000))
    data = ''.join((f'{rng.randrange(1000)},{rng.randrange(10000)}\n' for _ in range(rows))).encode()
    read, write = (True, False)
    code = 'from pathlib import Path\n'
    if family == 'word_count':
        code += "from collections import Counter\ntext = Path('/input/data.txt').read_text()\ncounts = Counter(text.replace(',', ' ').split())\nprint(sum(counts.values()))\n"
    elif family == 'normalize':
        write = True
        code += "lines = Path('/input/data.txt').read_text().splitlines()\nresult = '\\n'.join(';'.join(str(int(x)) for x in line.split(',')) for line in lines)\nPath('/output/result.txt').write_text(result)\nprint(len(lines))\n"
    else:
        raise ValueError(f'Família desconhecida: {family}')
    code += SUFFIX
    return {'id': f'{family}-{index:03d}', 'family': family, 'seed': seed, 'code': code, 'input_data': data if read else b'', 'capabilities': [int(read), int(write)]}
SAMPLES_PER_FAMILY = {family: 12 for family in TEST_FAMILIES}
