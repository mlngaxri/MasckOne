"""Analytical and hostile checks; all quantities are synthetic test inputs."""
from copy import deepcopy
import json
from pathlib import Path
import os
import subprocess
import sys
import pytest

from masck_one.reduced_region_metrology import (
    Measurement, MetrologyError, mass_closure, blank_corrected,
    carryover_fraction, film_retention, reduce_campaign,
)
from masck_one.core_sketch_contracts import CoreSketchError
from masck_one.core_sketch_trial import assess_trial

ROOT = Path(__file__).resolve().parents[1]


def measured(value, uncertainty=0, unit='g'):
    return Measurement(value, uncertainty, unit, 'SYNTHETIC_RAW_RECORD', 'SYNTHETIC_CALIBRATION')


def raw(value, uncertainty=0):
    return dict(value=value, uncertainty=uncertainty, unit='g',
                source_record='SYNTHETIC_RAW_RECORD', calibration_record='SYNTHETIC_CALIBRATION')


def campaign():
    cell = {'id': 'support', 'previous_material_distinguishable': True,
        'mass_closure': dict(introduced=raw(1, .01), recovered=raw(.5, .01),
            retained=raw(.3, .01), fixture_transfer=raw(.1, .01), collected_loss=raw(.1, .01)),
        'carryover_fraction': dict(residual=raw(.02, .001), residual_blank=raw(.01, .001),
            total=raw(.11, .002), total_blank=raw(.01, .002)),
        'film_retention': dict(before=raw(.3, .01), before_blank=raw(.1, .01),
            after=raw(.28, .01), after_blank=raw(.1, .01)),
        'reference_film_retention': dict(before=raw(.3, .01), before_blank=raw(.1, .01),
            after=raw(.3, .01), after_blank=raw(.1, .01))}
    return dict(scope='INERT_SURROGATE_OFF_FACE', specimen_id='SYNTHETIC_SPECIMEN',
                stage_id='RELEASE', previous_material_id='SYNTHETIC_A', current_material_id='SYNTHETIC_B',
                predeclared_protocol_sha256='a'*64, required_cells=['support'], cells=[cell])


def test_mass_closure_sums_all_worst_case_uncertainties():
    out = mass_closure(measured(1, .01), measured(.5, .01), measured(.3, .01),
                       measured(.1, .01), measured(.1, .01))
    assert out['residual_bounds_g'] == pytest.approx([-.05, .05])
    assert out['absolute_error_upper_g'] == pytest.approx(.05)
    assert out['absolute_error_lower_g'] == 0
    # Over-recovery is an error just as missing mass is, not a successful recovery.
    out = mass_closure(measured(1), measured(1.2), measured(0), measured(0), measured(0))
    assert out['absolute_error_lower_g'] == pytest.approx(.2)


def test_blank_corrected_ratio_uses_adversarial_endpoints():
    bounds = carryover_fraction(measured(.02, .001), measured(.01, .001),
                                measured(.11, .002), measured(.01, .002))
    assert bounds == pytest.approx([.008/.104, .012/.096])
    bounds = film_retention(measured(.3, .01), measured(.1, .01),
                            measured(.28, .01), measured(.1, .01))
    assert bounds == pytest.approx([.16/.22, .20/.18])


def test_below_blank_is_unknown_and_unresolved_denominator_cannot_divide():
    assert blank_corrected(measured(.01), measured(.02)) is None
    assert carryover_fraction(measured(.02), measured(0), measured(.01, .02), measured(.01)) is None
    assert film_retention(measured(.01), measured(.02), measured(.03), measured(0)) is None


def test_zero_residue_is_not_zero_uncertainty():
    bounds = carryover_fraction(measured(0, .002), measured(0, .001), measured(.1), measured(0))
    assert bounds == pytest.approx([0, .02])


def test_finite_inputs_cannot_overflow_to_false_confidence():
    with pytest.raises(MetrologyError):
        blank_corrected(measured(1e308, 1e308), measured(0))
    with pytest.raises(MetrologyError):
        mass_closure(measured(1), *(measured(1e308) for _ in range(4)))
    with pytest.raises(MetrologyError):
        film_retention(measured(1e-308), measured(0), measured(1e308), measured(0))


@pytest.mark.parametrize('value', [True, -1, float('nan'), float('inf'), '0'])
def test_invalid_measurements_rejected(value):
    with pytest.raises(MetrologyError):
        measured(value)
    with pytest.raises(MetrologyError):
        measured(1, value)


def test_units_and_uncalibrated_intensity_ratios_rejected():
    with pytest.raises(MetrologyError, match='unit mismatch'):
        blank_corrected(measured(1), measured(0, unit='mg'))
    with pytest.raises(MetrologyError, match='calibrated material masses'):
        carryover_fraction(*(measured(v, unit='fluorescence') for v in [1, 0, 10, 0]))
    with pytest.raises(MetrologyError):
        Measurement(1, 0, 'g', 'record', '')


def test_deterministic_source_binding_and_no_evidence_promotion():
    original = campaign()
    saved = deepcopy(original)
    report = reduce_campaign(original)
    assert original == saved
    assert report == reduce_campaign(original)
    assert report['method_blockers'] == []
    assert not any(report[k] for k in ('bench_evidence_accepted', 'whole_face_complete',
                                      'human_use_authorized', 'spf_validated', 'acceptance_limits_established'))
    assert report['metrics_by_cell']['support']['retention_minus_reference_bounds'][0] < 0
    original['cells'][0]['film_retention']['after']['uncertainty'] = .1
    assert reduce_campaign(original)['input_sha256'] != report['input_sha256']


def test_missing_cell_or_one_measurement_stays_unknown():
    data = campaign(); data['required_cells'].append('seal')
    data['cells'][0]['mass_closure']['collected_loss'] = None
    report = reduce_campaign(data)
    assert report['metrics_by_cell']['support']['mass_closure'] is None
    assert report['metrics_by_cell']['seal']['film_retention'] is None
    assert 'seal:film_retention:MEASUREMENTS_UNKNOWN' in report['method_blockers']
    assert 'support:mass_closure:MEASUREMENTS_UNKNOWN' in report['method_blockers']


def test_missing_sibling_does_not_bypass_validation_of_bad_measurement():
    data = campaign(); data['cells'][0]['carryover_fraction']['residual'] = None
    data['cells'][0]['carryover_fraction']['residual_blank']['uncertainty'] = -1
    with pytest.raises(MetrologyError):
        reduce_campaign(data)


def test_required_regions_cannot_hide_behind_average():
    data = campaign(); data['required_cells'].append('seal')
    seal = deepcopy(data['cells'][0]); seal['id'] = 'seal'
    seal['previous_material_distinguishable'] = False
    seal['film_retention']['before'] = raw(0)
    seal['film_retention']['before_blank'] = raw(0)
    data['cells'].append(seal)
    report = reduce_campaign(data)
    assert 'seal:CARRYOVER_METHOD_NOT_DISTINGUISHABLE' in report['method_blockers']
    assert 'seal:film_retention:SIGNAL_OR_DENOMINATOR_UNRESOLVED' in report['method_blockers']
    assert report['metrics_by_cell']['support']['film_retention'] is not None


def test_impossible_ratio_is_reported_without_clipping_to_one():
    data = campaign(); group = data['cells'][0]['carryover_fraction']
    group['residual'] = raw(.5)
    report = reduce_campaign(data)
    assert report['metrics_by_cell']['support']['carryover_fraction'][0] > 1
    assert 'support:carryover_fraction:FRACTION_INCONSISTENT_OR_REDISTRIBUTED' in report['method_blockers']


@pytest.mark.parametrize('change', ['scope', 'duplicate', 'unknown_cell', 'unexpected_component', 'protocol'])
def test_bad_campaign_structure_rejected(change):
    data = campaign()
    if change == 'scope': data['scope'] = 'HUMAN'
    elif change == 'duplicate': data['cells'].append(deepcopy(data['cells'][0]))
    elif change == 'unknown_cell': data['cells'][0]['id'] = 'not_required'
    elif change == 'unexpected_component': data['cells'][0]['mass_closure']['free_bonus'] = raw(0)
    else: data['predeclared_protocol_sha256'] = 'stale'
    with pytest.raises(MetrologyError): reduce_campaign(data)


@pytest.mark.parametrize('metric', ['mass_balance_error_g', 'carryover_fraction', 'protected_deposit_g',
                                  'film_retention_fraction'])
@pytest.mark.parametrize('value', [-1, '0', True])
@pytest.mark.parametrize('part', ['value', 'uncertainty'])
def test_trial_unestablished_limit_cannot_hide_malformed_metrics(metric, value, part):
    protocol = json.loads((ROOT/'docs/contracts/reduced_region_protocol.json').read_text())
    trial = json.loads((ROOT/'docs/contracts/reduced_region_trial_template.json').read_text())
    row = trial['stages'][-1]['cells'][0]
    row[metric if part == 'value' else metric+'_uncertainty'] = value
    with pytest.raises(CoreSketchError): assess_trial(protocol, trial)


def test_carryover_above_one_reported_even_without_limit():
    protocol = json.loads((ROOT/'docs/contracts/reduced_region_protocol.json').read_text())
    trial = json.loads((ROOT/'docs/contracts/reduced_region_trial_template.json').read_text())
    trial['stages'][0]['cells'][0].update(carryover_fraction=1.1, carryover_fraction_uncertainty=0)
    report = assess_trial(protocol, trial)
    assert 'CLEAN:acquisition_edge:carryover_fraction:MEASUREMENT_INCONSISTENT' in report['blockers']


def test_blank_template_cli_keeps_unknown_values_and_evidence_firewall(tmp_path):
    target = tmp_path/'metrology.json'
    subprocess.run([sys.executable, '-m', 'masck_one.reduced_region_metrology',
        '--input', str(ROOT/'docs/contracts/reduced_region_metrology_template.json'),
        '--output', str(target)], check=True, cwd=ROOT,
        env={**os.environ, 'PYTHONPATH': str(ROOT/'src')}, capture_output=True)
    report = json.loads(target.read_text())
    assert len(report['method_blockers']) == 26
    assert not report['bench_evidence_accepted']
    assert all(row['mass_closure'] is None for row in report['metrics_by_cell'].values())
