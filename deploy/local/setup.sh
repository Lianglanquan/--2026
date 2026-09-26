#!/usr/bin/env bash
# WheelBot 本机（开发机）环境配置脚本
# 适用：Ubuntu 24.04 (Noble) x86_64 + ROS 2 Jazzy Desktop
# 特性：幂等（已安装的跳过）、出错立即停止、不破坏已有环境
set -euo pipefail

# 权限提升：本机约定 sudo -A（SUDO_ASKPASS 自动提供密码），其他机器退回普通 sudo
if [ -n "${SUDO_ASKPASS:-}" ]; then
    SUDO="sudo -A"
else
    SUDO="sudo"
fi

echo "==> 检查发行版"
if [ "$(lsb_release -rs 2>/dev/null)" != "24.04" ]; then
    echo "错误：仅支持 Ubuntu 24.04，当前为 $(lsb_release -ds 2>/dev/null || echo 未知)" >&2
    echo "不擅自安装 Ubuntu ROS deb 包，请先确认发行版与兼容方案。" >&2
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
        $SUDO apt-get update
        $SUDO apt-get install -y "${missing[@]}"
    else
        echo "==> 已安装，跳过: $*"
    fi
}

echo "==> 基础开发工具"
apt_install_if_missing git curl cmake ninja-build build-essential \
    python3 python3-pip python3-venv \
    python3-colcon-common-extensions python3-rosdep python3-vcstool

echo "==> ROS 2 Jazzy Desktop"
if [ -f /opt/ros/jazzy/setup.bash ]; then
    echo "==> /opt/ros/jazzy 已存在，跳过 ROS 安装"
else
    echo "==> 安装 ROS 2 Jazzy（官方 apt 源）"
    apt_install_if_missing software-properties-common
    $SUDO add-apt-repository -y universe
    $SUDO curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
        -o /usr/share/keyrings/ros-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo "$UBUNTU_CODENAME") main" \
        | $SUDO tee /etc/apt/sources.list.d/ros2.list >/dev/null
    $SUDO apt-get update
    $SUDO apt-get install -y ros-jazzy-desktop ros-dev-tools
fi

echo "==> WheelBot 依赖的 ROS 组件"
apt_install_if_missing ros-jazzy-xacro ros-jazzy-robot-state-publisher \
    ros-jazzy-joint-state-publisher ros-jazzy-tf2-ros ros-jazzy-rosbag2

echo "==> rosdep 初始化"
if [ -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
    echo "==> rosdep 已初始化，跳过"
else
    $SUDO rosdep init
fi
rosdep update

echo "==> 配置 WheelBot ROS 2 通信环境"
ENV_FILE="${WHEELBOT_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}/deploy/local/ros_env.sh"
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

echo "==> 本机环境配置完成"
echo "后续每个新终端执行：source /opt/ros/jazzy/setup.bash"
