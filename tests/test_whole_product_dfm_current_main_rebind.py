import importlib

from masck_one.whole_product_dfm import (
    MATURITY_RELEASED_TOPOLOGY,
    SOURCE_MAIN_SHA,
    build_whole_product_dfm_architecture,
)


def test_current_main_rebind_consumes_released_waste_realization_without_overpromotion():
    assert SOURCE_MAIN_SHA == "628ec5f5766937433b1bdf8f30edc372924cf41e"
    importlib.import_module("masck_one.realized_waste_backbone")

    architecture = build_whole_product_dfm_architecture()
    by_id = {part.part_id: part for part in architecture.parts}
    route = by_id["MASCK_ONE-DFM-WASTE-BACKBONE-ROUTE-SET"]

    assert route.maturity == MATURITY_RELEASED_TOPOLOGY
    assert route.source_ref == "src/masck_one/realized_waste_backbone.py:centerline-geometry"
    assert route.part_id not in architecture.unresolved_required_part_ids
    assert architecture.physical_validation_eligible is False
    assert architecture.production_validation_eligible is False
