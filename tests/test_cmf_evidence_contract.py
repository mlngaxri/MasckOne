import math
import pytest

from masck_one.cmf_evidence_contract import CMFEvidenceContractError, validate_cmf_evidence


def valid():
    return {
        "CMF_SHELL_GLOSS_GU60_A": 18.0,
        "CMF_SHELL_GLOSS_GU60_B": 19.0,
        "CMF_SHELL_GLOSS_GU60_C": 17.5,
        "CMF_SHELL_POST_CLEAN_GLOSS_SHIFT_GU60": 2.0,
        "CMF_SHELL_POST_CLEAN_DELTA_E00": 1.2,
    }


def test_accepts_measured_low_gloss_candidate():
    validate_cmf_evidence(valid())


@pytest.mark.parametrize("key,value", [
    ("CMF_SHELL_GLOSS_GU60_A", 7.9),
    ("CMF_SHELL_GLOSS_GU60_B", 28.1),
    ("CMF_SHELL_POST_CLEAN_GLOSS_SHIFT_GU60", 5.1),
    ("CMF_SHELL_POST_CLEAN_DELTA_E00", 3.1),
])
def test_rejects_out_of_window_or_cleaning_instability(key, value):
    evidence = valid()
    evidence[key] = value
    with pytest.raises(CMFEvidenceContractError):
        validate_cmf_evidence(evidence)


def test_rejects_excessive_gloss_spread():
    evidence = valid()
    evidence["CMF_SHELL_GLOSS_GU60_A"] = 14.0
    evidence["CMF_SHELL_GLOSS_GU60_C"] = 18.1
    with pytest.raises(CMFEvidenceContractError):
        validate_cmf_evidence(evidence)


def test_fails_closed_on_missing_measurement():
    evidence = valid()
    del evidence["CMF_SHELL_GLOSS_GU60_C"]
    with pytest.raises(CMFEvidenceContractError):
        validate_cmf_evidence(evidence)


@pytest.mark.parametrize("bad", [math.nan, math.inf, -1.0])
def test_rejects_nonfinite_or_negative_evidence(bad):
    evidence = valid()
    evidence["CMF_SHELL_POST_CLEAN_DELTA_E00"] = bad
    with pytest.raises(CMFEvidenceContractError):
        validate_cmf_evidence(evidence)
