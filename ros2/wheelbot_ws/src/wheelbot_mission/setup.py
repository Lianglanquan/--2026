from glob import glob

from setuptools import setup


package_name = "wheelbot_mission"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", glob("launch/*.launch.py")),
        ("share/" + package_name + "/config", glob("config/*.yaml")),
    ],
    install_requires=["setuptools", "PyYAML"],
    zip_safe=True,
    entry_points={"console_scripts": [
        "mission_manager_node = wheelbot_mission.mission_manager_node:main",
        "fake_arm_node = wheelbot_mission.fake_arm_node:main",
    ]},
)
