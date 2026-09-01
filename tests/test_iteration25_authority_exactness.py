from copy import deepcopy

import pytest

from masck_one.authority import Authority, load_authority
from masck_one.iteration25_source_integrity import (
    Iteration25SourceIntegrityError,
    _repository_authority,
)


def _mutated_authority(mutator):
    current = load_authority()
    mutated = Authority(
        data=deepcopy(current.data),
        source=current.source,
        validation_report=current.validation_report,
    )
    mutator(mutated.data)
    return mutated


@pytest.mark.parametrize(
    "mutator",
    (
        lambda data: data["commercial"].__setitem__("paid_preorder_gate", 0),
        lambda data: data["safety"]["quick_release"].__setitem__("one_hand_wet_unpowered", 1),
        lambda data: data["actuation"].__setitem__("count", 4.0),
        lambda data: data["coordinate_system"]["origin"].__setitem__(0, -0.0),
    ),
)
def test_repository_authority_rejects_cross_type_and_signed_zero_aliases(mutator):
    with pytest.raises(Iteration25SourceIntegrityError):
        _repository_authority(_mutated_authority(mutator))


def test_repository_authority_rejects_same_value_hostile_string_subclass():
    class Alias(str):
        pass

    def mutate(data):
        data["project"]["authority_revision"] = Alias(data["project"]["authority_revision"])

    with pytest.raises(Iteration25SourceIntegrityError):
        _repository_authority(_mutated_authority(mutate))


def test_repository_authority_accepts_fresh_exact_repository_tree():
    current = load_authority()
    fresh = _repository_authority(current)
    assert fresh.data == current.data
    assert fresh.source == current.source
