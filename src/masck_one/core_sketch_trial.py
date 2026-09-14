"""Off-face inert-surrogate data completeness and declared-limit screening.

No human-use parameters, chemical recipes, powered treatment or hardware control.
A consistent record is only a candidate for independent bench-evidence review.
"""
from .core_sketch_contracts import CoreSketchError, digest, number, result, text, unique

TRIAL_STEPS = ('CLEAN', 'RINSE_RECOVER', 'THIN_LEAVE_ON', 'THICK_LEAVE_ON',
               'FINAL_LEAVE_ON', 'SETTLE', 'RELEASE')


def assess_trial(protocol: dict, trial: dict) -> dict:
    digest([protocol, trial])
    if protocol.get('scope') != 'INERT_SURROGATE_OFF_FACE' or trial.get('scope') != protocol['scope']:
        raise CoreSketchError('this package only screens off-face inert-surrogate records')
    cells = protocol.get('required_cells')
    if type(cells) is not list or not cells or any(type(c) is not str or not c for c in cells) or len(set(cells)) != len(cells):
        raise CoreSketchError('explicit unique coupon observation cells required')
    blockers = []
    if trial.get('protocol_digest') != digest(protocol):
        blockers.append('PREDECLARED_PROTOCOL_CHANGED')
    if not protocol.get('independent_review_record'):
        blockers.append('PROTOCOL_AND_LIMITS_NOT_REVIEWED')
    limits = protocol.get('limits', {})
    keys = {'max_mass_balance_error_g', 'max_carryover_fraction', 'min_film_retention_fraction', 'max_protected_deposit_g'}
    if set(limits) != keys:
        raise CoreSketchError('all declared acceptance limits required')
    for key, value in limits.items():
        if value is None:
            blockers.append(key + ':LIMIT_NOT_ESTABLISHED')
        elif number(value, key) > 1 and 'fraction' in key:
            raise CoreSketchError('fraction limit above one')
    if trial.get('completed_order') != list(TRIAL_STEPS):
        blockers.append('SEQUENCE_INCOMPLETE')
    stages = unique(trial.get('stages', []))
    if set(stages) != set(TRIAL_STEPS):
        blockers.append('STAGE_INVENTORY_INCOMPLETE')
    for ident in TRIAL_STEPS:
        stage = stages.get(ident, {})
        rows = unique(stage.get('cells', []))
        if set(rows) != set(cells):
            blockers.append(ident + ':COVERAGE_CELLS_MISSING')
        if not stage.get('photograph_records') or not stage.get('balance_calibration_record'):
            blockers.append(ident + ':TRACEABILITY_MISSING')
        if stage.get('unknown_or_occluded_cells') != []:
            blockers.append(ident + ':OCCLUDED_OR_UNKNOWN_CELL')
        for cell in cells:
            row = rows.get(cell, {})
            if row.get('covered') is not True:
                blockers.append(ident + ':' + cell + ':NOT_COVERED')
            for metric, limit in [('mass_balance_error_g','max_mass_balance_error_g'),
                                  ('carryover_fraction','max_carryover_fraction'),
                                  ('protected_deposit_g','max_protected_deposit_g')]:
                value, uncertainty = row.get(metric), row.get(metric + '_uncertainty')
                if value is None or uncertainty is None:
                    blockers.append(ident + ':' + cell + ':' + metric + ':UNKNOWN')
                elif limits[limit] is not None and number(value, metric) + number(uncertainty, metric) > limits[limit]:
                    blockers.append(ident + ':' + cell + ':' + metric + ':LIMIT_EXCEEDED')
            if ident in {'FINAL_LEAVE_ON','SETTLE','RELEASE'}:
                retained, uncertainty = row.get('film_retention_fraction'), row.get('film_retention_fraction_uncertainty')
                if retained is None or uncertainty is None:
                    blockers.append(ident + ':' + cell + ':FILM_SURVIVAL_UNKNOWN')
                elif number(retained, 'retention') > 1:
                    blockers.append(ident + ':' + cell + ':FILM_MEASUREMENT_INCONSISTENT')
                elif limits['min_film_retention_fraction'] is not None and number(retained, 'retention') - number(uncertainty, 'retention uncertainty') < limits['min_film_retention_fraction']:
                    blockers.append(ident + ':' + cell + ':FILM_NOT_PRESERVED')
    return result(blockers, candidate_for_independent_bench_review=not blockers,
        whole_face_complete=False, spf_validated=False, human_use_authorized=False)
