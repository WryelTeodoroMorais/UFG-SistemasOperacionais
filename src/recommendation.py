"""Perfis fixo, heurístico e aprendido, sujeitos à mesma autorização."""
import math

from features import extract
from policy import Budget, authorize

METHODS = ("fixed", "heuristic", "ml")


def profile(method: str, code: str, input_bytes: int, ceiling: Budget, model_path=None) -> dict:
    if method == "ml":
        if model_path is None:
            raise ValueError("--method ml exige --model com um modelo JSON treinado")
        from learning import recommend_ml
        return recommend_ml(code, input_bytes, ceiling, model_path)
    if method == "heuristic":
        return recommend(code, input_bytes, ceiling)
    if method != "fixed":
        raise ValueError(f"Método desconhecido: {method}")
    suggestion = {"memory_mb": min(128, ceiling.memory_mb),
                  "wall_seconds": min(2.0, ceiling.wall_seconds),
                  "read_input": ceiling.read_input, "write_output": ceiling.write_output}
    return {"method": "fixed", "trained_model": False, "suggestion": suggestion,
            "authorized_budget": authorize(suggestion, ceiling).to_dict(),
            "note": "Perfil fixo de referência; não foi aprendido a partir de dados."}


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
