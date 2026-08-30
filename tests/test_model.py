from masck_one.assertions import run_assertions
from masck_one.model import build_model


def test_model_builds():
    model = build_model()
    assert model.shell.solid.val().Volume() > 0
    assert model.nasal_interface.solid.val().Volume() > 0
    assert len(model.actuator_envelopes) == 4


def test_all_software_verifiable_assertions_pass():
    model = build_model()
    checks = run_assertions(model)
    failures = [c for c in checks if c.status == "FAIL"]
    assert failures == []


def test_shell_fits_xy_authority_envelope():
    model = build_model()
    bb = model.shell.solid.val().BoundingBox()
    max_x, max_y = model.authority.pair("geometry", "outer_xy_envelope_mm")
    assert bb.xlen <= max_x + 1e-6
    assert bb.ylen <= max_y + 1e-6


def test_water_reservoir_gross_volume_exact():
    model = build_model()
    volume_ml = model.water_reservoir_envelope.solid.val().Volume() / 1000.0
    assert abs(volume_ml - 6.5) < 1e-9


def test_cartridge_envelope_exact():
    model = build_model()
    bb = model.waste_cartridge_envelope.solid.val().BoundingBox()
    assert abs(bb.xlen - 74.0) < 1e-9
    assert abs(bb.ylen - 36.0) < 1e-9
    assert abs(bb.zlen - 20.0) < 1e-9
