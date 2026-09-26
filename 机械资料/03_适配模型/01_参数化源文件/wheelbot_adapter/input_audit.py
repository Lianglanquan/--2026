from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import cadquery as cq
import numpy as np
import trimesh


ORIGINAL_SOURCE = Path("机械资料/01_灯哥小型轮足")
ORIGINAL_STL_DIRECTORY = ORIGINAL_SOURCE / "01_原版STL"
HA8_SOURCE = Path("机械资料/02_华馨京_HA8-U25H-M")
QD4310_MANUAL = Path("QD4310使用手册.pdf")

HA8_BODY_STEP = HA8_SOURCE / "01_舵机本体_STEP/ha8-hp8-hx8-series-3D.STEP"
HA8_HORN_STEP = HA8_SOURCE / "03_25T舵盘/main-horn-25T-8holes-3D.STEP"
MANIFEST = Path("机械资料/03_适配模型/04_装配检查/input_manifest.json")


def _repo_relative(path: Path, repo_root: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bounding_box(minimum: Any, maximum: Any) -> dict[str, list[float]]:
    minimum_array = np.asarray(minimum, dtype=float)
    maximum_array = np.asarray(maximum, dtype=float)
    if minimum_array.shape != (3,) or maximum_array.shape != (3,):
        raise ValueError("geometry does not have a three-dimensional bounding box")
    if not np.isfinite(minimum_array).all() or not np.isfinite(maximum_array).all():
        raise ValueError("geometry bounding box contains non-finite values")
    return {
        "minimum": minimum_array.tolist(),
        "maximum": maximum_array.tolist(),
        "extents": (maximum_array - minimum_array).tolist(),
    }


def _audit_stl(path: Path) -> dict[str, object]:
    try:
        mesh = trimesh.load(path, file_type="stl", force="mesh", process=True)
        if not isinstance(mesh, trimesh.Trimesh):
            raise ValueError(f"expected a mesh, got {type(mesh).__name__}")
        if len(mesh.faces) == 0 or mesh.bounds is None:
            raise ValueError("mesh contains no faces")
        bounds = _bounding_box(mesh.bounds[0], mesh.bounds[1])
    except Exception as exc:
        raise ValueError(f"unable to parse required STL input: {path}") from exc
    return {
        "face_count": int(len(mesh.faces)),
        "bounding_box_mm": bounds,
        "watertight": bool(mesh.is_watertight),
    }


def _audit_step(path: Path) -> dict[str, object]:
    try:
        imported = cq.importers.importStep(str(path))
        values = imported.vals()
        if not values:
            raise ValueError("STEP import returned no shapes")
        compound = cq.Compound.makeCompound(values)
        solid_count = len(compound.Solids())
        if solid_count == 0:
            raise ValueError("STEP import returned no solids")
        box = compound.BoundingBox()
        bounds = _bounding_box(
            (box.xmin, box.ymin, box.zmin),
            (box.xmax, box.ymax, box.zmax),
        )
    except Exception as exc:
        raise ValueError(f"unable to parse required STEP input: {path}") from exc
    return {
        "solid_count": solid_count,
        "bounding_box_mm": bounds,
    }


def _collect_input_files(repo_root: Path) -> list[Path]:
    input_roots = [repo_root / ORIGINAL_SOURCE, repo_root / HA8_SOURCE]
    files: list[Path] = []
    for input_root in input_roots:
        if not input_root.is_dir():
            raise ValueError(f"missing required input directory: {input_root}")
        files.extend(path for path in input_root.rglob("*") if path.is_file())

    manual = repo_root / QD4310_MANUAL
    if not manual.is_file():
        raise ValueError(f"missing required input file: {manual}")
    files.append(manual)
    return sorted(files, key=lambda path: _repo_relative(path, repo_root))


def _validate_pdf(path: Path) -> None:
    try:
        with path.open("rb") as source:
            signature = source.read(5)
    except OSError as exc:
        raise ValueError(f"unable to read required PDF input: {path}") from exc
    if signature != b"%PDF-":
        raise ValueError(f"unable to parse required PDF input: {path}")


def audit_inputs(repo_root: Path) -> dict[str, object]:
    """Audit immutable mechanical inputs and write their reproducible baseline."""

    repo_root = Path(repo_root).resolve()
    input_files = _collect_input_files(repo_root)

    relative_paths = [_repo_relative(path, repo_root) for path in input_files]
    if len(relative_paths) != len(set(relative_paths)):
        raise ValueError("duplicate relative input paths")

    empty_files = [
        relative_path
        for path, relative_path in zip(input_files, relative_paths, strict=True)
        if path.stat().st_size == 0
    ]
    if empty_files:
        raise ValueError(f"empty input files: {', '.join(empty_files)}")

    required_files = [
        repo_root / HA8_BODY_STEP,
        repo_root / HA8_HORN_STEP,
        repo_root / QD4310_MANUAL,
    ]
    missing_files = [path for path in required_files if path not in input_files]
    if missing_files:
        missing = ", ".join(_repo_relative(path, repo_root) for path in missing_files)
        raise ValueError(f"missing required authoritative inputs: {missing}")

    file_records = [
        {
            "relative_path": relative_path,
            "bytes": path.stat().st_size,
            "extension": path.suffix.lower(),
            "sha256": _sha256(path),
        }
        for path, relative_path in zip(input_files, relative_paths, strict=True)
    ]

    original_stl_paths = sorted(
        (
            path
            for path in (repo_root / ORIGINAL_STL_DIRECTORY).iterdir()
            if path.is_file() and path.suffix.lower() == ".stl"
        ),
        key=lambda path: path.name,
    )
    if len(original_stl_paths) != 29:
        raise ValueError(
            f"expected 29 original STL inputs, found {len(original_stl_paths)}"
        )

    original_stl_geometry = {
        _repo_relative(path, repo_root): _audit_stl(path) for path in original_stl_paths
    }

    ha8_step_paths = sorted(
        (
            path
            for path in (repo_root / HA8_SOURCE).rglob("*")
            if path.is_file() and path.suffix.lower() in {".step", ".stp"}
        ),
        key=lambda path: _repo_relative(path, repo_root),
    )
    ha8_step_geometry = {
        _repo_relative(path, repo_root): _audit_step(path) for path in ha8_step_paths
    }

    _validate_pdf(repo_root / QD4310_MANUAL)

    report: dict[str, object] = {
        "schema_version": 1,
        "input_roots": [
            ORIGINAL_SOURCE.as_posix(),
            HA8_SOURCE.as_posix(),
            QD4310_MANUAL.as_posix(),
        ],
        "files": file_records,
        "empty_files": [],
        "original_stl_count": len(original_stl_paths),
        "original_stls": [path.name for path in original_stl_paths],
        "original_stl_geometry": original_stl_geometry,
        "ha8_body_step": HA8_BODY_STEP.as_posix(),
        "ha8_horn_step": HA8_HORN_STEP.as_posix(),
        "ha8_step_geometry": ha8_step_geometry,
        "qd4310_manual": QD4310_MANUAL.as_posix(),
    }

    manifest_path = repo_root / MANIFEST
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_manifest = manifest_path.with_suffix(".json.tmp")
    temporary_manifest.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary_manifest.replace(manifest_path)
    return report
