from __future__ import annotations

import hashlib
import json

from masck_one.spatial import Point3
from masck_one.surface_workflow import SurfaceSample, surface_sample_manifest_sha256


def test_surface_sample_digest_binds_canonical_world_frame_and_mm_units() -> None:
    samples = (SurfaceSample("A", Point3(1.0, 2.0, 3.0)),)
    expected_payload = {
        "schema": "MASCK_ONE_SURFACE_SAMPLE_MANIFEST_V2",
        "coordinate_frame": "MASCK_ONE_AUTHORITY_WORLD_MM",
        "coordinate_unit": "mm",
        "samples": [
            {
                "sample_id": "A",
                "point_mm_float_hex": [1.0.hex(), 2.0.hex(), 3.0.hex()],
            }
        ],
    }
    expected = hashlib.sha256(
        json.dumps(
            expected_payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()

    assert surface_sample_manifest_sha256(samples) == expected
