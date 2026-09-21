"""Four-zone actuation impedance sweep completeness and provenance checks."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping

from .actuation_parameters import ActuationParameterError, ActuationParameterSet, ImpedanceTestRecord
from .actuator_frames import ZONE_IDS


def _canonical_sha256(value: object, *, label: str) -> str:
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ActuationParameterError(f"{label} must be a canonical lowercase SHA-256 digest")
    return value


@dataclass(frozen=True, slots=True)
class ZoneImpedanceRecord:
    """Bind one impedance record to one controlled actuator zone."""

    zone_id: str
    record: ImpedanceTestRecord

    def __post_init__(self) -> None:
        if self.zone_id not in ZONE_IDS:
            raise ActuationParameterError(f"Unknown actuator zone {self.zone_id!r}")
        if type(self.record) is not ImpedanceTestRecord:
            raise ActuationParameterError("Zone impedance evidence requires exact ImpedanceTestRecord")


@dataclass(frozen=True, slots=True)
class ZoneMeasuredResponse:
    """Lossless extrema and requirement margins without declaring physical qualification."""

    zone_id: str
    point_count: int
    min_force_N: float
    max_force_N: float
    min_displacement_pp_mm: float
    max_displacement_pp_mm: float
    max_abs_displacement_error_mm: float
    min_continuous_force_margin_N: float
    min_transient_force_margin_N: float


@dataclass(frozen=True, slots=True)
class FourZoneImpedanceSweep:
    """A complete zone x axis-angle matrix at the authority-bound CLEAN command."""

    source_parameter_sha256: str
    records: tuple[ZoneImpedanceRecord, ...]

    def __post_init__(self) -> None:
        _canonical_sha256(self.source_parameter_sha256, label="four-zone sweep parameter identity")
        if type(self.records) is not tuple:
            raise ActuationParameterError("Four-zone sweep records must be an immutable tuple")
        if not self.records:
            raise ActuationParameterError("Four-zone sweep cannot contain empty evidence")

        observed: set[tuple[str, float]] = set()
        record_ids: set[str] = set()
        for item in self.records:
            if type(item) is not ZoneImpedanceRecord:
                raise ActuationParameterError("Four-zone sweep contains non-zone impedance evidence")
            if item.record.source_parameter_sha256 != self.source_parameter_sha256:
                raise ActuationParameterError(
                    "Four-zone sweep record parameter identity must match the sweep parameter identity"
                )
            key = (item.zone_id, float(item.record.axis_angle_deg))
            if key in observed:
                raise ActuationParameterError(f"Duplicate four-zone sweep point {key!r}")
            if item.record.record_id in record_ids:
                raise ActuationParameterError("Four-zone sweep record IDs must be unique")
            observed.add(key)
            record_ids.add(item.record.record_id)

    def validate(self, parameters: ActuationParameterSet) -> None:
        if type(parameters) is not ActuationParameterSet:
            raise ActuationParameterError("Four-zone sweep requires exact ActuationParameterSet evidence")
        if self.source_parameter_sha256 != parameters.parameter_sha256:
            raise ActuationParameterError("Four-zone sweep is stale for the supplied actuation parameter set")

        expected = {(zone_id, angle) for zone_id in ZONE_IDS for angle in parameters.axis_angle_doe_deg}
        observed: set[tuple[str, float]] = set()
        source_kinds: set[str] = set()

        for item in self.records:
            item.record.validate_command_envelope(parameters)
            observed.add((item.zone_id, float(item.record.axis_angle_deg)))
            source_kinds.add(item.record.source_kind)

        missing = expected - observed
        extra = observed - expected
        if missing or extra:
            raise ActuationParameterError(
                f"Four-zone sweep must cover every controlled zone x axis-angle point; missing={sorted(missing)!r}, extra={sorted(extra)!r}"
            )
        if len(source_kinds) != 1:
            raise ActuationParameterError("Four-zone sweep cannot mix predicted and measured evidence")

    def measured_response_by_zone(self, parameters: ActuationParameterSet) -> Mapping[str, ZoneMeasuredResponse]:
        """Reduce measured evidence to zone extrema and signed force margins, not qualification."""
        self.validate(parameters)
        if any(item.record.source_kind != "MEASURED" for item in self.records):
            raise ActuationParameterError("Measured response reduction requires a complete measured four-zone sweep")

        result: dict[str, ZoneMeasuredResponse] = {}
        target = parameters.displacement_pp_baseline_mm
        for zone_id in ZONE_IDS:
            zone_records = [item.record for item in self.records if item.zone_id == zone_id]
            forces = [record.measured_force_N for record in zone_records]
            displacements = [record.measured_displacement_pp_mm for record in zone_records]
            if any(value is None for value in forces + displacements):
                raise ActuationParameterError("Measured sweep lost required force or displacement observations")
            force_values = [float(value) for value in forces if value is not None]
            displacement_values = [float(value) for value in displacements if value is not None]
            minimum_force = min(force_values)
            result[zone_id] = ZoneMeasuredResponse(
                zone_id=zone_id,
                point_count=len(zone_records),
                min_force_N=minimum_force,
                max_force_N=max(force_values),
                min_displacement_pp_mm=min(displacement_values),
                max_displacement_pp_mm=max(displacement_values),
                max_abs_displacement_error_mm=max(abs(value - target) for value in displacement_values),
                min_continuous_force_margin_N=minimum_force - parameters.continuous_force_requirement_N,
                min_transient_force_margin_N=minimum_force - parameters.transient_force_requirement_N,
            )
        return result

    def manifest(self, *, include_sha: bool = True) -> Mapping[str, object]:
        """Return canonical, order-independent evidence for downstream provenance binding."""
        records = sorted(
            self.records,
            key=lambda item: (item.zone_id, float(item.record.axis_angle_deg), item.record.record_id),
        )
        payload: dict[str, object] = {
            "source_parameter_sha256": self.source_parameter_sha256,
            "records": [
                {"zone_id": item.zone_id, "record": dict(item.record.manifest())}
                for item in records
            ],
        }
        if include_sha:
            payload["sweep_sha256"] = self.sweep_sha256
        return payload

    @property
    def sweep_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    @property
    def point_count(self) -> int:
        return len(self.records)
