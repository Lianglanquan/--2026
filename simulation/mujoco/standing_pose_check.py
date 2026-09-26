"""Inspect the nominal standing keyframe without running a balance policy."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import mujoco
import numpy as np


JOINT_NAMES = ("LT_joint", "LC_joint", "RT_joint", "RC_joint")
WHEEL_GEOM_NAMES = ("left_wheel_collision", "right_wheel_collision")


def inspect_nominal_stand(model_path: Path) -> dict[str, object]:
    model = mujoco.MjModel.from_xml_path(str(model_path))
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, model.key("nominal_stand").id)
    mujoco.mj_forward(model, data)

    joint_positions = np.array(
        [data.qpos[model.jnt_qposadr[model.joint(name).id]] for name in JOINT_NAMES]
    )
    joint_ranges = np.array(
        [model.jnt_range[model.joint(name).id] for name in JOINT_NAMES]
    )
    wheel_heights = []
    wheel_clearances = []
    for name in WHEEL_GEOM_NAMES:
        geom_id = model.geom(name).id
        height = float(data.geom_xpos[geom_id][2])
        wheel_heights.append(height)
        wheel_clearances.append(abs(height - float(model.geom_size[geom_id][0])))

    base_id = model.body("base_link").id
    wheel_positions = np.array(
        [data.xpos[model.body(name).id] for name in ("left_wheel", "right_wheel")]
    )
    wheel_axis = np.mean(wheel_positions, axis=0)
    com = np.asarray(data.subtree_com[base_id], dtype=float)
    com_to_wheel_axis = abs(float(com[0] - wheel_axis[0]))
    wheel_span_y = abs(float(wheel_positions[0, 1] - wheel_positions[1, 1]))
    com_inside_wheel_span = bool(
        min(wheel_positions[:, 1]) - 1e-6
        <= com[1]
        <= max(wheel_positions[:, 1]) + 1e-6
    )

    base_quaternion = np.asarray(data.qpos[3:7], dtype=float)
    root = ET.parse(model_path).getroot()
    material_names = {
        material.attrib["name"] for material in root.findall("./asset/material")
    }
    texture_names = {
        texture.attrib["name"] for texture in root.findall("./asset/texture")
    }
    return {
        "keyframe": "nominal_stand",
        "joint_positions_rad": joint_positions.tolist(),
        "joint_limits_ok": bool(
            np.all(joint_ranges[:, 0] <= joint_positions)
            and np.all(joint_positions <= joint_ranges[:, 1])
        ),
        "wheel_center_heights_m": wheel_heights,
        "max_wheel_ground_clearance_m": max(wheel_clearances),
        "wheel_height_difference_m": abs(wheel_heights[0] - wheel_heights[1]),
        "com_to_wheel_axis_offset_m": com_to_wheel_axis,
        "wheel_span_y_m": wheel_span_y,
        "com_y_m": float(com[1]),
        "com_inside_wheel_span": com_inside_wheel_span,
        "base_orientation_level": bool(
            np.allclose(base_quaternion, [1.0, 0.0, 0.0, 0.0], atol=1e-9)
        ),
        "contact_count": int(data.ncon),
        "unexpected_self_contact_count": sum(
            1
            for index in range(data.ncon)
            if model.geom(data.contact[index].geom[0]).name != "ground"
            and model.geom(data.contact[index].geom[1]).name != "ground"
        ),
        "has_ground_material": "ground_material" in material_names,
        "has_robot_material": "robot_material" in material_names,
        "has_skybox": "skybox_texture" in texture_names,
        "has_directional_light": any(
            light.attrib.get("directional") == "true"
            for light in root.findall("./worldbody/light")
        ),
        "has_inspection_camera": root.find("./worldbody/camera[@name='inspection_view']") is not None,
        "scope": "kinematic_and_initial_contact_only",
    }


def main() -> None:
    model_path = Path(__file__).with_name("wheelbot_nominal.xml")
    print(json.dumps(inspect_nominal_stand(model_path), indent=2))


if __name__ == "__main__":
    main()
