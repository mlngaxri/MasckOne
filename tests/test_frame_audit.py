from __future__ import annotations

import pytest

from masck_one.frame_audit import scan_python_frame_declarations
from masck_one.frame_contract import FrameContractError


def test_scanner_accepts_canonical_world_frame_constant() -> None:
    declarations = scan_python_frame_declarations(
        'WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"\n',
        path="src/masck_one/example.py",
    )
    assert len(declarations) == 1
    assert declarations[0].frame_id == "MASCK_ONE_AUTHORITY_WORLD_MM"


def test_scanner_accepts_explicit_local_frame_constant() -> None:
    declarations = scan_python_frame_declarations(
        'ACTUATOR_FRAME_ID = "MASCK_ONE_LOCAL_ACTUATOR_ZONE_A"\n',
        path="src/masck_one/example.py",
    )
    assert len(declarations) == 1
    assert declarations[0].frame_id.startswith("MASCK_ONE_LOCAL_")


def test_scanner_rejects_alternate_world_frame_manifest_label() -> None:
    source = (
        'report = {"coordinate_frame": '
        '"MASCK_ONE_CANONICAL_WORLD_X_WEARER_RIGHT_Y_SUPERIOR_Z_ANTERIOR"}\n'
    )
    with pytest.raises(FrameContractError, match="unknown cross-system frame"):
        scan_python_frame_declarations(source, path="src/masck_one/exterior_evidence.py")


def test_scanner_rejects_legacy_global_alias_outside_internal_boundary() -> None:
    with pytest.raises(FrameContractError, match="legacy frame alias"):
        scan_python_frame_declarations(
            'WORLD_FRAME_ID = "MASCK_ONE_GLOBAL"\n',
            path="src/masck_one/new_subsystem.py",
        )


def test_scanner_allows_legacy_alias_only_in_controlled_internal_module() -> None:
    declarations = scan_python_frame_declarations(
        'WORLD_FRAME_ID = "MASCK_ONE_GLOBAL"\n',
        path="src/masck_one/reference_surfaces.py",
    )
    assert len(declarations) == 1
    assert declarations[0].frame_id == "MASCK_ONE_GLOBAL"


def test_scanner_ignores_non_frame_strings_and_dynamic_manifest_values() -> None:
    source = (
        'LABEL = "MASCK_ONE_SOMETHING_WORLDISH"\n'
        'frame_id = get_frame_id()\n'
        'report = {"coordinate_frame_id": frame_id}\n'
    )
    assert scan_python_frame_declarations(source, path="src/masck_one/example.py") == ()
