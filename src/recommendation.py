"""Regra heurística inicial; não é um modelo treinado."""
import math

from features import extract
from policy import Budget, authorize


def recommend(code: str, input_bytes: int, ceiling: Budget) -> dict:
    features = extract(code, input_bytes)
    input_mib = input_bytes / (1024 * 1024)
    raw_memory = (32 + 8 * input_mib + 2 * features["loops"]
                  + 3 * features["comprehensions"] + 5 * features["allocation_calls"]
                  + 0.02 * features["ast_nodes"])
    raw_wall = (0.25 + 0.20 * input_mib + 0.03 * features["calls"]
                + 0.15 * features["loops"])
    suggestion = {
        "memory_mb": math.ceil(raw_memory),
        "wall_seconds": raw_wall,
        "read_input": input_bytes > 0 and features["read_calls"] > 0,
        "write_output": features["write_calls"] > 0,
    }
    budget = authorize(suggestion, ceiling)
    return {
        "method": "heuristic",
        "trained_model": False,
        "features": features,
        "suggestion": suggestion,
        "authorized_budget": budget.to_dict(),
        "note": "Estimativa inicial baseada em AST e tamanho da entrada; revise para tarefas importantes.",
    }
