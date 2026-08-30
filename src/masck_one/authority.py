from __future__ import annotations

import argparse
from collections.abc import Hashable, Iterable
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
import yaml


class AuthorityError(ValueError):
    """Raised when the machine authority is incomplete or internally invalid."""


@dataclass(frozen=True)
class AuthorityValidationIssue:
    """One deterministic authority-contract violation."""

    code: str
    path: str
    message: str
    actual: object | None = None
    expected: object | None = None

    def to_dict(self) -> dict[str, object | None]:
        return asdict(self)


@dataclass(frozen=True)
class AuthorityValidationReport:
    """Complete schema + semantic validation result for one authority document."""

    source: str
    schema: str
    valid: bool
    issues: tuple[AuthorityValidationIssue, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "schema": self.schema,
            "valid": self.valid,
            "issue_count": len(self.issues),
            "issues": [issue.to_dict() for issue in self.issues],
        }

    def format_errors(self) -> str:
        if self.valid:
            return "authority valid"
        return "; ".join(
            f"{issue.code} at {issue.path}: {issue.message}" for issue in self.issues
        )


@dataclass(frozen=True)
class Authority:
    """Typed access wrapper around the validated Masck One YAML authority."""

    data: dict[str, Any]
    source: Path
    validation_report: AuthorityValidationReport

    def get(self, *path: str) -> Any:
        node: Any = self.data
        for key in path:
            if not isinstance(node, dict) or key not in node:
                joined = ".".join(path)
                raise AuthorityError(f"Missing authority path: {joined}")
            node = node[key]
        return node

    def number(self, *path: str) -> float:
        value = self.get(*path)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise AuthorityError(f"Expected numeric value at {'.'.join(path)}, got {value!r}")
        return float(value)

    def pair(self, *path: str) -> tuple[float, float]:
        value = self.get(*path)
        if not isinstance(value, list) or len(value) != 2:
            raise AuthorityError(f"Expected 2-item list at {'.'.join(path)}, got {value!r}")
        return float(value[0]), float(value[1])

    def triple(self, *path: str) -> tuple[float, float, float]:
        value = self.get(*path)
        if not isinstance(value, list) or len(value) != 3:
            raise AuthorityError(f"Expected 3-item list at {'.'.join(path)}, got {value!r}")
        return float(value[0]), float(value[1]), float(value[2])

    def require_paths(self, paths: Iterable[tuple[str, ...]]) -> None:
        for path in paths:
            self.get(*path)


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys instead of overwriting them."""


def _construct_unique_mapping(
    loader: _UniqueKeySafeLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, Hashable):
            raise AuthorityError(
                f"Unhashable YAML mapping key at line {key_node.start_mark.line + 1}"
            )
        if key in mapping:
            raise AuthorityError(
                f"Duplicate YAML key {key!r} at line {key_node.start_mark.line + 1}"
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def default_authority_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "masck_one_authority.yaml"


def default_schema_path() -> Path:
    return Path(__file__).resolve().parents[2] / "schemas" / "masck_one_authority.schema.json"


def _read_authority_yaml(source: Path) -> dict[str, Any]:
    if not source.exists():
        raise AuthorityError(f"Authority file does not exist: {source}")
    try:
        with source.open("r", encoding="utf-8") as handle:
            raw = yaml.load(handle, Loader=_UniqueKeySafeLoader)
    except yaml.YAMLError as exc:
        raise AuthorityError(f"Authority YAML cannot be parsed: {exc}") from exc
    if not isinstance(raw, dict):
        raise AuthorityError("Authority root must be a mapping")
    return raw


def _read_schema(source: Path) -> dict[str, Any]:
    if not source.exists():
        raise AuthorityError(f"Authority schema does not exist: {source}")
    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AuthorityError(f"Authority schema is not valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise AuthorityError("Authority schema root must be an object")
    try:
        Draft202012Validator.check_schema(raw)
    except Exception as exc:  # jsonschema raises several schema-specific subclasses
        raise AuthorityError(f"Authority schema itself is invalid: {exc}") from exc
    return raw


def _json_path(parts: Iterable[object]) -> str:
    rendered = ".".join(str(part) for part in parts)
    return rendered or "<root>"


def _schema_issues(data: dict[str, Any], schema: dict[str, Any]) -> list[AuthorityValidationIssue]:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda error: list(error.absolute_path))
    issues: list[AuthorityValidationIssue] = []
    for error in errors:
        code = f"SCHEMA_{str(error.validator).upper()}"
        issues.append(
            AuthorityValidationIssue(
                code=code,
                path=_json_path(error.absolute_path),
                message=error.message,
            )
        )
    return issues


def _get(data: dict[str, Any], *path: str) -> Any:
    node: Any = data
    for key in path:
        node = node[key]
    return node


def _isclose(a: float, b: float, *, abs_tol: float = 1e-9) -> bool:
    return math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=abs_tol)


def _contains_close(values: Iterable[float], target: float) -> bool:
    return any(_isclose(float(value), float(target)) for value in values)


def _semantic_issues(data: dict[str, Any]) -> list[AuthorityValidationIssue]:
    """Validate relationships that JSON Schema cannot express clearly.

    These checks are intentionally limited to deterministic internal consistency.
    They do not claim physical validation of fit, safety, efficacy, materials, or suppliers.
    """

    issues: list[AuthorityValidationIssue] = []

    def add(
        code: str,
        path: str,
        message: str,
        actual: object | None = None,
        expected: object | None = None,
    ) -> None:
        issues.append(AuthorityValidationIssue(code, path, message, actual, expected))

    origin = [float(v) for v in _get(data, "coordinate_system", "origin")]
    if origin != [0.0, 0.0, 0.0]:
        add(
            "DATUM_ORIGIN_DRIFT",
            "coordinate_system.origin",
            "The frozen global origin may not drift silently.",
            origin,
            [0.0, 0.0, 0.0],
        )

    outer = [float(v) for v in _get(data, "geometry", "outer_xy_envelope_mm")]
    frame = [float(v) for v in _get(data, "geometry", "functional_frame_xy_mm")]
    if any(frame_value > outer_value for frame_value, outer_value in zip(frame, outer, strict=True)):
        add(
            "FRAME_EXCEEDS_OUTER_ENVELOPE",
            "geometry.functional_frame_xy_mm",
            "The functional frame cannot exceed the declared outer XY envelope.",
            frame,
            {"not_greater_than": outer},
        )

    wall = float(_get(data, "geometry", "shell_nominal_wall_mm"))
    wall_min = float(_get(data, "geometry", "shell_absolute_development_min_mm"))
    if wall < wall_min:
        add(
            "SHELL_WALL_ORDER",
            "geometry.shell_nominal_wall_mm",
            "Nominal shell wall must not be below the absolute development minimum.",
            wall,
            {"minimum": wall_min},
        )

    left_eye = [float(v) for v in _get(data, "geometry", "eye", "centers_mm", "left")]
    right_eye = [float(v) for v in _get(data, "geometry", "eye", "centers_mm", "right")]
    if not (_isclose(left_eye[0], -right_eye[0]) and _isclose(left_eye[1], right_eye[1])):
        add(
            "EYE_BASELINE_SYMMETRY",
            "geometry.eye.centers_mm",
            "The current neutral baseline eye centers must remain sagittally symmetric.",
            {"left": left_eye, "right": right_eye},
            "left.x = -right.x and left.y = right.y",
        )

    left_nostril = [float(v) for v in _get(data, "geometry", "nostrils", "centers_mm", "left")]
    right_nostril = [float(v) for v in _get(data, "geometry", "nostrils", "centers_mm", "right")]
    if not (
        _isclose(left_nostril[0], -right_nostril[0])
        and _isclose(left_nostril[1], right_nostril[1])
    ):
        add(
            "NOSTRIL_BASELINE_SYMMETRY",
            "geometry.nostrils.centers_mm",
            "The current neutral baseline nostril centers must remain sagittally symmetric.",
            {"left": left_nostril, "right": right_nostril},
            "left.x = -right.x and left.y = right.y",
        )

    mouth = [float(v) for v in _get(data, "geometry", "mouth", "center_mm")]
    if not _isclose(mouth[0], 0.0):
        add(
            "MOUTH_BASELINE_CENTERLINE",
            "geometry.mouth.center_mm",
            "The current neutral baseline mouth center must lie on the sagittal centerline.",
            mouth,
            {"x": 0.0},
        )

    geometry_airway_area = float(
        _get(data, "geometry", "nostrils", "minimum_deformed_area_each_mm2")
    )
    safety_airway_area = float(_get(data, "safety", "airway", "minimum_area_each_mm2"))
    if not _isclose(geometry_airway_area, safety_airway_area):
        add(
            "AIRWAY_AREA_DUPLICATION_MISMATCH",
            "safety.airway.minimum_area_each_mm2",
            "The duplicated airway-area safety value must exactly match the geometry authority.",
            safety_airway_area,
            geometry_airway_area,
        )

    geometry_airway_dim = float(
        _get(data, "geometry", "nostrils", "minimum_local_opening_dimension_mm")
    )
    safety_airway_dim = float(_get(data, "safety", "airway", "minimum_local_dimension_mm"))
    if not _isclose(geometry_airway_dim, safety_airway_dim):
        add(
            "AIRWAY_DIMENSION_DUPLICATION_MISMATCH",
            "safety.airway.minimum_local_dimension_mm",
            "The duplicated airway local-dimension value must exactly match the geometry authority.",
            safety_airway_dim,
            geometry_airway_dim,
        )

    dp30 = float(_get(data, "safety", "airway", "max_added_pressure_drop_pa", "at_30_lpm"))
    dp60 = float(_get(data, "safety", "airway", "max_added_pressure_drop_pa", "at_60_lpm"))
    if dp30 > dp60:
        add(
            "AIRWAY_PRESSURE_DROP_ORDER",
            "safety.airway.max_added_pressure_drop_pa",
            "The higher-flow pressure-drop allowance cannot be lower than the lower-flow allowance.",
            {"30_lpm": dp30, "60_lpm": dp60},
            "at_30_lpm <= at_60_lpm",
        )

    branch_volume = float(_get(data, "safety", "fluid_fault", "max_uncontrolled_branch_uL"))
    total_volume = float(_get(data, "safety", "fluid_fault", "max_uncontrolled_total_uL"))
    if branch_volume > total_volume:
        add(
            "FLUID_FAULT_VOLUME_ORDER",
            "safety.fluid_fault.max_uncontrolled_branch_uL",
            "A single-branch uncontrolled-volume limit cannot exceed the total limit.",
            branch_volume,
            {"maximum": total_volume},
        )

    pressure = _get(data, "safety", "pressure")
    dynamic_pressure = float(pressure["dynamic_max_kPa"])
    regional_pressure_max = max(
        float(pressure["bridge_p95_max_kPa"]),
        float(pressure["bridge_steady_max_kPa"]),
        float(pressure["cheek_p95_max_kPa"]),
    )
    if dynamic_pressure < regional_pressure_max:
        add(
            "PRESSURE_LIMIT_ORDER",
            "safety.pressure.dynamic_max_kPa",
            "The transient/dynamic maximum must not be below a regional steady/P95 limit.",
            dynamic_pressure,
            {"minimum": regional_pressure_max},
        )

    strain_p95 = float(_get(data, "safety", "membrane_strain", "p95_max_percent"))
    strain_local = float(_get(data, "safety", "membrane_strain", "local_max_percent"))
    if strain_local < strain_p95:
        add(
            "MEMBRANE_STRAIN_ORDER",
            "safety.membrane_strain.local_max_percent",
            "Local absolute strain maximum must not be lower than the P95 strain limit.",
            strain_local,
            {"minimum": strain_p95},
        )

    release_force = [float(v) for v in _get(data, "safety", "quick_release", "force_target_N")]
    if release_force[0] > release_force[1]:
        add(
            "QUICK_RELEASE_FORCE_RANGE_ORDER",
            "safety.quick_release.force_target_N",
            "Quick-release force range must be ordered minimum to maximum.",
            release_force,
            "min <= max",
        )

    membrane_center = float(_get(data, "geometry", "nasal_lobe_membrane", "thickness_center_mm"))
    membrane_doe = [float(v) for v in _get(data, "geometry", "nasal_lobe_membrane", "thickness_doe_mm")]
    if not _contains_close(membrane_doe, membrane_center):
        add(
            "MEMBRANE_CENTER_NOT_IN_DOE",
            "geometry.nasal_lobe_membrane.thickness_doe_mm",
            "The declared membrane center point must be explicitly represented in its DOE set.",
            membrane_doe,
            {"must_contain": membrane_center},
        )

    actuator_angle = float(_get(data, "actuation", "clean", "axis_angle_baseline_deg"))
    actuator_doe = [float(v) for v in _get(data, "actuation", "clean", "axis_angle_doe_deg")]
    if not _contains_close(actuator_doe, actuator_angle):
        add(
            "ACTUATOR_ANGLE_CENTER_NOT_IN_DOE",
            "actuation.clean.axis_angle_doe_deg",
            "The CLEAN actuator-axis center point must be represented in the DOE set.",
            actuator_doe,
            {"must_contain": actuator_angle},
        )

    continuous_force = float(_get(data, "actuation", "clean", "continuous_force_requirement_N"))
    transient_force = float(_get(data, "actuation", "clean", "transient_force_requirement_N"))
    if transient_force < continuous_force:
        add(
            "ACTUATOR_FORCE_ORDER",
            "actuation.clean.transient_force_requirement_N",
            "Transient actuator-force requirement must not be below the continuous requirement.",
            transient_force,
            {"minimum": continuous_force},
        )

    gross_water = float(_get(data, "fluid", "water_reservoir", "gross_mL"))
    usable_water = float(_get(data, "fluid", "water_reservoir", "minimum_usable_mL"))
    if usable_water > gross_water:
        add(
            "WATER_RESERVOIR_VOLUME_ORDER",
            "fluid.water_reservoir.minimum_usable_mL",
            "Minimum usable water volume cannot exceed gross reservoir volume.",
            usable_water,
            {"maximum": gross_water},
        )

    face_water = float(_get(data, "fluid", "clean_cycle", "face_water_mL"))
    cleanser = float(_get(data, "fluid", "clean_cycle", "cleanser_mL"))
    flush = float(_get(data, "fluid", "clean_cycle", "post_flush_water_mL"))
    nominal = float(_get(data, "fluid", "clean_cycle", "nominal_introduced_liquid_mL"))
    nominal_derived = face_water + cleanser + flush
    if not _isclose(nominal, nominal_derived, abs_tol=1e-8):
        add(
            "CLEAN_CYCLE_LEDGER_MISMATCH",
            "fluid.clean_cycle.nominal_introduced_liquid_mL",
            "Nominal introduced liquid must equal face water + cleanser + post-flush water.",
            nominal,
            nominal_derived,
        )

    prime = float(_get(data, "fluid", "clean_cycle", "maximum_initial_prime_mL"))
    service_cycles = int(_get(data, "fluid", "cartridge", "service_cycles_baseline"))
    cartridge_capacity = float(_get(data, "fluid", "cartridge", "retained_capacity_min_mL"))
    required_with_margin = 1.25 * (service_cycles * nominal + prime)
    if cartridge_capacity + 1e-8 < required_with_margin:
        add(
            "CARTRIDGE_CAPACITY_LEDGER_MARGIN",
            "fluid.cartridge.retained_capacity_min_mL",
            "Current retained-capacity baseline must cover the service-cycle liquid ledger plus the authority's 25% system margin.",
            cartridge_capacity,
            {"minimum": required_with_margin},
        )

    dry_mass = float(_get(data, "mass", "dry_target_max_g"))
    loaded_mass = float(_get(data, "mass", "loaded_absolute_max_g"))
    if dry_mass > loaded_mass:
        add(
            "MASS_LIMIT_ORDER",
            "mass.dry_target_max_g",
            "Dry mass target cannot exceed the absolute loaded mass ceiling.",
            dry_mass,
            {"maximum": loaded_mass},
        )

    rib_range = [float(v) for v in _get(data, "manufacturing", "rib_thickness_ratio_range")]
    if rib_range[0] > rib_range[1]:
        add(
            "RIB_RATIO_RANGE_ORDER",
            "manufacturing.rib_thickness_ratio_range",
            "Rib-thickness ratio range must be ordered minimum to maximum.",
            rib_range,
            "min <= max",
        )

    rms = float(_get(data, "manufacturing", "a_surface", "rms_deviation_max_mm"))
    maximum = float(_get(data, "manufacturing", "a_surface", "max_deviation_mm"))
    if rms > maximum:
        add(
            "A_SURFACE_DEVIATION_ORDER",
            "manufacturing.a_surface.rms_deviation_max_mm",
            "RMS surface-deviation allowance cannot exceed the absolute maximum allowance.",
            rms,
            {"maximum": maximum},
        )

    if (
        _get(data, "commercial", "initial_state") == "PAID_PREORDER"
        and not bool(_get(data, "commercial", "paid_preorder_gate"))
    ):
        add(
            "COMMERCIAL_STATE_GATE_CONTRADICTION",
            "commercial.initial_state",
            "PAID_PREORDER cannot be the initial state while its private evidence gate is false.",
            "PAID_PREORDER",
            "EARLY_ACCESS or RESERVATION while paid_preorder_gate=false",
        )

    required_classifications = {
        "coordinate_system.status": "FROZEN_DATUM",
        "safety.airway.no_collapse_status": "FROZEN_SAFETY_REQUIREMENT",
        "safety.quick_release.time_status": "FROZEN_SAFETY_REQUIREMENT",
        "safety.quick_release.one_hand_wet_unpowered_status": "FROZEN_SAFETY_REQUIREMENT",
        "actuation.architecture_status": "FROZEN_ARCHITECTURE",
        "mass.loaded_absolute_max_status": "PROJECT_REQUIREMENT",
        "manufacturing.hygiene_classification_status": "FROZEN_REQUIREMENT",
    }
    for dotted_path, expected in required_classifications.items():
        actual = _get(data, *dotted_path.split("."))
        if actual != expected:
            add(
                "AUTHORITY_CLASSIFICATION_DRIFT",
                dotted_path,
                "A protected authority classification changed without updating the contract validator.",
                actual,
                expected,
            )

    return issues


def validate_authority_data(
    data: dict[str, Any],
    *,
    source: str = "<memory>",
    schema_path: str | Path | None = None,
) -> AuthorityValidationReport:
    schema_source = Path(schema_path) if schema_path is not None else default_schema_path()
    schema_source = schema_source.resolve()
    schema = _read_schema(schema_source)

    issues = _schema_issues(data, schema)
    if not issues:
        issues.extend(_semantic_issues(data))

    return AuthorityValidationReport(
        source=source,
        schema=str(schema_source),
        valid=not issues,
        issues=tuple(issues),
    )


def validate_authority_path(
    path: str | Path | None = None,
    *,
    schema_path: str | Path | None = None,
) -> AuthorityValidationReport:
    source = Path(path) if path is not None else default_authority_path()
    source = source.resolve()
    schema_source = Path(schema_path) if schema_path is not None else default_schema_path()
    schema_source = schema_source.resolve()
    try:
        data = _read_authority_yaml(source)
        return validate_authority_data(data, source=str(source), schema_path=schema_source)
    except AuthorityError as exc:
        return AuthorityValidationReport(
            source=str(source),
            schema=str(schema_source),
            valid=False,
            issues=(
                AuthorityValidationIssue(
                    code="AUTHORITY_PARSE_OR_SCHEMA_ERROR",
                    path="<document>",
                    message=str(exc),
                ),
            ),
        )


def load_authority(
    path: str | Path | None = None,
    *,
    schema_path: str | Path | None = None,
) -> Authority:
    source = Path(path) if path is not None else default_authority_path()
    source = source.resolve()
    data = _read_authority_yaml(source)
    report = validate_authority_data(data, source=str(source), schema_path=schema_path)
    if not report.valid:
        raise AuthorityError(report.format_errors())

    authority = Authority(data, source, report)
    authority.require_paths(
        [
            ("project", "name"),
            ("project", "id"),
            ("coordinate_system", "origin"),
            ("geometry", "outer_xy_envelope_mm"),
            ("geometry", "shell_nominal_wall_mm"),
            ("geometry", "eye", "centers_mm", "left"),
            ("geometry", "eye", "centers_mm", "right"),
            ("geometry", "eye", "visual_aperture_wh_mm"),
            ("geometry", "mouth", "center_mm"),
            ("geometry", "mouth", "visual_aperture_wh_mm"),
            ("geometry", "nostrils", "centers_mm", "left"),
            ("geometry", "nostrils", "centers_mm", "right"),
            ("geometry", "nostrils", "minimum_deformed_area_each_mm2"),
            ("actuation", "count"),
            ("fluid", "water_reservoir", "gross_mL"),
            ("fluid", "cartridge", "external_envelope_mm"),
        ]
    )
    return authority


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the Masck One machine engineering authority.")
    parser.add_argument("authority", nargs="?", default=None, help="Optional authority YAML path")
    parser.add_argument("--schema", default=None, help="Optional JSON Schema path")
    args = parser.parse_args(argv)

    report = validate_authority_path(args.authority, schema_path=args.schema)
    print(json.dumps(report.to_dict(), indent=2))
    return 0 if report.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
