"""Regressão inicial de recursos, com inferência em uma árvore JSON portátil."""
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import struct

from artifacts import check_destination, write_json
from features import extract
from policy import Budget, authorize
from recommendation import METHODS, profile

FEATURES = tuple(extract("pass"))
SCHEMA = "sentinela-tree-v1"
MARGINS = {"memory_factor": 1.5, "memory_extra_mb": 8, "wall_factor": 2, "wall_extra_seconds": .15}


def _resource_limits(prediction) -> dict:
    memory = prediction[0] * MARGINS["memory_factor"] + MARGINS["memory_extra_mb"]
    wall = prediction[1] * MARGINS["wall_factor"] + MARGINS["wall_extra_seconds"]
    if not math.isfinite(memory) or not math.isfinite(wall):
        raise ValueError("Predição excede o intervalo numérico de recursos")
    return {"memory_mb": math.ceil(memory), "wall_seconds": wall}


def _positive(value):
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def load_model(path: Path) -> dict:
    if path.stat().st_size > 1_000_000:
        raise ValueError("Modelo JSON máximo: 1 MB")
    model = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(model, dict) or model.get("schema") != SCHEMA or model.get("features") != list(FEATURES):
        raise ValueError("Modelo incompatível ou features diferentes")
    nodes = model.get("nodes")
    if not isinstance(nodes, list) or not 1 <= len(nodes) <= 31:
        raise ValueError("Árvore inválida")
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise ValueError("Nó inválido")
        if "prediction" in node:
            prediction = node["prediction"]
            if not isinstance(prediction, list) or len(prediction) != 2 or not all(_positive(v) for v in prediction):
                raise ValueError("Predição inválida")
        elif (type(node.get("feature")) is not int or not 0 <= node["feature"] < len(FEATURES)
              or type(node.get("threshold")) not in (int, float) or not math.isfinite(node["threshold"])
              or any(type(node.get(side)) is not int or not index < node[side] < len(nodes)
                     for side in ("left", "right"))):
            raise ValueError("Divisão inválida ou árvore cíclica")
    return model


def predict(model: dict, features: dict) -> list[float]:
    # sklearn usa float32 nas entradas da árvore; mantém a mesma comparação.
    try:
        vector = [struct.unpack("f", struct.pack("f", float(features[name])))[0] for name in FEATURES]
    except (OverflowError, struct.error) as exc:
        raise ValueError("Feature fora do intervalo numérico suportado pelo ML") from exc
    if not all(math.isfinite(value) for value in vector):
        raise ValueError("Features devem ser finitas")
    index = 0
    while "prediction" not in model["nodes"][index]:
        node = model["nodes"][index]
        index = node["left"] if vector[node["feature"]] <= node["threshold"] else node["right"]
    return model["nodes"][index]["prediction"]


def recommend_ml(code: str, input_bytes: int, ceiling: Budget, path: Path) -> dict:
    model = load_model(path)
    features = extract(code, input_bytes)
    memory, wall = predict(model, features)
    # Margens fixadas antes da avaliação; não ajustadas com o teste.
    suggestion = {**_resource_limits((memory, wall)),
                  "read_input": features["read_calls"] > 0,
                  "write_output": features["write_calls"] > 0}
    budget = authorize(suggestion, ceiling)
    return {"method": "ml", "trained_model": True,
            "model_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "features": features, "prediction": {"peak_vms_mb": memory, "wall_seconds": wall},
            "suggestion": suggestion, "authorized_budget": budget.to_dict(),
            "note": "Recursos previstos por árvore treinada; permissões por AST. Não usa argumentos do script nem garante conclusão."}


def read_dataset(path: Path) -> tuple[dict, list[dict]]:
    if path.stat().st_size > 32 * 1024**2:
        raise ValueError("Dataset máximo: 32 MiB")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") != "sentinela-measurements-v1":
        raise ValueError("Dataset incompatível")
    rows = data.get("tasks")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Dataset vazio")
    seen = set()
    for row in rows:
        if (not isinstance(row, dict) or row.get("split") not in ("train", "test")
                or not isinstance(row.get("code"), str) or not isinstance(row.get("input_text"), str)):
            raise ValueError("Tarefa inválida")
        signature = (row["code"], row["input_text"])
        if signature in seen:
            raise ValueError("Tarefa duplicada entre observações/partições")
        seen.add(signature)
        row["features"] = extract(row["code"], len(row["input_text"].encode()))
        measurements = row.get("measurements")
        if not isinstance(measurements, list) or not measurements:
            raise ValueError("Medições reais são obrigatórias")
        for measurement in measurements:
            if (not isinstance(measurement, dict) or measurement.get("returncode") != 0
                    or measurement.get("timed_out") is not False
                    or not all(_positive(measurement.get(key)) for key in ("peak_vms_mb", "wall_seconds"))):
                raise ValueError("Treino exige medições bem-sucedidas, finitas e positivas")
        row["target"] = [max(m[key] for m in measurements) for key in ("peak_vms_mb", "wall_seconds")]
    return data, rows


def train(dataset: Path, output: Path) -> dict:
    import numpy as np
    import sklearn
    from sklearn.tree import DecisionTreeRegressor

    check_destination(output)
    data, rows = read_dataset(dataset)
    training = [r for r in rows if r["split"] == "train"]
    testing = [r for r in rows if r["split"] == "test"]
    if len(training) < 4 or len(testing) < 2:
        raise ValueError("São necessárias pelo menos 4 tarefas de treino e 2 de teste")
    estimator = DecisionTreeRegressor(max_depth=4, min_samples_leaf=2, random_state=336)
    estimator.fit([[r["features"][name] for name in FEATURES] for r in training],
                  np.log1p([r["target"] for r in training]))
    tree = estimator.tree_
    nodes = []
    for index in range(tree.node_count):
        if tree.children_left[index] == -1:
            nodes.append({"prediction": np.expm1(tree.value[index, :, 0]).tolist()})
        else:
            nodes.append({"feature": int(tree.feature[index]), "threshold": float(tree.threshold[index]),
                          "left": int(tree.children_left[index]), "right": int(tree.children_right[index])})
    model = {"schema": SCHEMA, "features": list(FEATURES), "nodes": nodes,
             "created_at": datetime.now(timezone.utc).isoformat(),
             "algorithm": "DecisionTreeRegressor", "sklearn_version": sklearn.__version__,
             "parameters": {"max_depth": 4, "min_samples_leaf": 2, "random_state": 336},
             "dataset_sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
             "margins": MARGINS}
    predictions = np.array([predict(model, row["features"]) for row in testing])
    targets = np.array([row["target"] for row in testing])
    budgets = {method: [profile(method, row["code"], len(row["input_text"].encode()), Budget())["authorized_budget"]
                        for row in testing] for method in ("fixed", "heuristic")}
    budgets["ml"] = [authorize(_resource_limits(prediction), Budget()).to_dict() for prediction in predictions]
    report = {"train_tasks": len(training), "test_tasks": len(testing),
              "test_mae": dict(zip(("peak_vms_mb", "wall_seconds"), np.abs(predictions-targets).mean(axis=0).tolist())),
              "reference_coverage": {method: float(np.mean([b["memory_mb"] >= target[0] and b["wall_seconds"] >= target[1]
                                                          for b, target in zip(budgets[method], targets)]))
                                     for method in METHODS},
              "scope": "Cobertura das medições reservadas; não mede sucesso de replay, famílias inéditas ou economia de RAM física.",
              "dataset_scope": data.get("scope", "fornecido pelo operador")}
    model["evaluation"] = report
    write_json(output, model)
    return {"model": str(output), **report}


def evaluate(dataset: Path, model_path: Path, output: Path) -> dict:
    """Reexecuta apenas o teste; mantém o modelo congelado e compara saídas."""
    import random
    from sandbox import run

    check_destination(output)
    model = load_model(model_path)
    if model.get("dataset_sha256") != hashlib.sha256(dataset.read_bytes()).hexdigest():
        raise ValueError("O modelo e o dataset devem pertencer ao mesmo experimento")
    _, rows = read_dataset(dataset)
    testing = [row for row in rows if row["split"] == "test"]
    if not testing:
        raise ValueError("Não há tarefas de teste")
    results = []
    rng = random.Random(336)
    for row in testing:
        text = row["input_text"].encode()
        ceiling = Budget(read_input=bool(text))
        profiles = {method: Budget(**profile(method, row["code"], len(text), ceiling, model_path)["authorized_budget"])
                    for method in METHODS}
        order = list(profiles)
        rng.shuffle(order)
        reference = row["measurements"][0]
        for method in order:
            measured = run(row["code"], text, profiles[method])
            correct = (measured["returncode"] == 0 and not measured["timed_out"]
                       and measured["stdout"] == reference["stdout"]
                       and measured["outputs"] == reference["outputs"])
            results.append({"task": row.get("id"), "family": row.get("family"),
                            "method": method, "correct": correct, "execution": measured})
    summary = {}
    for method in METHODS:
        group = [r for r in results if r["method"] == method]
        summary[method] = {"correct": sum(r["correct"] for r in group), "tasks": len(group),
                           "mean_memory_limit_mb": sum(r["execution"]["budget"]["memory_mb"] for r in group) / len(group),
                           "mean_wall_seconds": sum(r["execution"]["wall_seconds"] for r in group) / len(group)}
    report = {"created_at": datetime.now(timezone.utc).isoformat(),
              "model_sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
              "dataset_sha256": model["dataset_sha256"], "summary": summary, "results": results,
              "scope": "Um replay por método e tarefa reservada; ordem embaralhada com semente 336. Limite configurado não é consumo de RAM; não demonstra superioridade geral."}
    write_json(output, report)
    return {"report": str(output), "summary": summary, "scope": report["scope"]}
