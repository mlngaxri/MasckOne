"""Unvalidated OFF-FACE compression-coupon nest and flat pusher planning CAD.

This independent fixture supports force-travel instrument setup experiments. It
does not reproduce a Masck assembly, attach to hardware, or qualify calibration.
No load cell, machine mount, material, stiffness or safe load has been selected.
"""
from dataclasses import dataclass
import math

import cadquery as cq


@dataclass(frozen=True)
class FixtureDimensions:
    base_width_mm: float = 40.0
    base_length_mm: float = 40.0
    base_height_mm: float = 6.0
    coupon_diameter_mm: float = 12.0
    coupon_height_mm: float = 4.0
    diametral_clearance_mm: float = 0.5
    nest_depth_mm: float = 1.0
    pusher_diameter_mm: float = 8.0
    pusher_height_mm: float = 4.0
    pusher_gap_mm: float = 2.0

    def validate(self) -> None:
        if any(isinstance(v, bool) or not isinstance(v, (int, float))
               or not math.isfinite(v) or v <= 0 for v in vars(self).values()):
            raise ValueError("all fixture planning dimensions must be finite and positive")
        if self.nest_depth_mm >= min(self.base_height_mm, self.coupon_height_mm):
            raise ValueError("nest must leave base floor and exposed coupon")
        if self.coupon_diameter_mm + self.diametral_clearance_mm >= min(self.base_width_mm, self.base_length_mm):
            raise ValueError("nest must leave side walls")
        if self.pusher_diameter_mm >= self.coupon_diameter_mm:
            raise ValueError("pusher must fit inside coupon footprint")


def build_fixture(d: FixtureDimensions = FixtureDimensions()) -> dict[str, cq.Shape]:
    d.validate()
    base = cq.Workplane("XY").box(d.base_width_mm, d.base_length_mm, d.base_height_mm,
                                   centered=(True, True, False))
    base = base.faces(">Z").workplane().hole(d.coupon_diameter_mm + d.diametral_clearance_mm, d.nest_depth_mm)
    coupon_z = d.base_height_mm - d.nest_depth_mm
    coupon = cq.Workplane("XY").workplane(offset=coupon_z).circle(d.coupon_diameter_mm / 2).extrude(d.coupon_height_mm)
    pusher_z = coupon_z + d.coupon_height_mm + d.pusher_gap_mm
    pusher = cq.Workplane("XY").workplane(offset=pusher_z).circle(d.pusher_diameter_mm / 2).extrude(d.pusher_height_mm)
    return {"coupon_nest": base.val(), "coupon_reference_only": coupon.val(), "flat_pusher": pusher.val()}
