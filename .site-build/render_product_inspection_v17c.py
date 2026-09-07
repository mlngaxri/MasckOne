from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path

import cadquery as cq
from PIL import Image
import vtk

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "website" / "images"
OUT.mkdir(parents=True, exist_ok=True)

EXTERIOR_SHA = "17e7db204c693f684855d923fcacd7c95468e599"
EXTERIOR_HEAD = "7361ad3ae3aa91373cd9e723179e19b0554ec1b4"
RETENTION_SHA = "25686766238b66ecf900009042d721c08e042592"
HMI_SHA = "7b32c674860cab87cbdd1f7e3303a4ce53515e95"
DRY_SIDE_SHA = "fa017c8379dabaefeecf53bf770858bebfde3067"
AUTHORITY_REVISION = "2026-08-30-R1"
FRAME = "MASCK_ONE_AUTHORITY_WORLD_MM"
CAMERA_ID = "CAM_WEARABILITY_V17C_80MM_EQUIV"
SIZE = 1200

STEP_DIR = Path(os.environ.get("MASCK_INSPECTION_STEP_DIR", "/tmp/masck-inspection-step"))
SHELL_STEP = STEP_DIR / "exterior_shell.step"
COVER_STEP = STEP_DIR / "rear_service_cover.step"
LEFT_YOKE_STEP = STEP_DIR / "occipital_yoke_left.step"
RIGHT_YOKE_STEP = STEP_DIR / "occipital_yoke_right.step"

for p in (SHELL_STEP, COVER_STEP, LEFT_YOKE_STEP, RIGHT_YOKE_STEP):
    if not p.exists():
        raise RuntimeError(f"missing registered source geometry: {p}")


def load_shape(path: Path) -> cq.Shape:
    shape = cq.importers.importStep(str(path)).val()
    if not shape.isValid():
        raise RuntimeError(f"invalid STEP geometry: {path.name}")
    return shape


def vtk_actor(shape: cq.Shape, rgb: tuple[float, float, float]) -> vtk.vtkActor:
    vertices, triangles = shape.tessellate(0.28, 0.12)
    points = vtk.vtkPoints()
    for v in vertices:
        points.InsertNextPoint(float(v.x), float(v.y), float(v.z))
    polys = vtk.vtkCellArray()
    for tri in triangles:
        cell = vtk.vtkTriangle()
        cell.GetPointIds().SetId(0, int(tri[0]))
        cell.GetPointIds().SetId(1, int(tri[1]))
        cell.GetPointIds().SetId(2, int(tri[2]))
        polys.InsertNextCell(cell)
    mesh = vtk.vtkPolyData()
    mesh.SetPoints(points)
    mesh.SetPolys(polys)
    normals = vtk.vtkPolyDataNormals()
    normals.SetInputData(mesh)
    normals.ComputePointNormalsOn()
    normals.ComputeCellNormalsOff()
    normals.SplittingOff()
    normals.ConsistencyOn()
    normals.AutoOrientNormalsOn()
    normals.Update()
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(normals.GetOutputPort())
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    prop = actor.GetProperty()
    prop.SetColor(*rgb)
    prop.SetAmbient(0.24)
    prop.SetDiffuse(0.72)
    prop.SetSpecular(0.16)
    prop.SetSpecularPower(26.0)
    prop.SetInterpolationToPhong()
    return actor


def normal(v: tuple[float, float, float]) -> tuple[float, float, float]:
    n = math.sqrt(sum(x * x for x in v))
    return tuple(x / n for x in v)


def project(renderer: vtk.vtkRenderer, point: tuple[float, float, float]) -> dict[str, float]:
    renderer.SetWorldPoint(point[0], point[1], point[2], 1.0)
    renderer.WorldToDisplay()
    x, y, _ = renderer.GetDisplayPoint()
    return {
        "x_percent": round(max(0.0, min(100.0, x / SIZE * 100.0)), 3),
        "y_percent": round(max(0.0, min(100.0, (1.0 - y / SIZE) * 100.0)), 3),
    }


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


shell = load_shape(SHELL_STEP)
cover = load_shape(COVER_STEP)
left_yoke = load_shape(LEFT_YOKE_STEP)
right_yoke = load_shape(RIGHT_YOKE_STEP)

all_shapes = [shell, cover, left_yoke, right_yoke]
for shape in all_shapes:
    if shape.Volume() <= 0:
        raise RuntimeError("inspection source contains non-positive material volume")

cover_bb = cover.BoundingBox()
cover_center = (
    (cover_bb.xmin + cover_bb.xmax) / 2.0,
    (cover_bb.ymin + cover_bb.ymax) / 2.0,
    (cover_bb.zmin + cover_bb.zmax) / 2.0,
)

BONE = tuple(int("E8E1D5"[i:i+2], 16) / 255.0 for i in (0, 2, 4))
BONE_REAR = tuple(int("DCD4C8"[i:i+2], 16) / 255.0 for i in (0, 2, 4))
BONE_RETENTION = tuple(int("CFC8BC"[i:i+2], 16) / 255.0 for i in (0, 2, 4))

views = {
    "front_three_quarter": {
        "direction": (-0.48, -0.035, -1.0),
        "file": "masck-inspection-front-3q-v17c.webp",
    },
    "side_rear": {
        "direction": (-0.98, -0.03, 0.22),
        "file": "masck-inspection-side-rear-v17c.webp",
    },
    "rear_three_quarter": {
        "direction": (-0.48, -0.035, 1.0),
        "file": "masck-inspection-rear-3q-v17c.webp",
    },
}

manifest_views: dict[str, object] = {}
focus = (0.0, 0.0, -10.0)
distance = 820.0
view_angle = 18.5

for name, spec in views.items():
    renderer = vtk.vtkRenderer()
    renderer.SetBackground(1.0, 1.0, 1.0)
    if hasattr(renderer, "SetBackgroundAlpha"):
        renderer.SetBackgroundAlpha(0.0)

    renderer.AddActor(vtk_actor(shell, BONE))
    renderer.AddActor(vtk_actor(cover, BONE_REAR))
    renderer.AddActor(vtk_actor(left_yoke, BONE_RETENTION))
    renderer.AddActor(vtk_actor(right_yoke, BONE_RETENTION))

    direction = normal(spec["direction"])
    camera = vtk.vtkCamera()
    camera.SetFocalPoint(*focus)
    camera.SetPosition(
        focus[0] - direction[0] * distance,
        focus[1] - direction[1] * distance,
        focus[2] - direction[2] * distance,
    )
    camera.SetViewUp(0.0, 1.0, 0.0)
    camera.SetViewAngle(view_angle)
    renderer.SetActiveCamera(camera)

    renderer.AutomaticLightCreationOff()
    key = vtk.vtkLight()
    key.SetLightTypeToSceneLight()
    key.SetPosition(260.0, 245.0, 420.0)
    key.SetFocalPoint(*focus)
    key.SetIntensity(0.96)
    fill = vtk.vtkLight()
    fill.SetLightTypeToSceneLight()
    fill.SetPosition(-310.0, 80.0, 180.0)
    fill.SetFocalPoint(*focus)
    fill.SetIntensity(0.43)
    rim = vtk.vtkLight()
    rim.SetLightTypeToSceneLight()
    rim.SetPosition(80.0, 300.0, -380.0)
    rim.SetFocalPoint(*focus)
    rim.SetIntensity(0.58)
    renderer.AddLight(key)
    renderer.AddLight(fill)
    renderer.AddLight(rim)

    window = vtk.vtkRenderWindow()
    window.SetSize(SIZE, SIZE)
    window.SetOffScreenRendering(1)
    window.SetAlphaBitPlanes(1)
    window.SetMultiSamples(8)
    window.AddRenderer(renderer)
    window.Render()

    anchors = {
        "hmi_primary_capacity": project(renderer, (69.0, 25.0, 9.0)),
        "right_occipital_backer": project(renderer, (52.0, -5.0, -49.5)),
        "rear_service_cover": project(renderer, cover_center),
    }

    capture = vtk.vtkWindowToImageFilter()
    capture.SetInput(window)
    capture.SetInputBufferTypeToRGBA()
    capture.ReadFrontBufferOff()
    capture.Update()
    png_path = OUT / (Path(spec["file"]).stem + ".png")
    writer = vtk.vtkPNGWriter()
    writer.SetFileName(str(png_path))
    writer.SetInputConnection(capture.GetOutputPort())
    writer.Write()

    image = Image.open(png_path).convert("RGBA")
    alpha_min, alpha_max = image.getchannel("A").getextrema()
    if alpha_min == alpha_max:
        raise RuntimeError(f"render {name} did not preserve a transparent alpha field")
    webp_path = OUT / spec["file"]
    image.save(webp_path, "WEBP", lossless=True, method=6)
    png_path.unlink()

    manifest_views[name] = {
        "asset": spec["file"],
        "asset_sha256": sha256_file(webp_path),
        "camera_direction": [round(v, 8) for v in direction],
        "camera_position_mm": [round(float(v), 6) for v in camera.GetPosition()],
        "focal_point_mm": list(focus),
        "vertical_view_angle_deg": view_angle,
        "image_px": [SIZE, SIZE],
        "hotspots": anchors,
    }
    window.Finalize()

manifest = {
    "schema": "MASCK_ONE_WEBSITE_PRODUCT_INSPECTION_V17C",
    "asset_version": "v17c",
    "coordinate_frame": FRAME,
    "authority_revision": AUTHORITY_REVISION,
    "camera_id": CAMERA_ID,
    "camera_character": "80MM_EQUIVALENT_RESTRAINED_PRODUCT_PORTRAIT",
    "website_build_main_sha": os.environ.get("MASCK_WEBSITE_BUILD_SHA"),
    "sources": {
        "exterior_render_checkpoint_sha": EXTERIOR_SHA,
        "exterior_current_head_observed_sha": EXTERIOR_HEAD,
        "retention_current_head_sha": RETENTION_SHA,
        "hmi_decision_head_sha": HMI_SHA,
        "dry_side_package_head_sha": DRY_SIDE_SHA,
    },
    "geometry_maturity": {
        "exterior": "CANDIDATE_LAST_RENDERER_PASS_CHECKPOINT_NOT_RELEASED_MAIN",
        "rear_service_cover": "CANDIDATE_VISIBLE_EXTERIOR_GEOMETRY",
        "retention": "CURRENT_CANDIDATE_MATERIAL_BREP_ATTACHMENT_COUNTERPART_UNRESOLVED",
        "hmi": "REGISTERED_CAPACITY_LOCATION_ONLY_MAPPING_AND_FINAL_HARDWARE_UNRESOLVED",
        "dry_side": "CURRENT_CANDIDATE_INTERNAL_PACKAGE_NOT_RENDERED_AS_VISIBLE_EXTERIOR",
    },
    "views": manifest_views,
    "claim_boundary": (
        "Registered digital review composition only. Exterior source uses the last PR70 checkpoint "
        "whose actual B-rep multi-view renderer passed before the current PR70 geometry regression. "
        "Retention uses the current green PR123 bilateral-yoke candidate in the same authority frame. "
        "The composition does not close frame-side attachment, fit, comfort, HMI mapping, material, "
        "serviceability, ingress, manufacturing or physical-validation gates."
    ),
}
manifest_path = OUT / "masck-inspection-v17c-manifest.json"
manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({"manifest": str(manifest_path), "views": list(manifest_views)}, indent=2))
