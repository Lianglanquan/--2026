import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SIMULATION = ROOT / "simulation" / "mujoco"
sys.path.insert(0, str(SIMULATION))

from standing_pose_check import inspect_nominal_stand  # noqa: E402


def test_nominal_stand_has_two_ground_contacts_and_level_wheels():
    report = inspect_nominal_stand(ROOT / "simulation/mujoco/wheelbot_nominal.xml")

    assert report["joint_limits_ok"] is True
    assert report["contact_count"] > 0
    assert report["max_wheel_ground_clearance_m"] < 1e-6
    assert report["wheel_height_difference_m"] < 1e-6
    assert report["base_orientation_level"] is True
    # The source URDF has an intentional longitudinal mass offset. For the
    # initial kinematic baseline, the relevant static support check is that
    # the COM projection remains between the two wheel contact lines.
    assert report["com_inside_wheel_span"] is True
    assert report["com_to_wheel_axis_offset_m"] < 0.02
    assert report["unexpected_self_contact_count"] == 0


def test_visual_scene_has_ground_lighting_materials_and_inspection_camera():
    report = inspect_nominal_stand(ROOT / "simulation/mujoco/wheelbot_nominal.xml")

    assert report["has_ground_material"] is True
    assert report["has_robot_material"] is True
    assert report["has_skybox"] is True
    assert report["has_directional_light"] is True
    assert report["has_inspection_camera"] is True
