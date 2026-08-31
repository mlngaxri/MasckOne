import hashlib
import json

import pytest

from masck_one.digital_export import DigitalExportError, DigitalTargetExport, export_visual_system
from masck_one.visual_system import AdaptiveVisualSystem, AppearanceRole, TypographyRole

SHA = "a" * 64


class LyingStr(str):
    def __eq__(self, other): return True
    def __ne__(self, other): return False
    def __hash__(self): return str.__hash__(self)


def system():
    return AdaptiveVisualSystem(
        "masck-one.visual-v1",
        SHA,
        (
            TypographyRole("body", "text.primary", 1.0, 1.5, 450, 0.0, 68),
            TypographyRole("display", "display.primary", 4.0, 0.98, 520, -0.035, 32),
        ),
        (
            AppearanceRole("appearance.dark", "dark", "#171917", "#f0eee7", "#b7c9b0", "#4b504b", "#d6e7cf"),
            AppearanceRole("appearance.high-contrast", "high-contrast", "#000000", "#ffffff", "#ffffff", "#ffffff", "#ffffff"),
            AppearanceRole("appearance.light", "light", "#e8e5dc", "#1d211f", "#526a55", "#a8aaa3", "#314f38"),
        ),
    )


def test_web_and_app_are_deterministic_and_semantically_identical():
    web = export_visual_system(system(), "web")
    app = export_visual_system(system(), "app")
    assert web.payload == app.payload
    assert web.payload_sha256 == app.payload_sha256
    assert web.visual_system_sha256 == system().manifest_sha256
    assert web.manifest_sha256 != app.manifest_sha256


def test_export_contains_accessible_appearance_and_typography_semantics():
    payload = dict(export_visual_system(system(), "web").payload)
    assert payload["appearance.light.focus"] == "#314f38"
    assert payload["appearance.dark.text"] == "#f0eee7"
    assert payload["type.body.max-line-chars"] == "68"
    assert payload["type.display.tracking-em"] == "-0.035"


def test_rejects_hostile_target_and_wrong_contract_type():
    with pytest.raises(DigitalExportError): export_visual_system(system(), LyingStr("web"))
    with pytest.raises(DigitalExportError): export_visual_system(object(), "web")
    with pytest.raises(DigitalExportError): export_visual_system(system(), "browser")


def test_payload_tamper_and_hostile_provenance_fail_closed():
    valid = export_visual_system(system(), "web")
    with pytest.raises(DigitalExportError):
        DigitalTargetExport("web", LyingStr(valid.visual_system_sha256), valid.payload_sha256, valid.payload)
    tampered = tuple((key, "#ffffff" if key == "appearance.light.surface" else value) for key, value in valid.payload)
    with pytest.raises(DigitalExportError):
        DigitalTargetExport("web", valid.visual_system_sha256, valid.payload_sha256, tampered)


def test_payload_requires_sorted_unique_exact_text_pairs():
    valid = export_visual_system(system(), "web")
    reversed_payload = tuple(reversed(valid.payload))
    digest = hashlib.sha256(json.dumps(dict(reversed_payload), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    with pytest.raises(DigitalExportError):
        DigitalTargetExport("web", valid.visual_system_sha256, digest, reversed_payload)
    with pytest.raises(DigitalExportError):
        DigitalTargetExport("web", valid.visual_system_sha256, valid.payload_sha256, (("x", LyingStr("y")),))


def test_evidence_promotion_is_impossible():
    valid = export_visual_system(system(), "app")
    with pytest.raises(DigitalExportError):
        DigitalTargetExport(valid.target, valid.visual_system_sha256, valid.payload_sha256, valid.payload, physical_validation_eligible=True)
    with pytest.raises(DigitalExportError):
        DigitalTargetExport(valid.target, valid.visual_system_sha256, valid.payload_sha256, valid.payload, evidence_status="MEASURED")
