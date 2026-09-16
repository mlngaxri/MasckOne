from __future__ import annotations

from pathlib import Path

from masck_one.treatment_cell6_source_binding import (
    CELL6_HEAD_SHA,
    CONSUMED_COUNTERFACE_BLOB_SHA1,
    PHYSICAL_VALIDATION_ELIGIBLE,
    RELEASED_MAIN_SHA,
    TREATMENT_CELL6_MERGE_CHECKPOINT_SHA,
    TREATMENT_PREMERGE_HEAD_SHA,
    manifest,
    verify_consumed_counterface_blobs,
)
from masck_one.treatment_terminal_datum_preload_v4 import (
    SOURCE_CELL6_HEAD_SHA as ACTIVE_TERMINAL_DATUM_CELL6_HEAD_SHA,
)


def test_treatment_cell6_v2_binding_is_exact_and_current() -> None:
    assert RELEASED_MAIN_SHA == "42fa11818184cde998c6df25d7c46d4fb0e4c3eb"
    assert CELL6_HEAD_SHA == "2d5ace19e2f87a8bd92f4620d8e6b225ba3826be"
    assert ACTIVE_TERMINAL_DATUM_CELL6_HEAD_SHA == CELL6_HEAD_SHA
    assert TREATMENT_PREMERGE_HEAD_SHA == "0073fc33d0605ea84e5322111d10a457585bdb59"
    assert TREATMENT_CELL6_MERGE_CHECKPOINT_SHA == "d070d927d03aa995fd7d34e86dc2629a5b37a5b4"
    assert len(CONSUMED_COUNTERFACE_BLOB_SHA1) == 6
    assert all(len(value) == 40 for value in CONSUMED_COUNTERFACE_BLOB_SHA1.values())

    repo_root = Path(__file__).resolve().parents[1]
    assert verify_consumed_counterface_blobs(repo_root) == CONSUMED_COUNTERFACE_BLOB_SHA1


def test_treatment_cell6_v2_binding_preserves_evidence_firewall_and_supersedes_only_identity() -> None:
    payload = manifest()
    assert payload["physical_validation_eligible"] is False
    assert PHYSICAL_VALIDATION_ELIGIBLE is False
    assert payload["supersedes_source_binding"].endswith("SOURCE_IDENTITY_ONLY")
    assert "PRIOR_RECONCILIATION_CALCULATIONS_REMAIN_PRIOR_DIGITAL_EVIDENCE" in payload["authority_rule"]
    assert len(payload["binding_sha256"]) == 64


def test_reported_astra_fixes_are_not_promoted_without_pushed_geometry() -> None:
    status = manifest()["pushed_evidence_status"]
    assert status["contact_equilibrium_zero_preload_wrench_screen"] == "PUSHED_PRIOR_DIGITAL_EVIDENCE"
    assert status["exact_bezier_terminal_cam_plus_flat_land"].startswith("NO_PUSHED_EVIDENCE_FOUND")
    assert status["moved_opposed_z_contacts_clearing_central_bridge"].startswith("NO_PUSHED_EVIDENCE_FOUND")
    assert status["corrected_spring_clamp_exits"].startswith("NO_PUSHED_EVIDENCE_FOUND")


import inspect

import pytest

from masck_one import structural_frame_realization as _cell6_realization
from masck_one.treatment_cell6_source_binding import (
    CELL6_VERIFIED_COMPATIBLE_HEAD_SHA,
    PROTECTED_ZONE_IMPL_CANDIDATE_PATHS,
    PROTECTED_ZONE_SOURCE_SHA256,
    PROTECTED_ZONE_SYMBOL,
    canonical_symbol_source,
    extract_symbol_source,
    symbol_source_sha256,
    verify_consumed_protected_zone_source,
    verify_runtime_protected_zone_binding,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _live_zone_source() -> str:
    return inspect.getsource(_cell6_realization._protected_zone_solid)


def _repo_carrying(tmp_path: Path, relative: str, module_text: str) -> Path:
    target = tmp_path / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(module_text, encoding="utf-8")
    return tmp_path


def test_protected_zone_builder_is_bound_to_the_runtime_import() -> None:
    record = verify_runtime_protected_zone_binding()
    assert record["symbol"] == PROTECTED_ZONE_SYMBOL
    assert record["symbol_source_sha256"] == PROTECTED_ZONE_SOURCE_SHA256


def test_protected_zone_builder_resolves_from_the_repository_tree() -> None:
    record = verify_consumed_protected_zone_source(_REPO_ROOT)
    assert record["symbol_source_sha256"] == PROTECTED_ZONE_SOURCE_SHA256
    assert record["path"] in PROTECTED_ZONE_IMPL_CANDIDATE_PATHS


def test_relocated_cell6_implementation_still_satisfies_the_binding(tmp_path: Path) -> None:
    """Cell 6 may move the implementation into a preserved blob; that is not drift."""
    relocated = _repo_carrying(
        tmp_path,
        "src/masck_one/_structural_frame_realization_impl.py",
        "import cadquery as cq\n\n\n" + _live_zone_source(),
    )
    record = verify_consumed_protected_zone_source(relocated)
    assert record["path"] == "src/masck_one/_structural_frame_realization_impl.py"
    assert record["symbol_source_sha256"] == PROTECTED_ZONE_SOURCE_SHA256


def test_shrunken_protected_envelope_is_refused(tmp_path: Path) -> None:
    """Halving the zone radii weakens protected anatomy and must not verify."""
    weakened = _live_zone_source().replace(
        "envelope_width_mm / 2.0, envelope_height_mm / 2.0",
        "envelope_width_mm / 4.0, envelope_height_mm / 4.0",
    )
    assert weakened != _live_zone_source()
    repo = _repo_carrying(
        tmp_path, "src/masck_one/structural_frame_realization.py", "import cadquery as cq\n\n\n" + weakened
    )
    with pytest.raises(ValueError, match="protected-anatomy builder"):
        verify_consumed_protected_zone_source(repo)


def test_absent_protected_zone_symbol_is_refused(tmp_path: Path) -> None:
    repo = _repo_carrying(
        tmp_path, "src/masck_one/structural_frame_realization.py", "SOURCE_MAIN_SHA = 'deadbeef'\n"
    )
    with pytest.raises(ValueError, match="SYMBOL_NOT_FOUND_IN_ANY_CANDIDATE_PATH"):
        verify_consumed_protected_zone_source(repo)


def test_monkeypatched_protected_zone_builder_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """The runtime binding follows the real import, so a substituted builder is caught."""

    def _substitute(**kwargs):  # pragma: no cover - never executed, only inspected
        raise AssertionError("substituted protected-zone builder")

    monkeypatch.setattr(_cell6_realization, PROTECTED_ZONE_SYMBOL, _substitute)
    with pytest.raises(ValueError, match="does not match the treatment source binding"):
        verify_runtime_protected_zone_binding()


def test_canonical_source_agrees_between_inspect_and_ast() -> None:
    """inspect keeps the trailing newline and ast drops it; both must still hash alike."""
    runtime = _live_zone_source()
    carrier = Path(inspect.getsourcefile(_cell6_realization._protected_zone_solid))
    parsed = extract_symbol_source(carrier.read_text(encoding="utf-8"), PROTECTED_ZONE_SYMBOL)
    assert runtime != parsed
    assert canonical_symbol_source(runtime) == canonical_symbol_source(parsed)
    assert symbol_source_sha256(runtime) == symbol_source_sha256(parsed) == PROTECTED_ZONE_SOURCE_SHA256


def test_verified_compatible_head_does_not_become_the_geometry_source_head() -> None:
    """Forward compatibility is not a re-derivation and not a live-currency claim."""
    payload = manifest()
    assert payload["cell6_head_sha"] == CELL6_HEAD_SHA
    assert payload["cell6_verified_compatible_head_sha"] == CELL6_VERIFIED_COMPATIBLE_HEAD_SHA
    assert CELL6_VERIFIED_COMPATIBLE_HEAD_SHA != CELL6_HEAD_SHA
    assert "NOT_A_REDERIVATION_OR_LIVE_CURRENCY_CLAIM" in payload["cell6_verified_compatible_semantics"]
    assert payload["physical_validation_eligible"] is False
