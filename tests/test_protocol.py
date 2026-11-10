from pathlib import Path
import pytest
from sentinela.data import load, validate_split
from sentinela.features import FEATURE_NAMES, extract
from sentinela.tasks import FAMILIES, make_task


def test_families_are_disjoint():
    groups = list(map(set, FAMILIES.values()))
    assert all(not a & b for i, a in enumerate(groups) for b in groups[i+1:])


@pytest.mark.parametrize("split", ["train", "validation", "test"])
def test_load_reads_split(tmp_path, split):
    data = tmp_path / "data"
    data.mkdir()
    row = {"split": split}
    (data / f"{split}.jsonl").write_text(json.dumps(row) + "\n")
    assert load(tmp_path, split) == [row]


def test_unknown_split_rejected():
    with pytest.raises(ValueError, match="Partição desconhecida"):
        validate_split("unknown")


def test_features_only_use_preexecution_inputs():
    task = make_task("csv_sum", 0)
    f = extract(task["code"], len(task["input_data"]))
    assert len(f) == len(FEATURE_NAMES)
    assert all(isinstance(x, (int, float)) for x in f)
    assert not {"family", "split", "peak_rss_mb", "wall_seconds"} & set(FEATURE_NAMES)


def test_task_reproducible():
    assert make_task("normalize", 0) == make_task("normalize", 0)
