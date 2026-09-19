from __future__ import annotations

import pytest

from masck_one import treatment_terminal_datum_preload_v4 as v4
from masck_one.treatment_terminal_datum_preload_v5 import (
    TreatmentTerminalDatumPreloadV5Error,
    build_terminal_datum_preload_v5_architecture,
    manifest_v5,
)


class HostileDict(dict):
    """A dict subclass must not cross the exact V5 evidence boundary."""


def test_v5_manifest_rejects_non_mapping_payload(monkeypatch):
    architecture = build_terminal_datum_preload_v5_architecture()
    monkeypatch.setattr(v4.TerminalDatumPreloadV4Architecture, "manifest", lambda _self: [])

    with pytest.raises(TreatmentTerminalDatumPreloadV5Error, match="requires exact dict payload"):
        manifest_v5(architecture)


def test_v5_manifest_rejects_dict_subclass_payload(monkeypatch):
    architecture = build_terminal_datum_preload_v5_architecture()
    original_manifest = v4.TerminalDatumPreloadV4Architecture.manifest

    def hostile_manifest(self):
        return HostileDict(original_manifest(self))

    monkeypatch.setattr(v4.TerminalDatumPreloadV4Architecture, "manifest", hostile_manifest)

    with pytest.raises(TreatmentTerminalDatumPreloadV5Error, match="requires exact dict payload"):
        manifest_v5(architecture)
