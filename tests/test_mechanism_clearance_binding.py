import hashlib
import json
import pytest

from masck_one.mechanism_clearance_binding import CollisionClearanceBinding
from masck_one.mechanism_tolerance import ClearanceStack, ScalarTolerance

MOVING = "a" * 64
PROTECTED = "b" * 64
FRAME = "ROOT_WORLD"


class LyingStr(str):
    """Adversarial string whose comparisons falsely claim identity."""
    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False

    __hash__ = str.__hash__


def composite(moving=MOVING, protected=PROTECTED, frame=FRAME):
    payload = {
        "coordinate_frame_id": frame,
        "moving_geometry_sha256": moving,
        "protected_geometry_sha256": protected,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii")).hexdigest()


def binding(*, moving=MOVING, protected=PROTECTED, frame=FRAME, stack_sha=None):
    sha = composite(moving, protected, frame) if stack_sha is None else stack_sha
    stack = ClearanceStack(
        stack_id="ACTUATOR_EYE_CLEARANCE",
        coordinate_frame_id=frame,
        source_geometry_sha256=sha,
        nominal_clearance_mm=1.0,
        contributions=(("MOUNT_DATUM", ScalarTolerance(0.0, 0.1, 0.2), -1),),
    )
    return CollisionClearanceBinding(
        binding_id="ZONE_A_EYE_CLEARANCE",
        coordinate_frame_id=frame,
        moving_geometry_sha256=moving,
        protected_geometry_sha256=protected,
        clearance_stack=stack,
    )


def test_exact_pair_executes_and_returns_conservative_positive_clearance():
    b = binding()
    got = b.assert_positive_clearance(
        current_moving_geometry_sha256=MOVING,
        current_protected_geometry_sha256=PROTECTED,
        coordinate_frame_id=FRAME,
    )
    assert 0.0 < got < 0.8


def test_stack_cannot_bind_only_one_collision_participant():
    with pytest.raises(ValueError, match="exact collision geometry pair"):
        binding(stack_sha=MOVING)


def test_stale_moving_and_protected_geometry_fail_independently():
    b = binding()
    with pytest.raises(RuntimeError, match="stale moving"):
        b.assert_positive_clearance(current_moving_geometry_sha256="c" * 64, current_protected_geometry_sha256=PROTECTED, coordinate_frame_id=FRAME)
    with pytest.raises(RuntimeError, match="stale protected"):
        b.assert_positive_clearance(current_moving_geometry_sha256=MOVING, current_protected_geometry_sha256="c" * 64, coordinate_frame_id=FRAME)


def test_local_world_mismatch_fails_before_clearance_execution():
    b = binding()
    with pytest.raises(RuntimeError, match="frame"):
        b.assert_positive_clearance(current_moving_geometry_sha256=MOVING, current_protected_geometry_sha256=PROTECTED, coordinate_frame_id="ACTUATOR_LOCAL")


def test_stack_frame_mismatch_is_rejected_at_construction():
    stack = ClearanceStack(
        stack_id="CLEARANCE",
        coordinate_frame_id="ACTUATOR_LOCAL",
        source_geometry_sha256=composite(),
        nominal_clearance_mm=1.0,
        contributions=(),
    )
    with pytest.raises(ValueError, match="stack frame"):
        CollisionClearanceBinding("BINDING", FRAME, MOVING, PROTECTED, stack)


def test_noncanonical_sha_and_identity_aliases_fail_closed():
    with pytest.raises(ValueError):
        binding(moving="A" * 64)
    b = binding()
    with pytest.raises(ValueError):
        b.assert_positive_clearance(current_moving_geometry_sha256=MOVING, current_protected_geometry_sha256=PROTECTED, coordinate_frame_id=" ROOT_WORLD")


def test_lying_string_subclasses_cannot_bypass_provenance_or_frame_gates():
    b = binding()
    with pytest.raises(ValueError, match="exact built-in"):
        b.assert_positive_clearance(
            current_moving_geometry_sha256=LyingStr("c" * 64),
            current_protected_geometry_sha256=PROTECTED,
            coordinate_frame_id=FRAME,
        )
    with pytest.raises(ValueError, match="exact built-in"):
        b.assert_positive_clearance(
            current_moving_geometry_sha256=MOVING,
            current_protected_geometry_sha256=LyingStr("c" * 64),
            coordinate_frame_id=FRAME,
        )
    with pytest.raises(ValueError, match="exact built-in"):
        b.assert_positive_clearance(
            current_moving_geometry_sha256=MOVING,
            current_protected_geometry_sha256=PROTECTED,
            coordinate_frame_id=LyingStr("ACTUATOR_LOCAL"),
        )


def test_lying_string_subclasses_are_rejected_at_construction_boundaries():
    with pytest.raises(ValueError, match="exact built-in"):
        binding(moving=LyingStr(MOVING))
    with pytest.raises(ValueError, match="exact built-in"):
        binding(protected=LyingStr(PROTECTED))
    with pytest.raises(ValueError, match="exact built-in"):
        CollisionClearanceBinding(LyingStr("BINDING"), FRAME, MOVING, PROTECTED, binding().clearance_stack)


def test_structural_lookalike_clearance_stack_is_rejected():
    class Fake:
        coordinate_frame_id = FRAME
        source_geometry_sha256 = composite()
    with pytest.raises(TypeError, match="exact ClearanceStack"):
        CollisionClearanceBinding("BINDING", FRAME, MOVING, PROTECTED, Fake())


def test_provenance_changes_if_either_collision_participant_changes():
    a = binding()
    b = binding(moving="c" * 64)
    c = binding(protected="d" * 64)
    assert len({a.provenance_sha256, b.provenance_sha256, c.provenance_sha256}) == 3
