import cadquery as cq
import pytest

from masck_one.release_package import ExportValidationError
from masck_one.step_integrity import verify_step_geometry


@pytest.mark.parametrize('change', ['missing', 'extra', 'translated', 'cavity_moved', 'tiny_hole'])
def test_step_material_tampering_fails_even_with_equal_volume_and_outer_bounds(tmp_path, change):
    block = cq.Workplane('XY').box(10, 10, 10).val()
    hole = cq.Workplane('XY').box(1, 1, 1).val()
    source = block.cut(hole)
    if change == 'missing':
        source = cq.Compound.makeCompound([source, block.translate((20, 0, 0))])
        target = block.cut(hole)
    elif change == 'extra':
        target = cq.Compound.makeCompound([source, block.translate((20, 0, 0))])
    elif change == 'translated':
        target = source.translate((0, 0, 0.001))
    elif change == 'cavity_moved':
        target = block.cut(hole.translate((0.1, 0, 0)))
    else:
        # 0.000125 mm3 is BELOW the per-solid volume allowance. The material
        # difference gate must still reject a real internal change this small.
        tiny = cq.Workplane('XY').box(0.05, 0.05, 0.05).translate((2, 0, 0)).val()
        target = source.cut(tiny)
    path = tmp_path / 'tampered.step'
    cq.exporters.export(target, str(path))
    with pytest.raises(ExportValidationError):
        verify_step_geometry(source, path)


def test_overlapping_compound_preserves_membership_without_boolean_fusion(tmp_path):
    box = cq.Workplane('XY').box(3, 4, 5).val()
    source = cq.Compound.makeCompound([box, box.translate((1, 0, 0))])
    path = tmp_path / 'overlap.step'
    cq.exporters.export(source, str(path))
    result = verify_step_geometry(source, path)
    assert result['solid_count'] == 2
    assert result['source_volume_mm3'] == pytest.approx(120)
    assert result['step_volume_mm3'] == pytest.approx(120)
