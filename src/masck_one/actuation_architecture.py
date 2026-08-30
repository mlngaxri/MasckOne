from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math

import cadquery as cq

from .authority import Authority
from .spatial import DatumFrame, Point3, Vector3


class ActuationArchitectureError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ActuatorReference:
    reference_id: str
    diameter_mm: float
    length_mm: float
    stroke_mm: float
    continuous_force_N: float
    mass_g: float | None
    supplier_status: str


@dataclass(frozen=True, slots=True)
class ActuatorStation:
    station_id: str
    local_frame: DatumFrame
    reference: ActuatorReference
    placement_status: str
    mount_geometry_status: str
    coupling_status: str

    def cad_envelope(self, angle_deg: float) -> cq.Workplane:
        solid = cq.Workplane("XY").circle(self.reference.diameter_mm / 2.0).extrude(self.reference.length_mm)
        sign = 1.0 if self.local_frame.origin.x < 0.0 else -1.0
        return solid.rotate((0, 0, 0), (0, 1, 0), sign * angle_deg).translate(self.local_frame.origin.as_tuple())


@dataclass(frozen=True, slots=True)
class ActuationArchitecture:
    stations: tuple[ActuatorStation, ...]
    axis_angle_baseline_deg: float
    axis_angle_doe_deg: tuple[float, ...]
    clean_frequency_hz: float
    frequency_doe_hz: tuple[float, ...]
    displacement_pp_mm: float
    continuous_force_N: float
    transient_force_N: float
    swept_volume_status: str
    collision_status: str
    flexure_load_path_status: str
    impedance_handoff_status: str
    evidence_status: str
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if len(self.stations) != 4 or len({station.station_id for station in self.stations}) != 4:
            raise ActuationArchitectureError("Frozen architecture requires four unique stations")
        if self.physical_validation_eligible:
            raise ActuationArchitectureError("Packaging/sensitivity architecture is not physical evidence")

    def cad_envelopes(self, *, angle_deg: float | None = None) -> tuple[cq.Workplane, ...]:
        angle = self.axis_angle_baseline_deg if angle_deg is None else float(angle_deg)
        if angle not in self.axis_angle_doe_deg:
            raise ActuationArchitectureError("Envelope angle must be a controlled DOE value")
        return tuple(station.cad_envelope(angle) for station in self.stations)

    def swept_envelopes(self) -> tuple[cq.Workplane, ...]:
        swept = []
        for station in self.stations:
            shape = station.cad_envelope(self.axis_angle_doe_deg[0])
            for angle in self.axis_angle_doe_deg[1:]:
                shape = shape.union(station.cad_envelope(angle))
            swept.append(shape)
        return tuple(swept)

    @property
    def topology_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        result: dict[str, object] = {
            "stations": [
                {
                    "station_id": station.station_id,
                    "origin_mm": list(station.local_frame.origin.as_tuple()),
                    "reference": asdict(station.reference),
                    "placement_status": station.placement_status,
                    "mount_geometry_status": station.mount_geometry_status,
                    "coupling_status": station.coupling_status,
                }
                for station in self.stations
            ],
            "axis_angle_baseline_deg": self.axis_angle_baseline_deg,
            "axis_angle_doe_deg": list(self.axis_angle_doe_deg),
            "clean_frequency_hz": self.clean_frequency_hz,
            "frequency_doe_hz": list(self.frequency_doe_hz),
            "displacement_pp_mm": self.displacement_pp_mm,
            "continuous_force_N": self.continuous_force_N,
            "transient_force_N": self.transient_force_N,
            "swept_volume_status": self.swept_volume_status,
            "collision_status": self.collision_status,
            "flexure_load_path_status": self.flexure_load_path_status,
            "impedance_handoff_status": self.impedance_handoff_status,
            "evidence_status": self.evidence_status,
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        if include_sha:
            result["topology_sha256"] = self.topology_sha256
        return result


def build_actuation_architecture(authority: Authority) -> ActuationArchitecture:
    primary = ActuatorReference(
        "H2W_NCM01-04-001-2IBH", 10.2, 18.7, 2.5, 0.45, 5.6,
        "ALPHA_PHYSICS_REFERENCE_NOT_PRODUCTION_FREEZE",
    )
    angle = authority.number("actuation", "clean", "axis_angle_baseline_deg")
    placements = (
        ("ACTUATOR_UPPER_LEFT", Point3(-48.0, 52.0, 2.0)),
        ("ACTUATOR_UPPER_RIGHT", Point3(48.0, 52.0, 2.0)),
        ("ACTUATOR_LOWER_LEFT", Point3(-50.0, -38.0, 2.0)),
        ("ACTUATOR_LOWER_RIGHT", Point3(50.0, -38.0, 2.0)),
    )
    stations = tuple(
        ActuatorStation(
            station_id,
            DatumFrame(
                f"MASCK_ONE_{station_id}_FRAME",
                origin,
                Vector3(1.0, 0.0, 0.0),
                Vector3(0.0, 1.0, 0.0),
                Vector3(0.0, 0.0, 1.0),
            ),
            primary,
            "DEVELOPMENT_PACKAGING_SEED_REQUIRES_REGISTERED_SURFACE_AND_FRAME_CLOSURE",
            "MOUNT_INTERFACE_UNRESOLVED_UNTIL_FRAME_SECTION_AND_SUPPLIER_CAD",
            "COUPLING_FLEXURE_AND_REACTION_PATH_UNRESOLVED",
        )
        for station_id, origin in placements
    )
    return ActuationArchitecture(
        stations=stations,
        axis_angle_baseline_deg=angle,
        axis_angle_doe_deg=tuple(float(v) for v in authority.get("actuation", "clean", "axis_angle_doe_deg")),
        clean_frequency_hz=authority.number("actuation", "clean", "frequency_baseline_hz"),
        frequency_doe_hz=(20.0, 40.0, 80.0, 120.0),
        displacement_pp_mm=authority.number("actuation", "clean", "displacement_pp_baseline_mm"),
        continuous_force_N=authority.number("actuation", "clean", "continuous_force_requirement_N"),
        transient_force_N=authority.number("actuation", "clean", "transient_force_requirement_N"),
        swept_volume_status="DOE_SWEEP_GEOMETRY_GENERATED_FOR_DEVELOPMENT_REFERENCE",
        collision_status="DIGITAL_ENVELOPE_ONLY_REQUIRES_FINAL_FRAME_INTERFACE_AND_SUPPLIER_TOLERANCE",
        flexure_load_path_status="BLOCKED_GEOMETRY_MATERIAL_AND_IMPEDANCE_UNRESOLVED",
        impedance_handoff_status="RIG_PROTOCOL_SCHEMA_READY_MEASURED_DATA_ABSENT",
        evidence_status="ITERATIONS17_19_PACKAGING_SWEEP_AND_SENSITIVITY_ONLY_NOT_ACTUATION_OR_CLEANSING_VALIDATION",
    )
