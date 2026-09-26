"""Read-only kinematic topology audit for the wheelbot baseline."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import mujoco
import numpy as np


JOINT_NAMES = (
    "LT_joint",
    "LC_joint",
    "LW_joint",
    "RT_joint",
    "RC_joint",
    "RW_joint",
)


def _rpy_matrix(text: str) -> np.ndarray:
    roll, pitch, yaw = map(float, text.split())
    cr, sr = np.cos(roll), np.sin(roll)
    cp, sp = np.cos(pitch), np.sin(pitch)
    cy, sy = np.cos(yaw), np.sin(yaw)
    return np.array(
        [
            [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
            [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
            [-sp, cp * sr, cp * cr],
        ],
        dtype=float,
    )


def _urdf_joints(path: Path) -> dict[str, dict[str, object]]:
    root = ET.parse(path).getroot()
    links = {element.attrib["name"] for element in root.findall("link")}
    joints: list[dict[str, object]] = []
    for element in root.findall("joint"):
        origin = element.find("origin")
        axis = element.find("axis")
        limit = element.find("limit")
        joints.append(
            {
                "name": element.attrib["name"],
                "parent": element.find("parent").attrib["link"],
                "child": element.find("child").attrib["link"],
                "xyz": np.fromstring(origin.attrib.get("xyz", "0 0 0"), sep=" "),
                "rotation": _rpy_matrix(origin.attrib.get("rpy", "0 0 0")),
                "axis": np.fromstring(axis.attrib.get("xyz", "1 0 0"), sep=" "),
                "lower": float(limit.attrib["lower"]),
                "upper": float(limit.attrib["upper"]),
            }
        )
    by_parent: dict[str, list[dict[str, object]]] = {}
    for joint in joints:
        by_parent.setdefault(str(joint["parent"]), []).append(joint)
    child_names = {str(joint["child"]) for joint in joints}
    base = next(iter(links - child_names))
    output: dict[str, dict[str, object]] = {}

    def walk(link: str, transform: np.ndarray) -> None:
        for joint in by_parent.get(link, []):
            local = np.eye(4)
            local[:3, :3] = joint["rotation"]
            local[:3, 3] = joint["xyz"]
            world = transform @ local
            output[str(joint["name"])] = {
                **joint,
                "world_position": world[:3, 3],
                "world_axis": world[:3, :3] @ joint["axis"],
            }
            walk(str(joint["child"]), world)

    walk(base, np.eye(4))
    return output


def _adapter_status(root: Path) -> dict[str, object]:
    path = root / "机械资料/03_适配模型/04_装配检查/geometry_report.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    joint_frames = report.get("joint_transforms", [])
    wheel_frames = report.get("wheel_transforms", [])
    baseline_path = root / "simulation/mujoco/adapter_placement_baseline.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    preserves_urdf_frames = bool(baseline.get("preserves_urdf_frames", False))
    basis = baseline.get("basis", "unknown")

    if preserves_urdf_frames:
        joint_status = [
            {
                "frame": row.get("frame_name"),
                "status": "accepted_by_design_confirmation",
                "source_status": row.get("assembly_placement_status"),
            }
            for row in joint_frames
        ]
        wheel_status = [
            {
                "frame": row.get("frame_name"),
                "status": "accepted_by_design_confirmation",
                "source_status": row.get("assembly_placement_status"),
            }
            for row in wheel_frames
        ]
    else:
        joint_status = [
            {"frame": row.get("frame_name"), "status": row.get("assembly_placement_status")}
            for row in joint_frames
        ]
        wheel_status = [
            {"frame": row.get("frame_name"), "status": row.get("assembly_placement_status")}
            for row in wheel_frames
        ]

    return {
        "basis": basis,
        "preserves_urdf_frames": preserves_urdf_frames,
        "all_joint_frames_resolved": preserves_urdf_frames or all(
            row.get("assembly_placement_status") == "resolved" for row in joint_frames
        ),
        "all_wheel_frames_resolved": preserves_urdf_frames or all(
            row.get("assembly_placement_status") == "resolved" for row in wheel_frames
        ),
        "joint_frame_status": joint_status,
        "wheel_frame_status": wheel_status,
    }


def audit_topology(root: Path) -> dict[str, object]:
    root = Path(root)
    urdf = _urdf_joints(
        root
        / "机械资料"
        / "01_灯哥小型轮足"
        / "02_Seeed官方URDF_STL"
        / "urdf"
        / "20250820_1.urdf"
    )
    model = mujoco.MjModel.from_xml_path(
        str(root / "simulation/mujoco/wheelbot_nominal.xml")
    )
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    base_pos = data.xpos[model.body("base_link").id].copy()
    topology_match = True
    axes_match = True
    max_center_error = 0.0
    joints: list[dict[str, object]] = []
    for name in JOINT_NAMES:
        expected = urdf[name]
        jid = model.joint(name).id
        body_id = model.jnt_bodyid[jid]
        body_name = model.body(body_id).name
        parent_name = model.body(model.body_parentid[body_id]).name
        center_error = float(
            np.linalg.norm(
                np.asarray(expected["world_position"]) - (data.xanchor[jid] - base_pos)
            )
        )
        axis_dot = float(
            np.dot(np.asarray(expected["world_axis"]), data.xaxis[jid])
        )
        topology_match &= (
            parent_name == {
                "LT_joint": "base_link",
                "LC_joint": "left_thigh",
                "LW_joint": "left_calf",
                "RT_joint": "base_link",
                "RC_joint": "right_thigh",
                "RW_joint": "right_calf",
            }[name]
        )
        axes_match &= axis_dot > 1.0 - 1e-6
        max_center_error = max(max_center_error, center_error)
        joints.append(
            {
                "name": name,
                "urdf_parent": expected["parent"],
                "urdf_child": expected["child"],
                "mjcf_body": body_name,
                "mjcf_parent_body": parent_name,
                "center_error_m": center_error,
                "axis_dot": axis_dot,
            }
        )
    adapter = _adapter_status(root)
    gate = (
        "allowed"
        if topology_match
        and axes_match
        and max_center_error < 1e-5
        and adapter["all_joint_frames_resolved"]
        and adapter["all_wheel_frames_resolved"]
        else "blocked"
    )
    return {
        "urdf_mjcf": {
            "topology_match": topology_match,
            "all_joint_axes_match": axes_match,
            "max_joint_center_error_m": max_center_error,
            "joints": joints,
        },
        "adapter_placement": adapter,
        "training_gate": gate,
    }


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(audit_topology(root), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
