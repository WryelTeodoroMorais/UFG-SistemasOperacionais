"""Features anteriores à execução. Não recebe rótulos, split ou família."""
import ast
import math
import operator

FEATURE_NAMES = (
    "log_input_bytes", "log_code_bytes", "ast_nodes", "loops", "comprehensions",
    "calls", "imports", "input_read_calls", "output_write_calls", "sort_calls",
    "json_calls", "hash_calls", "allocation_calls", "log_max_literal",
    "log_max_range_iterations", "log_materialized_items", "log_estimated_allocation_mib",
)

_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.FloorDiv: operator.floordiv,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}


def _numeric_value(node, constants):
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        value = node.value
    elif isinstance(node, ast.Name):
        value = constants.get(node.id)
    elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        operand = _numeric_value(node.operand, constants)
        value = None if operand is None else operand if isinstance(node.op, ast.UAdd) else -operand
    elif isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        left = _numeric_value(node.left, constants)
        right = _numeric_value(node.right, constants)
        if left is None or right is None or (isinstance(node.op, ast.Pow) and abs(right) > 16):
            value = None
        else:
            try:
                value = _BINARY_OPERATORS[type(node.op)](left, right)
            except (ArithmeticError, OverflowError, ValueError):
                value = None
    else:
        value = None
    if value is None or not math.isfinite(value) or abs(value) > 10**12:
        return None
    return value


def _constant_bindings(tree):
    constants = {}
    for statement in tree.body:
        if isinstance(statement, ast.Assign):
            targets = statement.targets
        elif isinstance(statement, ast.AnnAssign):
            targets = [statement.target]
        else:
            continue
        value = _numeric_value(statement.value, constants)
        for target in targets:
            if isinstance(target, ast.Name):
                if value is None:
                    constants.pop(target.id, None)
                else:
                    constants[target.id] = value
    return constants


def _range_iterations(node, constants):
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == "range" and 1 <= len(node.args) <= 3):
        return None
    values = [_numeric_value(arg, constants) for arg in node.args]
    if any(value is None or int(value) != value for value in values):
        return None
    try:
        return len(range(*(int(value) for value in values)))
    except (OverflowError, ValueError):
        return None


def _comprehension_items(node, constants):
    count = 1
    for generator in node.generators:
        if isinstance(generator.iter, (ast.Tuple, ast.List, ast.Set)):
            size = len(generator.iter.elts)
        else:
            size = _range_iterations(generator.iter, constants)
        if size is None:
            return None
        count *= size
        if count > 10**12:
            return None
    return count


def _estimated_allocated_bytes(call, constants):
    if not isinstance(call.func, ast.Name) or call.func.id not in {"bytearray", "bytes"} or not call.args:
        return None
    value = _numeric_value(call.args[0], constants)
    if value is None:
        value = _range_iterations(call.args[0], constants)
    if value is None or value < 0:
        return None
    return value


def extract(code: str, input_bytes: int) -> list[float]:
    if input_bytes < 0 or len(code.encode()) > 128_000:
        raise ValueError("Entrada ou código fora do escopo")
    tree = ast.parse(code)
    nodes = list(ast.walk(tree))
    bindings = _constant_bindings(tree)
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
    literal_values = [abs(n.value) for n in nodes if isinstance(n, ast.Constant)
                      and type(n.value) in (int, float) and math.isfinite(n.value)]
    range_iterations = [n for node in nodes if isinstance(node, ast.Call)
                        if (n := _range_iterations(node, bindings)) is not None]
    materialized = [n for node in nodes if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp))
                    if (n := _comprehension_items(node, bindings)) is not None]
    parents = {}
    stack = [(tree, None)]
    while stack:
        node, parent = stack.pop()
        parents[node] = parent
        stack.extend((child, node) for child in ast.iter_child_nodes(node))
    allocated_bytes = 0
    for node in nodes:
        if not isinstance(node, ast.Call):
            continue
        amount = _estimated_allocated_bytes(node, bindings)
        if amount is None:
            continue
        parent = parents.get(node)
        while parent is not None and not isinstance(parent, (ast.ListComp, ast.SetComp, ast.DictComp)):
            parent = parents.get(parent)
        if parent is not None:
            multiplier = _comprehension_items(parent, bindings)
            if multiplier is not None:
                amount *= multiplier
        allocated_bytes += amount
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
        math.log1p(max(literal_values, default=0)),
        math.log1p(max(range_iterations, default=0)),
        math.log1p(sum(materialized)),
        math.log1p(allocated_bytes / 1024**2),
    ]
