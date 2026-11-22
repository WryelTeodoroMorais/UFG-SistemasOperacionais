from sentinela import evaluation


def test_evaluate_creates_report_root_when_missing(tmp_path, monkeypatch):
    root = tmp_path / "new" / "project"
    rows = [{
        "id": "example-000",
        "family": "example",
        "features": [0] * 9,
        "input_bytes": 0,
        "capabilities": [False, False],
        "runs": [{"stdout": "ok\n", "outputs": {}}],
    }]
    monkeypatch.setattr(evaluation, "load", lambda _root, _split: rows)
    monkeypatch.setattr(
        evaluation,
        "frozen",
        lambda _root: ({"train_families": []}, {
            "margin": 1.0, "wall_margin": 1.0, "model_sha256": "model-hash",
        }),
    )
    monkeypatch.setattr(evaluation, "digest", lambda _path: "test-hash")
    monkeypatch.setattr(evaluation, "prediction_report", lambda _root, _split: {})
    monkeypatch.setattr(
        evaluation,
        "make_task",
        lambda _family, index: {"seed": index, "code": "print('ok')", "input_data": b""},
    )
    monkeypatch.setattr(
        evaluation,
        "recommend",
        lambda *_args: {
            "memory_mb": 64, "wall_seconds": 1.0,
            "read_input": False, "write_output": False,
        },
    )

    def fake_run(_code, _input_data, budget):
        return {
            "returncode": 0,
            "timed_out": False,
            "stdout": "ok\n",
            "outputs": {},
            "wall_seconds": 0.05,
            "budget": budget.to_dict(),
        }

    monkeypatch.setattr(evaluation, "run", fake_run)

    report = evaluation.evaluate(root, "test")

    assert report["methods"]["supervised"]["successes"] == 1
    assert (root / "reports" / "test.json").is_file()
