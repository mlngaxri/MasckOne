from __future__ import annotations

"""Session-scoped reuse for immutable Cell 3 CAD dependencies.

The Prompt 08-11 regression modules intentionally retain their own top-level builders,
tamper tests, deterministic rebuilds and STEP round-trip assertions. What was expensive
and redundant was rebuilding the same immutable upstream model/mechanism chain again
inside every downstream module. This autouse fixture memoizes only dependency calls that
resolve to the exact current session objects; foreign or modified inputs fall through to
the original builders so hostile source/geometry tests remain effective.
"""

import pytest

import masck_one.hair_pinch_keepouts as hair_module
import masck_one.occipital_stabilizer as occipital_module
import masck_one.retention_fit_adjustment as fit_module
import masck_one.retention_load_path as load_module
import masck_one.retention_load_path_release as release_module
from masck_one.model import build_model


@pytest.fixture(scope="session", autouse=True)
def _cell3_shared_immutable_cad_dependencies():
    model = build_model()
    authority = model.authority

    occipital = occipital_module.build_occipital_stabilizer(authority, model)
    fit = fit_module.build_retention_fit_adjustment(authority, model, occipital)
    hair = hair_module.build_hair_pinch_keepouts(authority, model, fit)
    load = load_module.build_retention_load_path(authority, model, fit, hair)

    original_occipital = fit_module.build_occipital_stabilizer
    original_fit_hair = hair_module.build_retention_fit_adjustment
    original_fit_load = load_module.build_retention_fit_adjustment
    original_hair_load = load_module.build_hair_pinch_keepouts
    original_load_release = release_module.build_retention_load_path

    def _same_authority(value) -> bool:
        return value is None or value is authority

    def _same_model(value) -> bool:
        return value is None or value is model

    def cached_occipital(authority_arg=None, model_arg=None):
        if _same_authority(authority_arg) and _same_model(model_arg):
            return occipital
        return original_occipital(authority_arg, model_arg)

    def cached_fit(authority_arg=None, model_arg=None, occipital_arg=None):
        if (
            _same_authority(authority_arg)
            and _same_model(model_arg)
            and (occipital_arg is None or occipital_arg is occipital)
        ):
            return fit
        return original_fit_hair(authority_arg, model_arg, occipital_arg)

    def cached_fit_for_load(authority_arg=None, model_arg=None, occipital_arg=None):
        if (
            _same_authority(authority_arg)
            and _same_model(model_arg)
            and (occipital_arg is None or occipital_arg is occipital)
        ):
            return fit
        return original_fit_load(authority_arg, model_arg, occipital_arg)

    def cached_hair(authority_arg=None, model_arg=None, fit_arg=None):
        if (
            _same_authority(authority_arg)
            and _same_model(model_arg)
            and (fit_arg is None or fit_arg is fit)
        ):
            return hair
        return original_hair_load(authority_arg, model_arg, fit_arg)

    def cached_load(source=None):
        if source is None:
            return load
        return original_load_release(source)

    patch = pytest.MonkeyPatch()
    patch.setattr(fit_module, "build_occipital_stabilizer", cached_occipital)
    patch.setattr(hair_module, "build_retention_fit_adjustment", cached_fit)
    patch.setattr(load_module, "build_retention_fit_adjustment", cached_fit_for_load)
    patch.setattr(load_module, "build_hair_pinch_keepouts", cached_hair)
    patch.setattr(release_module, "build_retention_load_path", cached_load)

    try:
        yield
    finally:
        patch.undo()
