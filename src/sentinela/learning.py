"""Treino supervisionado apenas no split train; seleção só na validação."""
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import (ExtraTreesClassifier, ExtraTreesRegressor,
                              GradientBoostingRegressor)
from sklearn.metrics import mean_absolute_error, f1_score

from .assets import asset_path
from .data import digest, load
from .features import FEATURE_NAMES, extract

_MIN_OPERATING_MEMORY_MARGIN = 1.5
_MIN_OPERATING_WALL_MARGIN = 2.0
_INPUT_ENVELOPE_MIN_MIB = 0.5
_INPUT_ENVELOPE_QUANTILE = 0.99
_ENVELOPE_MEMORY_BASE_MB = 24.0
_ENVELOPE_MEMORY_CAP_MB = 128.0
_INPUT_WALL_BASE_SECONDS = 0.08
_INPUT_WALL_CAP_SECONDS = 2.0
_COLLECTION_ENVELOPE_MIN_ITEMS = 1_000
_COLLECTION_ENVELOPE_QUANTILE = 0.95


def _resource_slope(targets, base, scale):
    return np.maximum(0, np.asarray(targets) - base) / scale


def _fit_input_resource_envelope(rows):
    """Estimate conservative per-MiB resource floors from input-reading train rows."""
    samples = [r for r in rows
               if r["features"][7] > 0 and r["input_bytes"] >= _INPUT_ENVELOPE_MIN_MIB * 1024**2]
    if not samples:
        raise ValueError("Treino sem amostras de leitura grandes para calibrar o envelope")
    input_mib = np.array([r["input_bytes"] / 1024**2 for r in samples])
    memory_slope = _resource_slope(
        [r["targets"]["memory_mb"] for r in samples], _ENVELOPE_MEMORY_BASE_MB, input_mib)
    wall_slope = _resource_slope(
        [r["targets"]["wall_seconds"] for r in samples], _INPUT_WALL_BASE_SECONDS, input_mib)
    return {
        "minimum_input_mib": _INPUT_ENVELOPE_MIN_MIB,
        "quantile": _INPUT_ENVELOPE_QUANTILE,
        "sample_count": len(samples),
        "memory_base_mb": _ENVELOPE_MEMORY_BASE_MB,
        "memory_mb_per_mib": float(np.quantile(memory_slope, _INPUT_ENVELOPE_QUANTILE)),
        "wall_base_seconds": _INPUT_WALL_BASE_SECONDS,
        "wall_seconds_per_mib": float(np.quantile(wall_slope, _INPUT_ENVELOPE_QUANTILE)),
    }


def _fit_collection_memory_envelope(rows):
    """Estimate memory per materialized item from train-only targets."""
    items = np.expm1(np.array([r["features"][15] for r in rows]))
    memory = np.array([r["targets"]["memory_mb"] for r in rows])
    selected = items >= _COLLECTION_ENVELOPE_MIN_ITEMS
    if not selected.any():
        raise ValueError("Treino sem coleções materializadas para calibrar o envelope")
    memory_slope = _resource_slope(
        memory[selected], _ENVELOPE_MEMORY_BASE_MB, items[selected] / 1_000_000)
    return {
        "minimum_items": _COLLECTION_ENVELOPE_MIN_ITEMS,
        "quantile": _COLLECTION_ENVELOPE_QUANTILE,
        "sample_count": int(selected.sum()),
        "memory_base_mb": _ENVELOPE_MEMORY_BASE_MB,
        "memory_mb_per_million_items": float(np.quantile(memory_slope, _COLLECTION_ENVELOPE_QUANTILE)),
    }


def _apply_resource_envelopes(memory_budget, wall_budget, features,
                              input_envelope, collection_envelope):
    values = np.asarray(features, dtype=float)
    adjusted_memory, adjusted_wall = memory_budget, wall_budget
    if input_envelope:
        input_mib = np.expm1(values[:, 0]) / 1024**2
        reads_input = values[:, 7] > 0
        apply_floor = reads_input & (input_mib >= input_envelope["minimum_input_mib"])
        memory_floor = np.minimum(
            _ENVELOPE_MEMORY_CAP_MB, input_envelope["memory_base_mb"] +
            input_envelope["memory_mb_per_mib"] * input_mib)
        wall_floor = np.minimum(
            _INPUT_WALL_CAP_SECONDS, input_envelope["wall_base_seconds"] +
            input_envelope["wall_seconds_per_mib"] * input_mib)
        adjusted_memory = np.where(apply_floor, np.maximum(adjusted_memory, memory_floor), adjusted_memory)
        adjusted_wall = np.where(apply_floor, np.maximum(adjusted_wall, wall_floor), adjusted_wall)
    if collection_envelope:
        materialized_items = np.expm1(values[:, 15])
        apply_floor = materialized_items >= collection_envelope["minimum_items"]
        memory_floor = np.minimum(
            _ENVELOPE_MEMORY_CAP_MB, collection_envelope["memory_base_mb"] +
            collection_envelope["memory_mb_per_million_items"] * materialized_items / 1_000_000)
        adjusted_memory = np.where(apply_floor, np.maximum(adjusted_memory, memory_floor), adjusted_memory)
    if np.ndim(memory_budget) == 0 and len(values) == 1:
        return float(adjusted_memory[0]), float(adjusted_wall[0])
    return adjusted_memory, adjusted_wall


class HybridResourceRegressor:
    """Extra Trees para memória e Gradient Boosting para tempo."""

    def __init__(self):
        self.memory_model = ExtraTreesRegressor(
            n_estimators=256, min_samples_leaf=4, random_state=336, n_jobs=1)
        self.time_model = GradientBoostingRegressor(
            n_estimators=200, max_depth=2, learning_rate=0.03,
            loss="huber", random_state=336)

    def fit(self, features, targets):
        targets = np.asarray(targets)
        self.memory_model.fit(features, targets[:, 0])
        self.time_model.fit(features, targets[:, 1])
        return self

    def predict(self, features):
        return np.column_stack((self.memory_model.predict(features),
                                self.time_model.predict(features)))


def train(root: Path):
    if (root / "models" / "frozen.json").exists():
        raise FileExistsError("Modelo congelado: não retreinar após avaliação")
    rows = load(root, "train")
    x = np.array([r["features"] for r in rows])
    y = np.array([[r["targets"]["memory_mb"], r["targets"]["wall_seconds"]] for r in rows])
    labels = np.array([r["capabilities"] for r in rows])
    reg = HybridResourceRegressor()
    clf = ExtraTreesClassifier(n_estimators=128, min_samples_leaf=2, random_state=336, n_jobs=1)
    reg.fit(x, np.log1p(y))
    clf.fit(x, labels)
    package = {"regressor": reg, "regressor_kind": "hybrid-et256-leaf4",
               "classifier": clf, "features": FEATURE_NAMES,
               "input_resource_envelope": _fit_input_resource_envelope(rows),
               "collection_memory_envelope": _fit_collection_memory_envelope(rows),
               "train_sha256": digest(asset_path(root, "data/train.jsonl")),
               "train_ids": [r["id"] for r in rows],
               "train_families": sorted({r["family"] for r in rows})}
    (root / "models").mkdir(exist_ok=True)
    joblib.dump(package, root / "models/model.joblib")
    return _freeze_model(root)


def _resource_budgets(memory, wall, margin: float, wall_margin: float, features,
                      input_envelope, collection_envelope):
    memory_budget = np.maximum(24, memory * margin + 4)
    wall_budget = np.maximum(0.2, wall * wall_margin + 0.08)
    return _apply_resource_envelopes(
        memory_budget, wall_budget, features, input_envelope, collection_envelope)


def _budget_metrics(memory_budget, wall_budget, memory_targets, wall_targets,
                    heuristic_memory, heuristic_wall):
    memory_met = memory_budget >= memory_targets
    wall_met = wall_budget >= wall_targets
    mean_memory = float(memory_budget.mean())
    mean_wall = float(wall_budget.mean())
    return {
        "coverage": float(np.mean(memory_met & wall_met)),
        "memory_coverage": float(memory_met.mean()),
        "wall_coverage": float(wall_met.mean()),
        "mean_memory_mb": mean_memory,
        "mean_wall_seconds": mean_wall,
        "normalized_budget": float((mean_memory / heuristic_memory.mean() +
                                     mean_wall / heuristic_wall.mean()) / 2),
    }


def recommend(package: dict, features: list, margin: float, wall_margin: float) -> dict:
    memory, wall = np.expm1(package["regressor"].predict([features])[0])
    memory_budget, wall_budget = _resource_budgets(
        memory, wall, margin, wall_margin, [features],
        package.get("input_resource_envelope"), package.get("collection_memory_envelope"))
    caps = package["classifier"].predict([features])[0]
    return {"memory_mb": float(memory_budget), "wall_seconds": float(wall_budget),
            "read_input": bool(caps[0]), "write_output": bool(caps[1])}


def _freeze_model(root: Path):
    """Escolhe orçamento na validação e aplica as margens operacionais mínimas."""
    if (root / "models/frozen.json").exists():
        raise FileExistsError("Configuração já congelada")
    package = joblib.load(root / "models/model.joblib")
    rows = load(root, "validation")
    if set(package["train_families"]) & {r["family"] for r in rows}:
        raise ValueError("Vazamento entre famílias")
    heuristic_memory = np.array([
        min(256, 32 + r["input_bytes"] / 1024**2 * 64) for r in rows
    ])
    heuristic_wall = np.array([
        1.0 + r["input_bytes"] / 1024**2 for r in rows
    ])
    feature_rows = [r["features"] for r in rows]
    memory, wall = np.expm1(package["regressor"].predict(feature_rows)).T
    input_envelope = package.get("input_resource_envelope")
    collection_envelope = package.get("collection_memory_envelope")
    memory_targets = np.array([r["targets"]["memory_mb"] for r in rows])
    wall_targets = np.array([r["targets"]["wall_seconds"] for r in rows])
    candidates = []
    for margin in (1.0, 1.05, 1.1, 1.15, 1.2, 1.35, 1.5, 1.7, 2.1, 2.5):
        for wall_margin in (1.0, 1.05, 1.1, 1.2, 1.35, 1.5, 2.0, 3.0):
            memory_budget, wall_budget = _resource_budgets(
                memory, wall, margin, wall_margin, feature_rows,
                input_envelope, collection_envelope)
            candidates.append({"margin": margin, "wall_margin": wall_margin,
                               **_budget_metrics(memory_budget, wall_budget, memory_targets,
                                                 wall_targets, heuristic_memory, heuristic_wall),
                               "heuristic_mean_memory_mb": float(heuristic_memory.mean()),
                               "heuristic_mean_wall_seconds": float(heuristic_wall.mean())})
    coverage_target = 1.0
    qualified = [p for p in candidates if p["coverage"] >= coverage_target]
    if qualified:
        chosen = min(qualified, key=lambda p: (
            p["normalized_budget"], -p["coverage"], p["mean_memory_mb"],
            p["mean_wall_seconds"], p["wall_margin"],
        ))
    else:
        chosen = min(candidates, key=lambda p: (
            -p["coverage"], p["normalized_budget"], p["mean_memory_mb"],
            p["mean_wall_seconds"],
        ))
    chosen = dict(chosen)
    chosen["margin"] = max(chosen["margin"], _MIN_OPERATING_MEMORY_MARGIN)
    chosen["wall_margin"] = max(chosen["wall_margin"], _MIN_OPERATING_WALL_MARGIN)
    memory_budget, wall_budget = _resource_budgets(
        memory, wall, chosen["margin"], chosen["wall_margin"], feature_rows,
        input_envelope, collection_envelope)
    chosen.update(_budget_metrics(memory_budget, wall_budget, memory_targets, wall_targets,
                                  heuristic_memory, heuristic_wall))
    freeze = {**chosen, "candidate_count": len(candidates),
              "regressor_kind": package.get("regressor_kind", "hybrid"),
              "model_sha256": digest(root / "models/model.joblib"),
              "train_sha256": package["train_sha256"],
              "train_samples": len(package["train_ids"]),
              "train_families": len(package["train_families"]),
              "validation_sha256": digest(asset_path(root, "data/validation.jsonl")),
              "test_used": False,
              "coverage_target": coverage_target,
              "minimum_operating_memory_margin": _MIN_OPERATING_MEMORY_MARGIN,
              "minimum_operating_wall_margin": _MIN_OPERATING_WALL_MARGIN,
              "input_resource_envelope": input_envelope,
              "collection_memory_envelope": collection_envelope,
              "selection_rule": "minimum mean budget normalized to the heuristic, subject to 100% joint memory/time target coverage on validation when attainable, then apply the calibrated operating margins and train-only resource envelopes; test targets not used for fitting or margin selection",
              "feature_schema": list(FEATURE_NAMES)}
    (root / "models/frozen.json").write_text(json.dumps(freeze, indent=2))
    return freeze


def frozen(root: Path):
    config = json.loads(asset_path(root, "models/frozen.json").read_text())
    model_path = asset_path(root, "models/model.joblib")
    if digest(model_path) != config["model_sha256"]:
        raise ValueError("Modelo alterado depois do congelamento")
    if digest(asset_path(root, "data/train.jsonl")) != config["train_sha256"]:
        raise ValueError("Treino alterado depois do congelamento")
    if digest(asset_path(root, "data/validation.jsonl")) != config["validation_sha256"]:
        raise ValueError("Validação alterada depois do congelamento")
    return joblib.load(model_path), config


def prediction_report(root: Path, split: str):
    package, config = frozen(root)
    rows = load(root, split)
    predictions = [recommend(package, r["features"], config["margin"], config["wall_margin"]) for r in rows]
    actual = np.array([r["capabilities"] for r in rows])
    estimated = np.array([[p["read_input"], p["write_output"]] for p in predictions])
    raw = np.expm1(package["regressor"].predict([r["features"] for r in rows]))
    return {"memory_mae_mb": float(mean_absolute_error([r["targets"]["memory_mb"] for r in rows], raw[:, 0])),
            "time_mae_seconds": float(mean_absolute_error([r["targets"]["wall_seconds"] for r in rows], raw[:, 1])),
            "capabilities_f1_micro": float(f1_score(actual, estimated, average="micro", zero_division=0)),
            "capabilities_exact_match": float(np.mean(np.all(actual == estimated, axis=1))),
            "missing_capabilities": int(np.logical_and(actual, ~estimated).sum()),
            "excess_capabilities": int(np.logical_and(~actual.astype(bool), estimated).sum())}
