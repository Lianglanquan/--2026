# 阶段一 SLAM 软件联调

## 1. 构建

在 ASCII 路径的树莓派工作区中执行：

```bash
source /opt/ros/jazzy/setup.bash
source deploy/raspberry_pi/ros_env.sh
colcon build --symlink-install
source install/setup.bash
```

## 2. 无实物联调

fake 模式验证状态适配和 EKF。它不会验证真实雷达、真实轮速或物理地图：

```bash
ros2 launch wheelbot_bringup phase1.launch.py \
  use_fake_bridge:=true \
  use_real_bridge:=false \
  use_lidar:=false \
  use_ekf:=true \
  use_slam:=false
```

检查：

```bash
ros2 topic hz /wheelbot/state
ros2 topic hz /imu/data
ros2 topic hz /wheelbot/wheel_odom
ros2 topic hz /odometry/filtered
ros2 run tf2_ros tf2_echo odom base_link
ros2 run tf2_ros tf2_echo base_link laser_frame
```

## 3. 真实雷达与建图

实物接好并且 X2 驱动已经能够发布真实 `/scan` 后：

```bash
ros2 launch wheelbot_bringup phase1.launch.py \
  use_fake_bridge:=false \
  use_real_bridge:=true \
  use_lidar:=true \
  use_ekf:=true \
  use_slam:=true
```

建图前必须确认：

- `/scan` 持续输出；
- `/imu/data` 时间戳持续更新；
- `/wheelbot/wheel_odom` 与 `/odometry/filtered` 持续输出；
- `odom -> base_link -> laser_frame` 只有一条有效 TF 链；
- `laser_frame` 的实际安装外参已经替换 URDF 中的零值；
- `wheel_radius_m`、`wheel_track_m` 与左右轮符号已经标定；
- 第二轮反馈启用前，`robot_kinematics.yaml` 保持 `wheel_indices: [0]`，不要伪造双轮里程计。

地图保存可以使用 ROS 2 的 map saver：

```bash
ros2 run nav2_map_server map_saver_cli -f ~/wheelbot_maps/phase1
```

## 4. 当前边界

阶段一只完成二维定位和建图基础闭环，不包括视觉 SLAM、YOLO/VLM、三维重建、地形可通行性分析和足端规划。GPU 服务器后续应订阅 ROS 话题做异步视觉/语义计算，不应成为树莓派基础安全闭环的单点依赖。
