from types import SimpleNamespace

from masck_one import treatment_guided_preload_spring_v5 as guided_v5
from masck_one.structural_frame_actuator_reactions import REACTION_IDS


def _valid_capture_screen():
    return {"X_root": 0.01, "Z_root": 0.01, "X_tip": 0.01, "Z_tip": 0.01}


def _terminal():
    return SimpleNamespace(
        source_cell6_head_sha=guided_v5.SOURCE_CELL6_HEAD_SHA,
        stations=tuple(SimpleNamespace(reaction_id=value) for value in REACTION_IDS),
    )


def test_guided_v5_rejects_duck_typed_generated_station(monkeypatch):
    def proxy_station(station):
        return SimpleNamespace(
            reaction_id=station.reaction_id,
            capture_screen=_valid_capture_screen(),
        )

    monkeypatch.setattr(
        guided_v5,
        "build_terminal_datum_preload_v5_architecture",
        lambda **_kwargs: _terminal(),
    )
    monkeypatch.setattr(guided_v5, "build_guided_preload_spring_station", proxy_station)

    try:
        guided_v5.build_guided_preload_spring_v5_architecture()
    except ValueError as exc:
        assert "generator returned invalid station type" in str(exc)
        assert "SimpleNamespace" in str(exc)
    else:
        raise AssertionError("duck-typed station proxy must fail closed")


def test_guided_v5_missing_generated_identity_fails_closed_as_value_error(monkeypatch):
    monkeypatch.setattr(
        guided_v5,
        "build_terminal_datum_preload_v5_architecture",
        lambda **_kwargs: _terminal(),
    )
    monkeypatch.setattr(guided_v5, "build_guided_preload_spring_station", lambda _station: object())

    try:
        guided_v5.build_guided_preload_spring_v5_architecture()
    except ValueError as exc:
        assert "generated station identity drifted" in str(exc)
        assert "got None" in str(exc)
    else:
        raise AssertionError("station without identity must fail closed")


def test_guided_v5_missing_capture_screen_fails_closed_as_value_error(monkeypatch):
    def missing_capture(station):
        return SimpleNamespace(reaction_id=station.reaction_id)

    monkeypatch.setattr(
        guided_v5,
        "build_terminal_datum_preload_v5_architecture",
        lambda **_kwargs: _terminal(),
    )
    monkeypatch.setattr(guided_v5, "build_guided_preload_spring_station", missing_capture)

    try:
        guided_v5.build_guided_preload_spring_v5_architecture()
    except ValueError as exc:
        assert "capture screen must be a mapping" in str(exc)
        assert "NoneType" in str(exc)
    else:
        raise AssertionError("station without capture evidence must fail closed")
