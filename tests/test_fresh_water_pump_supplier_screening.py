import math

from masck_one.realized_fresh_water_pump import (
    PACKAGE_ENVELOPE_XYZ_MM,
    REFERENCE_PACKAGE_STATUS,
    SUPPLIER_SCREENING_EVIDENCE_STATUS,
    SUPPLIER_SCREENING_RECORD_HASH_ROLE,
    SUPPLIER_SCREENING_RECORD_SHA256,
    SUPPLIER_SCREENING_REFERENCES,
    build_current_realized_fresh_water_pump,
)


def test_supplier_screening_record_is_exact_nonselection_evidence():
    assert len(SUPPLIER_SCREENING_REFERENCES) == 3
    assert len(SUPPLIER_SCREENING_RECORD_SHA256) == 64
    assert all(c in "0123456789abcdef" for c in SUPPLIER_SCREENING_RECORD_SHA256)
    assert SUPPLIER_SCREENING_RECORD_HASH_ROLE == (
        "HASH_OF_NORMALIZED_CELL4_DIMENSIONAL_SCREENING_RECORD_NOT_VENDOR_DOCUMENT_HASH"
    )
    assert SUPPLIER_SCREENING_EVIDENCE_STATUS == (
        "VERIFIED_OFFICIAL_BODY_DIMENSIONS_FOR_DIGITAL_SCREENING_ONLY_NOT_SUPPLIER_SELECTION"
    )
    assert all(
        item["selection_status"] == "SCREENING_REFERENCE_ONLY_NOT_SELECTED"
        for item in SUPPLIER_SCREENING_REFERENCES
    )


def test_family_bounding_envelope_contains_every_verified_reference_body_dimension():
    x, y, z = PACKAGE_ENVELOPE_XYZ_MM
    assert (x, y, z) == (30.0, 25.0, 8.2)
    for item in SUPPLIER_SCREENING_REFERENCES:
        sx, sy, sz = item["body_envelope_xyz_mm"]
        assert sx <= x
        assert sy <= y
        assert sz <= z


def test_realization_keeps_supplier_selection_fields_unset_and_records_screening_basis():
    realized = build_current_realized_fresh_water_pump()
    manifest = realized.manifest()

    assert realized.supplier_package_candidate_id is None
    assert realized.supplier_package_evidence_sha256 is None
    assert realized.supplier_screening_record_sha256 == SUPPLIER_SCREENING_RECORD_SHA256
    assert manifest["supplier_screening"]["selection_status"] == "NO_SUPPLIER_PACKAGE_SELECTED"
    assert manifest["supplier_screening"]["record_sha256"] == SUPPLIER_SCREENING_RECORD_SHA256
    assert manifest["supplier_screening"]["references"] == list(SUPPLIER_SCREENING_REFERENCES)
    assert manifest["reference_package"]["status"] == REFERENCE_PACKAGE_STATUS
    assert manifest["reference_package"]["construction_role"] == (
        "COMPONENTWISE_BOUND_OF_VERIFIED_REFERENCE_BODIES_NOT_DIMENSIONS_OF_ONE_ACTUAL_PUMP"
    )
    assert math.isclose(manifest["reference_package"]["geometric_envelope_volume_mm3"], 6150.0)
    assert manifest["physical_validation_eligible"] is False
