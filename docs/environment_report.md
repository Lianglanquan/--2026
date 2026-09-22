# WheelBot 双机环境检测报告

检测日期：2026-09-06
检测原则：先只读检测；随后仅执行树莓派依赖脚本与 ROS 环境配置，不修改网络参数。

## 1. 本机（开发机）

| 项目 | 结果 |
|------|------|
| 发行版 | Ubuntu 24.04.3 LTS (Noble Numbat) |
| CPU 架构 | x86_64（20 核） |
| Git | 2.43.0 ✓ |
| SSH | OpenSSH 9.6p1 ✓ |
| CMake | 3.30.9（/usr/local/bin/cmake）✓ |
| Ninja | 1.11.1 ✓ |
| Python | 3.12.3 ✓（pip3、venv 可用） |
| g++ / build-essential | ✓ |
| ROS 2 | Jazzy，位于 /opt/ros/jazzy，`ros2` 命令可用 ✓ |
| ROS_DISTRO | jazzy（~/.bashrc 中已 source /opt/ros/jazzy/setup.bash）|
| colcon | ✓ |
| rosdep / vcstool | ✓ |
| ROS 包数量 | 400 个 ros-jazzy 包 |
| ROS 变体 | ros-jazzy-desktop 已安装 ✓ |
| 关键 ROS 包 | xacro ✓ robot-state-publisher ✓ joint-state-publisher ✓ tf2-ros ✓ rosbag2 ✓ demo-nodes-cpp/py ✓ |
| 磁盘 | / 共 97G，可用 11G（89% 已用，偏紧）|
| 网络 | wlp0s20f3 = 10.200.224.187/24（Wi-Fi）；wg0 = 10.77.0.2/32（WireGuard）；默认网关 10.200.224.17 |

注意：
- `~/.bashrc` 第 140-141 行还会 source `~/ros2_study_lab/ros2_ws` 的 overlay，属既有环境，未改动。
- 默认 Fast DDS 在本机触发 `Fast CDR BadParamException`；双方 WheelBot 环境统一选择已验证可用的 `rmw_cyclonedds_cpp`。
- 本机存在 WireGuard 接口 wg0，DDS 发现时需注意接口选择（FastDDS 默认可能绑定错误接口，见 5.4）。

## 2. Raspberry Pi 4（10.200.224.147）

| 项目 | 结果 |
|------|------|
| 发行版 | Ubuntu 24.04.4 LTS (Noble Numbat) |
| CPU 架构 | aarch64（4 核） |
| SSH 登录 | fool@10.200.224.147 密钥登录正常 ✓ |
| sudo | NOPASSWD 可用 ✓ |
| 内存 | 7.6 GiB |
| 磁盘 | / 共 28G，可用 21G ✓ |
| Git | 2.43.0 ✓ |
| CMake | 3.28.3 ✓（make 有，但 g++/build-essential 未装 ✗）|
| Python | 3.12.3 ✓（venv 可用；pip3 未装 ✗）|
| ROS 2 | Jazzy 已安装，`source /opt/ros/jazzy/setup.bash` 后 `ros2` 命令正常 ✓ |
| ROS_DISTRO | 非登录 shell 未设置；source 后为 jazzy；setup 已将 ROS 环境加入 `~/.bashrc` |
| ROS 包数量 | 316 个 ros-jazzy 包 |
| ROS 变体 | ros-base ✓（未安装 ros-jazzy-desktop 元包）|
| 关键 ROS 包 | xacro ✓ robot-state-publisher ✓ tf2-ros ✓ rosbag2 ✓ diagnostic-updater ✓；Cyclone DDS RMW ✓ |
| 额外已装 | navigation2、robot-localization、rviz、ros-gz、slam-toolbox 等（既有环境，保留不动）|
| colcon | ✗ 未安装 |
| rosdep / vcstool | ✗ 未安装 |
| python3-serial | ✓ 已安装 |
| tmux / htop | ✓ 已安装 |
| demo_nodes_cpp/py | ✓ 已安装（通信测试用）|
| 家目录 | 尚无 `/home/fool/wheelbot` Git 工作树；未擅自创建无 remote 的日常同步目录 |
| USB | 当前无 C Board 设备 |

## 3. 网络连通性

- 本机与 Pi 同处 10.200.224.0/24 网段（本机 .187，Pi .147），SSH 直连正常。
- 两机间 ROS 2 DDS 通信待 Phase 5 实测。

## 4. 已执行动作与结论

本机（Phase 3）：
- ROS 2 Jazzy Desktop 及全部要求工具已就绪，无需安装新软件。
- 生成幂等的 `deploy/local/setup.sh` 供重装/新机器使用；本机现有依赖无需安装。

树莓派（Phase 4）：
- setup 脚本复核并跳过所有已安装基础包和 ROS 组件；补装 `ros-jazzy-rmw-cyclonedds-cpp` 以统一 DDS 实现。
- ROS_DOMAIN_ID=42 已写入 Pi `~/.bashrc`，并提供 `deploy/raspberry_pi/ros_env.sh`。
- 未安装 Gazebo、MuJoCo、CUDA 或强化学习环境。

通信实测（2026-09-06）：

- Pi talker → 本机 listener：通过，收到 Hello World 连续消息。
- 本机 talker → Pi listener：通过，收到 Hello World 连续消息。
- 两端均使用 `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`；未设置 `ROS_LOCALHOST_ONLY=1`。

## 5. 风险与注意事项

1. Pi 上 ROS 环境不会自动 source，所有 Pi 脚本必须显式 `source /opt/ros/jazzy/setup.bash`。
2. 本机磁盘仅剩 11G，后续 MuJoCo/训练数据需关注空间。
3. 本机多网卡（Wi-Fi + WireGuard + docker 网桥），DDS 通信若失败优先按 Phase 5 诊断清单排查接口选择。
4. Pi 已装 316 个 ROS 包（含 nav2/rviz/gz），虽超出"最小环境"范围，但按要求不做卸载，仅记录。
5. 本机默认 Fast DDS 会触发 `Fast CDR BadParamException`；WheelBot 环境片段已固定使用 Cyclone DDS。其他项目若依赖 Fast DDS，请在其独立 shell 中显式覆盖 `RMW_IMPLEMENTATION`。

## 6. 当前 Wi-Fi 固定连接（2026-09-21）

本机与树莓派通过 Wi-Fi SSID `fool` 连接，SSH 使用固定地址，不依赖 DHCP 租约：

| 设备 | Wi-Fi 接口 | 固定地址 | SSH 入口 |
|------|------------|----------|----------|
| 本机开发机 | `wlp0s20f3` | `10.171.200.11/24` | — |
| Raspberry Pi 4 | `wlan0` | `10.171.200.10/24` | `ssh wheelbot-pi` |

本机 `~/.ssh/config` 已配置 `wheelbot-pi` 别名、密钥登录、连接保活和连接复用。树莓派有线接口已关闭 IPv4 配置，SSH 路径固定走 Wi-Fi；树莓派 `ssh.socket` 已启用并处于 active 状态。
