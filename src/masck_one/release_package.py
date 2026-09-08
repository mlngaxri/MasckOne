"""Integrity of a generated development package, independent of the CAD kernel.

The manifest commits a particular set of file bytes. It is not a manufacturing
approval, and no successful software check can supply missing physical evidence.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import tempfile
from typing import Callable


MANIFEST_NAME = "package_manifest.json"
PACKAGE_SCHEMA = "MASCK_ONE_DEVELOPMENT_PACKAGE_V1"


class ExportValidationError(ValueError):
    """The candidate must not be published as a completed CAD package."""


def validate_checks(checks: list[dict]) -> None:
    if not checks:
        raise ExportValidationError("Cannot export without engineering checks")
    seen = set()
    for check in checks:
        check_id = check.get("id")
        if not isinstance(check_id, str) or not check_id or check_id in seen:
            raise ExportValidationError("Engineering check IDs must be unique nonempty strings")
        seen.add(check_id)
        if check.get("status") not in ("PASS", "BLOCKED"):
            raise ExportValidationError(f"Engineering check {check_id}: {check.get('status')}")


def development_readiness(checks: list[dict], components: list[dict]) -> dict:
    validate_checks(checks)
    return {
        "status": "BLOCKED",
        "production_ready": False,
        "scope": "CURRENT_DEVELOPMENT_MODEL_ONLY",
        "blocked_checks": [
            {"id": c["id"], "message": c["message"]}
            for c in checks if c["status"] == "BLOCKED"
        ],
        "component_maturity": {c["name"]: c["status"] for c in components},
        "required_release_evidence": [
            "Complete released component geometry and positive assembly/service interfaces",
            "Approved materials, supplier BOM, manufacturing drawings and tolerance stacks",
            "Source-bound mass, CG, power, thermal and fluid ledgers",
            "Validated fit, airway, contact, leakage, hygiene, durability and release behavior",
        ],
        "note": (
            "This exporter generates development geometry and reference envelopes. "
            "Even an all-PASS check list does not provide a production release path. "
            "Manufacturing approval requires a separately reviewed evidence contract."
        ),
    }


def _file_record(path: Path) -> dict:
    data = path.read_bytes()
    return {"size_bytes": len(data), "sha256": sha256(data).hexdigest()}


def publish_package(output_dir: str | Path, writer: Callable[[Path], None]) -> None:
    """Stage all exports first; install a hash manifest only after every file exists.

    Validation/serialization/kernel failures leave the previous package untouched.
    If filesystem publication is interrupted, the absent completion manifest makes
    the partial directory fail verification. Unrelated files are never removed.
    """
    output = Path(output_dir).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and not output.is_dir():
        raise ExportValidationError("Output must be a directory")
    with tempfile.TemporaryDirectory(prefix="masck-one-export-", dir=output.parent) as tmp:
        stage = Path(tmp)
        writer(stage)
        paths = sorted(stage.iterdir())
        if not paths or any(not p.is_file() or p.is_symlink() for p in paths):
            raise ExportValidationError("Package must contain regular files only")
        if any(p.name == MANIFEST_NAME for p in paths):
            raise ExportValidationError("The publisher owns the completion manifest")
        new_names = {p.name for p in paths}
        if output.exists():
            stale = [p.name for p in output.iterdir()
                     if p.suffix.lower() in (".step", ".stp") and p.name not in new_names]
            if stale:
                raise ExportValidationError(f"Output contains unlisted STEP files; use a clean directory: {sorted(stale)}")
            for name in (*new_names, MANIFEST_NAME):
                target = output / name
                if target.is_symlink() or (target.exists() and not target.is_file()):
                    raise ExportValidationError(f"Cannot replace non-regular output: {name}")
        manifest = {
            "schema": PACKAGE_SCHEMA,
            "scope": "DEVELOPMENT_ONLY",
            "files": {p.name: _file_record(p) for p in paths},
        }
        manifest_path = stage / MANIFEST_NAME
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        output.mkdir(parents=True, exist_ok=True)
        (output / MANIFEST_NAME).unlink(missing_ok=True)
        for path in paths:
            path.replace(output / path.name)
        manifest_path.replace(output / MANIFEST_NAME)


def verify_package(output_dir: str | Path) -> dict:
    output = Path(output_dir).resolve()
    manifest_path = output / MANIFEST_NAME
    if manifest_path.is_symlink():
        raise ExportValidationError("Completion manifest cannot be a symlink")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != PACKAGE_SCHEMA:
        raise ExportValidationError("Unknown package schema")
    if manifest.get("scope") != "DEVELOPMENT_ONLY":
        raise ExportValidationError("Package scope must be DEVELOPMENT_ONLY")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ExportValidationError("Empty or malformed package file inventory")
    for name, expected in files.items():
        if (not isinstance(name, str) or not name or name in (".", "..", MANIFEST_NAME)
                or "/" in name or "\\" in name):
            raise ExportValidationError("Package filenames must stay inside package as local basenames")
        path = output / name
        if path.is_symlink() or not path.is_file() or _file_record(path) != expected:
            raise ExportValidationError(f"Missing or changed package file: {name}")
    stale = [p.name for p in output.iterdir()
             if p.suffix.lower() in (".step", ".stp") and p.name not in files]
    if stale:
        raise ExportValidationError(f"Unlisted STEP files: {sorted(stale)}")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify generated Masck One package bytes.")
    parser.add_argument("directory")
    args = parser.parse_args(argv)
    try:
        manifest = verify_package(args.directory)
    except (OSError, ValueError) as exc:
        print(json.dumps({"result": "FAIL", "error": str(exc)}))
        return 1
    print(json.dumps({"result": "PASS", "scope": manifest["scope"], "file_count": len(manifest["files"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
