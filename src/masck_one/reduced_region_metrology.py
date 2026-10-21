"""Bounded data reduction for unpowered, off-face inert-surrogate trials.

Absolute uncertainties are worst-case bounds, not statistical confidence or
independent Gaussian errors. Raw records/calibrations must be retained and
independently reviewed. No method here authenticates a measurement, establishes
acceptance limits, or promotes BENCH/HUMAN/SPF evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path

from . import _contracts


class MetrologyError(ValueError):
    pass


@dataclass(frozen=True)
class Measurement:
    value: float
    uncertainty: float
    unit: str
    source_record: str
    calibration_record: str

    def __post_init__(self):
        _contracts.non_negative(self.value, 'measured value', MetrologyError)
        _contracts.non_negative(self.uncertainty, 'absolute uncertainty', MetrologyError)
        for key in ('unit', 'source_record', 'calibration_record'):
            _contracts.non_empty_text(getattr(self, key), key, MetrologyError)

    @property
    def bounds(self):
        # A raw nonnegative quantity cannot physically fall below zero.
        upper = self.value + self.uncertainty
        _contracts.finite(upper, 'measurement upper bound', MetrologyError)
        return (max(0., self.value - self.uncertainty), upper)


def same_unit(*measurements):
    if not measurements or any(not isinstance(m, Measurement) for m in measurements):
        raise MetrologyError('explicit measured quantities required')
    if len({m.unit for m in measurements}) != 1:
        raise MetrologyError('unit mismatch; conversion must be explicit upstream')


def mass_closure(introduced, recovered, retained, fixture_transfer, collected_loss):
    """Disjoint final inventories, including retained intended film, all in g.

    The five records are separately supplied even when a measured value is zero.
    Internal transfers cannot be counted again as recovered or collected loss.
    """
    records = (introduced, recovered, retained, fixture_transfer, collected_loss)
    same_unit(*records)
    if introduced.unit != 'g':
        raise MetrologyError('mass inventory requires grams')
    nominal = introduced.value - sum(m.value for m in records[1:])
    lower = introduced.bounds[0] - sum(m.bounds[1] for m in records[1:])
    upper = introduced.bounds[1] - sum(m.bounds[0] for m in records[1:])
    for value in (nominal, lower, upper):
        _contracts.finite(value, 'mass closure', MetrologyError)
    return {'signed_residual_g': nominal, 'residual_bounds_g': [lower, upper],
            'absolute_error_upper_g': max(abs(lower), abs(upper)),
            'absolute_error_lower_g': 0. if lower <= 0 <= upper else min(abs(lower), abs(upper))}


def blank_corrected(signal, blank):
    """A blank interval is subtracted, never silently substituted by zero."""
    same_unit(signal, blank)
    lo = signal.bounds[0] - blank.bounds[1]
    hi = signal.bounds[1] - blank.bounds[0]
    if hi < 0:
        return None  # Even the maximum corrected signal is negative.
    return (max(0., lo), hi)


def ratio_bounds(numerator, denominator):
    # Validate both supplied intervals before an unknown sibling can short-circuit.
    for interval in (numerator, denominator):
        if interval is None:
            continue
        if type(interval) not in (tuple, list) or len(interval) != 2:
            raise MetrologyError('ratio interval requires two ordered nonnegative bounds')
        for bound in interval:
            _contracts.non_negative(bound, 'ratio input bound', MetrologyError)
        if interval[0] > interval[1]:
            raise MetrologyError('ratio interval bounds are reversed')
    if numerator is None or denominator is None or denominator[0] <= 0:
        return None
    bounds = [numerator[0] / denominator[1], numerator[1] / denominator[0]]
    for value in bounds:
        _contracts.non_negative(value, 'ratio bound', MetrologyError)
    return bounds


def carryover_fraction(residual, residual_blank, total, total_blank):
    """Previous-material mass / total sampled material mass, blank corrected.

    Both quantities must be independently calibrated to the same mass basis.
    Raw fluorescence/intensity ratios cannot establish material fraction. A
    distinguishable previous-material method is an explicit campaign input.
    """
    same_unit(residual, residual_blank, total, total_blank)
    if residual.unit != 'g':
        raise MetrologyError('carryover requires calibrated material masses in grams')
    return ratio_bounds(blank_corrected(residual, residual_blank),
                        blank_corrected(total, total_blank))


def film_retention(before, before_blank, after, after_blank):
    """Same-cell post/pre retained mass; deliberately no dispensed-dose proxy."""
    same_unit(before, before_blank, after, after_blank)
    if before.unit != 'g':
        raise MetrologyError('film retention requires calibrated film masses in grams')
    return ratio_bounds(blank_corrected(after, after_blank),
                        blank_corrected(before, before_blank))


def reduce_campaign(record: dict) -> dict:
    """Reduce per-cell measurements, preserving unknowns and source binding.

    This is a method-screen report, not an assess_trial receipt. Spatial coverage,
    calibrated photographs, distinct-layer identity, limits and repeatability
    remain obligations of the existing predeclared trial protocol/reviewer.
    """
    if type(record) is not dict:
        raise MetrologyError('campaign must be an object')
    try:
        raw = json.dumps(record, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    except (ValueError, TypeError) as exc:
        raise MetrologyError('finite canonical JSON record required') from exc
    if record.get('scope') != 'INERT_SURROGATE_OFF_FACE':
        raise MetrologyError('off-face inert-surrogate scope required')
    for key in ('specimen_id', 'stage_id', 'previous_material_id', 'current_material_id'):
        _contracts.non_empty_text(record.get(key), key, MetrologyError)
    from .core_sketch_trial import TRIAL_STEPS
    if record['stage_id'] not in TRIAL_STEPS:
        raise MetrologyError('declared reduced-region stage required')
    required = record.get('required_cells')
    if (type(required) is not list or not required or
        any(type(c) is not str or not c.strip() for c in required) or
        len(set(required)) != len(required)):
        raise MetrologyError('explicit unique required cells needed')
    rows = record.get('cells')
    if type(rows) is not list:
        raise MetrologyError('measurement cells must be a list')
    cells = {}
    for row in rows:
        if type(row) is not dict:
            raise MetrologyError('cell must be an object')
        ident = _contracts.non_empty_text(row.get('id'), 'cell id', MetrologyError)
        if ident in cells or ident not in required:
            raise MetrologyError('duplicate or undeclared cell')
        cells[ident] = row
    blockers, metrics = [], {}
    protocol_hash = record.get('predeclared_protocol_sha256')
    if protocol_hash is None:
        blockers.append('PREDECLARED_PROTOCOL_BINDING_UNKNOWN')
    elif (type(protocol_hash) is not str or len(protocol_hash) != 64 or
          any(c not in '0123456789abcdef' for c in protocol_hash)):
        raise MetrologyError('protocol binding must be a SHA-256 digest or null')
    groups = {
        'mass_closure': ('introduced', 'recovered', 'retained', 'fixture_transfer', 'collected_loss'),
        'carryover_fraction': ('residual', 'residual_blank', 'total', 'total_blank'),
        'film_retention': ('before', 'before_blank', 'after', 'after_blank'),
        'reference_film_retention': ('before', 'before_blank', 'after', 'after_blank'),
    }
    for ident in required:
        row = cells.get(ident, {})
        metrics[ident] = {}
        if row.get('previous_material_distinguishable') is not True:
            blockers.append(ident + ':CARRYOVER_METHOD_NOT_DISTINGUISHABLE')
        for group, names in groups.items():
            values = row.get(group, {})
            if type(values) is not dict:
                raise MetrologyError('measurement group must be an object')
            if set(values) - set(names):
                raise MetrologyError('undeclared inventory or ratio input')
            # Validate every supplied measurement, even if a sibling is absent.
            parsed = {}
            for key, value in values.items():
                if value is not None:
                    if type(value) is not dict:
                        raise MetrologyError('measurement must be an object or null')
                    try:
                        parsed[key] = Measurement(**value)
                    except TypeError as exc:
                        raise MetrologyError('exact measurement fields required') from exc
            if set(parsed) != set(names):
                metrics[ident][group] = None
                blockers.append(ident + ':' + group + ':MEASUREMENTS_UNKNOWN')
                continue
            method = mass_closure if group == 'mass_closure' else (
                carryover_fraction if group == 'carryover_fraction' else film_retention)
            output = method(*(parsed[k] for k in names))
            metrics[ident][group] = output
            if output is None:
                blockers.append(ident + ':' + group + ':SIGNAL_OR_DENOMINATOR_UNRESOLVED')
            elif group != 'mass_closure' and output[0] > 1:
                blockers.append(ident + ':' + group + ':FRACTION_INCONSISTENT_OR_REDISTRIBUTED')
        film, reference = (metrics[ident][k] for k in ('film_retention', 'reference_film_retention'))
        metrics[ident]['retention_minus_reference_bounds'] = (
            [film[0] - reference[1], film[1] - reference[0]] if film and reference else None)
    return {'schema': 'MASCK_REDUCED_REGION_METROLOGY_1',
            'classification': 'SUPPLIED_MEASUREMENT_DATA_REDUCTION_NOT_AUTHENTICATED_EVIDENCE',
            'input_sha256': sha256(raw).hexdigest(),
            'predeclared_protocol_sha256': protocol_hash,
            'specimen_id': record['specimen_id'], 'stage_id': record['stage_id'],
            'previous_material_id': record['previous_material_id'],
            'current_material_id': record['current_material_id'],
            'producer_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
            'metrics_by_cell': metrics, 'method_blockers': sorted(set(blockers)),
            'uncertainty_model': 'ABSOLUTE_WORST_CASE_INTERVALS_NO_CONFIDENCE_CLAIM',
            'acceptance_limits_established': False, 'bench_evidence_accepted': False,
            'whole_face_complete': False, 'human_use_authorized': False, 'spf_validated': False}


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = reduce_campaign(json.loads(args.input.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + '\n')
    print(json.dumps({'method_blockers': report['method_blockers'], 'bench_evidence_accepted': False}))


if __name__ == '__main__':
    main()
