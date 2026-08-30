from pathlib import Path

from masck_one.preflight import run_preflight


def test_phase_1_preflight_passes():
    report = run_preflight()
    failed = [check for check in report["checks"] if check["status"] != "PASS"]
    assert failed == []
    assert report["result"] == "PASS"


def test_generated_directory_policy_is_explicit():
    generated = Path("generated")
    assert (generated / ".gitkeep").exists()
    ignore = Path(".gitignore").read_text(encoding="utf-8")
    assert "generated/*" in ignore
    assert "!generated/.gitkeep" in ignore
