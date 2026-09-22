from __future__ import annotations

import sys
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = SOURCE_ROOT.parents[2]
sys.path.insert(0, str(SOURCE_ROOT))

from wheelbot_adapter.export_models import export_all
from wheelbot_adapter.parameters import load_parameters
from wheelbot_adapter.validate_exports import validate_all_exports


def main() -> int:
    output_root = REPO_ROOT / "机械资料/03_适配模型"
    params = load_parameters()
    export_all(output_root, params)
    validation = validate_all_exports(output_root)
    failures = (
        validation.empty_files
        + validation.non_watertight_stls
        + validation.non_manifold_stls
        + validation.unit_mismatches
        + validation.bounding_box_mismatches
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
