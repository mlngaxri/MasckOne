"""Per-solid STEP fidelity, separate from product or manufacturing tolerances."""
from __future__ import annotations

import math
from pathlib import Path
import cadquery as cq

from .release_package import ExportValidationError

INTEGRATION_TOLERANCE = 1e-12
# CQ 2.8/OCP 7.9.3.1: largest measured per-solid read-back delta is
# 0.0001283191533 mm3 in the trimmed membrane. No relative allowance that
# grows with part size. Independent material-difference checks remain tighter.
STEP_SOLID_VOLUME_LIMIT_MM3 = 2e-4
STEP_BOUND_LIMIT_MM = 2e-6
STEP_MATERIAL_DIFFERENCE_LIMIT_MM3 = 1e-7


def solid_volume(shape: cq.Shape) -> float:
    return math.fsum(s.Volume(INTEGRATION_TOLERANCE) for s in shape.Solids())


def _bounds(shape: cq.Shape) -> tuple[float, ...]:
    box = shape.BoundingBox()
    return tuple(float(getattr(box, k)) for k in ('xmin', 'xmax', 'ymin', 'ymax', 'zmin', 'zmax'))


def verify_step_geometry(original: cq.Shape, path: str | Path) -> dict:
    """Compare the solid multiset, including position and material occupancy.

    Never use Compound.Volume() as the sum-of-components invariant: OCC's
    integration reference changes with compound grouping. No healing is applied.
    """
    imported = cq.importers.importStep(str(path)).val()
    before = sorted(original.Solids(), key=_bounds)
    after = sorted(imported.Solids(), key=_bounds)
    if not before or len(before) != len(after):
        raise ExportValidationError(f'{path}: STEP solid membership changed')
    if not original.isValid() or not imported.isValid():
        raise ExportValidationError(f'{path}: invalid STEP geometry')
    rows = []
    for index, (source, target) in enumerate(zip(before, after)):
        a, b = source.Volume(INTEGRATION_TOLERANCE), target.Volume(INTEGRATION_TOLERANCE)
        bound_delta = max(abs(x-y) for x, y in zip(_bounds(source), _bounds(target)))
        if not source.isValid() or not target.isValid() or not all(math.isfinite(v) and v > 0 for v in (a, b)):
            raise ExportValidationError(f'{path}: invalid STEP solid {index}')
        if not math.isfinite(bound_delta) or bound_delta > STEP_BOUND_LIMIT_MM:
            raise ExportValidationError(f'{path}: STEP position/bounds changed at solid {index}')
        if abs(b-a) > STEP_SOLID_VOLUME_LIMIT_MM3:
            raise ExportValidationError(f'{path}: STEP volume changed at solid {index}')
        removed = solid_volume(source.cut(target))
        added = solid_volume(target.cut(source))
        if any(not math.isfinite(v) or abs(v) > STEP_MATERIAL_DIFFERENCE_LIMIT_MM3 for v in (removed, added)):
            raise ExportValidationError(f'{path}: STEP material occupancy changed at solid {index}')
        rows.append(dict(solid_index=index, source_volume_mm3=a, step_volume_mm3=b,
                         volume_delta_mm3=b-a, max_bound_delta_mm=bound_delta,
                         removed_material_mm3=removed, added_material_mm3=added))
    return dict(status='PASS', method='PER_SOLID_ADAPTIVE_VOLUME_BOUNDS_AND_BIDIRECTIONAL_MATERIAL_DIFFERENCE',
                solid_count=len(rows), source_volume_mm3=math.fsum(r['source_volume_mm3'] for r in rows),
                step_volume_mm3=math.fsum(r['step_volume_mm3'] for r in rows),
                integration_tolerance=INTEGRATION_TOLERANCE,
                per_solid_volume_limit_mm3=STEP_SOLID_VOLUME_LIMIT_MM3,
                bound_limit_mm=STEP_BOUND_LIMIT_MM,
                material_difference_limit_mm3=STEP_MATERIAL_DIFFERENCE_LIMIT_MM3,
                solids=rows)
