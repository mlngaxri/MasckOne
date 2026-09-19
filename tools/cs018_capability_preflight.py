"""Report current CS-018 owner binding. Exit 2 while capabilities are unresolved."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from masck_one.cleansing_capabilities import bind_capabilities, _json
from masck_one.regional_cleansing import Region


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--snapshot", type=Path,
                        default=ROOT / "docs/contracts/cs018_cleansing_sources_v1.json")
    parser.add_argument("--live-heads", type=Path, required=True,
                        help="Separate current owner-head inventory, refreshed from GitHub")
    parser.add_argument("--regions", type=Path,
                        help="Registered region records; omission reports source binding only")
    args = parser.parse_args()
    regions = {}
    if args.regions:
        for row in _json(args.regions.read_bytes()):
            row["cells"] = frozenset(row["cells"])
            region = Region(**row)
            if region.region_id in regions:
                parser.error("duplicate region identity")
            regions[region.region_id] = region
    result = bind_capabilities(args.repo, _json(args.snapshot.read_bytes()),
                               _json(args.live_heads.read_bytes()), regions)
    print(json.dumps(result.receipt, indent=2, sort_keys=True))
    return 2 if result.receipt["blockers"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
