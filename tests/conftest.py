from __future__ import annotations

"""Lazy session reuse for immutable Cell 3 CAD dependencies.

The Prompt 08-11 regression modules retain their own top-level builders, hostile source
checks, deterministic fresh rebuilds and STEP round-trip assertions. Only zero-argument
upstream dependency calls made by downstream builders are memoized. This avoids eagerly
constructing the complete model -> occipital -> fit -> hair -> load chain before pytest
while preserving every direct builder call made by the owning test module.
"""

import functools

import pytest

import masck_one.hair_pinch_keepouts as hair_module
import masck_one.occipital_stabilizer as occipital_module
import masck_one.retention_fit_adjustment as fit_module
import masck_one.retention_load_path as load_module
import masck_one.retention_load_path_release as release_module


@pytest.fixture(scope="session", autouse=True)
def _reuse_cell3_retention_dependencies():
    original_occipital = fit_module.build_occipital_stabilizer
    original_fit_hair = hair_module.build_retention_fit_adjustment
    original_fit_load = load_module.build_retention_fit_adjustment
    original_hair_load = load_module.build_hair_pinch_keepouts
    original_load_release = release_module.build_retention_load_path

    cached_occipital = functools.lru_cache(maxsize=1)(original_occipital)
    cached_fit_hair = functools.lru_cache(maxsize=1)(original_fit_hair)
    cached_fit_load = functools.lru_cache(maxsize=1)(original_fit_load)
    cached_hair_load = functools.lru_cache(maxsize=1)(original_hair_load)
    cached_load_release = functools.lru_cache(maxsize=1)(original_load_release)

    patch = pytest.MonkeyPatch()
    patch.setattr(fit_module, "build_occipital_stabilizer", cached_occipital)
    patch.setattr(hair_module, "build_retention_fit_adjustment", cached_fit_hair)
    patch.setattr(load_module, "build_retention_fit_adjustment", cached_fit_load)
    patch.setattr(load_module, "build_hair_pinch_keepouts", cached_hair_load)
    patch.setattr(release_module, "build_retention_load_path", cached_load_release)

    try:
        yield
    finally:
        patch.undo()
        cached_occipital.cache_clear()
        cached_fit_hair.cache_clear()
        cached_fit_load.cache_clear()
        cached_hair_load.cache_clear()
        cached_load_release.cache_clear()
