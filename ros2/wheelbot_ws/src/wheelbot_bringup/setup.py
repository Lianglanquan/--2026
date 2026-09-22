from setuptools import setup


package_name = "wheelbot_bringup"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", ["launch/phase1.launch.py"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
)
