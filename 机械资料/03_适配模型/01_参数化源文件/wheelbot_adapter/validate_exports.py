from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import cadquery as cq
import numpy as np
import trimesh

from .export_models import CHECK_DIR, STEP_DIR, STL_DIR
from .parameters import REPO_ROOT


@dataclass(frozen=True)
class ValidationReport:
    empty_files: list[str]
    non_watertight_stls: list[str]
    non_manifold_stls: list[str]
    unit_mismatches: list[str]
    bounding_box_mismatches: list[str]
    records: list[dict[str, object]]
    meshlabserver_status: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest


def _box_extents(box: cq.BoundBox) -> np.ndarray:
    return np.asarray((box.xlen, box.ylen, box.zlen), dtype=float)


def validate_all_exports(output_root: Path) -> ValidationReport:
    output_root = Path(output_root)
    step_dir = output_root / STEP_DIR
    stl_dir = output_root / STL_DIR
    check_dir = output_root / CHECK_DIR
    check_dir.mkdir(parents=True, exist_ok=True)
    empty_files: list[str] = []
    non_watertight: list[str] = []
    non_manifold: list[str] = []
    unit_mismatches: list[str] = []
    bbox_mismatches: list[str] = []
    records: list[dict[str, object]] = []

    all_exports = sorted(step_dir.glob("*.step")) + sorted(stl_dir.glob("*.stl"))
    for path in all_exports:
        if path.stat().st_size == 0:
            empty_files.append(path.relative_to(output_root).as_posix())

    for stl_path in sorted(stl_dir.glob("*.stl")):
        relative = stl_path.relative_to(output_root).as_posix()
        # CadQuery's STL writer may emit coincident vertices at shared triangle
        # boundaries. Trimesh processing merges those read-time vertices for
        # topology validation; no file is repaired or rewritten.
        mesh = trimesh.load(stl_path, force="mesh", process=True)
        if not isinstance(mesh, trimesh.Trimesh) or len(mesh.faces) == 0:
            empty_files.append(relative)
            continue
        if not mesh.is_watertight:
            non_watertight.append(relative)
        if not mesh.is_winding_consistent or not mesh.is_watertight:
            non_manifold.append(relative)
        stl_extents = np.asarray(mesh.extents, dtype=float)
        step_path = step_dir / f"{stl_path.stem}.step"
        step_shape = cq.importers.importStep(str(step_path))
        step_extents = _box_extents(step_shape.val().BoundingBox())
        if np.max(step_extents) / max(np.max(stl_extents), 1e-12) > 10.0 or np.max(stl_extents) / max(np.max(step_extents), 1e-12) > 10.0:
            unit_mismatches.append(relative)
        if np.max(np.abs(step_extents - stl_extents)) > 0.05:
            bbox_mismatches.append(relative)
        records.append(
            {
                "step": step_path.relative_to(output_root).as_posix(),
                "stl": relative,
                "step_bytes": step_path.stat().st_size,
                "stl_bytes": stl_path.stat().st_size,
                "step_sha256": _sha256(step_path),
                "stl_sha256": _sha256(stl_path),
                "step_extents_mm": step_extents.tolist(),
                "stl_extents_mm": stl_extents.tolist(),
                "stl_faces": int(len(mesh.faces)),
                "stl_watertight": bool(mesh.is_watertight),
                "stl_winding_consistent": bool(mesh.is_winding_consistent),
            }
        )

    meshlab = shutil.which("meshlabserver")
    meshlab_status = "unavailable"
    if meshlab and list(stl_dir.glob("*.stl")):
        probe = sorted(stl_dir.glob("*.stl"))[0]
        result = subprocess.run(
            [meshlab, "-i", str(probe)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        meshlab_status = "read_ok" if result.returncode == 0 else f"read_failed_{result.returncode}"

    report = ValidationReport(
        empty_files=sorted(set(empty_files)),
        non_watertight_stls=sorted(non_watertight),
        non_manifold_stls=sorted(non_manifold),
        unit_mismatches=sorted(unit_mismatches),
        bounding_box_mismatches=sorted(bbox_mismatches),
        records=records,
        meshlabserver_status=meshlab_status,
    )
    (check_dir / "export_validation.json").write_text(
        json.dumps(asdict(report), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    checksum_paths = sorted(step_dir.glob("*.step")) + sorted(stl_dir.glob("*.stl"))
    checksum_lines = []
    for path in checksum_paths:
        try:
            display = path.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            display = str(path.resolve())
        checksum_lines.append(f"{_sha256(path)}  {display}")
    (check_dir / "SHA256SUMS.txt").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    return report


__all__ = ["ValidationReport", "validate_all_exports"]
