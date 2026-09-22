from pathlib import Path

import yaml


CONFIG_DIR = Path(__file__).parents[1] / "config"


def _params(name):
    data = yaml.safe_load((CONFIG_DIR / name).read_text())
    return data["ekf_filter_node"]["ros__parameters"]


def test_ekf_uses_odom_world_frame_and_two_d_mode():
    params = _params("ekf.yaml")

    assert params["two_d_mode"] is True
    assert params["world_frame"] == "odom"
    assert params["odom_frame"] == "odom"
    assert params["base_link_frame"] == "base_link"
    assert params["publish_tf"] is True


def test_ekf_fuses_wheel_odom_and_imu_yaw_rate():
    params = _params("ekf.yaml")

    assert params["odom0"] == "/wheelbot/wheel_odom"
    assert params["imu0"] == "/imu/data"
    assert params["odom0_config"][0] is True
    assert params["odom0_config"][5] is True
    assert params["odom0_config"][6] is True
    assert params["odom0_config"][11] is True
    assert params["imu0_config"][11] is True


def test_kinematics_defaults_to_explicit_single_wheel_firmware_capability():
    data = yaml.safe_load((CONFIG_DIR / "robot_kinematics.yaml").read_text())
    params = data["wheelbot_state_adapter"]["ros__parameters"]

    assert params["wheel_indices"] == [0]
    assert len(params["wheel_signs"]) == len(params["wheel_indices"])
    assert params["wheel_radius_m"] > 0.0
    assert params["wheel_track_m"] > 0.0
