from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
import json
from pathlib import Path

from .authority import load_authority
from .frame_contract import (
    CANONICAL_FRAME_ID,
    LEGACY_INTERNAL_FRAME_ALIASES,
    LOCAL_FRAME_PREFIX,
    FrameContractError,
    build_cross_system_frame_contract,
)


FRAME_MANIFEST_KEYS = frozenset(
    {
        "coordinate_frame",
        "coordinate_frame_id",
        "world_frame_id",
    }
)
LEGACY_ALIAS_ALLOWED_MODULES = frozenset(
    {
        "frame_contract.py",
        "reference_surfaces.py",
        "spatial.py",
    }
)


@dataclass(frozen=True, slots=True)
class FrameDeclaration:
    path: str
    line: int
    site_kind: str
    frame_id: str


def _target_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    return None


def _is_frame_id_target(name: str) -> bool:
    upper = name.upper()
    return upper in {"WORLD_FRAME_ID", "COORDINATE_FRAME_ID"} or upper.endswith("_FRAME_ID")


def _constant_text(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and type(node.value) is str:
        return node.value
    return None


def _validate_frame_literal(frame_id: str, *, module_name: str, line: int) -> None:
    if frame_id == CANONICAL_FRAME_ID:
        return
    if frame_id.startswith(LOCAL_FRAME_PREFIX) and len(frame_id) > len(LOCAL_FRAME_PREFIX):
        return
    if frame_id in LEGACY_INTERNAL_FRAME_ALIASES and module_name in LEGACY_ALIAS_ALLOWED_MODULES:
        return
    if frame_id in LEGACY_INTERNAL_FRAME_ALIASES:
        raise FrameContractError(
            f"{module_name}:{line} uses legacy frame alias {frame_id!r} outside the explicit internal-alias boundary"
        )
    raise FrameContractError(
        f"{module_name}:{line} declares unknown cross-system frame {frame_id!r}; expected "
        f"{CANONICAL_FRAME_ID!r} or an explicit {LOCAL_FRAME_PREFIX}* frame"
    )


def scan_python_frame_declarations(
    source: str,
    *,
    path: str,
) -> tuple[FrameDeclaration, ...]:
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as exc:
        raise FrameContractError(f"cannot audit frame declarations in syntactically invalid {path}: {exc}") from exc

    module_name = Path(path).name
    declarations: list[FrameDeclaration] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            text = _constant_text(node.value)
            if text is not None:
                for target in node.targets:
                    name = _target_name(target)
                    if name is not None and _is_frame_id_target(name):
                        _validate_frame_literal(text, module_name=module_name, line=node.lineno)
                        declarations.append(
                            FrameDeclaration(path, node.lineno, f"assignment:{name}", text)
                        )
        elif isinstance(node, ast.AnnAssign):
            name = _target_name(node.target)
            text = None if node.value is None else _constant_text(node.value)
            if name is not None and _is_frame_id_target(name) and text is not None:
                _validate_frame_literal(text, module_name=module_name, line=node.lineno)
                declarations.append(
                    FrameDeclaration(path, node.lineno, f"annotated_assignment:{name}", text)
                )
        elif isinstance(node, ast.Dict):
            for key_node, value_node in zip(node.keys, node.values, strict=True):
                if key_node is None:
                    continue
                key = _constant_text(key_node)
                value = _constant_text(value_node)
                if key in FRAME_MANIFEST_KEYS and value is not None:
                    _validate_frame_literal(value, module_name=module_name, line=value_node.lineno)
                    declarations.append(
                        FrameDeclaration(path, value_node.lineno, f"manifest:{key}", value)
                    )

    return tuple(sorted(declarations, key=lambda item: (item.path, item.line, item.site_kind, item.frame_id)))


def audit_repository_frame_declarations(root: Path | None = None) -> tuple[FrameDeclaration, ...]:
    repository_root = root or Path(__file__).resolve().parents[2]
    source_root = repository_root / "src" / "masck_one"
    if not source_root.is_dir():
        raise FrameContractError(f"Masck One source root does not exist: {source_root}")

    declarations: list[FrameDeclaration] = []
    for path in sorted(source_root.glob("*.py")):
        relative = path.relative_to(repository_root).as_posix()
        declarations.extend(
            scan_python_frame_declarations(
                path.read_text(encoding="utf-8"),
                path=relative,
            )
        )
    return tuple(declarations)


def main() -> int:
    contract = build_cross_system_frame_contract(load_authority())
    declarations = audit_repository_frame_declarations()
    payload = {
        "schema": "MASCK_ONE_CROSS_SYSTEM_FRAME_AUDIT_V1",
        "contract": contract.manifest(),
        "repository_frame_declarations": [asdict(item) for item in declarations],
        "declaration_count": len(declarations),
        "status": "PASS",
        "physical_validation_eligible": False,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
