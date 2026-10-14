"""Export the current source-bound Cell 11 cartridge as a Fusion 360 handoff."""
from __future__ import annotations

import argparse
import json

from masck_one.cartridge_fusion_handoff import export_fusion_handoff


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export separate cartridge material/reference STEP files and Fusion handoff manifest."
    )
    parser.add_argument(
        "--output",
        default="generated/cartridge_fusion_handoff",
        help="Output directory for the cartridge handoff.",
    )
    args = parser.parse_args(argv)
    manifest = export_fusion_handoff(args.output)
    print(
        json.dumps(
            {
                "result": "PASS",
                "scope": manifest["scope"],
                "schema": manifest["schema"],
                "geometric_free_capacity_mL": manifest["geometric_free_capacity_mL"],
                "retained_capacity_mL": manifest["retained_capacity_mL"],
                "file_count": len(manifest["files"]) + 1,
                "production_ready": manifest["production_ready"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
