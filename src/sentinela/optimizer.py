"""Promoção supervisionada somente contra a implementação fundida forte.

Inferência com stdlib; treinamento opcional/offline. A validação decide se vale
pagar o custo de ML. Teste reservado não participa da promoção.
"""
import hashlib
import json
import math
from pathlib import Path
import struct
import time

from .strategies import ALL_STRATEGIES, features

SCHEMA = "fusion-optimizer-v1"


def infer(package: dict, values: list[float]) -> list[float]:
    """Avalia as árvores exportadas sem depender de scikit-learn no runtime."""
    # O sklearn converte X para float32 antes de percorrer árvores.
    values = [struct.unpack('f', struct.pack('f', value))[0] for value in values]
    totals = [0.0, 0.0]
    for tree in package["trees"]:
        node = 0
        while tree["left"][node] != -1:
            index = tree["feature"][node]
            node = tree["left"][node] if values[index] <= tree["threshold"][node] else tree["right"][node]
        for index in range(2):
            totals[index] += tree["value"][node][index]
    return [math.expm1(value / len(package["trees"])) for value in totals]


def vector(metadata: dict, strategy: str):
    if strategy not in ALL_STRATEGIES:
        raise ValueError("Estratégia não suportada")
    base = features(metadata, "memory" if strategy == "memory" else "blocks")
    return base + [float(strategy == "fused")]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def candidate_decision(package, metadata, target):
    if not math.isfinite(target) or target <= 0:
        raise ValueError("Meta de memória inválida")
    candidates = []
    for strategy in ALL_STRATEGIES:
        rss, seconds = infer(package, vector(metadata, strategy))
        candidates.append({"strategy":strategy, "predicted_rss_mb":rss,
                           "conservative_rss_mb":rss*package["rss_margin"],
                           "predicted_total_seconds":seconds})
    feasible = [p for p in candidates if p["conservative_rss_mb"] <= target]
    selected = min(feasible,key=lambda p:p["predicted_total_seconds"]) if feasible else min(candidates,key=lambda p:p["conservative_rss_mb"])
    return {"selected":selected["strategy"],"predicted_feasible":bool(feasible),"candidates":candidates}


def load_optimizer(root: Path):
    base = root / "evolution/fusion"
    policy_path = base / "frozen.json"
    if not policy_path.exists():
        return {"policy":{"ml_enabled":False,"reason":"no_promoted_model_use_fused"},"model":None}
    policy = json.loads(policy_path.read_text())
    if policy.get("schema") != SCHEMA:
        raise ValueError("Política incompatível")
    # Não carregar as árvores quando a validação não justifica ML.
    package = None
    if policy["ml_enabled"]:
        if sha(base / "model.json") != policy["model_sha256"]:
            raise ValueError("Modelo otimizado alterado")
        package = json.loads((base / "model.json").read_text())
    return {"policy":policy,"model":package}


def decide(optimizer, metadata, target):
    if not math.isfinite(target) or target <= 0:
        raise ValueError("Meta de memória inválida")
    policy = optimizer["policy"]
    if not policy["ml_enabled"]:
        return {"selected":"fused","ml_used":False,"reason":policy["reason"],
                "memory_target_mb":target,"predicted_feasible":None,
                "note":"Uma passagem, sem manter todas as linhas; meta RSS verificada após execução."}
    decision = candidate_decision(optimizer["model"],metadata,target)
    return {**decision,"ml_used":True,"reason":"promoted_on_validation", "memory_target_mb":target}


def train_optimizer(base: Path):
    import numpy as np
    from sklearn.ensemble import ExtraTreesRegressor
    if (base / "frozen.json").exists() or (base / "test.jsonl").exists():
        raise FileExistsError("Rodada fechada ou teste já aberto")
    rows = lambda split: [json.loads(line) for line in (base / f"{split}.jsonl").read_text().splitlines()]
    train, validation = rows("train"), rows("validation")
    if {r["dataset_id"] for r in train} & {r["dataset_id"] for r in validation}:
        raise ValueError("Arquivo presente nos dois conjuntos")
    model = ExtraTreesRegressor(n_estimators=128,min_samples_leaf=2,random_state=337,n_jobs=1)
    x = [vector(r["description"],r["strategy"]) for r in train]
    y = [[r["rss_mb"],r["total_seconds"]] for r in train]
    model.fit(x,np.log1p(y))
    predicted = np.expm1(model.predict([vector(r["description"],r["strategy"]) for r in validation]))
    margin = max(1.05,float(np.quantile([r["rss_mb"]/max(1,p[0]) for r,p in zip(validation,predicted)],.9)))
    trees = []
    for estimator in model.estimators_:
        t = estimator.tree_
        trees.append({"left":t.children_left.tolist(),"right":t.children_right.tolist(),
                      "feature":t.feature.tolist(),"threshold":t.threshold.tolist(),
                      "value":t.value[:,:,0].tolist()})
    package = {"format":SCHEMA,"rss_margin":margin,"trees":trees}
    for row in train + validation:
        v = vector(row["description"],row["strategy"])
        expected = np.expm1(model.predict([v])[0])
        if not all(math.isclose(a,float(b),rel_tol=1e-8,abs_tol=1e-8) for a,b in zip(infer(package,v),expected)):
            raise ValueError("Inferência leve divergente")
    (base / "model.json").write_text(json.dumps(package,separators=(',',':')))
    started = time.perf_counter()
    loaded = json.loads((base / "model.json").read_text())
    setup = time.perf_counter()-started
    groups = {}
    for row in validation:
        groups.setdefault((row["dataset_id"],row["description"]["passes"]),{})[row["strategy"]] = row
    comparisons = {}
    # As três metas e o limiar de promoção foram fixados no protocolo.
    for target in (24,64,128):
        total = setup
        baseline_total = 0
        successes = baseline_successes = 0
        for candidates in groups.values():
            meta = candidates["fused"]["description"]
            started = time.perf_counter()
            selected = candidate_decision(loaded,meta,target)["selected"]
            total += time.perf_counter()-started + candidates[selected]["total_seconds"]
            baseline_total += candidates["fused"]["total_seconds"]
            successes += candidates[selected]["rss_mb"] <= target
            baseline_successes += candidates["fused"]["rss_mb"] <= target
        comparisons[str(target)] = {"ml_seconds":total,"fused_seconds":baseline_total,
                                   "ml_targets_met":successes,"fused_targets_met":baseline_successes,
                                   "jobs":len(groups),"relative_gain":1-total/baseline_total}
    promoted = all(v["relative_gain"] >= .05 and v["ml_targets_met"] >= v["fused_targets_met"] for v in comparisons.values())
    policy = {"schema":SCHEMA,"ml_enabled":promoted,
              "reason":"promoted_on_validation" if promoted else "fused_baseline_not_beaten_on_validation",
              "promotion_rule":"at least 5% lower total time and no more RSS-target violations, at every validation target 24/64/128 MiB",
              "validation":comparisons,"setup_seconds":setup,"rss_margin":margin,
              "model_sha256":sha(base / "model.json"),
              "train_sha256":sha(base / "train.jsonl"),"validation_sha256":sha(base / "validation.jsonl"),
              "protocol_sha256":sha(base / "protocol.json"),"test_used":False}
    (base / "frozen.json").write_text(json.dumps(policy,indent=2))
    return policy
