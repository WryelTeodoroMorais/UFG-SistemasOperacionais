import copy
import json

import pytest

from cli import main
from learning import FEATURES, load_model, predict, recommend_ml, train
from policy import Budget


@pytest.fixture
def dataset(tmp_path):
    # Rótulos artificiais usados apenas para testes do contrato, não benchmark.
    rows = []
    for index in range(8):
        rows.append({"code": f"x=bytearray({index + 1}*1024)\nprint(len(x))",
                     "input_text": "", "split": "train" if index < 6 else "test",
                     "measurements": [{"returncode": 0, "timed_out": False,
                                       "peak_vms_mb": 20 + index, "wall_seconds": .05 + index * .01}]})
    path = tmp_path / "data.json"
    path.write_text(json.dumps({"schema": "sentinela-measurements-v1", "tasks": rows}))
    return path


def test_test_labels_cannot_change_fitted_tree(dataset, tmp_path):
    first, second = tmp_path / "a.json", tmp_path / "b.json"
    train(dataset, first)
    data = json.loads(dataset.read_text())
    for row in data["tasks"]:
        if row["split"] == "test":
            row["measurements"][0]["peak_vms_mb"] *= 100
    dataset.write_text(json.dumps(data))
    train(dataset, second)
    a, b = load_model(first), load_model(second)
    assert a["nodes"] == b["nodes"]
    assert a["evaluation"]["test_mae"] != b["evaluation"]["test_mae"]


def test_model_predictions_remain_inside_authority(dataset, tmp_path):
    path = tmp_path / "model.json"
    train(dataset, path)
    result = recommend_ml("open('/input/data.txt').read()\nopen('/output/x', 'w').write('x')",
                          10, Budget(memory_mb=16, wall_seconds=.15, read_input=False, write_output=False), path)
    assert result["trained_model"]
    budget = result["authorized_budget"]
    assert budget["memory_mb"] == 16 and budget["wall_seconds"] == .15
    assert not budget["read_input"] and not budget["write_output"]


@pytest.mark.parametrize("failure", ["duplicate", "timeout", "nan", "empty_test"])
def test_invalid_training_data_rejected(dataset, tmp_path, failure):
    data = json.loads(dataset.read_text())
    if failure == "duplicate":
        data["tasks"][-1] = copy.deepcopy(data["tasks"][0])
        data["tasks"][-1]["split"] = "test"
    elif failure == "timeout":
        data["tasks"][0]["measurements"][0]["timed_out"] = True
    elif failure == "nan":
        data["tasks"][0]["measurements"][0]["peak_vms_mb"] = float("nan")
    else:
        for row in data["tasks"]:
            row["split"] = "train"
    dataset.write_text(json.dumps(data))
    target = tmp_path / "invalid.json"
    with pytest.raises(ValueError):
        train(dataset, target)
    assert not target.exists()


@pytest.mark.parametrize("failure", ["cycle", "nan", "features"])
def test_invalid_json_model_rejected(dataset, tmp_path, failure):
    path = tmp_path / "model.json"
    train(dataset, path)
    model = json.loads(path.read_text())
    if failure == "cycle":
        model["nodes"][0] = {"feature": 0, "threshold": 1, "left": 0, "right": 0}
    elif failure == "nan":
        model["nodes"] = [{"prediction": [float("nan"), 1]}]
    else:
        model["features"] = ["measured_memory"]
    path.write_text(json.dumps(model))
    with pytest.raises(ValueError):
        load_model(path)


def test_export_matches_sklearn(dataset, tmp_path):
    import numpy as np
    from sklearn.tree import DecisionTreeRegressor
    from features import extract
    from learning import read_dataset

    path = tmp_path / "model.json"
    train(dataset, path)
    model = load_model(path)
    _, rows = read_dataset(dataset)
    training = [r for r in rows if r["split"] == "train"]
    estimator = DecisionTreeRegressor(max_depth=4, min_samples_leaf=2, random_state=336)
    estimator.fit([[r["features"][name] for name in FEATURES] for r in training],
                  np.log1p([r["target"] for r in training]))
    for value in range(1, 20):
        features = extract(f"x=bytearray({value}*1024)\nprint(len(x))")
        expected = np.expm1(estimator.predict([[features[name] for name in FEATURES]]))[0]
        assert predict(model, features) == pytest.approx(expected)


def test_ml_requires_explicit_model(tmp_path, capsys):
    script = tmp_path / "task.py"
    script.write_text("print('ok')")
    assert main(["plan", str(script), "--method", "ml"]) == 2
    assert "exige --model" in capsys.readouterr().err


def test_evaluate_detects_incorrect_output(dataset, tmp_path, monkeypatch):
    from learning import evaluate
    import sandbox

    model = tmp_path / "model.json"
    train(dataset, model)

    def fake_run(code, text, budget):
        return {"returncode": 0, "timed_out": False, "stdout": "incorrect",
                "outputs": {}, "wall_seconds": .1, "budget": budget.to_dict()}

    monkeypatch.setattr(sandbox, "run", fake_run)
    data = json.loads(dataset.read_text())
    # Este caso deve ser rejeitado antes de executar: dataset mudou após treino.
    data["tasks"][0]["code"] += "\n# changed"
    dataset.write_text(json.dumps(data))
    output = tmp_path / "evaluation.json"
    with pytest.raises(ValueError, match="mesmo experimento"):
        evaluate(dataset, model, output)
    assert not output.exists()

    # Volta a treinar para vincular o hash, com stdout esperado explícito.
    for row in data["tasks"]:
        row["measurements"][0].update(stdout="correct", outputs={})
    dataset.write_text(json.dumps(data))
    model2 = tmp_path / "model2.json"
    train(dataset, model2)
    report = evaluate(dataset, model2, output)
    assert all(group["correct"] == 0 and group["tasks"] == 2 for group in report["summary"].values())


def test_ml_cli_plan(dataset, tmp_path, capsys):
    model = tmp_path / "model.json"
    train(dataset, model)
    script = tmp_path / "script.py"
    script.write_text("print('ok')")
    assert main(["plan", str(script), "--method", "ml", "--model", str(model)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["method"] == "ml" and result["trained_model"]
    assert not result["authorized_budget"]["read_input"]
    assert not result["authorized_budget"]["write_output"]
