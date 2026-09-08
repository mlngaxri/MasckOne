from __future__ import annotations

import argparse
from collections.abc import Hashable
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
import yaml


class BrandIdentityError(ValueError):
    """Raised when the MASCK brand/product identity contract is invalid."""


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate keys."""


def _construct_unique_mapping(
    loader: _UniqueKeySafeLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, Hashable):
            raise BrandIdentityError(
                f"Unhashable YAML mapping key at line {key_node.start_mark.line + 1}"
            )
        if key in mapping:
            raise BrandIdentityError(
                f"Duplicate YAML key {key!r} at line {key_node.start_mark.line + 1}"
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def default_brand_authority_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "masck_brand_authority.yaml"


def default_brand_schema_path() -> Path:
    return Path(__file__).resolve().parents[2] / "schemas" / "masck_brand_authority.schema.json"


@dataclass(frozen=True)
class BrandIdentity:
    data: dict[str, Any]
    source: Path
    schema_source: Path

    @property
    def revision(self) -> str:
        return str(self.data["brand"]["revision"])

    @property
    def master_brand(self) -> str:
        return str(self.data["architecture"]["master_brand"])

    @property
    def product_name(self) -> str:
        return str(self.data["architecture"]["product_name"])

    @property
    def master_mark(self) -> str:
        return str(self.data["architecture"]["master_mark_id"])

    @property
    def product_designation(self) -> str:
        return str(self.data["architecture"]["product_designation"])

    def manifest(self) -> dict[str, Any]:
        canonical = json.dumps(
            self.data,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        return {
            "contract": "MASCK_BRAND_IDENTITY_V1",
            "revision": self.revision,
            "master_brand": self.master_brand,
            "master_mark": self.master_mark,
            "master_mark_status": self.data["master_mark"]["status"],
            "product_name": self.product_name,
            "product_machine_id": self.data["architecture"]["product_machine_id"],
            "product_designation": self.product_designation,
            "product_designation_role": self.data["architecture"]["product_designation_role"],
            "company_category": self.data["brand"]["company_category"],
            "execution_focus": self.data["brand"]["execution_focus"],
            "brand_promise": self.data["brand"]["promise"],
            "surface_language": self.data["surface_language"],
            "interaction_signature": self.data["interaction_signature"],
            "optical_language": self.data["optical_language"],
            "cmf": self.data["cmf"],
            "cost_discipline": self.data["cost_discipline"],
            "evidence_boundary": self.data["evidence_boundary"],
            "source_contract": str(self.source),
            "schema_contract": str(self.schema_source),
            "canonical_content_sha256": sha256(canonical.encode("utf-8")).hexdigest(),
        }


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise BrandIdentityError(f"Brand authority file does not exist: {path}")
    try:
        raw = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeySafeLoader)
    except yaml.YAMLError as exc:
        raise BrandIdentityError(f"Brand authority YAML cannot be parsed: {exc}") from exc
    if not isinstance(raw, dict):
        raise BrandIdentityError("Brand authority root must be a mapping")
    return raw


def _read_schema(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise BrandIdentityError(f"Brand authority schema does not exist: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BrandIdentityError(f"Brand authority schema is invalid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise BrandIdentityError("Brand authority schema root must be an object")
    Draft202012Validator.check_schema(raw)
    return raw


def _schema_error_message(error: Any) -> str:
    path = ".".join(str(part) for part in error.absolute_path) or "<root>"
    return f"{path}: {error.message}"


def _validate_semantics(data: dict[str, Any]) -> None:
    architecture = data["architecture"]
    master_mark = data["master_mark"]
    primary_control = data["interaction_signature"]["primary_control"]
    surface_prohibited = set(data["surface_language"]["prohibited"])

    if architecture["master_brand"] != data["brand"]["master_name"]:
        raise BrandIdentityError("Master brand name must be identical across brand and architecture")
    if architecture["master_mark_id"] != master_mark["id"]:
        raise BrandIdentityError("Architecture master mark must match the master-mark contract")
    if primary_control["mark"] != master_mark["id"]:
        raise BrandIdentityError("Primary control must carry the master mark, not a product-only badge")
    if primary_control["product_designation_on_primary_control"]:
        raise BrandIdentityError("M/1 is a product designation and may not become the master-button logo")
    if architecture["product_designation"] == architecture["master_mark_id"]:
        raise BrandIdentityError("Product designation and master mark must remain distinct identities")

    required_visual_rejections = {
        "goggle_eye_rings",
        "vr_headset",
        "respirator",
        "medical_ppe",
        "tactical_panels",
        "helmet",
    }
    missing = required_visual_rejections - surface_prohibited
    if missing:
        raise BrandIdentityError(
            "Brand surface language lost mandatory anti-goggle/anti-PPE constraints: "
            + ", ".join(sorted(missing))
        )

    reference = primary_control["candidate_mechanical_reference"]
    travel_order = [
        float(reference["force_peak_travel_mm"]),
        float(reference["first_landing_start_mm"]),
        float(reference["second_landing_start_mm"]),
        float(reference["nominal_bottom_travel_mm"]),
        float(reference["hard_stop_travel_mm"]),
    ]
    if travel_order != sorted(travel_order) or len(set(travel_order)) != len(travel_order):
        raise BrandIdentityError(
            "Primary-control candidate travel events must remain strictly ordered from tactile peak to hard stop"
        )


def load_brand_identity(
    source: str | Path | None = None,
    schema_source: str | Path | None = None,
) -> BrandIdentity:
    source_path = Path(source) if source is not None else default_brand_authority_path()
    schema_path = Path(schema_source) if schema_source is not None else default_brand_schema_path()
    data = _read_yaml(source_path)
    schema = _read_schema(schema_path)

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda error: list(error.absolute_path))
    if errors:
        rendered = "; ".join(_schema_error_message(error) for error in errors)
        raise BrandIdentityError(f"Brand authority failed schema validation: {rendered}")

    _validate_semantics(data)
    return BrandIdentity(data=data, source=source_path.resolve(), schema_source=schema_path.resolve())


def build_brand_identity_manifest() -> dict[str, Any]:
    return load_brand_identity().manifest()


def write_brand_identity_manifest(output_dir: str | Path) -> Path:
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    destination = output / "brand_identity.json"
    destination.write_text(
        json.dumps(build_brand_identity_manifest(), indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return destination


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="masck-brand-check",
        description="Validate and emit the MASCK master-brand / Masck One product identity contract.",
    )
    parser.add_argument("--source", default=None, help="Optional brand-authority YAML path")
    parser.add_argument("--schema", default=None, help="Optional brand-authority JSON Schema path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    identity = load_brand_identity(args.source, args.schema)
    print(json.dumps(identity.manifest(), indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
