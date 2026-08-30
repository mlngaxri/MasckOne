from __future__ import annotations

from dataclasses import asdict, dataclass
import importlib.metadata
import json
from pathlib import Path
import re
import sys
from typing import Iterable

from .authority import AuthorityError, load_authority


REQUIRED_PYTHON = (3, 13)
EXPECTED_DISTRIBUTIONS = {
    "cadquery": "2.8.0",
    "jsonschema": "4.26.0",
    "PyYAML": "6.0.3",
}
LEGACY_PRODUCT_TOKEN = "F" + "CW"


@dataclass(frozen=True)
class PreflightCheck:
    id: str
    status: str
    message: str
    actual: object | None = None
    expected: object | None = None

    def to_dict(self) -> dict[str, object | None]:
        return asdict(self)


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _check_python() -> PreflightCheck:
    actual = [sys.version_info.major, sys.version_info.minor]
    status = "PASS" if tuple(actual) == REQUIRED_PYTHON else "FAIL"
    return PreflightCheck(
        id="PYTHON_VERSION",
        status=status,
        message="Runtime uses the repository's controlled Python major/minor version.",
        actual=actual,
        expected=list(REQUIRED_PYTHON),
    )


def _check_dependencies() -> list[PreflightCheck]:
    checks: list[PreflightCheck] = []
    for distribution, expected in EXPECTED_DISTRIBUTIONS.items():
        try:
            actual = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            actual = None
        checks.append(
            PreflightCheck(
                id=f"DEPENDENCY_{re.sub(r'[^A-Za-z0-9]+', '_', distribution).upper()}",
                status="PASS" if actual == expected else "FAIL",
                message="Runtime dependency matches the controlled repository version.",
                actual=actual,
                expected=expected,
            )
        )
    return checks


def _check_authority() -> list[PreflightCheck]:
    try:
        authority = load_authority()
    except AuthorityError as exc:
        return [
            PreflightCheck(
                id="AUTHORITY_LOAD",
                status="FAIL",
                message="Machine authority must load without schema or semantic errors.",
                actual=str(exc),
                expected="valid authority",
            )
        ]

    return [
        PreflightCheck("AUTHORITY_LOAD", "PASS", "Machine authority loads successfully."),
        PreflightCheck(
            "AUTHORITY_CONTRACT",
            "PASS" if authority.validation_report.valid else "FAIL",
            "Authority passes strict JSON Schema and deterministic semantic validation.",
            len(authority.validation_report.issues),
            0,
        ),
        PreflightCheck(
            "PRODUCT_NAME",
            "PASS" if authority.get("project", "name") == "Masck One" else "FAIL",
            "Human-facing product name is exactly Masck One.",
            authority.get("project", "name"),
            "Masck One",
        ),
        PreflightCheck(
            "PROJECT_ID",
            "PASS" if authority.get("project", "id") == "MASCK_ONE" else "FAIL",
            "Machine project identifier is stable.",
            authority.get("project", "id"),
            "MASCK_ONE",
        ),
        PreflightCheck(
            "AUTHORITY_SCHEMA_VERSION",
            "PASS" if authority.get("project", "schema_version") == "1.0.0" else "FAIL",
            "Authority schema version is explicit and controlled.",
            authority.get("project", "schema_version"),
            "1.0.0",
        ),
    ]


def _iter_text_files(root: Path) -> Iterable[Path]:
    ignored_parts = {".git", ".pytest_cache", "__pycache__", ".venv", "generated"}
    allowed_suffixes = {".py", ".md", ".toml", ".yaml", ".yml", ".json", ".txt"}
    for path in root.rglob("*"):
        if not path.is_file() or any(part in ignored_parts for part in path.parts):
            continue
        if path.name == ".gitignore" or path.suffix.lower() in allowed_suffixes:
            yield path


def _check_legacy_naming(root: Path) -> PreflightCheck:
    offenders: list[str] = []
    for path in _iter_text_files(root):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if path.resolve() == Path(__file__).resolve():
            text = text.replace('"F" + "CW"', '"legacy"')
        if LEGACY_PRODUCT_TOKEN.lower() in text.lower():
            offenders.append(path.relative_to(root).as_posix())
    return PreflightCheck(
        "LEGACY_PRODUCT_NAMING",
        "PASS" if not offenders else "FAIL",
        "No legacy product naming appears in source-controlled text artifacts.",
        offenders,
        [],
    )


def _check_required_structure(root: Path) -> PreflightCheck:
    required = [
        "README.md",
        "pyproject.toml",
        "config/masck_one_authority.yaml",
        "schemas/masck_one_authority.schema.json",
        "src/masck_one/__init__.py",
        "src/masck_one/authority.py",
        "src/masck_one/model.py",
        "src/masck_one/assertions.py",
        "src/masck_one/export.py",
        "src/masck_one/cli.py",
        "tests/test_authority.py",
        "tests/test_authority_contract.py",
        "tests/test_model.py",
    ]
    missing = [item for item in required if not (root / item).exists()]
    return PreflightCheck(
        "REPOSITORY_STRUCTURE",
        "PASS" if not missing else "FAIL",
        "Required Phase 1 source files exist at deterministic paths.",
        missing,
        [],
    )


def run_preflight() -> dict[str, object]:
    root = repository_root()
    checks = [
        _check_python(),
        *_check_dependencies(),
        *_check_authority(),
        _check_legacy_naming(root),
        _check_required_structure(root),
    ]
    result = "PASS" if all(check.status == "PASS" for check in checks) else "FAIL"
    return {
        "project": "Masck One",
        "phase": "1",
        "iteration": "2",
        "result": result,
        "checks": [check.to_dict() for check in checks],
    }


def main() -> int:
    report = run_preflight()
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
