"""Deterministic synthetic analyzer check; stdout only, never physical evidence."""
import json
import math

from masck_one.interaction_metrology import Sample, Trace, analyse


def comparison() -> dict[str, object]:
    # Existing owner's 1.07 mm stop is context only, not changed or authorised
    # for actuation. Both force profiles below are invented pipeline stimuli.
    owner = "9fb64aa4753dad03a455aad4802910d8814ef5ce"
    xs = [1.07 * i / 40 for i in range(41)]
    results = {}
    for name, amplitude in (("linear_reference", 0.0), ("added_sample_ripple", .08)):
        load = tuple(Sample(x, .3 + x + amplitude * math.sin(10 * math.pi * x / 1.07), .001, .01) for x in xs)
        unload = tuple(Sample(x, .2 + .8 * x, .001, .01) for x in reversed(xs))
        results[name] = analyse(Trace(load, unload, "synthetic",
            "invented analytic software-regression stimulus; no predicted hardware forces",
            "primary-control passive off-face force-travel characterization"), roughness_window_samples=5)
    return {"owner_sha": owner, "owner_context": "V11 series force path remains rejected",
            "owner_hard_stop_context_mm": 1.07, "results": results}


if __name__ == "__main__":
    print(json.dumps(comparison(), indent=2, allow_nan=False))
