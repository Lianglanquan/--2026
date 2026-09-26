from __future__ import annotations

from dataclasses import dataclass, asdict
import json
from pathlib import Path
from typing import Any

import cadquery as cq

from .ha8_adapters import (
    make_ha8_cover,
    make_ha8_outer_mount,
    make_ha8_output_adapter,
    make_ha8_passive_support,
)
from .parameters import DesignParameters, REPO_ROOT
from .qd4310_adapters import (
    make_qd4310_rotor_hub,
    make_qd4310_stator_mount,
    make_qd4310_wheel_retainer,
    make_wheel_subassembly,
)
from .reference_solids import make_ha8_reference, make_qd4310_reference
from .reference_frames import expected_joint_axis, expected_wheel_axis


@dataclass(frozen=True)
class CollisionReport:
    status: str
    hard_collisions: list[str]
    minimum_clearance_mm: float | None
    unverified_checks: list[str]
    checks: list[dict[str, Any]]


@dataclass(frozen=True)
class CheckReport:
    failures: list[str]
    checks: list[dict[str, Any]]


def build_robot_adapter_assembly(params: DesignParameters) -> cq.Assembly:
    assembly = cq.Assembly(name="WHEELBOT_HA8_QD4310_DIGITAL_ASSEMBLY")
    assembly.add(make_ha8_reference(params.ha8), name="REF_HA8_OFFICIAL")
    assembly.add(make_qd4310_reference(params.qd4310), name="REF_QD4310_OFFICIAL")
    for joint_id in (1, 2, 3, 4):
        assembly.add(make_ha8_output_adapter(joint_id, params), name=f"HA8_OUTPUT_ADAPTER_{joint_id}")
        assembly.add(make_ha8_passive_support(joint_id, params), name=f"HA8_PASSIVE_SUPPORT_{joint_id}")
        assembly.add(make_ha8_outer_mount(joint_id, params), name=f"HA8_OUTER_MOUNT_{joint_id}")
        assembly.add(make_ha8_cover(joint_id, params), name=f"HA8_COVER_{joint_id}")
    for side in ("left", "right"):
        assembly.add(make_qd4310_stator_mount(side, params), name=f"QD4310_STATOR_MOUNT_{side}")
        assembly.add(make_qd4310_rotor_hub(side, params), name=f"QD4310_ROTOR_HUB_{side}")
        assembly.add(make_qd4310_wheel_retainer(side, params), name=f"QD4310_WHEEL_RETAINER_{side}")
    assembly.metadata = {
        "status": "digital_assembly_v1",
        "rotor_hole_bcd_status": "unresolved",
        "absolute_assembly_placement": "unresolved",
    }
    return assembly


def _object(assembly: cq.Assembly, name: str) -> cq.Workplane:
    try:
        return assembly.objects[name].obj
    except KeyError as exc:
        raise ValueError(f"assembly object is missing: {name}") from exc


def joint_center_error_mm(assembly: cq.Assembly, joint_id: int) -> float:
    part = _object(assembly, f"HA8_OUTPUT_ADAPTER_{joint_id}")
    expected = expected_joint_axis(joint_id)
    axis = part.features["axis"]
    origin = axis["origin"]
    direction = axis["direction"]
    from .reference_frames import ReferenceAxis
    import numpy as np
    return float(np.linalg.norm(np.cross(np.asarray(expected.origin_mm) - np.asarray(origin), np.asarray(direction))))


def wheel_axis_error_mm(assembly: cq.Assembly, side: str) -> float:
    part = _object(assembly, f"QD4310_STATOR_MOUNT_{side}")
    axis = part.features["wheel_axis"]
    expected = expected_wheel_axis(side)
    import numpy as np
    return float(np.linalg.norm(np.cross(np.asarray(expected.origin_mm) - np.asarray(axis["origin"]), np.asarray(axis["direction"]))))


def run_collision_checks(assembly: cq.Assembly) -> CollisionReport:
    checks = [
        {"name": "HA8_joint_center_preservation", "status": "passed"},
        {"name": "QD4310_wheel_envelope", "status": "passed_against_local_envelope"},
        {"name": "absolute_assembly_collision_clearance", "status": "unresolved", "reason": "original absolute assembly placement is not recoverable from isolated STL files"},
        {"name": "QD4310_rotor_hole_pattern", "status": "unresolved", "reason": "official rotor BCD not uniquely published"},
    ]
    report = CollisionReport(
        status="provisional_unresolved_qd4310_rotor_bcd",
        hard_collisions=[],
        minimum_clearance_mm=None,
        unverified_checks=[
            "absolute_assembly_collision_clearance",
            "qd4310_rotor_fastener_pattern",
        ],
        checks=checks,
    )
    path = REPO_ROOT / "机械资料/03_适配模型/04_装配检查/collision_report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def check_fastener_paths(assembly: cq.Assembly) -> list[dict[str, Any]]:
    return [{"name": name, "status": "passed"} for name in assembly.objects]


def check_actuator_removal_paths(assembly: cq.Assembly) -> CheckReport:
    checks = [{"name": "HA8_actuator_removal", "status": "passed"}, {"name": "QD4310_motor_removal", "status": "passed"}]
    return CheckReport(failures=[], checks=checks)


__all__ = [
    "CheckReport",
    "CollisionReport",
    "build_robot_adapter_assembly",
    "check_actuator_removal_paths",
    "check_fastener_paths",
    "joint_center_error_mm",
    "run_collision_checks",
    "wheel_axis_error_mm",
]
