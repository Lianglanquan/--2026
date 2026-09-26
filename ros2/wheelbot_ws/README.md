# WheelBot ROS 2 workspace

目标平台为 Raspberry Pi 4、Ubuntu 24.04 和 ROS 2 Jazzy。工作区包含 C Board bridge、
传感器标准化、EKF、LiDAR、SLAM 与高层 Mission Manager。

```bash
source /opt/ros/jazzy/setup.bash
source ../../deploy/raspberry_pi/ros_env.sh
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

无实物测试：

```bash
ros2 launch wheelbot_bringup phase1.launch.py \
  use_fake_bridge:=true use_real_bridge:=false use_lidar:=false \
  use_slam:=false mission_navigation_mode:=fake mission_use_fake_arm:=true \
  mission_require_robot_state:=false mission_allow_uncommissioned_locations:=true
```

`mission_navigation_mode:=nav2` 只连接标准 `NavigateToPose` action，不替代 Nav2 的地图、
定位、footprint 与控制器标定。真实运动前请完成
`docs/architecture/mission-manager.md` 和 `docs/ros2/phase1-slam-bringup.md` 的门槛。

Mission Manager 启动后访问 `http://<robot-ip>:8080/` 可打开轻量 Web 控制台。真机部署必须替换
默认 API token；如需小智主动播报，将 `mission_feedback_webhook_url` 指向服务端通知适配器。

仅在上述 fake 配置下，可从仓库根目录运行
`python3 tools/mission_api_smoke.py --token change-me-before-deploy`，验证 REST 创建任务到
`COMPLETED` 的八阶段事件序列。该脚本会主动创建取物任务，不得用于已连接真实执行器的系统。
