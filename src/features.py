"""Extração estática de sinais simples para planejamento heurístico."""
import ast
import math

READ_NAMES = {"read", "read_text", "read_bytes", "load", "reader", "readline", "readlines"}
WRITE_NAMES = {"write", "write_text", "write_bytes", "dump", "writer", "writelines"}
ALLOC_NAMES = {"list", "dict", "set", "bytearray", "bytes", "tuple"}


def _call_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def extract(code: str, input_bytes: int = 0) -> dict:
    if type(input_bytes) is not int or input_bytes < 0:
        raise ValueError("Tamanho da entrada deve ser um inteiro não negativo")
    code_bytes = len(code.encode("utf-8"))
    if code_bytes > 128_000:
        raise ValueError("Código máximo: 128 kB")
    tree = ast.parse(code)
    nodes = list(ast.walk(tree))
    calls = [node for node in nodes if isinstance(node, ast.Call)]
    read_calls = 0
    write_calls = 0
    allocation_calls = 0
    for call in calls:
        name = _call_name(call.func)
        if name in READ_NAMES:
            read_calls += 1
        elif name in WRITE_NAMES:
            write_calls += 1
        elif name == "open":
            mode = "r"
            if len(call.args) > 1 and isinstance(call.args[1], ast.Constant) and isinstance(call.args[1].value, str):
                mode = call.args[1].value
            if any(flag in mode for flag in ("w", "a", "x", "+")):
                write_calls += 1
            else:
                read_calls += 1
        if name in ALLOC_NAMES:
            allocation_calls += 1
    loops = sum(isinstance(node, (ast.For, ast.AsyncFor, ast.While)) for node in nodes)
    comprehensions = sum(isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)) for node in nodes)
    imports = sum(isinstance(node, (ast.Import, ast.ImportFrom)) for node in nodes)
    literals = [abs(node.value) for node in nodes if isinstance(node, ast.Constant)
                and type(node.value) in (int, float) and math.isfinite(node.value)]
    return {
        "input_bytes": input_bytes,
        "code_bytes": code_bytes,
        "ast_nodes": len(nodes),
        "calls": len(calls),
        "loops": loops,
        "comprehensions": comprehensions,
        "imports": imports,
        "read_calls": read_calls,
        "write_calls": write_calls,
        "allocation_calls": allocation_calls,
        "largest_numeric_literal": max(literals, default=0),
    }
