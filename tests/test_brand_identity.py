from __future__ import annotations

import json
import re

from masck_one.brand_identity import build_brand_identity_manifest, load_brand_identity


def test_brand_identity_contract_loads_and_keeps_parent_product_split() -> None:
    identity = load_brand_identity()
    assert identity.master_brand == "MASCK"
    assert identity.product_name == "Masck One"
    assert identity.master_mark == "M_CUT"
    assert identity.product_designation == "M/1"
    assert identity.master_mark != identity.product_designation


def test_primary_control_uses_master_mark_not_model_badge() -> None:
    identity = load_brand_identity()
    control = identity.data["interaction_signature"]["primary_control"]
    assert control["mark"] == "M_CUT"
    assert control["product_designation_on_primary_control"] is False
    assert control["candidate_mechanical_reference"]["evidence_status"] == "PROVISIONAL_DESIGN_REFERENCE_ONLY"


def test_surface_language_rejects_goggle_vr_and_ppe_drift() -> None:
    identity = load_brand_identity()
    prohibited = set(identity.data["surface_language"]["prohibited"])
    assert {
        "goggle_eye_rings",
        "vr_headset",
        "respirator",
        "medical_ppe",
        "tactical_panels",
        "helmet",
    }.issubset(prohibited)


def test_primary_cmf_tokens_are_valid_hex_and_named() -> None:
    identity = load_brand_identity()
    palette = identity.data["cmf"]["palette"]
    assert set(palette) == {
        "shell",
        "primary_control",
        "facial_interface",
        "recessive_mechanics",
        "optical_inlay",
    }
    for token in palette.values():
        assert token["name"]
        assert re.fullmatch(r"#[0-9A-Fa-f]{6}", token["hex"])


def test_button_travel_reference_remains_ordered_and_hard_stop_is_abnormal() -> None:
    identity = load_brand_identity()
    reference = identity.data["interaction_signature"]["primary_control"]["candidate_mechanical_reference"]
    ordered = [
        reference["force_peak_travel_mm"],
        reference["first_landing_start_mm"],
        reference["second_landing_start_mm"],
        reference["nominal_bottom_travel_mm"],
        reference["hard_stop_travel_mm"],
    ]
    assert ordered == sorted(ordered)
    assert len(set(ordered)) == len(ordered)
    assert reference["hard_stop_travel_mm"] > reference["nominal_bottom_travel_mm"]


def test_manifest_is_deterministic_and_explicit_about_provisional_evidence() -> None:
    first = build_brand_identity_manifest()
    second = build_brand_identity_manifest()
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first["canonical_content_sha256"] == second["canonical_content_sha256"]
    assert first["master_mark_status"] == "PROVISIONAL_MASTER_MARK_CANDIDATE"
    assert any("physical prototype validation" in item for item in first["evidence_boundary"])
