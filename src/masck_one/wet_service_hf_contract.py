"""Prototype wet-hand service human-factors convergence contract.

These limits are CAD/prototype screening hypotheses, not validated ergonomic,
cleanability, retention, ingress, or production claims.
"""

import math


class WetServiceHFContractError(ValueError):
    pass


LIMITS = {
    "HF_SERVICE_GRIP_WIDTH_MM_MIN": 12.0,
    "HF_SERVICE_GRIP_DEPTH_MM_MIN": 1.2,
    "HF_SERVICE_GRIP_EDGE_RADIUS_MM_MIN": 0.8,
    "HF_SERVICE_RELEASE_CLEARANCE_MM_MIN": 1.5,
    "HF_SERVICE_TRAVEL_MM_MIN": 3.0,
    "HF_SERVICE_TRAVEL_MM_MAX": 8.0,
    "HF_SERVICE_ENDSTOP_OVERTRAVEL_MM_MIN": 0.8,
    "HF_SERVICE_BILATERAL_GRIP_WIDTH_MISMATCH_MM_MAX": 1.0,
}

REQUIRED = (
    "HF_SERVICE_GRIP_WIDTH_L_MM",
    "HF_SERVICE_GRIP_WIDTH_R_MM",
    "HF_SERVICE_GRIP_DEPTH_MM",
    "HF_SERVICE_GRIP_EDGE_RADIUS_MM",
    "HF_SERVICE_RELEASE_CLEARANCE_MM",
    "HF_SERVICE_TRAVEL_MM",
    "HF_SERVICE_ENDSTOP_OVERTRAVEL_MM",
)


def validate_wet_service_hf_evidence(evidence):
    values = {}
    for key in REQUIRED:
        if key not in evidence:
            raise WetServiceHFContractError(f"missing required evidence: {key}")
        value = evidence[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise WetServiceHFContractError(f"{key} must be numeric")
        value = float(value)
        if not math.isfinite(value) or value < 0:
            raise WetServiceHFContractError(f"{key} must be finite and nonnegative")
        values[key] = value

    for side in ("L", "R"):
        if values[f"HF_SERVICE_GRIP_WIDTH_{side}_MM"] < LIMITS["HF_SERVICE_GRIP_WIDTH_MM_MIN"]:
            raise WetServiceHFContractError("service grip width is below prototype wet-finger target")

    if abs(values["HF_SERVICE_GRIP_WIDTH_L_MM"] - values["HF_SERVICE_GRIP_WIDTH_R_MM"]) > LIMITS["HF_SERVICE_BILATERAL_GRIP_WIDTH_MISMATCH_MM_MAX"]:
        raise WetServiceHFContractError("bilateral service grip width mismatch is excessive")
    if values["HF_SERVICE_GRIP_DEPTH_MM"] < LIMITS["HF_SERVICE_GRIP_DEPTH_MM_MIN"]:
        raise WetServiceHFContractError("service grip depth is below prototype acquisition target")
    if values["HF_SERVICE_GRIP_EDGE_RADIUS_MM"] < LIMITS["HF_SERVICE_GRIP_EDGE_RADIUS_MM_MIN"]:
        raise WetServiceHFContractError("service grip edge is too sharp for the prototype target")
    if values["HF_SERVICE_RELEASE_CLEARANCE_MM"] < LIMITS["HF_SERVICE_RELEASE_CLEARANCE_MM_MIN"]:
        raise WetServiceHFContractError("release clearance is obstructed")
    if not LIMITS["HF_SERVICE_TRAVEL_MM_MIN"] <= values["HF_SERVICE_TRAVEL_MM"] <= LIMITS["HF_SERVICE_TRAVEL_MM_MAX"]:
        raise WetServiceHFContractError("service travel is outside prototype tactile range")
    if values["HF_SERVICE_ENDSTOP_OVERTRAVEL_MM"] < LIMITS["HF_SERVICE_ENDSTOP_OVERTRAVEL_MM_MIN"]:
        raise WetServiceHFContractError("service end-stop lacks protected overtravel margin")

    return values
