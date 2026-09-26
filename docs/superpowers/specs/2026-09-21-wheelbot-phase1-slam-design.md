# WheelBot 阶段一二维 SLAM 与导航基础闭环设计

## 目标

在 Raspberry Pi 4、ROS 2 Jazzy、YDLIDAR X2、C Board IMU 和轮速反馈的现有基础上，建立可验证的基础定位与二维建图闭环：标准传感器消息、`robot_localization` 状态融合、完整 TF、`slam_toolbox` 建图，以及后续接入 Nav2 的稳定接口。

本阶段不实现视觉 SLAM、YOLO/VLM、三维重建、足端规划或完整自主导航行为树；但所有坐标系、消息接口和启动边界必须为后续视觉与三维地图扩展保留空间。

## 现状与约束

- ROS 2 发行版为 Jazzy；目标运行平台为 Raspberry Pi 4 ARM64。
- X2 通过 FishBot Laser Board TCP 链路转 PTY，由官方 YDLIDAR 驱动发布 `/scan`。
- C Board 二进制状态已包含 IMU 四元数、陀螺仪、加速度、轮位置和轮速字段。
- 现有 bridge 只发布自定义 `wheelbot/state`，尚未发布标准 `sensor_msgs/Imu` 和 `nav_msgs/Odometry`。
- 当前 C Board 固件只明确填充 `wheel_position[0]` 与 `wheel_velocity[0]`；第二轮字段可能为零值，不能伪造为有效反馈。
- 当前 URDF 只有 `base_link` 占位，不能虚构腿部机械尺寸；阶段一只增加雷达外参和必须的固定 TF。
- 工作区存在未提交的用户改动；实现只能修改本设计涉及的 ROS 2 文件，不得重置、覆盖或回退其他文件。

## 选定架构

```text
C Board IMU + wheel state
          |
          v
wheelbot_bridge: /imu/data, /wheelbot/wheel_odom
          |
          v
robot_localization EKF: /odometry/filtered
          |
          +--> odom -> base_link
          |
YDLIDAR X2: /scan -- base_link -> laser_frame
          |
          v
slam_toolbox: map -> odom, /map
          |
          v
Nav2 (optional next boundary): map + filtered odom + costmaps
```

### 坐标系契约

- `map`：SLAM 全局坐标系，由 `slam_toolbox` 发布。
- `odom`：连续但会漂移的局部运动坐标系，由 EKF 发布。
- `base_link`：机器人机身参考坐标系。
- `laser_frame`：X2 雷达坐标系，由机器人描述或静态 TF 发布。
- 阶段一不发布第二个节点生成的重复 `odom -> base_link`；EKF 是唯一发布者。
- 阶段一把导航状态限制在平面运动模型，但保留 IMU 四元数和角速度输入，后续可以升级到姿态补偿和视觉融合。

## 数据接口

### Bridge 输出

保留现有：

- `/wheelbot/state`：自定义 `wheelbot_interfaces/msg/RobotState`，用于诊断和兼容已有消费者。

新增：

- `/imu/data`：`sensor_msgs/msg/Imu`
  - 使用 C Board 状态中的四元数、角速度和线性加速度。
  - `header.frame_id` 为 `imu_link`。
  - 没有有效字段时使用高协方差或明确无效配置，不填充虚假测量。
- `/wheelbot/wheel_odom`：`nav_msgs/msg/Odometry`
  - `header.frame_id` 为 `odom`，`child_frame_id` 为 `base_link`。
  - 由轮位置增量或轮速计算平面运动估计。
  - 在左右轮数据不足时不生成可信的角速度；节点必须发出诊断日志并保持可观测状态。

### 状态估计输出

- `/odometry/filtered`：`nav_msgs/msg/Odometry`。
- TF：`odom -> base_link`。
- EKF 只负责融合和连续运动估计，不发布 `map -> odom`。

### SLAM 输出

- `/map`：`nav_msgs/msg/OccupancyGrid`。
- TF：`map -> odom`。
- `slam_toolbox` 输入 `/scan`、TF 和 `/odometry/filtered`。

## 轮速里程计策略

阶段一不把机器人腿部运动学和足端接触估计混入第一版里程计。第一版只封装现有轮反馈接口，并显式区分：

1. 双轮位置/速度有效：生成差速平面里程计；
2. 只有单轮有效：发布线速度可观测性降低的结果，不把缺失轮伪造成另一侧；默认关闭或显著增大 yaw 相关协方差；
3. 两轮均无效：停止里程计更新或发布零速度并提高协方差，不能继续累加旧速度。

轮半径、轮距、左右轮符号和初始零位全部作为 YAML 参数，不写死在 bridge 业务逻辑中。里程计时间使用 ROS 接收时间；C Board 时间戳只用于诊断和后续时钟同步，不直接假设与 Pi 时钟同源。

## EKF 配置策略

使用 `robot_localization/ekf_node`：

- 输入 `/wheelbot/wheel_odom` 和 `/imu/data`。
- 输出 `/odometry/filtered`。
- `world_frame: odom`、`base_link_frame: base_link`。
- 阶段一启用二维模式，融合轮速的平面位置/速度与 IMU 的 yaw 相关信息；不把未经验证的 IMU绝对姿态当作全局位置。
- 协方差必须保守，特别是轮足机器人可能出现打滑时，不把轮速设置成绝对可信。
- 只由 EKF 发布 `odom -> base_link`。

## SLAM 配置策略

使用 `slam_toolbox` 的同步建图模式作为第一阶段默认模式：

- `base_frame: base_link`
- `odom_frame: odom`
- `map_frame: map`
- `scan_topic: /scan`
- 初始分辨率使用 `0.05 m`
- 通过最小平移/旋转阈值避免重复处理静止扫描。
- 地图保存使用标准 `map_saver` 或 `slam_toolbox` 的序列化接口，路径由启动参数指定。
- 不在没有真实 `/scan`、有效 TF 和有效里程计前宣称建图通过。

## 启动边界

提供以下可组合启动文件：

- 雷达驱动：现有 `wheelbot_lidar/x2.launch.py`。
- 机器人描述与固定 TF：`wheelbot_description`。
- Bridge 与标准消息转换：`wheelbot_bridge`。
- EKF：新的 localization 配置/启动文件。
- SLAM：新的 mapping 配置/启动文件。
- 阶段一总启动：`wheelbot_bringup/phase1.launch.py`。

总启动文件必须允许通过 launch 参数关闭真实 bridge、雷达、EKF 或 SLAM，便于 fake 数据和分层验收；不能把所有节点不可分割地硬编码在一个进程中。

Nav2 不作为阶段一的强制运行依赖。阶段一只保证其未来所需的 `/map`、`/odometry/filtered`、TF 和机器人 footprint 接口清晰可接入。

## 错误处理

- C Board 断开：bridge 停止发布新鲜状态并发布可见诊断，不保留旧数据冒充实时数据。
- 单轮/无轮数据：保留消息可观测性，增大对应协方差或停止积分；不伪造反馈。
- 缺少 `/scan`：SLAM 节点可以启动但验收失败，文档必须把这作为前置条件。
- 缺失 TF：SLAM 和 Nav2 不应通过静态猜测继续运行；启动日志要明确缺失的 frame。
- 多个节点发布同一 TF：视为配置错误，验收脚本必须检查。

## 测试和验收

### 自动化

- bridge 的 IMU 消息转换测试：四元数、角速度、加速度、frame_id 和时间戳。
- 轮速里程计测试：双轮直行、原地转向、轮符号、单轮缺失和零速度。
- 现有协议和雷达 TCP-to-PTY 测试必须保持通过。
- 配置静态检查：YAML 可解析、launch 文件可导入、TF frame 名称一致。

### 树莓派真实验收

```bash
source /opt/ros/jazzy/setup.bash
source deploy/raspberry_pi/ros_env.sh

ros2 topic hz /scan
ros2 topic hz /imu/data
ros2 topic hz /wheelbot/wheel_odom
ros2 topic hz /odometry/filtered
ros2 run tf2_ros tf2_echo odom base_link
ros2 run tf2_ros tf2_echo base_link laser_frame
ros2 topic echo /map --once
```

验收标准：

- `/scan` 持续输出真实 `sensor_msgs/LaserScan`；
- `/imu/data` 和轮速里程计时间戳持续更新；
- `odom -> base_link -> laser_frame` 链路唯一且连续；
- `/odometry/filtered` 随机器人运动变化，停止时速度回到零；
- `slam_toolbox` 能在静态室内环境中生成无明显重影的地图；
- 能保存地图，并可用保存的地图重新启动定位流程；
- 没有硬件数据时只报告软件链路通过，不报告物理建图通过。

## 明确不做的事情

- 不在本阶段加入 VLM、YOLO、视觉 SLAM 或三维重建。
- 不把普通单目相机深度估计作为定位真值。
- 不虚构第二轮反馈、雷达安装外参或腿部机械尺寸。
- 不在没有地图和 footprint 标定的情况下声称 Nav2 全链路完成。
- 不修改或回退工作区中与本阶段无关的未提交文件。
