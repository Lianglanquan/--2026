from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import json
from pathlib import Path

import cadquery as cq

from .assembly_check import build_robot_adapter_assembly
from .ha8_adapters import (
    make_ha8_cover,
    make_ha8_outer_mount,
    make_ha8_output_adapter,
    make_ha8_passive_support,
    make_ha8_spacer,
)
from .parameters import DesignParameters, REPO_ROOT, load_parameters
from .qd4310_adapters import (
    make_qd4310_rotor_hub,
    make_qd4310_stator_mount,
    make_qd4310_wheel_retainer,
)


STEP_DIR = "02_STEP装配与零件"
STL_DIR = "03_STL打印件"
CHECK_DIR = "04_装配检查"
STL_TOLERANCE_MM = 0.05
STL_ANGULAR_TOLERANCE = 0.1


@dataclass(frozen=True)
class ExportReport:
    part_names: tuple[str, ...]
    assembly_names: tuple[str, ...]
    stl_tolerance_mm: float
    stl_angular_tolerance: float
    files: tuple[dict[str, object], ...]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manufacturing_parts(params: DesignParameters) -> dict[str, cq.Workplane]:
    parts: dict[str, cq.Workplane] = {}
    for joint_id in (1, 2, 3, 4):
        parts[f"HA8_舵机接口{joint_id}_v1"] = make_ha8_output_adapter(joint_id, params)
        parts[f"HA8_被动支撑{joint_id}_v1"] = make_ha8_passive_support(joint_id, params)
        parts[f"HA8_隔套{joint_id}_v1"] = make_ha8_spacer(joint_id, params)
        parts[f"HA8_外固定{joint_id}_v1"] = make_ha8_outer_mount(joint_id, params)
        parts[f"HA8_盖板{joint_id}_v1"] = make_ha8_cover(joint_id, params)
    for index, side in enumerate(("left", "right"), start=1):
        parts[f"QD4310_电机固定X{index}_v1"] = make_qd4310_stator_mount(side, params)
        parts[f"QD4310_轮毂X{index}_v1"] = make_qd4310_rotor_hub(side, params)
        parts[f"QD4310_轮固定X{index}_v1"] = make_qd4310_wheel_retainer(side, params)
    return dict(sorted(parts.items()))


def _manufacturing_assembly(parts: dict[str, cq.Workplane], predicate, name: str) -> cq.Assembly:
    assembly = cq.Assembly(name=name)
    for part_name, part in parts.items():
        if predicate(part_name):
            assembly.add(part, name=part_name)
    return assembly


def _assemblies(parts: dict[str, cq.Workplane], params: DesignParameters) -> dict[str, cq.Assembly]:
    return {
        "HA8_关节适配分总成_v1": _manufacturing_assembly(
            parts, lambda name: name.startswith("HA8_"), "HA8_ADAPTER_ASSEMBLY_V1"
        ),
        "QD4310_轮端适配分总成_v1": _manufacturing_assembly(
            parts, lambda name: name.startswith("QD4310_"), "QD4310_WHEEL_ASSEMBLY_V1"
        ),
        "轮足机器人_HA8_QD4310_全适配总装_v1": _manufacturing_assembly(
            parts, lambda name: True, "WHEELBOT_ADAPTER_ASSEMBLY_V1"
        ),
    }


def _assembly_shape(assembly: cq.Assembly) -> cq.Shape:
    """Flatten an Assembly before passing it to CadQuery's exporter dispatch."""

    compound = assembly.toCompound()
    if compound is None or not compound.Solids():
        raise ValueError(f"assembly {assembly.name!r} has no exportable solids")
    return compound


def export_all(output_root: Path, params: DesignParameters | None = None) -> ExportReport:
    params = params or load_parameters()
    output_root = Path(output_root)
    step_dir = output_root / STEP_DIR
    stl_dir = output_root / STL_DIR
    check_dir = output_root / CHECK_DIR
    for directory in (step_dir, stl_dir, check_dir):
        directory.mkdir(parents=True, exist_ok=True)

    parts = manufacturing_parts(params)
    exported: list[dict[str, object]] = []
    for name, part in parts.items():
        step_path = step_dir / f"{name}.step"
        stl_path = stl_dir / f"{name}.stl"
        cq.exporters.export(part, str(step_path), exportType="STEP")
        cq.exporters.export(
            part,
            str(stl_path),
            exportType="STL",
            tolerance=STL_TOLERANCE_MM,
            angularTolerance=STL_ANGULAR_TOLERANCE,
        )
        for path, kind in ((step_path, "STEP"), (stl_path, "STL")):
            exported.append(
                {
                    "relative_path": path.relative_to(output_root).as_posix(),
                    "format": kind,
                    "bytes": path.stat().st_size,
                    "sha256": _sha256(path),
                }
            )

    assemblies = _assemblies(parts, params)
    for name, assembly in assemblies.items():
        step_path = step_dir / f"{name}.step"
        cq.exporters.export(_assembly_shape(assembly), str(step_path), exportType="STEP")
        exported.append(
            {
                "relative_path": step_path.relative_to(output_root).as_posix(),
                "format": "STEP_ASSEMBLY",
                "bytes": step_path.stat().st_size,
                "sha256": _sha256(step_path),
            }
        )

    report = ExportReport(
        part_names=tuple(parts),
        assembly_names=tuple(assemblies),
        stl_tolerance_mm=STL_TOLERANCE_MM,
        stl_angular_tolerance=STL_ANGULAR_TOLERANCE,
        files=tuple(sorted(exported, key=lambda item: str(item["relative_path"]))),
    )
    (check_dir / "export_report.json").write_text(
        json.dumps(asdict(report), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


__all__ = ["ExportReport", "export_all", "manufacturing_parts"]
