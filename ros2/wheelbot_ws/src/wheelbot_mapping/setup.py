from setuptools import setup


package_name = "wheelbot_mapping"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/config", ["config/mapper_params_online_sync.yaml"]),
        ("share/" + package_name + "/launch", ["launch/mapping.launch.py"]),
    ],
    install_requires=["setuptools"],
    tests_require=["pytest"],
    zip_safe=True,
)
