from setuptools import setup

package_name = 'wheelbot_bridge'
setup(name=package_name, version='0.1.0', packages=[package_name], data_files=[
    ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
    ('share/' + package_name, ['package.xml']),
    ('share/' + package_name + '/launch', ['launch/bridge.launch.py']),
], install_requires=['setuptools'], zip_safe=True,
entry_points={'console_scripts': [
    'bridge_node = wheelbot_bridge.bridge_node:main',
    'fake_bridge_node = wheelbot_bridge.fake_bridge_node:main',
    'state_adapter_node = wheelbot_bridge.state_adapter_node:main',
]})
