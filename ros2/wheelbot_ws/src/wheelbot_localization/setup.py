from setuptools import setup


package_name = "wheelbot_localization"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/config", [
            "config/ekf.yaml",
            "config/robot_kinematics.yaml",
        ]),
        ("share/" + package_name + "/launch", [
            "launch/localization.launch.py",
        ]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
)
