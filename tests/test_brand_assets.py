from pathlib import Path

from masck_one.brand_identity import load_brand_identity


ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "brand" / "assets" / "masck_m_cut_candidate.svg"
PRODUCT = ROOT / "brand" / "assets" / "masck_one_m1_candidate.svg"


def test_master_mark_is_a_negative_cut_not_a_hidden_product_number():
    identity = load_brand_identity()
    svg = MASTER.read_text(encoding="utf-8")

    assert identity.master_mark == "M_CUT"
    assert identity.product_designation == "M/1"
    assert "PROVISIONAL" in identity.data["master_mark"]["status"]
    assert "M32 22v22" not in svg
    assert "<text" not in svg
    assert svg.count("<path") == 2
    assert "currentColor" in svg


def test_product_designation_reuses_master_geometry_without_polluting_master_asset():
    master = MASTER.read_text(encoding="utf-8")
    product = PRODUCT.read_text(encoding="utf-8")

    left = 'd="M10 48V19c0-2.8 3.4-4.2 5.4-2.2L29 31.2"'
    right = 'd="M35 31.2l13.6-14.4c2-2 5.4-.6 5.4 2.2v29"'
    slash = 'd="M68 48L82 16"'
    one = 'd="M94 22l6-5v31"'

    for fragment in (left, right):
        assert fragment in master
        assert fragment in product
    assert slash not in master
    assert one not in master
    assert slash in product
    assert one in product
    assert "<text" not in product
