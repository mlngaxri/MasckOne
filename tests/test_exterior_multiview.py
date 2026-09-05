from masck_one.exterior_multiview import SECTION_SPECS, VIEW_PROJECTIONS


def test_multiview_registry_covers_required_aesthetic_baseline_views():
    view_ids = tuple(view_id for view_id, _ in VIEW_PROJECTIONS)
    assert view_ids == (
        "front",
        "front_three_quarter_right",
        "front_three_quarter_left",
        "right",
        "left",
        "rear",
        "top",
        "bottom",
    )
    assert tuple(view_id for view_id, _, _ in SECTION_SPECS) == (
        "section_yz_center",
        "section_xz_center",
    )


def test_multiview_projection_vectors_are_nonzero():
    for _, projection in VIEW_PROJECTIONS:
        assert any(component != 0.0 for component in projection)
    for _, _, projection in SECTION_SPECS:
        assert any(component != 0.0 for component in projection)
