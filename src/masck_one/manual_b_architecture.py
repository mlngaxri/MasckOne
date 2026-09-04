from __future__ import annotations

"""Manual B packaging, CMF, HMI and wet-system architecture for MVP convergence.

This is an executable design and reservation contract, not production selection or
physical validation. It intentionally fails closed where live main has no selected PCB,
charging connector, WARM hardware or COOL hardware envelope.
"""

from dataclasses import dataclass
import hashlib
import json

from .authority import Authority


MANUAL_B_SCHEMA = "MASCK_ONE_MANUAL_B_ARCHITECTURE_V1"
EVIDENCE_STATUS = "DIGITAL_MVP_DESIGN_AND_PACKAGE_RESERVATION_NOT_PHYSICAL_VALIDATION"


@dataclass(frozen=True, slots=True)
class PackageReservation:
    package_id: str
    location_intent: str
    envelope_mm: tuple[float, float, float] | None
    status: str
    wet_dry_class: str
    notes: str

    def manifest(self) -> dict[str, object]:
        return {
            "package_id": self.package_id,
            "location_intent": self.location_intent,
            "envelope_mm": list(self.envelope_mm) if self.envelope_mm is not None else None,
            "status": self.status,
            "wet_dry_class": self.wet_dry_class,
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class CMFRole:
    role_id: str
    visual_role: str
    material_family_status: str
    finish_intent: str
    colour_intent: str
    evidence_status: str

    def manifest(self) -> dict[str, str]:
        return {
            "role_id": self.role_id,
            "visual_role": self.visual_role,
            "material_family_status": self.material_family_status,
            "finish_intent": self.finish_intent,
            "colour_intent": self.colour_intent,
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class PhysicalHMIReservation:
    primary_action: str
    primary_tactile_land_min_mm: float
    secondary_tactile_land_min_mm: float
    minimum_control_separation_mm: float
    status_window_minor_axis_min_mm: float
    status_window_recess_max_mm: float
    location_intent: str
    geometry_status: str
    app_independent: bool
    evidence_status: str

    def manifest(self) -> dict[str, object]:
        return {
            "primary_action": self.primary_action,
            "primary_tactile_land_min_mm": self.primary_tactile_land_min_mm,
            "secondary_tactile_land_min_mm": self.secondary_tactile_land_min_mm,
            "minimum_control_separation_mm": self.minimum_control_separation_mm,
            "status_window_minor_axis_min_mm": self.status_window_minor_axis_min_mm,
            "status_window_recess_max_mm": self.status_window_recess_max_mm,
            "location_intent": self.location_intent,
            "geometry_status": self.geometry_status,
            "app_independent": self.app_independent,
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class ManualBArchitecture:
    source_authority_revision: str
    packages: tuple[PackageReservation, ...]
    cmf_roles: tuple[CMFRole, ...]
    hmi: PhysicalHMIReservation
    charging_policy: str
    active_wet_cycle_charging_authorized: bool
    drainage_policy: str
    seam_policy: str
    evidence_status: str = EVIDENCE_STATUS
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if not self.source_authority_revision:
            raise ValueError("Manual B architecture requires authority provenance")
        if tuple(item.package_id for item in self.packages) != tuple(sorted(item.package_id for item in self.packages)):
            raise ValueError("Manual B package reservations must be canonically sorted")
        if tuple(item.role_id for item in self.cmf_roles) != tuple(sorted(item.role_id for item in self.cmf_roles)):
            raise ValueError("CMF roles must be canonically sorted")
        allowed = {"DRY_ALWAYS", "WET_DRAINABLE", "WET_REMOVABLE", "SEALED_NONUSER"}
        if any(item.wet_dry_class not in allowed for item in self.packages):
            raise ValueError("Manual B package uses a non-authoritative wet/dry class")
        if self.hmi.primary_action != "CLEAN":
            raise ValueError("Physical HMI must remain CLEAN-first")
        if not self.hmi.app_independent:
            raise ValueError("Physical HMI cannot depend on the companion app")
        if self.active_wet_cycle_charging_authorized:
            raise ValueError("Active wet-cycle charging is not authorized by current evidence")
        if self.evidence_status != EVIDENCE_STATUS or self.physical_validation_eligible:
            raise ValueError("Manual B digital architecture cannot be promoted to physical evidence")

    def validate_current_authority(self, authority: Authority) -> None:
        if self.source_authority_revision != str(authority.get("project", "authority_revision")):
            raise ValueError("Manual B architecture is stale for current authority")
        allowed = set(authority.get("manufacturing", "hygiene_classes"))
        if any(item.wet_dry_class not in allowed for item in self.packages):
            raise ValueError("Manual B wet/dry classification no longer matches authority")
        battery = next(item for item in self.packages if item.package_id == "BATTERY_REFERENCE")
        expected = tuple(float(value) for value in authority.get("battery_reference", "envelope_mm"))
        if battery.envelope_mm != expected:
            raise ValueError("Battery package reservation no longer matches authority benchmark")
        if battery.status != str(authority.get("battery_reference", "status")):
            raise ValueError("Battery package status no longer matches authority")

    @property
    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        payload: dict[str, object] = {
            "schema": MANUAL_B_SCHEMA,
            "source_authority_revision": self.source_authority_revision,
            "packages": [item.manifest() for item in self.packages],
            "cmf_roles": [item.manifest() for item in self.cmf_roles],
            "hmi": self.hmi.manifest(),
            "charging_policy": self.charging_policy,
            "active_wet_cycle_charging_authorized": self.active_wet_cycle_charging_authorized,
            "drainage_policy": self.drainage_policy,
            "seam_policy": self.seam_policy,
            "evidence_status": self.evidence_status,
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        payload["manifest_sha256"] = hashlib.sha256(raw).hexdigest()
        return payload


def build_manual_b_architecture(authority: Authority) -> ManualBArchitecture:
    battery_envelope = tuple(float(value) for value in authority.get("battery_reference", "envelope_mm"))
    packages = (
        PackageReservation(
            "BATTERY_REFERENCE",
            "HALO_OR_CLOSE_TO_HEAD_DRY_VOLUME; FINAL RETENTION INTEGRATION OWNED BY MANUAL_A",
            battery_envelope,
            str(authority.get("battery_reference", "status")),
            "DRY_ALWAYS",
            "Packaging benchmark only. No runtime or production battery claim.",
        ),
        PackageReservation(
            "CHARGING_INTERFACE",
            "LOW_HIGHLIGHT_REAR_OR_TEMPORAL_TURNOVER_OUTSIDE_WET_SERVICE_PATH",
            None,
            "BLOCKED_PENDING_SELECTED_CONNECTOR_INGRESS_AND_ELECTRICAL_ARCHITECTURE",
            "SEALED_NONUSER",
            "USB-C is a commercial preference only, not selected hardware.",
        ),
        PackageReservation(
            "CLEANSER_MODULE",
            "SERVICEABLE_FRESH_SIDE_MODULE_WITH_DIRECT_DRAIN_AND_WIPE_ACCESS",
            None,
            "CURRENT_CLEANSER_STORAGE_ARCHITECTURE_CONSUMER_FINAL_3D_SERVICE_GEOMETRY_OPEN",
            "WET_REMOVABLE",
            "Do not hide cleanser fill/service interfaces behind electronics.",
        ),
        PackageReservation(
            "COOL_RESERVATION",
            "DRY_THERMAL_RESERVATION_BEHIND_FACIAL_FIELD_WITH_CONDENSATION_ISOLATION_REQUIRED",
            None,
            "BLOCKED_PENDING_SELECTED_HARDWARE_AND_DEW_POINT_EVIDENCE",
            "SEALED_NONUSER",
            "Reservation only. No cooling performance claim.",
        ),
        PackageReservation(
            "FRESH_DISTRIBUTION",
            "FACIAL_FIELD_MANIFOLD_AND_ROUTES_FROM_CURRENT_RELEASED_GEOMETRY",
            None,
            "CONSUME_CURRENT_DISTRIBUTION_GEOMETRY; PHYSICAL_FLOW_PERFORMANCE_UNVALIDATED",
            "WET_DRAINABLE",
            "No decorative exterior venting or fake route exposure.",
        ),
        PackageReservation(
            "PCB_CONTROL",
            "CLOSE_TO_HEAD_DRY_BAY_OUTBOARD_OF_PRIMARY_WET_PATHS",
            None,
            "BLOCKED_PENDING_SELECTED_PCB_ENVELOPE_AND_CONNECTOR_SET",
            "DRY_ALWAYS",
            "No invented board dimensions. Harness exits must cross wet/dry boundary only at sealed interfaces.",
        ),
        PackageReservation(
            "WARM_RESERVATION",
            "SEALED_SKIN_ADJACENT_THERMAL_RESERVATION_WITH_DRY_CONTROL_SIDE",
            None,
            "BLOCKED_PENDING_SELECTED_HARDWARE_THERMAL_LIMITS_AND_PHYSICAL_EVIDENCE",
            "SEALED_NONUSER",
            "Reservation only. No warming performance or safety claim.",
        ),
        PackageReservation(
            "WASTE_CARTRIDGE",
            "INFERIOR_REAR_SERVICE_VOLUME_CLOSE_TO_HEAD",
            tuple(float(value) for value in authority.get("fluid", "cartridge", "external_envelope_mm")),
            str(authority.get("fluid", "cartridge", "external_envelope_status")),
            "WET_REMOVABLE",
            "Retained capacity and service cadence remain validation-gated.",
        ),
        PackageReservation(
            "WASTE_ROUTES",
            "INFERIOR_DRAIN_BIASED_ROUTES_TO_REMOVABLE_CARTRIDGE",
            None,
            "CONSUME_CURRENT_WASTE_ROUTE_GEOMETRY; DRAINING_AND_RECOVERY_PHYSICAL_EVIDENCE_OPEN",
            "WET_DRAINABLE",
            "Avoid local liquid traps adjacent to dry bay seams.",
        ),
        PackageReservation(
            "WATER_RESERVOIR",
            "SUPERIOR_SERVICE_VOLUME_WITH_FILL_VENT_PICKUP_ACCESS",
            None,
            str(authority.get("fluid", "water_reservoir", "status")),
            "WET_REMOVABLE",
            "Gross and usable targets are authority-backed; final internal geometry and dead volume remain open.",
        ),
    )

    cmf_roles = (
        CMFRole(
            "compliant_interface",
            "SOFT_RECESSIVE_PERIMETER_AND_FACIAL_CONTACT",
            "SOFT_ELASTOMER_FAMILY_UNSELECTED",
            "LOW_GLOSS_EASY_WIPE_INTENT",
            "WARM_NEUTRAL_LOW_CONTRAST_TO_SHELL",
            "DESIGN_INTENT_ONLY_SAMPLE_CHEMICAL_STAIN_AND_DURABILITY_TESTING_REQUIRED",
        ),
        CMFRole(
            "control_status",
            "ONE_CONTROLLED_ACCENT_FOR_CLEAN_AND_STATE_FEEDBACK",
            "HMI_MATERIAL_STACK_UNSELECTED",
            "SATIN_OR_FLUSH_WINDOW_NO_DEEP_GROOVE",
            "DARK_NEUTRAL_WITH_ONE_RESTRAINED_COOL_ACCENT",
            "DESIGN_INTENT_ONLY_OPTICAL_AND_CLEANABILITY_SAMPLES_REQUIRED",
        ),
        CMFRole(
            "retention",
            "VISUALLY_LIGHT_LOW_CONTRAST_SUPPORT",
            "MANUAL_A_MATERIAL_SELECTION",
            "QUIET_MATTE_NON_METALLIC_INTENT",
            "LOW_CONTRAST_NEUTRAL",
            "DESIGN_INTENT_ONLY_MANUAL_A_MECHANICAL_RELEASE_EVIDENCE_GOVERNS",
        ),
        CMFRole(
            "rigid_shell",
            "PRIMARY_CALM_CONTINUOUS_FIELD",
            "RIGID_POLYMER_FAMILY_UNSELECTED",
            "LOW_SATIN_PROTOTYPE_EXPLORATION_WINDOW_8_TO_28_GU60_NOT_PRODUCTION_SPEC",
            "LIGHT_WARM_NEUTRAL",
            "DESIGN_INTENT_ONLY_PHYSICAL_PLAQUE_STAIN_FINGERPRINT_SCRATCH_AND_CLEANING_EVIDENCE_REQUIRED",
        ),
    )

    hmi = PhysicalHMIReservation(
        primary_action="CLEAN",
        primary_tactile_land_min_mm=10.0,
        secondary_tactile_land_min_mm=8.0,
        minimum_control_separation_mm=2.0,
        status_window_minor_axis_min_mm=2.0,
        status_window_recess_max_mm=0.60,
        location_intent="WEARER_RIGHT_UPPER_SIDE_TURNOVER_OUTSIDE_PRIMARY_FRONTAL_HIGHLIGHT_AND_WET_SERVICE_GRIP",
        geometry_status="VISIBLE_SURFACE_PLACEMENT_RESERVED; SWITCH_LED_AND_SEAL_STACK_UNSELECTED",
        app_independent=True,
        evidence_status="PROTOTYPE_HMI_DESIGN_TARGET_NOT_VALIDATED_USABILITY_OR_ACCESSIBILITY_EVIDENCE",
    )

    architecture = ManualBArchitecture(
        source_authority_revision=str(authority.get("project", "authority_revision")),
        packages=packages,
        cmf_roles=cmf_roles,
        hmi=hmi,
        charging_policy="NO_ACTIVE_WET_CYCLE_CHARGING; CONNECTOR_TYPE_AND_INGRESS_ARCHITECTURE_UNSELECTED",
        active_wet_cycle_charging_authorized=False,
        drainage_policy="WET_DRAINABLE_PATHS_BIAS_TO_INFERIOR_SERVICE_EXIT; NO_BLIND_WELLS_AGAINST_DRY_BAY_BOUNDARIES",
        seam_policy="VISIBLE_SEAMS_ON_LOW_HIGHLIGHT_TURNOVERS; WET_SERVICE_SEAMS_MUST_REMAIN_WIPEABLE_AND_DRAINABLE",
    )
    architecture.validate_current_authority(authority)
    return architecture
