"""Sample-domain interaction measurements; no tactile acceptance or release decision.

Displacement is inward from an operator-defined datum (mm); force is the
non-negative compressive magnitude (N), including on the outward unloading leg.
N mm = mJ. These are actuator work magnitudes, not signed path integrals.
"""
from dataclasses import dataclass
import math
from typing import Literal


@dataclass(frozen=True)
class Sample:
    displacement_mm: float
    compression_N: float
    displacement_bound_mm: float = 0.0
    force_bound_N: float = 0.0


@dataclass(frozen=True)
class Trace:
    loading: tuple[Sample, ...]
    unloading: tuple[Sample, ...]
    provenance: Literal["measured", "synthetic"]
    source: str
    interaction: str


def _finite(value: float) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _branch(samples: tuple[Sample, ...], direction: int) -> None:
    if len(samples) < 2:
        raise ValueError("each leg needs at least two samples")
    for s in samples:
        values = (s.displacement_mm, s.compression_N, s.displacement_bound_mm, s.force_bound_N)
        if not all(_finite(v) for v in values) or any(v < 0 for v in values):
            raise ValueError("samples and absolute uncertainty bounds must be finite and non-negative")
    if any(direction * (b.displacement_mm - a.displacement_mm) <= 0
           for a, b in zip(samples, samples[1:])):
        raise ValueError("legs must be strictly monotonic; segment dwell or reversal data first")


def _work(samples: tuple[Sample, ...]) -> dict[str, float]:
    nominal = lower = upper = 0.0
    for a, b in zip(samples, samples[1:]):
        dx = b.displacement_mm - a.displacement_mm
        du = a.displacement_bound_mm + b.displacement_bound_mm
        f = (a.compression_N + b.compression_N) / 2
        flo = (max(0.0, a.compression_N - a.force_bound_N)
               + max(0.0, b.compression_N - b.force_bound_N)) / 2
        fhi = f + (a.force_bound_N + b.force_bound_N) / 2
        nominal += dx * f
        lower += max(0.0, dx - du) * flo
        upper += (dx + du) * fhi
    if not all(math.isfinite(v) for v in (nominal, lower, upper)):
        raise ValueError("sample work exceeds finite numeric range")
    return {"nominal_mJ": nominal, "sample_bound_lower_mJ": lower,
            "sample_bound_upper_mJ": upper}


def _windows(samples: tuple[Sample, ...], width: int) -> list[dict[str, float]]:
    windows = []
    for start in range(len(samples) - width + 1):
        group = samples[start:start + width]
        # Centring avoids cancellation when the datum is far from the stroke.
        xs = [s.displacement_mm - group[0].displacement_mm for s in group]
        ys = [s.compression_N for s in group]
        try:
            xm, ym = sum(xs) / width, sum(ys) / width
            denominator = sum((x - xm)**2 for x in xs)
            if not math.isfinite(denominator) or denominator <= 0:
                raise ValueError("window displacement variance exceeds supported numeric range")
            slope = sum((x - xm) * (y - ym) for x, y in zip(xs, ys)) / denominator
            rms = math.sqrt(sum((y - ym - slope * (x - xm))**2 for x, y in zip(xs, ys)) / width)
        except OverflowError as exc:
            raise ValueError("window diagnostics exceed finite numeric range") from exc
        if not math.isfinite(slope) or not math.isfinite(rms):
            raise ValueError("window diagnostics exceed finite numeric range")
        windows.append({"start_mm": group[0].displacement_mm,
                        "end_mm": group[-1].displacement_mm,
                        "linear_residual_rms_N": rms,
                        "fitted_gradient_N_per_mm": slope})
    return windows


def analyse(trace: Trace, *, roughness_window_samples: int = 3) -> dict[str, object]:
    """Integrate observed legs and expose local departures from linear force travel.

    Bounds enclose trapezoidal *sample* work under the supplied absolute errors
    and monotonic underlying legs. They exclude between-sample curvature,
    rate dependence, datum error beyond supplied bounds and instrument dynamics.
    Roughness is descriptive, sampling-dependent and may include intentional
    snap-through; it is not a friction or perceived-smoothness qualification.
    """
    if (trace.provenance not in ("measured", "synthetic")
            or not isinstance(trace.source, str) or not trace.source.strip()
            or not isinstance(trace.interaction, str) or not trace.interaction.strip()):
        raise ValueError("explicit provenance, source and interaction are required")
    _branch(trace.loading, 1)
    _branch(trace.unloading, -1)
    unload = tuple(reversed(trace.unloading))
    if (trace.loading[0].displacement_mm != unload[0].displacement_mm
            or trace.loading[-1].displacement_mm != unload[-1].displacement_mm):
        raise ValueError("loading and unloading must cover identical nominal displacement endpoints")
    if (isinstance(roughness_window_samples, bool) or not isinstance(roughness_window_samples, int)
            or not 3 <= roughness_window_samples <= min(len(trace.loading), len(unload))):
        raise ValueError("roughness window must be an integer from 3 through the shorter leg length")
    load_work, unload_work = _work(trace.loading), _work(unload)
    return {
        "provenance": trace.provenance, "source": trace.source, "interaction": trace.interaction,
        "force_convention": "nonnegative_compressive_magnitude_on_both_legs",
        "loading_work": load_work, "unloading_work": unload_work,
        "signed_hysteresis_mJ": load_work["nominal_mJ"] - unload_work["nominal_mJ"],
        "signed_hysteresis_sample_bounds_mJ": [
            load_work["sample_bound_lower_mJ"] - unload_work["sample_bound_upper_mJ"],
            load_work["sample_bound_upper_mJ"] - unload_work["sample_bound_lower_mJ"]],
        "loading_windows": _windows(trace.loading, roughness_window_samples),
        "unloading_windows": _windows(unload, roughness_window_samples),
        "physical_validation": "not_established_by_this_analysis",
    }
