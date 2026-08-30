from pathlib import Path

import yaml

from masck_one.authority import load_authority


def test_authority_loads_and_uses_correct_name():
    authority = load_authority()
    assert authority.get("project", "name") == "Masck One"
    assert authority.get("project", "id") == "MASCK_ONE"


def test_no_legacy_product_name_in_machine_authority():
    path = Path("config/masck_one_authority.yaml")
    text = path.read_text(encoding="utf-8")
    legacy = "F" + "CW"
    assert legacy not in text


def test_yaml_is_mapping():
    data = yaml.safe_load(Path("config/masck_one_authority.yaml").read_text(encoding="utf-8"))
    assert isinstance(data, dict)
