"""Features anteriores à execução. Não recebe rótulos, split ou família."""
import ast
import math

FEATURE_NAMES = (
    "log_input_bytes", "log_code_bytes", "ast_nodes", "loops", "comprehensions",
    "calls", "imports", "read_calls", "write_calls", "sort_calls",
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
    constants = [abs(n.value) for n in nodes if isinstance(n, ast.Constant)
                 and type(n.value) in (int, float) and math.isfinite(n.value)]
    return [
        math.log1p(input_bytes), math.log1p(len(code.encode())), len(nodes),
        sum(isinstance(n, (ast.For, ast.While)) for n in nodes),
        sum(isinstance(n, (ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)) for n in nodes),
        len(names), sum(isinstance(n, (ast.Import, ast.ImportFrom)) for n in nodes),
        count({"read", "read_text", "read_bytes", "load", "reader"}),
        count({"write", "write_text", "write_bytes", "dump", "writer"}),
        count({"sort", "sorted"}), count({"loads", "dumps", "load", "dump"}),
        count({"sha256", "md5", "blake2b"}),
        count({"list", "dict", "set", "bytearray", "bytes"}),
        math.log1p(max(constants, default=0)),
    ]
