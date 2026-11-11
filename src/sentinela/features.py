"""Features anteriores à execução. Não recebe rótulos, split ou família."""
import ast
import math

FEATURE_NAMES = (
    "log_input_bytes", "log_code_bytes", "ast_nodes", "loops", "comprehensions",
    "calls", "imports", "input_read_calls", "output_write_calls", "sort_calls",
    "json_calls", "hash_calls", "allocation_calls", "log_max_literal",
)


def extract(code: str, input_bytes: int) -> list[float]:
    if input_bytes < 0 or len(code.encode()) > 128_000:
        raise ValueError("Entrada ou código fora do escopo")
    tree = ast.parse(code)
    nodes = list(ast.walk(tree))
    names = []
    for n in nodes:
        if isinstance(n, ast.Call):
            names.append(n.func.attr if isinstance(n.func, ast.Attribute)
                         else n.func.id if isinstance(n.func, ast.Name) else "")
    count = lambda group: sum(name in group for name in names)

    def literal_path(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "Path" and node.args):
            return literal_path(node.args[0])
        return None

    open_reads = open_writes = 0
    for node in nodes:
        if not isinstance(node, ast.Call):
            continue
        method_open = isinstance(node.func, ast.Attribute) and node.func.attr == "open"
        builtin_open = isinstance(node.func, ast.Name) and node.func.id == "open"
        if not (method_open or builtin_open):
            continue
        path_node = node.func.value if method_open else (node.args[0] if node.args else None)
        path = literal_path(path_node)
        mode_node = (node.args[0] if method_open and node.args else
                     node.args[1] if builtin_open and len(node.args) > 1 else None)
        if mode_node is None:
            mode_node = next((kw.value for kw in node.keywords if kw.arg == "mode"), None)
        mode = mode_node.value if isinstance(mode_node, ast.Constant) and isinstance(mode_node.value, str) else "r"
        writes = any(flag in mode for flag in ("w", "a", "x", "+"))
        reads = "r" in mode or "+" in mode
        if path and path.startswith("/input/"):
            open_reads += 1
        elif path and path.startswith("/output/"):
            open_writes += 1
        else:
            open_reads += int(reads)
            open_writes += int(writes)
    constants = [abs(n.value) for n in nodes if isinstance(n, ast.Constant)
                 and type(n.value) in (int, float) and math.isfinite(n.value)]
    return [
        math.log1p(input_bytes), math.log1p(len(code.encode())), len(nodes),
        sum(isinstance(n, (ast.For, ast.While)) for n in nodes),
        sum(isinstance(n, (ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)) for n in nodes),
        len(names), sum(isinstance(n, (ast.Import, ast.ImportFrom)) for n in nodes),
        count({"read", "read_text", "read_bytes", "load", "reader"}) + open_reads,
        count({"write", "write_text", "write_bytes", "dump", "writer"}) + open_writes,
        count({"sort", "sorted"}), count({"loads", "dumps", "load", "dump"}),
        count({"sha256", "md5", "blake2b"}),
        count({"list", "dict", "set", "bytearray", "bytes"}),
        math.log1p(max(constants, default=0)),
    ]
