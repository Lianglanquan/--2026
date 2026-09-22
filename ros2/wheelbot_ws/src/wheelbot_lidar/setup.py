from setuptools import setup

package_name = 'wheelbot_lidar'
setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/config', ['config/x2.yaml']),
        ('share/' + package_name + '/launch', ['launch/x2.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    entry_points={'console_scripts': [
        'tcp_to_pty = wheelbot_lidar.tcp_to_pty:main',
        'scan_watchdog = wheelbot_lidar.scan_watchdog:main',
    ]},
)
