from masck_one.mechanical_package_ingestion import build_mechanical_package_integration
from masck_one.model import build_model
from masck_one.right_quick_release_assembly import build_right_quick_release_assembly


def test_cell1_integration_package_digests_equal_actual_cell3_source_chain():
    model = build_model()
    source = build_right_quick_release_assembly(model=model)
    integration = build_mechanical_package_integration()

    assert integration.source_assembly_package_sha256 == source.package_sha256
    assert integration.source_reset_package_sha256 == source.reset.package_sha256
    assert integration.source_continuous_sweep_package_sha256 == source.continuous.package_sha256


def test_cell1_static_package_consumes_split_guide_successor_not_source_capsule():
    integration = build_mechanical_package_integration()
    source_ids = {record.source_id for record in integration.static_solids}

    assert "RIGHT_LATCH_GUIDE_LOWER_BODY" in source_ids
    assert "RIGHT_LATCH_GUIDE_UPPER_CLOSURE" in source_ids
    assert "RIGHT_LATCH_GUIDE_CAPSULE" not in source_ids
