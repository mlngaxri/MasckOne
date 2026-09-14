"""Geometry role must be declared, never inferred from assembly membership.

ENGINEERING_GOVERNANCE treats one distinction as fundamental: manufactured
material physically exists in the product, everything else is a design aid.
Before this, export.py computed

    "geometry_role": "PHYSICAL_MATERIAL" if included else "NON_MATERIAL_REFERENCE"

which made the role a restatement of assembly membership rather than a fact
about the body. Two silent substitutions followed:

  * a real manufactured part not yet registered in the assembly was reported as
    reference geometry;
  * a reference envelope included for a visualisation was promoted to
    manufactured material -- the exact substitution the governance forbids.

Role is now declared on the Component and read out. Inclusion is a separate
fact, and disagreeing with the role fails the export closed.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from masck_one.export import ExportValidationError, _component_record
from masck_one.model import GeometryRole, build_model


@pytest.fixture(scope="module")
def model():
    return build_model()


def test_the_shell_is_the_only_declared_manufactured_body(model) -> None:
    """The current baseline manufactures one part; everything else is a design aid."""

    material = [c.name for c in model.components if c.geometry_role is GeometryRole.PHYSICAL_MATERIAL]
    assert material == ["rigid_shell"]


def test_every_component_declares_a_role(model) -> None:
    for component in model.components:
        assert isinstance(component.geometry_role, GeometryRole)


def test_packaging_envelopes_are_not_manufactured_material(model) -> None:
    """An envelope bounds a volume; it does not establish what is inside it."""

    for component in model.components:
        if component.name.endswith("_envelope"):
            assert component.geometry_role is GeometryRole.NON_MATERIAL_REFERENCE


def test_record_reports_the_declared_role_not_the_inclusion_flag(model) -> None:
    """A reference body excluded from the assembly still reports its own role."""

    envelope = next(c for c in model.components if c.name == "battery_reference_envelope")
    record = _component_record(envelope, included=False)
    assert record["geometry_role"] == "NON_MATERIAL_REFERENCE"
    assert record["included_in_development_assembly"] is False


def test_a_reference_body_cannot_be_assembled_as_material(model) -> None:
    """The regression that matters: inclusion must not promote a role."""

    envelope = next(c for c in model.components if c.name == "water_reservoir_envelope")
    with pytest.raises(ExportValidationError, match="never be assembled"):
        _component_record(envelope, included=True)


def test_a_motion_sweep_cannot_be_assembled_as_material(model) -> None:
    """A swept volume is occupied space, not product mass."""

    sweep = replace(
        next(c for c in model.components if c.name == "actuator_envelope_1"),
        geometry_role=GeometryRole.MOTION_SWEEP,
    )
    with pytest.raises(ExportValidationError, match="never be assembled"):
        _component_record(sweep, included=True)


def test_a_keepout_cannot_be_assembled_as_material(model) -> None:
    keepout = replace(
        next(c for c in model.components if c.name == "waste_cartridge_envelope"),
        geometry_role=GeometryRole.KEEPOUT,
    )
    with pytest.raises(ExportValidationError, match="never be assembled"):
        _component_record(keepout, included=True)


def test_declared_material_may_be_assembled(model) -> None:
    shell = next(c for c in model.components if c.name == "rigid_shell")
    record = _component_record(shell, included=True)
    assert record["geometry_role"] == "PHYSICAL_MATERIAL"
    assert record["included_in_development_assembly"] is True


def test_role_defaults_to_reference_not_material(model) -> None:
    """A body that forgets to declare must fail safe, not become a part."""

    from masck_one.model import Component

    undeclared = Component("x", model.shell.solid, "CAD_BASELINE")
    assert undeclared.geometry_role is GeometryRole.NON_MATERIAL_REFERENCE
