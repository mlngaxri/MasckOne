from dataclasses import replace
import math

import pytest

from masck_one.actuation_sweep_contract import (
    ActuationDisplacementContract,
    ActuationSweepContractError,
    build_actuation_displacement_contract,
)
from masck_one.actuator_frames import build_actuator_frame_architecture
from masck_one.boundary_release import build_verified_interface_boundary_topology
from masck_one.interface_attachment import build_interface_attachment_architecture
from masck_one.model import build_model
from masck_one.structural_frame import build_structural_frame_topology


HUGE_POS = 10**10000
HUGE_NEG = -HUGE_POS


def _inputs():
    model = build_model()
    boundaries = build_verified_interface_boundary_topology(
        model.authority,
        model.facial_surface,
        model.coverage_mesh,
        model.compliant_interface_topology,
    )
    attachment = build_interface_attachment_architecture(model.authority, boundaries)
    frame = build_structural_frame_topology(model.authority, attachment)
    architecture = build_actuator_frame_architecture(model.authority, frame)
    return model.authority, frame, architecture


def test_authority_peak_to_peak_is_not_misread_as_peak_amplitude():
    authority, _, architecture = _inputs()
    contract = build_actuation_displacement_contract(authority, architecture)
    assert contract.displacement_pp_mm == 0.52
    assert contract.displacement_peak_from_neutral_mm == 0.26
    assert contract.neutral_relative_interval_mm == (-0.26, 0.26)
    assert contract.semantic == "SYMMETRIC_PEAK_TO_PEAK_ABOUT_NEUTRAL"
    assert contract.source_actuator_architecture_sha256 == architecture.architecture_sha256


def test_geometry_execution_remains_blocked_while_released_architecture_is_not_sweep_ready():
    authority, frame, architecture = _inputs()
    contract = build_actuation_displacement_contract(authority, architecture)
    with pytest.raises(ActuationSweepContractError, match="sweep geometry remains blocked"):
        contract.require_geometry_ready(authority=authority, architecture=architecture, structural_frame=frame)


def test_geometry_execution_rejects_stale_structural_frame_even_if_architecture_object_is_internally_sweep_ready():
    authority, frame, architecture = _inputs()
    contract = build_actuation_displacement_contract(authority, architecture)
    stale_frame = replace(frame, source_registered_mesh_sha256="a" * 64)
    with pytest.raises(ActuationSweepContractError, match="structural-frame topology"):
        contract.require_geometry_ready(authority=authority, architecture=architecture, structural_frame=stale_frame)


def test_geometry_execution_rejects_registered_mesh_provenance_mismatch():
    authority, frame, architecture = _inputs()
    contract = build_actuation_displacement_contract(authority, architecture)
    mismatched_architecture = replace(architecture, source_registered_mesh_sha256="b" * 64)
    rebound_contract = replace(contract, source_actuator_architecture_sha256=mismatched_architecture.architecture_sha256)
    with pytest.raises(ActuationSweepContractError, match="registered-mesh provenance is stale"):
        rebound_contract.require_geometry_ready(
            authority=authority,
            architecture=mismatched_architecture,
            structural_frame=frame,
        )


def test_valid_but_stale_actuator_architecture_identity_is_rejected():
    authority, _, architecture = _inputs()
    contract = build_actuation_displacement_contract(authority, architecture)
    stale = replace(contract, source_actuator_architecture_sha256="a" * 64)
    with pytest.raises(ActuationSweepContractError, match="stale for the current actuator-frame architecture"):
        stale.validate_current_sources(authority=authority, architecture=architecture)


def test_peak_vs_peak_to_peak_semantic_corruption_is_rejected():
    authority, _, architecture = _inputs()
    contract = build_actuation_displacement_contract(authority, architecture)
    with pytest.raises(ActuationSweepContractError, match="exactly half"):
        replace(contract, displacement_peak_from_neutral_mm=contract.displacement_pp_mm)
    with pytest.raises(ActuationSweepContractError, match="peak-to-peak authority meaning"):
        replace(contract, semantic="PEAK_FROM_NEUTRAL")


def test_digital_motion_contract_cannot_claim_physical_validation():
    authority, _, architecture = _inputs()
    contract = build_actuation_displacement_contract(authority, architecture)
    with pytest.raises(ActuationSweepContractError, match="cannot be promoted"):
        replace(contract, physical_validation_eligible=True)


def test_contract_identity_changes_with_motion_or_architecture_source():
    authority, _, architecture = _inputs()
    contract = build_actuation_displacement_contract(authority, architecture)
    assert contract.contract_sha256 != replace(
        contract,
        source_actuator_architecture_sha256="b" * 64,
    ).contract_sha256
    changed = ActuationDisplacementContract(
        contract.source_actuator_architecture_sha256,
        contract.source_authority_revision,
        0.6,
        0.3,
        contract.semantic,
        False,
    )
    assert contract.contract_sha256 != changed.contract_sha256


def test_noncanonical_and_boolean_inputs_fail_closed():
    authority, _, architecture = _inputs()
    contract = build_actuation_displacement_contract(authority, architecture)
    with pytest.raises(ActuationSweepContractError, match="canonical SHA-256"):
        replace(contract, source_actuator_architecture_sha256=contract.source_actuator_architecture_sha256.upper())
    with pytest.raises(ActuationSweepContractError, match="positive finite"):
        replace(contract, displacement_pp_mm=True)
    with pytest.raises(ActuationSweepContractError, match="cannot be promoted"):
        replace(contract, physical_validation_eligible=0)


def test_hostile_string_subclasses_fail_closed_at_all_identity_boundaries():
    authority, _, architecture = _inputs()
    contract = build_actuation_displacement_contract(authority, architecture)

    class LyingStr(str):
        def __eq__(self, other):
            return True

    with pytest.raises(ActuationSweepContractError, match="canonical SHA-256"):
        replace(contract, source_actuator_architecture_sha256=LyingStr(contract.source_actuator_architecture_sha256))
    with pytest.raises(ActuationSweepContractError, match="Authority revision"):
        replace(contract, source_authority_revision=LyingStr(contract.source_authority_revision))
    with pytest.raises(ActuationSweepContractError, match="peak-to-peak authority meaning"):
        replace(contract, semantic=LyingStr("SYMMETRIC_PEAK_TO_PEAK_ABOUT_NEUTRAL"))


@pytest.mark.parametrize(
    "huge",
    [pytest.param(HUGE_POS, id="huge-positive"), pytest.param(HUGE_NEG, id="huge-negative")],
)
def test_unrepresentable_integer_displacements_fail_closed_without_raw_overflow(huge):
    authority, _, architecture = _inputs()
    contract = build_actuation_displacement_contract(authority, architecture)
    with pytest.raises(ActuationSweepContractError, match="representable"):
        replace(contract, displacement_pp_mm=huge)
    with pytest.raises(ActuationSweepContractError, match="representable"):
        replace(contract, displacement_peak_from_neutral_mm=huge)


def test_large_representable_exact_integer_remains_supported():
    value = 10**300
    contract = ActuationDisplacementContract(
        "a" * 64,
        "TEST_REVISION",
        value,
        value // 2,
        "SYMMETRIC_PEAK_TO_PEAK_ABOUT_NEUTRAL",
        False,
    )
    assert math.isfinite(contract.displacement_pp_mm)
    assert contract.displacement_pp_mm == float(value)
    assert contract.displacement_peak_from_neutral_mm == float(value // 2)


def _assert_corruption_rejected_everywhere(contract, authority, architecture, frame, match):
    with pytest.raises(ActuationSweepContractError, match=match):
        contract.validate_invariants()
    with pytest.raises(ActuationSweepContractError, match=match):
        contract.manifest()
    with pytest.raises(ActuationSweepContractError, match=match):
        _ = contract.contract_sha256
    with pytest.raises(ActuationSweepContractError, match=match):
        contract.validate_current_sources(authority=authority, architecture=architecture)
    with pytest.raises(ActuationSweepContractError, match=match):
        contract.require_geometry_ready(authority=authority, architecture=architecture, structural_frame=frame)


def test_postconstruction_physical_evidence_promotion_cannot_hash_export_or_source_validate():
    authority, frame, architecture = _inputs()
    contract = build_actuation_displacement_contract(authority, architecture)
    object.__setattr__(contract, "physical_validation_eligible", True)
    _assert_corruption_rejected_everywhere(contract, authority, architecture, frame, "cannot be promoted")


def test_postconstruction_semantic_and_identity_alias_corruption_cannot_escape():
    authority, frame, architecture = _inputs()

    class LyingStr(str):
        def __eq__(self, other):
            return True

    semantic_corrupt = build_actuation_displacement_contract(authority, architecture)
    object.__setattr__(semantic_corrupt, "semantic", LyingStr("SYMMETRIC_PEAK_TO_PEAK_ABOUT_NEUTRAL"))
    _assert_corruption_rejected_everywhere(
        semantic_corrupt,
        authority,
        architecture,
        frame,
        "peak-to-peak authority meaning",
    )

    sha_corrupt = build_actuation_displacement_contract(authority, architecture)
    object.__setattr__(
        sha_corrupt,
        "source_actuator_architecture_sha256",
        LyingStr(sha_corrupt.source_actuator_architecture_sha256),
    )
    _assert_corruption_rejected_everywhere(sha_corrupt, authority, architecture, frame, "canonical SHA-256")


def test_postconstruction_displacement_value_and_type_corruption_cannot_escape():
    authority, frame, architecture = _inputs()
    inconsistent = build_actuation_displacement_contract(authority, architecture)
    object.__setattr__(inconsistent, "displacement_peak_from_neutral_mm", inconsistent.displacement_pp_mm)
    _assert_corruption_rejected_everywhere(inconsistent, authority, architecture, frame, "exactly half")

    malformed = build_actuation_displacement_contract(authority, architecture)
    object.__setattr__(malformed, "displacement_pp_mm", "0.52")
    _assert_corruption_rejected_everywhere(malformed, authority, architecture, frame, "canonical float")
