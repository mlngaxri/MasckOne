from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml


class AuthorityError(ValueError):
    """Raised when the machine authority is incomplete or internally invalid."""


@dataclass(frozen=True)
class Authority:
    """Typed access wrapper around the Masck One YAML authority."""

    data: dict[str, Any]
    source: Path

    def get(self, *path: str) -> Any:
        node: Any = self.data
        for key in path:
            if not isinstance(node, dict) or key not in node:
                joined = ".".join(path)
                raise AuthorityError(f"Missing authority path: {joined}")
            node = node[key]
        return node

    def number(self, *path: str) -> float:
        value = self.get(*path)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise AuthorityError(f"Expected numeric value at {'.'.join(path)}, got {value!r}")
        return float(value)

    def pair(self, *path: str) -> tuple[float, float]:
        value = self.get(*path)
        if not isinstance(value, list) or len(value) != 2:
            raise AuthorityError(f"Expected 2-item list at {'.'.join(path)}, got {value!r}")
        return float(value[0]), float(value[1])

    def triple(self, *path: str) -> tuple[float, float, float]:
        value = self.get(*path)
        if not isinstance(value, list) or len(value) != 3:
            raise AuthorityError(f"Expected 3-item list at {'.'.join(path)}, got {value!r}")
        return float(value[0]), float(value[1]), float(value[2])

    def require_paths(self, paths: Iterable[tuple[str, ...]]) -> None:
        for path in paths:
            self.get(*path)


def default_authority_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "masck_one_authority.yaml"


def load_authority(path: str | Path | None = None) -> Authority:
    source = Path(path) if path is not None else default_authority_path()
    source = source.resolve()
    if not source.exists():
        raise AuthorityError(f"Authority file does not exist: {source}")
    with source.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        raise AuthorityError("Authority root must be a mapping")

    authority = Authority(raw, source)
    authority.require_paths(
        [
            ("project", "name"),
            ("coordinate_system", "origin"),
            ("geometry", "outer_xy_envelope_mm"),
            ("geometry", "shell_nominal_wall_mm"),
            ("geometry", "eye", "centers_mm", "left"),
            ("geometry", "eye", "centers_mm", "right"),
            ("geometry", "eye", "visual_aperture_wh_mm"),
            ("geometry", "mouth", "center_mm"),
            ("geometry", "mouth", "visual_aperture_wh_mm"),
            ("geometry", "nostrils", "centers_mm", "left"),
            ("geometry", "nostrils", "centers_mm", "right"),
            ("geometry", "nostrils", "minimum_deformed_area_each_mm2"),
            ("actuation", "count"),
            ("fluid", "water_reservoir", "gross_mL"),
            ("fluid", "cartridge", "external_envelope_mm"),
        ]
    )

    if authority.get("project", "name") != "Masck One":
        raise AuthorityError("Product name must be exactly 'Masck One'")
    return authority
