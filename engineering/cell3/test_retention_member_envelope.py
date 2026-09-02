from engineering.cell3.retention_member_envelope import MemberEnvelope, evaluate_member_envelopes
from engineering.cell3.retention_package_contract import AABB, RetentionDatums


def datums():
    return RetentionDatums((-40,0,0),(40,0,0),(-45,20,20),(45,20,20),(0,20,65),(0,45,20))


def envelopes(radius=2.0, positional=0.5, manufacturing=0.5):
    names=("left_yoke_link","right_yoke_link","crown_left","crown_right","occipital_left","occipital_right")
    return {n: MemberEnvelope(radius,positional,manufacturing) for n in names}


def test_clear_geometry_passes():
    result=evaluate_member_envelopes(datums(),envelopes(),{"electronics":AABB((-10,-10,-10),(10,10,10))},minimum_residual_clearance_mm=1.0)
    assert result.passed


def test_centerline_clear_but_physical_envelope_fails():
    # Left yoke link lies near x=-40..-45. The keepout is centerline-clear,
    # but the released member envelope plus tolerance consumes that gap.
    box=AABB((-38,5,5),(-36,15,15))
    result=evaluate_member_envelopes(datums(),envelopes(radius=3.0,positional=1.0,manufacturing=1.0),{"fluid":box},minimum_residual_clearance_mm=0.5)
    assert not result.passed
    assert any("left_yoke_link:envelope_keepout:fluid" == f for f in result.failures)


def test_continuous_segment_crossing_is_detected_without_sampling():
    # Thin box intersects crown-left between arbitrary sample locations.
    box=AABB((-23.01,19.99,41.99),(-22.99,20.01,42.01))
    result=evaluate_member_envelopes(datums(),envelopes(radius=0.0,positional=0.0,manufacturing=0.0),{"thin":box},minimum_residual_clearance_mm=0.001)
    assert not result.passed


def test_missing_member_envelope_fails_closed():
    env=envelopes(); env.pop("crown_left")
    try:
        evaluate_member_envelopes(datums(),env,{},minimum_residual_clearance_mm=0.0)
        assert False
    except ValueError:
        pass


def test_negative_tolerance_rejected():
    env=envelopes(); env["crown_left"]=MemberEnvelope(2.0,-0.1,0.5)
    try:
        evaluate_member_envelopes(datums(),env,{},minimum_residual_clearance_mm=0.0)
        assert False
    except ValueError:
        pass
