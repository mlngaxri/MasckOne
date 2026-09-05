import json

from masck_one.export import _realized_waste_backbone_manifest
from masck_one.realized_waste_backbone_release import build_current_waste_routing_sources


def test_deterministic_release_artifact_emits_current_waste_backbone_geometry(monkeypatch):
    sources = build_current_waste_routing_sources()
    from masck_one import realized_waste_backbone_release as release_module

    # Reconstruct the current repository source graph once, then exercise the release
    # serializer twice against that exact accepted graph. Trusted release-source
    # reconstruction is independently covered by the dedicated release tests.
    monkeypatch.setattr(
        release_module,
        "build_current_waste_routing_sources",
        lambda: sources,
    )
    first = _realized_waste_backbone_manifest()
    second = _realized_waste_backbone_manifest()

    assert json.dumps(first, sort_keys=True, allow_nan=False) == json.dumps(
        second,
        sort_keys=True,
        allow_nan=False,
    )
    assert (
        first["release"]["source_waste_pump_architecture_sha256"]
        == sources.architecture.architecture_sha256
    )
    assert first["release"]["release_state"] == "PROVISIONAL_DIGITAL_GEOMETRY_VALIDATION_GATED"

    realized = tuple(
        (
            route["segment_id"],
            route["stage"],
            route["fluid_identity"],
            route["source_interface_id"],
            route["target_interface_id"],
        )
        for route in first["routes"]
    )
    current = tuple(
        (
            route.route_id,
            route.stage,
            route.phase_semantics,
            route.source_interface_id,
            route.target_interface_id,
        )
        for route in sources.architecture.routes
    )
    assert realized == current
    assert len(first["routes"]) == 3
    assert first["total_geometric_dead_volume_mL"] > 0.0
