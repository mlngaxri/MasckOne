from __future__ import annotations

import pytest

from masck_one import treatment_terminal_datum_preload_v4 as v4
from masck_one.treatment_terminal_datum_preload_v5 import (
    TreatmentTerminalDatumPreloadV5Error,
    build_terminal_datum_preload_v5_architecture,
    manifest_v5,
)


@pytest.mark.parametrize("hostile_value", [float("nan"), float("inf"), float("-inf")])
def test_v5_manifest_rejects_nonfinite_certification_evidence(monkeypatch, hostile_value):
    architecture = build_terminal_datum_preload_v5_architecture()
    original_manifest = v4.TerminalDatumPreloadV4Architecture.manifest

    def hostile_manifest(self):
        payload = original_manifest(self)
        payload["hostile_nonfinite_evidence"] = hostile_value
        return payload

    monkeypatch.setattr(v4.TerminalDatumPreloadV4Architecture, "manifest", hostile_manifest)

    with pytest.raises(TreatmentTerminalDatumPreloadV5Error, match="non-canonical certification evidence"):
        manifest_v5(architecture)


def test_v5_manifest_rejects_nonserializable_certification_evidence(monkeypatch):
    architecture = build_terminal_datum_preload_v5_architecture()
    original_manifest = v4.TerminalDatumPreloadV4Architecture.manifest

    def hostile_manifest(self):
        payload = original_manifest(self)
        payload["hostile_object_evidence"] = object()
        return payload

    monkeypatch.setattr(v4.TerminalDatumPreloadV4Architecture, "manifest", hostile_manifest)

    with pytest.raises(TreatmentTerminalDatumPreloadV5Error, match="non-canonical certification evidence"):
        manifest_v5(architecture)
