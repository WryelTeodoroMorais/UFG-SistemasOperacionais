"""Treino supervisionado apenas no split train; seleção só na validação."""
import hashlib
import json
import math
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import (ExtraTreesClassifier, ExtraTreesRegressor,
                              GradientBoostingRegressor)
from sklearn.metrics import mean_absolute_error, f1_score

from .data import digest, load
from .features import FEATURE_NAMES, extract
from .policy import Budget, authorize


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
               "train_sha256": digest(root / "data/train.jsonl"),
               "train_ids": [r["id"] for r in rows],
               "train_families": sorted({r["family"] for r in rows})}
    (root / "models").mkdir(exist_ok=True)
    joblib.dump(package, root / "models/model.joblib")
    return _freeze_model(root)


def recommend(package: dict, features: list, margin: float, wall_margin: float) -> dict:
    memory, wall = np.expm1(package["regressor"].predict([features])[0])
    caps = package["classifier"].predict([features])[0]
    return {"memory_mb": max(24, float(memory) * margin + 4),
            "wall_seconds": max(0.2, float(wall) * wall_margin + 0.08),
            "read_input": bool(caps[0]), "write_output": bool(caps[1])}


def _freeze_model(root: Path):
    """Escolhe o menor orçamento com cobertura conjunta completa na validação."""
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
    candidates = []
    for margin in (1.0, 1.05, 1.1, 1.15, 1.2, 1.35, 1.5, 1.7, 2.1, 2.5):
        for wall_margin in (1.0, 1.05, 1.1, 1.2, 1.35, 1.5, 2.0, 3.0):
            recs = [recommend(package, r["features"], margin, wall_margin) for r in rows]
            memory_coverage = np.mean([
                p["memory_mb"] >= r["targets"]["memory_mb"]
                for p, r in zip(recs, rows)
            ])
            wall_coverage = np.mean([
                p["wall_seconds"] >= r["targets"]["wall_seconds"]
                for p, r in zip(recs, rows)
            ])
            coverage = np.mean([
                p["memory_mb"] >= r["targets"]["memory_mb"] and
                p["wall_seconds"] >= r["targets"]["wall_seconds"]
                for p, r in zip(recs, rows)
            ])
            mean_budget = float(np.mean([p["memory_mb"] for p in recs]))
            mean_wall = float(np.mean([p["wall_seconds"] for p in recs]))
            normalized_budget = float((mean_budget / heuristic_memory.mean() +
                                       mean_wall / heuristic_wall.mean()) / 2)
            candidates.append({"margin": margin, "wall_margin": wall_margin,
                               "coverage": float(coverage),
                               "memory_coverage": float(memory_coverage),
                               "wall_coverage": float(wall_coverage),
                               "mean_memory_mb": mean_budget,
                               "mean_wall_seconds": mean_wall,
                               "normalized_budget": normalized_budget,
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
    freeze = {**chosen, "candidate_count": len(candidates),
              "regressor_kind": package.get("regressor_kind", "hybrid"),
              "model_sha256": digest(root / "models/model.joblib"),
              "train_sha256": package["train_sha256"],
              "train_samples": len(package["train_ids"]),
              "train_families": len(package["train_families"]),
              "validation_sha256": digest(root / "data/validation.jsonl"),
              "test_used": False,
              "coverage_target": coverage_target,
              "selection_rule": "minimum mean budget normalized to the heuristic, subject to 100% joint memory/time coverage on validation when attainable; otherwise maximum coverage",
              "feature_schema": list(FEATURE_NAMES)}
    (root / "models/frozen.json").write_text(json.dumps(freeze, indent=2))
    return freeze


def frozen(root: Path):
    config = json.loads((root / "models/frozen.json").read_text())
    if digest(root / "models/model.joblib") != config["model_sha256"]:
        raise ValueError("Modelo alterado depois do congelamento")
    if digest(root / "data/train.jsonl") != config["train_sha256"]:
        raise ValueError("Treino alterado depois do congelamento")
    if digest(root / "data/validation.jsonl") != config["validation_sha256"]:
        raise ValueError("Validação alterada depois do congelamento")
    return joblib.load(root / "models/model.joblib"), config


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
