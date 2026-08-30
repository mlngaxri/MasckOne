from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .actuation_architecture import ActuationArchitecture, build_actuation_architecture
from .alpha_closure import AlphaClosure, build_alpha_closure
from .boundary_release import build_verified_interface_boundary_topology
from .contact_simulation import ContactSimulationFramework, build_contact_simulation_framework
from .distribution_manifold import DistributionManifoldArchitecture, build_distribution_manifold
from .fresh_fluid import FreshFluidArchitecture, build_fresh_fluid_architecture
from .interface_attachment import build_interface_attachment_architecture
from .spatial import Point3
from .structural_frame import StructuralFrameTopology, build_structural_frame_topology
from .surface_workflow import ClassAReferenceWorkflow, build_class_a_workflow
from .waste_architecture import WasteArchitecture, build_waste_architecture
from .wearable_architecture import WearableArchitecture, build_wearable_architecture

if TYPE_CHECKING:
    from .model import MasckOneModel


@dataclass(frozen=True, slots=True)
class DevelopmentArchitecture:
    contact_simulation: ContactSimulationFramework
    structural_frame: StructuralFrameTopology
    class_a_workflow: ClassAReferenceWorkflow
    actuation: ActuationArchitecture
    fresh_fluid: FreshFluidArchitecture
    distribution_manifold: DistributionManifoldArchitecture
    waste: WasteArchitecture
    wearable: WearableArchitecture
    alpha_closure: AlphaClosure
    completed_iteration_floor: int = 40
    roadmap_iteration_count: int = 90

    @property
    def roadmap_fraction(self) -> float:
        return self.completed_iteration_floor / self.roadmap_iteration_count

    def manifest(self) -> dict[str, object]:
        return {
            "scope": "MERGED_ITERATIONS_14_15_WITH_CANDIDATE_DIGITAL_ALPHA_THROUGH_ITERATION_40",
            "completed_iteration_floor": self.completed_iteration_floor,
            "roadmap_iteration_count": self.roadmap_iteration_count,
            "roadmap_fraction": self.roadmap_fraction,
            "contact_simulation": self.contact_simulation.manifest(),
            "structural_frame": self.structural_frame.manifest(),
            "class_a_workflow": {
                "rms_limit_mm": self.class_a_workflow.rms_limit_mm,
                "maximum_limit_mm": self.class_a_workflow.maximum_limit_mm,
                "reference_surface_id": self.class_a_workflow.reference_surface_id,
                "release_status": self.class_a_workflow.release_status,
                "evidence_status": self.class_a_workflow.evidence_status,
            },
            "actuation": self.actuation.manifest(),
            "fresh_fluid": self.fresh_fluid.manifest(),
            "distribution_manifold": self.distribution_manifold.manifest(),
            "waste": self.waste.manifest(),
            "wearable": self.wearable.manifest(),
            "alpha_closure": self.alpha_closure.manifest(),
        }


QuarterArchitecture = DevelopmentArchitecture


def build_development_architecture(model: "MasckOneModel") -> DevelopmentArchitecture:
    boundaries = build_verified_interface_boundary_topology(
        model.authority, model.facial_surface, model.coverage_mesh, model.compliant_interface_topology
    )
    attachment = build_interface_attachment_architecture(model.authority, boundaries)
    fresh_fluid = build_fresh_fluid_architecture(model.authority)
    cartridge_box = model.waste_cartridge_envelope.solid.val().BoundingBox()
    cartridge_center = (
        (cartridge_box.xmin + cartridge_box.xmax) / 2.0,
        (cartridge_box.ymin + cartridge_box.ymax) / 2.0,
        (cartridge_box.zmin + cartridge_box.zmax) / 2.0,
    )
    contact = build_contact_simulation_framework(model.authority, attachment)
    frame = build_structural_frame_topology(model.authority, attachment)
    class_a = build_class_a_workflow(model.authority)
    actuation = build_actuation_architecture(model.authority)
    manifold = build_distribution_manifold(model.authority, model.coverage_mesh, model.protected_volumes)
    waste = build_waste_architecture(
            model.authority,
            model.coverage_mesh,
            model.protected_volumes,
            Point3(*cartridge_center),
            fresh_fluid.route_ids,
        )
    battery_box = model.battery_reference_envelope.solid.val().BoundingBox()
    battery_center = Point3(
        (battery_box.xmin + battery_box.xmax) / 2.0,
        (battery_box.ymin + battery_box.ymax) / 2.0,
        (battery_box.zmin + battery_box.zmax) / 2.0,
    )
    wearable = build_wearable_architecture(model.authority, frame, battery_center)
    alpha = build_alpha_closure(
        model.authority,
        actuation,
        fresh_fluid,
        waste,
        wearable,
        (
            contact.framework_sha256,
            frame.topology_sha256,
            actuation.topology_sha256,
            fresh_fluid.topology_sha256,
            manifold.topology_sha256,
            waste.topology_sha256,
            wearable.topology_sha256,
        ),
    )
    return DevelopmentArchitecture(
        contact,
        frame,
        class_a,
        actuation,
        fresh_fluid,
        manifold,
        waste,
        wearable,
        alpha,
    )


def build_quarter_architecture(model: "MasckOneModel") -> DevelopmentArchitecture:
    """Compatibility entry point retained for existing callers."""
    return build_development_architecture(model)
