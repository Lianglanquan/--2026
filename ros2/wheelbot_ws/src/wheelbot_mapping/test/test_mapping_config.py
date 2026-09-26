from pathlib import Path

import yaml


CONFIG_DIR = Path(__file__).parents[1] / "config"


def test_mapping_config_uses_phase_one_frames_and_scan_topic():
    data = yaml.safe_load((CONFIG_DIR / "mapper_params_online_sync.yaml").read_text())
    params = data["slam_toolbox"]["ros__parameters"]

    assert params["mode"] == "mapping"
    assert params["map_frame"] == "map"
    assert params["odom_frame"] == "odom"
    assert params["base_frame"] == "base_link"
    assert params["scan_topic"] == "/scan"
    assert params["resolution"] == 0.05


def test_mapping_config_updates_only_after_meaningful_motion():
    data = yaml.safe_load((CONFIG_DIR / "mapper_params_online_sync.yaml").read_text())
    params = data["slam_toolbox"]["ros__parameters"]

    assert params["minimum_travel_distance"] > 0.0
    assert params["minimum_travel_heading"] > 0.0
    assert params["do_loop_closing"] is True
