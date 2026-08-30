from __future__ import annotations

from dataclasses import asdict, dataclass
import json

from .model import build_model
from .quarter_architecture import build_quarter_architecture
from .quarter_preflight import run_quarter_preflight


@dataclass(frozen=True, slots=True)
class AlphaPreflightCheck:
    id: str
    status: str
    message: str
    actual: object | None = None
    expected: object | None = None

    def to_dict(self) -> dict[str, object | None]:
        return asdict(self)


def run_alpha_preflight() -> dict[str, object]:
    model = build_model()
    architecture = build_quarter_architecture(model)
    alpha = architecture.alpha_closure
    wearable = architecture.wearable
    inherited = run_quarter_preflight()
    checks = (
        AlphaPreflightCheck(
            "INHERITED_DIGITAL_ARCHITECTURE",
            "PASS" if inherited["result"] == "PASS" else "FAIL",
            "Every inherited authority, interface, structure, actuation, fluid and waste preflight remains green.",
        ),
        AlphaPreflightCheck(
            "FROZEN_QUICK_RELEASE_SAFETY",
            "PASS" if (
                wearable.quick_release.one_hand_wet_unpowered
                and wearable.quick_release.release_time_max_s
                == model.authority.number("safety", "quick_release", "time_max_s")
            ) else "FAIL",
            "The digital architecture preserves the one-hand wet unpowered release and maximum-time requirements.",
        ),
        AlphaPreflightCheck(
            "HYGIENE_CLASSIFICATION_CLOSURE",
            "PASS" if (
                len(alpha.hygiene_cavities) > 0
                and len({cavity.cavity_id for cavity in alpha.hygiene_cavities})
                == len(alpha.hygiene_cavities)
                and all(
                    cavity.hygiene_class in model.authority.get("manufacturing", "hygiene_classes")
                    for cavity in alpha.hygiene_cavities
                )
            ) else "FAIL",
            "Every controlled cavity is assigned exactly one authority-defined hygiene class.",
        ),
        AlphaPreflightCheck(
            "QUANTITATIVE_LEDGER_DISCIPLINE",
            "PASS" if (
                alpha.ledgers.known_dry_mass_g > 0.0
                and not alpha.ledgers.mass_ledger_complete
                and "INCOMPLETE" in alpha.ledgers.closure_status
                and "BLOCKED" in alpha.ledgers.runtime_status
            ) else "FAIL",
            "Known supplier-reference mass is calculated while incomplete mass, CG, torque, runtime and thermal closure cannot pass.",
            {"known_dry_mass_g": alpha.ledgers.known_dry_mass_g},
        ),
        AlphaPreflightCheck(
            "RELEASE_AND_RECONSTRUCTION_CONTRACT",
            "PASS" if (
                alpha.release.exact_head_ci_required
                and alpha.release.export_formats
                == ("STEP_AP242_DEVELOPMENT_EXPORT", "JSON_HASHED_RELEASE_MANIFEST")
                and len(alpha.release.reconstruction_order) == 6
            ) else "FAIL",
            "Digital Alpha release requires deterministic reconstruction, STEP output, hashes and exact-head CI.",
        ),
        AlphaPreflightCheck(
            "PHYSICAL_MVP_GATE",
            "PASS" if (
                alpha.release.required_physical_gate_iterations == tuple(range(41, 51))
                and alpha.release.integrated_mvp_gate_iteration == 64
                and not alpha.physical_validation_eligible
                and "BLOCKED" in alpha.physical_mvp_status
            ) else "FAIL",
            "The repository completes digital Alpha code without bypassing physical evidence or the integrated MVP gate.",
        ),
    )
    result = "PASS" if all(check.status == "PASS" for check in checks) else "FAIL"
    return {
        "project": "Masck One",
        "phase": 8,
        "iteration": 40,
        "result": result,
        "checks": [check.to_dict() for check in checks],
        "digital_alpha_sha256": alpha.topology_sha256,
        "digital_alpha_status": alpha.digital_alpha_status,
        "physical_mvp_status": alpha.physical_mvp_status,
    }


def main() -> int:
    report = run_alpha_preflight()
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
