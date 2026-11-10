import json
import pytest

def test_freeze_protects_model(tmp_path):
    from sentinela.learning import frozen
    (tmp_path / "models").mkdir()
    (tmp_path / "models/model.joblib").write_bytes(b"altered")
    (tmp_path / "models/frozen.json").write_text(json.dumps({"model_sha256": "invalid"}))
    with pytest.raises(ValueError, match="Modelo alterado"):
        frozen(tmp_path)
