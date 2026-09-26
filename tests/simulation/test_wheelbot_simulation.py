import sys
from pathlib import Path

import mujoco
import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[2]
SIMULATION = ROOT / "simulation" / "mujoco"
sys.path.insert(0, str(SIMULATION))

from wheelbot_contract import (  # noqa: E402
    ACTION_SIZE,
    QD4310_CURRENT_LIMIT_A,
    QD4310_SPEED_LIMIT_RPM,
    NOMINAL_STAND_BASE_Z_M,
    NOMINAL_STAND_JOINT_TARGET_RAD,
    WHEEL_RADIUS_M,
    action_to_command,
    command_to_mujoco_ctrl,
)


MODEL_PATH = SIMULATION / "wheelbot_nominal.xml"


def test_nominal_model_loads_with_six_controlled_joints():
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))

    assert model.nq == 13  # free base + six hinge joints
    assert model.nu == 6
    assert [model.actuator(i).name for i in range(model.nu)] == [
        "ha8_left_thigh",
        "ha8_left_calf",
        "ha8_right_thigh",
        "ha8_right_calf",
        "qd4310_left_wheel",
        "qd4310_right_wheel",
    ]


def test_action_mapping_is_bounded_and_uses_real_qd4310_limit():
    command = action_to_command(np.ones(ACTION_SIZE, dtype=np.float32))

    assert command.joint_target_rad.shape == (4,)
    assert command.wheel_speed_rpm.shape == (2,)
    assert np.all(np.abs(command.wheel_speed_rpm) <= QD4310_SPEED_LIMIT_RPM)
    assert command.qd4310_current_limit_a == QD4310_CURRENT_LIMIT_A


def test_wheel_radius_matches_adapted_wheel_envelope():
    assert WHEEL_RADIUS_M == 0.033


def test_default_pose_places_wheels_on_ground():
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)

    for name in ("left_wheel_collision", "right_wheel_collision"):
        geom = model.geom(name)
        bottom_z = data.geom_xpos[geom.id][2] - model.geom_size[geom.id][0]
        assert abs(float(bottom_z)) < 1e-6


def test_nominal_stand_keyframe_is_level_and_within_joint_limits():
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, model.key("nominal_stand").id)
    mujoco.mj_forward(model, data)

    assert data.qpos[2] == pytest.approx(NOMINAL_STAND_BASE_Z_M, abs=1e-6)
    assert np.allclose(data.qpos[7:11], NOMINAL_STAND_JOINT_TARGET_RAD)
    joint_ids = [model.joint(name).id for name in ("LT_joint", "LC_joint", "RT_joint", "RC_joint")]
    assert np.all(model.jnt_range[joint_ids, 0] <= data.qpos[7:11])
    assert np.all(data.qpos[7:11] <= model.jnt_range[joint_ids, 1])
    assert np.allclose(data.qpos[3:7], [1.0, 0.0, 0.0, 0.0])


def test_nominal_zero_action_does_not_produce_nonfinite_state():
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)
    data.qpos[2] = NOMINAL_STAND_BASE_Z_M
    mujoco.mj_forward(model, data)
    for _ in range(100):
        data.ctrl[:] = 0.0
        mujoco.mj_step(model, data)

    assert np.all(np.isfinite(data.qpos))
    assert np.all(np.isfinite(data.qvel))
    assert data.ncon > 0


def test_hold_controller_maps_joint_targets_and_zero_wheel_speed():
    command = action_to_command(np.zeros(ACTION_SIZE, dtype=np.float32))
    ctrl = command_to_mujoco_ctrl(command)

    assert ctrl.shape == (6,)
    assert np.allclose(ctrl[:4], 0.0)
    assert np.allclose(ctrl[4:], 0.0)


def test_forward_wheel_command_accounts_for_mirrored_wheel_axes():
    command = action_to_command(np.array([0, 0, 0, 0, 1, 1], dtype=np.float32))
    ctrl = command_to_mujoco_ctrl(command)

    wheel_rad_s = QD4310_SPEED_LIMIT_RPM * 2.0 * np.pi / 60.0
    # World +X is robot-forward: left axle is +Y, right axle is -Y.
    assert ctrl[4] == pytest.approx(wheel_rad_s)
    assert ctrl[5] == pytest.approx(-wheel_rad_s)
