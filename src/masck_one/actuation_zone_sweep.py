"""Four-zone actuation impedance sweep completeness and provenance checks."""
from __future__ import annotations

from dataclasses import dataclass

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

    @property
    def point_count(self) -> int:
        return len(self.records)
