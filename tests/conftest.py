from __future__ import annotations

"""Lazy pytest reuse for immutable canonical inputs consumed by Cell 3 CAD builders.

The Cell 3 regression modules still execute their owning builders, deterministic fresh
rebuilds, hostile source checks, collision assertions and STEP round-trips. This fixture
only reuses the validated default authority and current canonical package model imported
inside the stacked Cell 3 producer modules. Modified or foreign authority inputs always
fall through to the original model builder.
"""

import pytest

from masck_one.authority import Authority, load_authority as original_load_authority
from masck_one.model import build_model as original_build_model
import masck_one.hair_pinch_keepouts as hair_module
import masck_one.occipital_stabilizer as occipital_module
import masck_one.retention_fit_adjustment as fit_module
import masck_one.retention_load_path as load_module


@pytest.fixture(scope="session", autouse=True)
def _reuse_cell3_canonical_inputs():
    canonical_authority: Authority | None = None
    canonical_model = None

    def get_canonical_authority() -> Authority:
        nonlocal canonical_authority
        if canonical_authority is None:
            canonical_authority = original_load_authority()
        return canonical_authority

    def is_canonical(authority: Authority) -> bool:
        canonical = get_canonical_authority()
        return authority.source == canonical.source and authority.data == canonical.data

    def shared_load_authority(*args, **kwargs):
        if not args and not kwargs:
            return get_canonical_authority()
        return original_load_authority(*args, **kwargs)

    def shared_build_model(authority: Authority | None = None):
        nonlocal canonical_model
        requested = get_canonical_authority() if authority is None else authority
        if is_canonical(requested):
            if canonical_model is None:
                canonical_model = original_build_model(get_canonical_authority())
            return canonical_model
        return original_build_model(requested)

    patch = pytest.MonkeyPatch()
    for module in (occipital_module, fit_module, hair_module, load_module):
        patch.setattr(module, "load_authority", shared_load_authority)
        patch.setattr(module, "build_model", shared_build_model)

    try:
        yield
    finally:
        patch.undo()
