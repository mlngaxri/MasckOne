"""One bounded investigation of the existing eye-fillet B-rep failure."""
import json
from pathlib import Path
import sys

from masck_one import exterior_eye_roll as eye
from masck_one.model import build_model

output = Path("/tmp/masck-eye-diagnostic")
output.mkdir(exist_ok=True)
records = []

def snapshot(shape):
    bb = shape.BoundingBox()
    return {
        "valid": shape.isValid(), "solid_count": len(shape.Solids()),
        "volume_mm3": float(shape.Volume()),
        "bounds_mm": [bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax],
    }

def investigate(shape, *, roll_radius_mm, eye_zones):
    rolled = eye._single_solid(shape, "diagnostic source")
    for index, zone in enumerate(eye_zones, 1):
        edge = eye._wearer_side_eye_edge(
            rolled, eye_width_mm=zone.envelope_width_mm,
            eye_height_mm=zone.envelope_height_mm, eye_x_mm=zone.center.x,
            eye_y_mm=zone.center.y, eye_cant_deg=zone.angle_deg,
        )
        raw = rolled.fillet(roll_radius_mm, [edge])
        record = {"eye": index, "radius_mm": roll_radius_mm, "raw": snapshot(raw)}
        # Evaluate the documented kernel repair once, without changing the radius,
        # protected envelopes, support dimensions or any acceptance assertion.
        fixed = raw.fix().clean()
        record["fixed"] = snapshot(fixed)
        records.append(record)
        print("EYE_DIAGNOSTIC " + json.dumps(record, allow_nan=False), flush=True)
        rolled = eye._single_solid(fixed, "diagnostic fixed fillet")
    return rolled

eye._fillet_protected_eye_edges_independently = investigate
result = {"source_candidate_sha": "da14a860e69c48191fc8e8204d895b2b9dd5f469",
          "scope": "KERNEL_REPAIR_EXPERIMENT_NOT_PRODUCTION_GEOMETRY"}
try:
    model = build_model()
    shell = eye.build_eye_rolled_exterior_shell(model.authority, model.facial_reference,
                                               model.protected_volumes)
    result["final"] = snapshot(shell.val())
    import pytest
    code = pytest.main(["-q", "-x", "tests/test_exterior_eye_roll.py",
                       "tests/test_exterior_rigid_clearance.py",
                       "tests/test_exterior_final_wall.py",
                       "tests/test_integrated_product.py"])
    result["test_exit_code"] = int(code)
except Exception as exc:
    result["error"] = type(exc).__name__ + ": " + str(exc)
    code = 1
finally:
    result["records"] = records
    (output / "eye-roll-diagnostic.json").write_text(json.dumps(result, indent=2, allow_nan=False))
    print("EYE_DIAGNOSTIC_RESULT " + json.dumps(result, allow_nan=False), flush=True)
sys.exit(code)
