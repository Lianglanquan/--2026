from pathlib import Path


def test_navigation_requires_external_commissioned_params():
    source = (Path(__file__).parents[1] / "launch" / "navigation.launch.py").read_text()
    assert 'DeclareLaunchArgument(\n            "params_file"' in source
    assert 'default_value=""' not in source
    assert 'get_package_share_directory("nav2_bringup")' in source
