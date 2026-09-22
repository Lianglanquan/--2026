from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).parents[1]


def test_urdf_contains_required_sensor_frames():
    urdf = ET.parse(ROOT.parent / "wheelbot_description" / "urdf" / "wheelbot.urdf")
    links = {element.attrib["name"] for element in urdf.findall("link")}

    assert {"base_link", "imu_link", "laser_frame"}.issubset(links)


def test_phase1_launch_declares_switches_for_real_and_fake_inputs():
    text = (ROOT / "launch" / "phase1.launch.py").read_text()

    for name in (
        "use_real_bridge",
        "use_fake_bridge",
        "use_lidar",
        "use_ekf",
        "use_slam",
        "use_description",
    ):
        assert f'"{name}"' in text
