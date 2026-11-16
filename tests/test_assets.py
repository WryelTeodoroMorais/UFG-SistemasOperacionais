from pathlib import Path

from sentinela.assets import asset_path


def test_uses_bundled_assets_when_project_root_has_none(tmp_path):
    for relative in (
        "data/train.jsonl",
        "data/validation.jsonl",
        "models/model.joblib",
        "models/frozen.json",
        "examples/resumir_jsonl.py",
    ):
        assert asset_path(tmp_path, relative).is_file()


def test_project_assets_take_precedence_over_bundled_assets(tmp_path):
    local = tmp_path / "data/train.jsonl"
    local.parent.mkdir(parents=True)
    local.write_text("local\n")

    assert asset_path(tmp_path, "data/train.jsonl") == local
    assert asset_path(tmp_path, "data/train.jsonl").read_text() == "local\n"


def test_asset_path_rejects_paths_outside_project():
    try:
        asset_path(Path.cwd(), "../outside")
    except ValueError as exc:
        assert "relativo" in str(exc)
    else:
        raise AssertionError("path traversal should be rejected")
