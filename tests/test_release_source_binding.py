import pytest

from masck_one.export import _RELEASE_SOURCE_ENV, _release_source_binding
from masck_one.release_package import ExportValidationError


def _clear_binding(monkeypatch) -> None:
    for env_name in _RELEASE_SOURCE_ENV.values():
        monkeypatch.delenv(env_name, raising=False)


def test_local_export_is_explicitly_unbound(monkeypatch) -> None:
    _clear_binding(monkeypatch)

    binding = _release_source_binding()

    assert binding["schema"] == "MASCK_ONE_RELEASE_SOURCE_BINDING_V1"
    assert binding["binding_state"] == "UNBOUND_LOCAL_BUILD"
    assert binding["physical_validation_eligible"] is False
    assert binding["evidence_scope"] == "LOCAL_BUILD_NOT_RELEASE_PROVENANCE"
    for field in _RELEASE_SOURCE_ENV:
        assert binding[field] is None


def test_ci_export_binds_all_exact_git_identities(monkeypatch) -> None:
    _clear_binding(monkeypatch)
    values = {
        "release_base_sha": "1" * 40,
        "source_head_sha": "2" * 40,
        "source_head_tree_sha": "3" * 40,
        "tested_commit_sha": "4" * 40,
        "tested_tree_sha": "5" * 40,
    }
    for field, value in values.items():
        monkeypatch.setenv(_RELEASE_SOURCE_ENV[field], value)

    binding = _release_source_binding()

    assert binding["binding_state"] == "CI_EXACT_BOUND"
    assert binding["physical_validation_eligible"] is False
    assert binding["evidence_scope"] == "DIGITAL_SOURCE_PROVENANCE_ONLY"
    for field, value in values.items():
        assert binding[field] == value


def test_partial_ci_binding_fails_closed(monkeypatch) -> None:
    _clear_binding(monkeypatch)
    monkeypatch.setenv(_RELEASE_SOURCE_ENV["release_base_sha"], "1" * 40)

    with pytest.raises(ExportValidationError, match="Incomplete release source binding"):
        _release_source_binding()


def test_malformed_ci_binding_fails_closed(monkeypatch) -> None:
    _clear_binding(monkeypatch)
    for field, env_name in _RELEASE_SOURCE_ENV.items():
        monkeypatch.setenv(env_name, "a" * 40)
    monkeypatch.setenv(_RELEASE_SOURCE_ENV["tested_tree_sha"], "not-a-sha")

    with pytest.raises(ExportValidationError, match="Malformed release source binding SHA"):
        _release_source_binding()
