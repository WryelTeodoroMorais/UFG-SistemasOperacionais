"""Geração das tarefas ativas, organizada pela partição de dados."""
from .test import (
    TEST_FAMILIES,
    SAMPLES_PER_FAMILY as TEST_SAMPLE_COUNTS,
    make_task as make_test_task,
)
from .train import (
    TRAIN_FAMILIES,
    SAMPLES_PER_FAMILY as TRAIN_SAMPLE_COUNTS,
    make_task as make_train_task,
)
from .validation import (
    VALIDATION_FAMILIES,
    SAMPLES_PER_FAMILY as VALIDATION_SAMPLE_COUNTS,
    make_task as make_validation_task,
)

FAMILIES = {
    "train": TRAIN_FAMILIES,
    "validation": VALIDATION_FAMILIES,
    "test": TEST_FAMILIES,
}
SAMPLES_PER_FAMILY = {
    **TRAIN_SAMPLE_COUNTS,
    **VALIDATION_SAMPLE_COUNTS,
    **TEST_SAMPLE_COUNTS,
}
_GENERATORS = {
    "train": make_train_task,
    "validation": make_validation_task,
    "test": make_test_task,
}
_FAMILY_SPLIT = {
    family: split for split, families in FAMILIES.items() for family in families
}


def make_task(family: str, index: int) -> dict:
    split = _FAMILY_SPLIT.get(family)
    if split is None:
        raise ValueError(f"Família de tarefa desconhecida: {family}")
    return _GENERATORS[split](family, index)


def tasks(split: str):
    if split not in FAMILIES:
        raise ValueError(f"Partição desconhecida: {split}")
    for family in FAMILIES[split]:
        for index in range(SAMPLES_PER_FAMILY[family]):
            yield make_task(family, index)
