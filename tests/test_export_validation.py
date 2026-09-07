from dataclasses import replace

import cadquery as cq
import pytest

from masck_one.assertions import Check
from masck_one.cli import main
from masck_one import export as export_module
from masck_one.export import _component_record, export_release
from masck_one.model import build_model
from masck_one.release_package import ExportValidationError


@pytest.fixture(scope="module")
def model():
    return build_model()


def test_failed_engineering_check_never_writes_step(tmp_path, monkeypatch, model):
    monkeypatch.setattr(export_module, "run_assertions", lambda m: [Check("BROKEN", "FAIL", "fixture")])
    with pytest.raises(ExportValidationError, match="BROKEN"):
        export_release(tmp_path, model)
    assert list(tmp_path.iterdir()) == []


def test_late_dfm_failure_never_writes_step(tmp_path, monkeypatch, model):
    def fail(**kwargs):
        raise ValueError("stale DFM source")
    monkeypatch.setattr(export_module, "build_waste_cartridge_dfm_audit", fail)
    with pytest.raises(ValueError, match="stale DFM source"):
        export_release(tmp_path, model)
    assert list(tmp_path.iterdir()) == []


def test_nonvolumetric_component_cannot_enter_step_package(model):
    wire = cq.Workplane("XY").circle(1)
    with pytest.raises(ExportValidationError, match="non-volumetric"):
        _component_record(replace(model.shell, solid=wire), included=True)


def test_unknown_or_duplicate_export_identity_is_rejected(tmp_path, model):
    renamed = replace(model.shell, name=model.water_reservoir_envelope.name)
    with pytest.raises(ExportValidationError, match="identities changed"):
        export_release(tmp_path, replace(model, shell=renamed))
    assert list(tmp_path.iterdir()) == []


def test_production_cli_rejects_before_build_or_export(tmp_path, monkeypatch, capsys):
    def unexpected_build():
        raise AssertionError("production refusal must precede geometry generation")
    monkeypatch.setattr(export_module, "build_model", unexpected_build)
    assert main(["--production", "--output", str(tmp_path)]) == 1
    assert "Production export is blocked" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []
