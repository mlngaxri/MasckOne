from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable

import cadquery as cq

from .authority import Authority, load_authority


@dataclass(frozen=True)
class Component:
    name: str
    solid: cq.Workplane
    status: str
    notes: str = ""


@dataclass(frozen=True)
class MasckOneModel:
    authority: Authority
    shell: Component
    nasal_interface: Component
    actuator_envelopes: tuple[Component, ...]
    water_reservoir_envelope: Component
    waste_cartridge_envelope: Component
    battery_reference_envelope: Component
    visual_keepouts: tuple[Component, ...]

    @property
    def components(self) -> tuple[Component, ...]:
        return (
            self.shell,
            self.nasal_interface,
            *self.actuator_envelopes,
            self.water_reservoir_envelope,
            self.waste_cartridge_envelope,
            self.battery_reference_envelope,
            *self.visual_keepouts,
        )


def _loft_ellipses(sections: Iterable[tuple[float, float, float]]) -> cq.Workplane:
    sections = list(sections)
    if len(sections) < 2:
        raise ValueError("At least two loft sections are required")

    z0, w0, h0 = sections[0]
    wp = cq.Workplane("XY").workplane(offset=z0).ellipse(w0 / 2.0, h0 / 2.0)
    previous_z = z0
    for z, width, height in sections[1:]:
        wp = wp.workplane(offset=z - previous_z).ellipse(width / 2.0, height / 2.0)
        previous_z = z
    return wp.loft(combine=True, ruled=True)


def _ellipse_cutter(width: float, height: float, center: tuple[float, float], depth: float = 50.0,
                    z_start: float = -10.0, angle_deg: float = 0.0) -> cq.Workplane:
    x, y = center
    cutter = (
        cq.Workplane("XY")
        .workplane(offset=z_start)
        .center(x, y)
        .ellipse(width / 2.0, height / 2.0)
        .extrude(depth)
    )
    if angle_deg:
        cutter = cutter.rotate((x, y, 0.0), (x, y, 1.0), angle_deg)
    return cutter


def _circle_cutter(diameter: float, center: tuple[float, float], depth: float = 50.0,
                   z_start: float = -10.0) -> cq.Workplane:
    x, y = center
    return (
        cq.Workplane("XY")
        .workplane(offset=z_start)
        .center(x, y)
        .circle(diameter / 2.0)
        .extrude(depth)
    )


def _box_centered(width_x: float, height_y: float, depth_z: float,
                  center: tuple[float, float, float]) -> cq.Workplane:
    x, y, z = center
    return (
        cq.Workplane("XY")
        .box(width_x, height_y, depth_z, centered=(True, True, True))
        .translate((x, y, z))
    )


def _derived_nostril_diameter(authority: Authority) -> float:
    """Derive a circular nominal CAD opening from the hard minimum area.

    The authority provides a minimum deformed area and a minimum local dimension,
    but not a frozen nominal aperture shape. The code therefore uses a circular
    development baseline with a 2% area margin. This is deliberately a CAD
    closure choice, not a promoted product requirement.
    """
    minimum_area = authority.number("geometry", "nostrils", "minimum_deformed_area_each_mm2")
    minimum_dim = authority.number("geometry", "nostrils", "minimum_local_opening_dimension_mm")
    diameter_from_area = math.sqrt(4.0 * minimum_area * 1.02 / math.pi)
    return max(minimum_dim, diameter_from_area)


def _build_shell(authority: Authority) -> cq.Workplane:
    outer_w, outer_h = authority.pair("geometry", "outer_xy_envelope_mm")
    frame_w, frame_h = authority.pair("geometry", "functional_frame_xy_mm")
    wall = authority.number("geometry", "shell_nominal_wall_mm")

    outer = _loft_ellipses(
        [
            (0.0, frame_w, frame_h),
            (10.0, outer_w - 4.0, outer_h - 3.0),
            (22.0, outer_w, outer_h),
        ]
    )
    inner = _loft_ellipses(
        [
            (-1.0, frame_w - 2.0 * wall, frame_h - 2.0 * wall),
            (10.0, outer_w - 4.0 - 2.0 * wall, outer_h - 3.0 - 2.0 * wall),
            (22.0 - wall, outer_w - 2.0 * wall, outer_h - 2.0 * wall),
        ]
    )
    shell = outer.cut(inner)

    eye_w, eye_h = authority.pair("geometry", "eye", "visual_aperture_wh_mm")
    left_eye = authority.pair("geometry", "eye", "centers_mm", "left")
    right_eye = authority.pair("geometry", "eye", "centers_mm", "right")
    cant = authority.number("geometry", "eye", "lateral_cant_deg")
    shell = shell.cut(_ellipse_cutter(eye_w, eye_h, left_eye, angle_deg=-cant))
    shell = shell.cut(_ellipse_cutter(eye_w, eye_h, right_eye, angle_deg=cant))

    mouth_w, mouth_h = authority.pair("geometry", "mouth", "visual_aperture_wh_mm")
    mouth_center = authority.pair("geometry", "mouth", "center_mm")
    shell = shell.cut(_ellipse_cutter(mouth_w, mouth_h, mouth_center))

    nostril_diameter = _derived_nostril_diameter(authority)
    left_nostril = authority.pair("geometry", "nostrils", "centers_mm", "left")
    right_nostril = authority.pair("geometry", "nostrils", "centers_mm", "right")
    shell = shell.cut(_circle_cutter(nostril_diameter, left_nostril))
    shell = shell.cut(_circle_cutter(nostril_diameter, right_nostril))

    return shell


def _build_nasal_interface(authority: Authority) -> cq.Workplane:
    thickness = authority.number("geometry", "nasal_lobe_membrane", "thickness_center_mm")
    nostril_diameter = _derived_nostril_diameter(authority)
    left_nostril = authority.pair("geometry", "nostrils", "centers_mm", "left")
    right_nostril = authority.pair("geometry", "nostrils", "centers_mm", "right")

    saddle = (
        cq.Workplane("XY")
        .workplane(offset=-thickness)
        .polyline([(-23.0, 31.0), (23.0, 31.0), (25.0, -22.0), (-25.0, -22.0)])
        .close()
        .extrude(thickness)
    )
    saddle = saddle.cut(_circle_cutter(nostril_diameter, left_nostril, depth=5.0, z_start=-3.0))
    saddle = saddle.cut(_circle_cutter(nostril_diameter, right_nostril, depth=5.0, z_start=-3.0))
    return saddle


def _build_actuators(authority: Authority) -> tuple[Component, ...]:
    count = int(authority.number("actuation", "count"))
    if count != 4:
        raise ValueError(f"This architecture expects four actuator zones, authority gives {count}")

    angle = authority.number("actuation", "clean", "axis_angle_baseline_deg")
    diameter = 10.2
    length = 18.7
    placements = [
        (-48.0, 52.0, 2.0, +1.0),
        (48.0, 52.0, 2.0, -1.0),
        (-50.0, -38.0, 2.0, +1.0),
        (50.0, -38.0, 2.0, -1.0),
    ]
    parts: list[Component] = []
    for index, (x, y, z, sign) in enumerate(placements, start=1):
        solid = cq.Workplane("XY").circle(diameter / 2.0).extrude(length)
        solid = solid.rotate((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), sign * angle)
        solid = solid.translate((x, y, z))
        parts.append(
            Component(
                name=f"actuator_envelope_{index}",
                solid=solid,
                status="ALPHA_PHYSICS_REFERENCE",
                notes="H2W NCM01-04-001-2IBH package envelope; production actuator remains validation-gated.",
            )
        )
    return tuple(parts)


def _build_visual_keepouts(authority: Authority) -> tuple[Component, ...]:
    eye_w, eye_h = authority.pair("geometry", "eye", "visual_aperture_wh_mm")
    left_eye = authority.pair("geometry", "eye", "centers_mm", "left")
    right_eye = authority.pair("geometry", "eye", "centers_mm", "right")
    mouth_w, mouth_h = authority.pair("geometry", "mouth", "visual_aperture_wh_mm")
    mouth_center = authority.pair("geometry", "mouth", "center_mm")
    nostril_d = _derived_nostril_diameter(authority)
    left_nostril = authority.pair("geometry", "nostrils", "centers_mm", "left")
    right_nostril = authority.pair("geometry", "nostrils", "centers_mm", "right")

    return (
        Component("visual_eye_left", _ellipse_cutter(eye_w, eye_h, left_eye), "REFERENCE_ONLY"),
        Component("visual_eye_right", _ellipse_cutter(eye_w, eye_h, right_eye), "REFERENCE_ONLY"),
        Component("visual_mouth", _ellipse_cutter(mouth_w, mouth_h, mouth_center), "REFERENCE_ONLY"),
        Component("visual_nostril_left", _circle_cutter(nostril_d, left_nostril), "REFERENCE_ONLY"),
        Component("visual_nostril_right", _circle_cutter(nostril_d, right_nostril), "REFERENCE_ONLY"),
    )


def build_model(authority: Authority | None = None) -> MasckOneModel:
    authority = authority or load_authority()
    shell = Component(
        "rigid_shell",
        _build_shell(authority),
        "CAD_BASELINE",
        "XY envelope and apertures follow authority; Class-A Z surface remains CAD-CLOSURE.",
    )
    nasal_interface = Component(
        "nasal_interface",
        _build_nasal_interface(authority),
        "CAD_CLOSURE_BASELINE",
        "Dedicated compliant nose/T-zone saddle; final scan-conforming geometry remains validation/CAD closure.",
    )

    water_reservoir = Component(
        "water_reservoir_envelope",
        _box_centered(26.0, 25.0, 10.0, (0.0, 76.0, 7.0)),
        "ENGINEERING_BASELINE_ENVELOPE",
        "6500 mm^3 gross volume; final wall/port geometry not frozen.",
    )

    cartridge_dims = authority.get("fluid", "cartridge", "external_envelope_mm")
    cw, ch, cd = (float(v) for v in cartridge_dims)
    waste_cartridge = Component(
        "waste_cartridge_envelope",
        _box_centered(cw, ch, cd, (0.0, -80.0, 8.0)),
        "ENGINEERING_BASELINE_ENVELOPE",
        "External envelope only; retained capacity is a physical validation gate.",
    )

    bw, bh, bd = authority.get("battery_reference", "envelope_mm")
    battery = Component(
        "battery_reference_envelope",
        _box_centered(float(bw), float(bh), float(bd), (0.0, 0.0, -15.0)),
        "PACKAGING_BENCHMARK_NOT_PRODUCTION_FREEZE",
        "Halo-location benchmark only; not a production-qualified battery pack.",
    )

    return MasckOneModel(
        authority=authority,
        shell=shell,
        nasal_interface=nasal_interface,
        actuator_envelopes=_build_actuators(authority),
        water_reservoir_envelope=water_reservoir,
        waste_cartridge_envelope=waste_cartridge,
        battery_reference_envelope=battery,
        visual_keepouts=_build_visual_keepouts(authority),
    )
