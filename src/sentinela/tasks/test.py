"""Famílias finais, isoladas dos dados usados no ajuste do modelo."""
import hashlib
import json
import random

TEST_FAMILIES = (
    "csv_column_stats", "csv_group_quantile", "csv_frequent_values",
    "json_key_histogram", "jsonl_dedupe", "text_char_histogram",
    "text_indent_report", "set_intersection_report", "graph_shortest_path",
    "spatial_bucket_report", "schedule_conflict_count", "matrix_trace_batch",
    "prime_factor_report", "fibonacci_mod", "tuple_rolling_hash",
    "buffer_slice_checksum", "csv_window_quantile",
)
SAMPLES_PER_FAMILY = {family: 50 for family in TEST_FAMILIES}
_ROWS = (100, 400, 1_000, 3_000, 8_000, 15_000, 25_000, 40_000, 60_000, 80_000)
_WORDS = ("amber", "birch", "cobalt", "dawn", "ember", "fjord", "grove", "harbor",
          "indigo", "juniper", "kernel", "linen", "maple", "nectar", "onyx", "prairie")
_SUFFIX = "\nimport time\ntime.sleep(0.04)\n"


def _csv(rng: random.Random, count: int, *, grouped: bool = False) -> bytes:
    return "".join(
        f"{rng.randrange(128) if grouped else index},{rng.randrange(-1_000_000, 1_000_001)}\n"
        for index in range(count)
    ).encode()


def _jsonl(rng: random.Random, count: int) -> bytes:
    return "".join(
        json.dumps({"group": f"g{rng.randrange(64)}", "value": rng.randrange(100_000),
                    "active": bool(rng.randrange(2))}, separators=(",", ":")) + "\n"
        for _ in range(count)
    ).encode()


def _text(rng: random.Random, count: int, *, indent: bool = False) -> bytes:
    lines = []
    for index in range(count):
        pad = " " * (index % 9) if indent else ""
        words = " ".join(rng.choice(_WORDS) for _ in range(rng.randrange(4, 9)))
        lines.append(pad + words)
    return ("\n".join(lines) + "\n").encode()


def make_task(family: str, index: int) -> dict:
    if family not in TEST_FAMILIES:
        raise ValueError(f"Família desconhecida: {family}")
    if type(index) is not int or not 0 <= index < SAMPLES_PER_FAMILY[family]:
        raise ValueError(f"Índice inválido para a família {family}: {index}")

    seed = int(hashlib.sha256(
        f"sentinela-final-test-v2:{family}:{index}".encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    rows = _ROWS[index % len(_ROWS)]
    data = b""
    read = write = False

    if family == "csv_column_stats":
        data, read = _csv(rng, rows), True
        code = (
            "from pathlib import Path\nvalues = []\n"
            "for line in Path('/input/data.txt').open():\n"
            "    values.append(int(line.rstrip().split(',')[1]))\n"
            "print(len(values), min(values), max(values), sum(values))\n"
        )
    elif family == "csv_group_quantile":
        data, read, write = _csv(rng, rows, grouped=True), True, True
        code = (
            "import json\nfrom collections import defaultdict\nfrom pathlib import Path\n"
            "groups = defaultdict(list)\n"
            "for line in Path('/input/data.txt').read_text().splitlines():\n"
            "    group, value = line.split(',')\n    groups[group].append(int(value))\n"
            "result = {}\nfor group, values in groups.items():\n"
            "    values.sort()\n    result[group] = values[len(values) // 4]\n"
            "Path('/output/quantiles.json').write_text(json.dumps(result, sort_keys=True))\n"
            "print(len(result))\n"
        )
    elif family == "csv_frequent_values":
        data, read = _csv(rng, rows, grouped=True), True
        code = (
            "from collections import Counter\nfrom pathlib import Path\n"
            "counts = Counter(line.split(',', 1)[0] for line in Path('/input/data.txt').read_text().splitlines())\n"
            "print(counts.most_common(5))\n"
        )
    elif family == "json_key_histogram":
        count = min(rows, 25_000)
        records = [{"key": f"k{rng.randrange(96)}", "value": rng.randrange(100_000),
                    "enabled": bool(rng.randrange(2))} for _ in range(count)]
        data, read, write = json.dumps(records, separators=(",", ":")).encode(), True, True
        code = (
            "import json\nfrom collections import Counter\nfrom pathlib import Path\n"
            "records = json.loads(Path('/input/data.txt').read_text())\n"
            "counts = Counter(row['key'] for row in records if row['enabled'])\n"
            "Path('/output/histogram.json').write_text(json.dumps(dict(sorted(counts.items()))))\n"
            "print(len(records), sum(counts.values()))\n"
        )
    elif family == "jsonl_dedupe":
        data, read, write = _jsonl(rng, min(rows, 60_000)), True, True
        code = (
            "import json\nfrom pathlib import Path\nseen = set()\nunique = []\n"
            "for line in Path('/input/data.txt').read_text().splitlines():\n"
            "    row = json.loads(line)\n    key = (row['group'], row['value'])\n"
            "    if key not in seen:\n        seen.add(key)\n        unique.append(row)\n"
            "Path('/output/unique.jsonl').write_text(''.join(json.dumps(row) + '\\n' for row in unique))\n"
            "print(len(unique))\n"
        )
    elif family == "text_char_histogram":
        data, read, write = _text(rng, min(rows, 60_000)), True, True
        code = (
            "import json\nfrom collections import Counter\nfrom pathlib import Path\n"
            "counts = Counter(Path('/input/data.txt').read_text())\n"
            "Path('/output/chars.json').write_text(json.dumps(dict(sorted(counts.items()))))\n"
            "print(len(counts), sum(counts.values()))\n"
        )
    elif family == "text_indent_report":
        data, read = _text(rng, min(rows, 60_000), indent=True), True
        code = (
            "from collections import Counter\nfrom pathlib import Path\n"
            "lines = Path('/input/data.txt').read_text().splitlines()\n"
            "counts = Counter(len(line) - len(line.lstrip(' ')) for line in lines)\n"
            "print(len(lines), dict(sorted(counts.items())))\n"
        )
    elif family == "set_intersection_report":
        size = (10_000, 20_000, 40_000, 60_000, 80_000, 100_000, 140_000, 180_000, 220_000, 260_000)[index % 10]
        code = (
            f"size = {size}\nleft = {{(i * 17) % (size * 2) for i in range(size)}}\n"
            "right = {(i * 29 + 3) % (size * 2) for i in range(size)}\n"
            "common = left & right\nprint(len(left), len(right), len(common), sum(common))\n"
        )
    elif family == "graph_shortest_path":
        nodes = max(20, min(8_000, rows // 4))
        edges = [(i, i + 1) for i in range(nodes - 1)]
        edges.extend((rng.randrange(nodes), rng.randrange(nodes)) for _ in range(rows))
        data, read = "".join(f"{a},{b}\n" for a, b in edges).encode(), True
        code = (
            "from collections import deque\nfrom pathlib import Path\nadjacency = {}\n"
            "for line in Path('/input/data.txt').read_text().splitlines():\n"
            "    left, right = line.split(',')\n"
            "    adjacency.setdefault(left, []).append(right)\n"
            "    adjacency.setdefault(right, []).append(left)\n"
            f"start, target = '0', {str(nodes - 1)!r}\nqueue = deque([(start, 0)])\nseen = {{start}}\ndistance = -1\n"
            "while queue:\n    node, depth = queue.popleft()\n"
            "    if node == target:\n        distance = depth\n        break\n"
            "    for neighbor in adjacency.get(node, ()):\n"
            "        if neighbor not in seen:\n            seen.add(neighbor)\n            queue.append((neighbor, depth + 1))\n"
            "print(len(adjacency), distance)\n"
        )
    elif family == "spatial_bucket_report":
        data = "".join(f"{rng.randrange(2_000_000)},{rng.randrange(2_000_000)}\n" for _ in range(rows)).encode()
        read = write = True
        width = (10, 25, 50, 100, 250)[index % 5]
        code = (
            "import json\nfrom collections import Counter\nfrom pathlib import Path\n"
            f"width = {width}\ncells = Counter()\n"
            "for line in Path('/input/data.txt').read_text().splitlines():\n"
            "    x, y = map(int, line.split(','))\n    cells[(x // width, y // width)] += 1\n"
            "payload = {f'{x}:{y}': count for (x, y), count in cells.most_common(100)}\n"
            "Path('/output/cells.json').write_text(json.dumps(payload))\n"
            "print(len(cells), max(cells.values(), default=0))\n"
        )
    elif family == "schedule_conflict_count":
        size = min(rows, 60_000)
        code = (
            f"size = {size}\nintervals = [((i * 31) % (size * 3), (i * 31) % (size * 3) + 1 + i % 101) for i in range(size)]\n"
            "events = [(start, 1) for start, end in intervals] + [(end, -1) for start, end in intervals]\n"
            "events.sort()\nactive = conflicts = maximum = 0\n"
            "for _, change in events:\n    active += change\n    maximum = max(maximum, active)\n"
            "    if active > 1: conflicts += 1\n"
            "print(len(intervals), maximum, conflicts)\n"
        )
    elif family == "matrix_trace_batch":
        side = (16, 24, 32, 40, 48, 56, 64, 72, 80, 88)[index % 10]
        code = (
            f"side = {side}\nmatrix = [[(r * 19 + c * 23) % 997 for c in range(side)] for r in range(side)]\n"
            "diagonal = sum(matrix[i][i] for i in range(side))\n"
            "row_totals = [sum(row) for row in matrix]\n"
            "print(side, diagonal, sum(row_totals), max(row_totals))\n"
        )
    elif family == "prime_factor_report":
        count = (100, 250, 500, 1_000, 2_000, 4_000, 6_000, 8_000, 10_000, 12_000)[index % 10]
        code = (
            f"count = {count}\nchecksum = factors_found = 0\n"
            "for offset in range(count):\n    number = 100_003 + offset * 37\n    factor = 2\n"
            "    while factor * factor <= number and number % factor:\n        factor += 1\n"
            "    factors_found += int(factor * factor <= number)\n    checksum += factor\n"
            "print(count, factors_found, checksum)\n"
        )
    elif family == "fibonacci_mod":
        steps = (10_000, 20_000, 40_000, 60_000, 80_000, 120_000, 180_000, 250_000, 350_000, 500_000)[index % 10]
        code = f"steps = {steps}\na, b = 0, 1\nmodulus = 1_000_000_007\nfor _ in range(steps): a, b = b, (a + b) % modulus\nprint(steps, a)\n"
    elif family == "tuple_rolling_hash":
        data, read = ("".join(f"{rng.randrange(-1_000_000, 1_000_001)}\n" for _ in range(rows))).encode(), True
        code = (
            "from pathlib import Path\nstate = 2166136261\n"
            "for line in Path('/input/data.txt').open():\n"
            "    state = ((state ^ int(line)) * 16777619) & 0xffffffff\n"
            "print(state)\n"
        )
    elif family == "buffer_slice_checksum":
        megabytes = (2, 4, 8, 12, 16, 24, 32, 48, 56, 64)[index % 10]
        code = (
            f"size = {megabytes} * 1024 * 1024\nbuffer = bytearray(size)\n"
            "for offset in range(0, size, 4096): buffer[offset] = (offset // 4096) % 251\n"
            "print(len(buffer), sum(buffer[::4096]))\n"
        )
    elif family == "csv_window_quantile":
        data, read = _csv(rng, rows), True
        window = (100, 200, 300, 400, 500, 600, 700, 800, 900, 1_000)[index % 10]
        code = (
            "from pathlib import Path\nvalues = [int(line.split(',')[1]) for line in Path('/input/data.txt').open()]\n"
            f"window = {window}\nmedians = []\n"
            "for start in range(0, len(values), window):\n"
            "    batch = sorted(values[start:start + window])\n"
            "    if batch: medians.append(batch[len(batch) // 2])\n"
            "print(len(values), len(medians), sum(medians))\n"
        )
    else:
        raise ValueError(f"Implementação ausente para {family}")

    code += _SUFFIX
    return {"id": f"{family}-{index:03d}", "family": family, "seed": seed,
            "code": code, "input_data": data,
            "capabilities": [int(read), int(write)]}
