import math
import pytest
from policy import Budget, authorize


def test_recommendation_cannot_enlarge_authority():
    budget = authorize({"memory_mb": 10**9, "wall_seconds": 10**9,
                        "read_input": True, "write_output": True},
                       Budget(memory_mb=64, wall_seconds=1, read_input=False, write_output=False))
    assert budget.memory_mb == 64 and budget.wall_seconds == 1
    assert not budget.read_input and not budget.write_output


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, 0])
def test_invalid_model_values_fail_closed(value):
    with pytest.raises(ValueError):
        authorize({"memory_mb": value}, Budget())


def test_unknown_capability_rejected():
    with pytest.raises(ValueError):
        authorize({"network": True}, Budget())


def test_string_cannot_be_permission():
    with pytest.raises(ValueError):
        authorize({"read_input": "False"}, Budget())
