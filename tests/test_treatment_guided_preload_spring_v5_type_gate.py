from types import SimpleNamespace

from masck_one import treatment_guided_preload_spring_v5 as guided_v5
from masck_one.structural_frame_actuator_reactions import REACTION_IDS


def _valid_capture_screen():
    return {"X_root": 0.01, "Z_root": 0.01, "X_tip": 0.01, "Z_tip": 0.01}


def test_guided_v5_rejects_duck_typed_generated_station(monkeypatch):
    terminal = SimpleNamespace(
        source_cell6_head_sha=guided_v5.SOURCE_CELL6_HEAD_SHA,
        stations=tuple(SimpleNamespace(reaction_id=value) for value in REACTION_IDS),
    )

    def proxy_station(station):
        return SimpleNamespace(
            reaction_id=station.reaction_id,
            capture_screen=_valid_capture_screen(),
        )

    monkeypatch.setattr(
        guided_v5,
        "build_terminal_datum_preload_v5_architecture",
        lambda **_kwargs: terminal,
    )
    monkeypatch.setattr(guided_v5, "build_guided_preload_spring_station", proxy_station)

    try:
        guided_v5.build_guided_preload_spring_v5_architecture()
    except ValueError as exc:
        assert "generator returned invalid station type" in str(exc)
        assert "SimpleNamespace" in str(exc)
    else:
        raise AssertionError("duck-typed station proxy must fail closed")
