from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from masck_one.digital_release import DigitalReleaseError, validate_repo_split_config


CONFIG_PATH = Path("config/digital_repo_split.yaml")


def _config() -> dict[str, object]:
    payload = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    assert type(payload) is dict
    return payload


def test_committed_v1_split_contract_is_accepted():
    validate_repo_split_config(_config())


def test_cad_firewall_cannot_be_removed():
    payload = _config()
    payload["import_policy"]["forbidden_direct_roots"].remove("cad/")
    with pytest.raises(DigitalReleaseError, match="firewall drift"):
        validate_repo_split_config(payload)


def test_release_url_environment_name_cannot_drift():
    payload = _config()
    payload["workspaces"]["web"]["environment_schema"][0]["name"] = (
        "NEXT_PUBLIC_RELEASE_URL"
    )
    with pytest.raises(DigitalReleaseError, match="environment schema drift"):
        validate_repo_split_config(payload)


def test_secret_environment_variable_cannot_be_downgraded_to_public():
    payload = _config()
    entries = payload["workspaces"]["web"]["environment_schema"]
    write_key = next(entry for entry in entries if entry["name"] == "ANALYTICS_WRITE_KEY")
    write_key["secret"] = False
    with pytest.raises(DigitalReleaseError, match="environment schema drift"):
        validate_repo_split_config(payload)


def test_mandatory_test_command_cannot_revert_to_if_present():
    payload = _config()
    payload["workspaces"]["app"]["test_command"] = "npm test --if-present"
    with pytest.raises(DigitalReleaseError, match="app.test_command drift"):
        validate_repo_split_config(payload)


def test_build_and_typecheck_commands_are_versioned_contract_fields():
    for field, value in (
        ("build_command", "npm run build:unsafe"),
        ("typecheck_command", "npm run typecheck"),
    ):
        payload = _config()
        payload["workspaces"]["web"][field] = value
        with pytest.raises(DigitalReleaseError, match=rf"web\.{field} drift"):
            validate_repo_split_config(payload)


def test_history_split_command_must_match_v1_exactly():
    payload = _config()
    payload["workspaces"]["web"]["history_split_command"] += " --force"
    with pytest.raises(DigitalReleaseError, match="history_split_command drift"):
        validate_repo_split_config(payload)


def test_workspace_cannot_hide_unversioned_fields():
    payload = _config()
    payload["workspaces"]["web"]["allow_direct_hardware_import"] = True
    with pytest.raises(DigitalReleaseError, match="workspace contract fields drift"):
        validate_repo_split_config(payload)


def test_top_level_contract_cannot_hide_unversioned_fields():
    payload = _config()
    payload["unsafe_override"] = True
    with pytest.raises(DigitalReleaseError, match="top-level contract drift"):
        validate_repo_split_config(payload)


def test_environment_entry_order_and_membership_are_exact_v1_contract():
    payload = _config()
    env = payload["workspaces"]["app"]["environment_schema"]
    payload["workspaces"]["app"]["environment_schema"] = list(reversed(env))
    with pytest.raises(DigitalReleaseError, match="environment schema drift"):
        validate_repo_split_config(payload)


def test_import_policy_fields_are_exactly_versioned():
    payload = _config()
    payload["import_policy"]["allow_generated_release_only"] = True
    with pytest.raises(DigitalReleaseError, match="import_policy fields drift"):
        validate_repo_split_config(payload)


def test_forbidden_root_list_cannot_be_weakened_or_rewritten():
    payload = _config()
    payload["import_policy"]["forbidden_direct_roots"] = [
        "src/",
        "config/masck_one_authority.yaml",
        "schemas/",
        "tests/",
        "cad/generated/",
    ]
    with pytest.raises(DigitalReleaseError, match="firewall drift"):
        validate_repo_split_config(payload)


def test_mutations_do_not_modify_fresh_source_fixture():
    original = _config()
    changed = deepcopy(original)
    changed["workspaces"]["web"]["environment_schema"][0]["name"] = "DRIFTED"
    assert _config() == original
