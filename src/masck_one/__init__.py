"""Masck One deterministic engineering/code-CAD package.

Public objects are loaded lazily so lightweight authority/preflight commands do not
import the CAD kernel unless geometry is actually requested.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .authority import Authority
    from .model import MasckOneModel

__all__ = ["Authority", "MasckOneModel", "load_authority", "build_model"]
__version__ = "0.1.0"


def __getattr__(name: str) -> Any:
    if name in {"Authority", "load_authority"}:
        from .authority import Authority, load_authority

        exports = {"Authority": Authority, "load_authority": load_authority}
        return exports[name]
    if name in {"MasckOneModel", "build_model"}:
        from .model import MasckOneModel, build_model

        exports = {"MasckOneModel": MasckOneModel, "build_model": build_model}
        return exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
