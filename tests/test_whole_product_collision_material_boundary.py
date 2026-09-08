from __future__ import annotations

import inspect

import masck_one.export as export_module
from masck_one.model import build_model


def test_development_reference_solids_are_explicitly_excluded_from_physical_assembly():
    model = build_model()
    assert model.nasal_interface.name == "nasal_lobe_membrane_reference"
    assert "REFERENCE" in model.nasal_interface.status
    assert model.waste_cartridge_envelope.name == "waste_cartridge_envelope"
    assert "ENVELOPE" in model.waste_cartridge_envelope.status

    source = inspect.getsource(export_module.export_release)
    assert '"nasal_lobe_membrane_reference",' in source
    assert '"waste_cartridge_envelope",' in source
    assert "development_assembly_exclusions" in source
    assert "component.name not in development_assembly_exclusions" in source
