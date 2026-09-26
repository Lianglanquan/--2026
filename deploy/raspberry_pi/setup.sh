#!/usr/bin/env bash
# WheelBot 树莓派 4 环境补全脚本（在 Pi 上执行）
# 适用：Ubuntu Server 24.04 LTS ARM64 + ROS 2 Jazzy（ros-base，已装）
# 特性：幂等（已安装的跳过）、出错立即停止、保留已有 ROS 环境
# 明确不安装：Gazebo / MuJoCo / ROS Desktop / CUDA / 强化学习训练环境
set -euo pipefail

echo "==> 检查发行版"
if [ "$(lsb_release -rs 2>/dev/null)" != "24.04" ]; then
    echo "错误：仅支持 Ubuntu 24.04，当前为 $(lsb_release -ds 2>/dev/null || echo 未知)" >&2
    exit 1
fi

echo "==> 检查 ROS 2 Jazzy 已存在"
if [ ! -f /opt/ros/jazzy/setup.bash ]; then
    echo "错误：/opt/ros/jazzy 不存在。请先按官方文档安装 ROS 2 Jazzy ros-base，再执行本脚本。" >&2
    exit 1
fi

apt_install_if_missing() {
    local -a missing=()
    for pkg in "$@"; do
        if ! dpkg -s "$pkg" >/dev/null 2>&1; then
            missing+=("$pkg")
        fi
    done
    if [ ${#missing[@]} -gt 0 ]; then
        echo "==> 安装: ${missing[*]}"
        sudo apt-get update
        sudo apt-get install -y "${missing[@]}"
    else
        echo "==> 已安装，跳过: $*"
    fi
}

echo "==> 开发/运行工具"
apt_install_if_missing git cmake build-essential \
    python3-pip python3-venv \
    python3-colcon-common-extensions python3-rosdep python3-vcstool \
    python3-serial tmux htop

echo "==> WheelBot 运行时 ROS 组件"
apt_install_if_missing ros-jazzy-xacro ros-jazzy-robot-state-publisher \
    ros-jazzy-tf2-ros ros-jazzy-rosbag2 ros-jazzy-diagnostic-updater \
    ros-jazzy-rmw-cyclonedds-cpp ros-jazzy-navigation2 \
    ros-jazzy-nav2-bringup ros-jazzy-robot-localization ros-jazzy-slam-toolbox

echo "==> 双机通信测试节点（talker/listener 验证用）"
apt_install_if_missing ros-jazzy-demo-nodes-cpp ros-jazzy-demo-nodes-py

echo "==> rosdep 初始化"
if [ -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
    echo "==> rosdep 已初始化，跳过"
else
    sudo rosdep init
fi
rosdep update

echo "==> 配置 WheelBot ROS 2 通信环境"
ENV_FILE="${WHEELBOT_REPO_ROOT:-${HOME}/wheelbot}/deploy/raspberry_pi/ros_env.sh"
if ! grep -Fqx '# WheelBot ROS 2' "${HOME}/.bashrc" 2>/dev/null; then
    if [ -f "$ENV_FILE" ]; then
        printf '\n# WheelBot ROS 2\nsource /opt/ros/jazzy/setup.bash\nsource %s\n' "$ENV_FILE" >> "${HOME}/.bashrc"
    else
        printf '\n# WheelBot ROS 2\nsource /opt/ros/jazzy/setup.bash\nexport ROS_DOMAIN_ID=42\nexport RMW_IMPLEMENTATION=rmw_cyclonedds_cpp\n' >> "${HOME}/.bashrc"
    fi
    echo "==> 已将 ROS 2 Jazzy 与 WheelBot 环境加入 ~/.bashrc"
else
    echo "==> ~/.bashrc 已配置 WheelBot ROS 环境，跳过"
fi

echo "==> 树莓派环境补全完成"
echo "验证：source /opt/ros/jazzy/setup.bash && ros2 run demo_nodes_cpp talker"
