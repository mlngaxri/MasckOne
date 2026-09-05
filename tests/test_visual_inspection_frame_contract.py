from masck_one.spatial import Point3
from masck_one.surface_workflow import SurfaceSample
from masck_one.visual_inspection import inspect_surface_samples


def test_visual_inspection_manifest_uses_canonical_authority_world_frame() -> None:
    report = inspect_surface_samples(
        (
            SurfaceSample("A", Point3(-10.0, -20.0, -5.0)),
            SurfaceSample("B", Point3(30.0, -10.0, 4.0)),
            SurfaceSample("C", Point3(20.0, 25.0, 12.0)),
            SurfaceSample("D", Point3(-5.0, 15.0, -2.0)),
        )
    )
    manifest = report.manifest()

    assert manifest["coordinate_frame"] == "MASCK_ONE_AUTHORITY_WORLD_MM"
    assert report.physical_validation_eligible is False
