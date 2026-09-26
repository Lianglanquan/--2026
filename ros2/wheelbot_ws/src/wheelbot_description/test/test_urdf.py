from pathlib import Path
import xml.etree.ElementTree as ET


URDF_PATH = Path(__file__).resolve().parents[1] / "urdf" / "wheelbot.urdf"


def test_urdf_is_well_formed_and_contains_required_frames():
    robot = ET.parse(URDF_PATH).getroot()

    assert robot.tag == "robot"
    link_names = {link.attrib["name"] for link in robot.findall("link")}
    joint_names = {joint.attrib["name"] for joint in robot.findall("joint")}

    assert {"base_link", "laser_frame", "imu_link"} <= link_names
    assert {"base_to_laser", "base_to_imu"} <= joint_names


def test_every_joint_references_existing_links():
    robot = ET.parse(URDF_PATH).getroot()
    link_names = {link.attrib["name"] for link in robot.findall("link")}

    for joint in robot.findall("joint"):
        parent = joint.find("parent")
        child = joint.find("child")
        assert parent is not None
        assert child is not None
        assert parent.attrib["link"] in link_names
        assert child.attrib["link"] in link_names
