# VS Code Remote SSH 远程开发（树莓派）

目标：在本机 VS Code 中直接编辑/构建/运行树莓派上的代码，所有命令实际在 Pi 上执行。
树莓派无需安装桌面环境。

## 前置条件

1. 本机已安装 VS Code 及扩展 **Remote - SSH**（ms-vscode-remote.remote-ssh）。
2. 本机可免密 SSH 登录：`ssh wheelbot-pi`。
3. 树莓派上已有 `/home/fool/wheelbot` 仓库，并配置了与本机相同的 Git remote。

## 连接步骤

1. VS Code 左下角绿色按钮 → **Remote-SSH: Connect to Host…** → 选择 `wheelbot-pi`。
2. 首次连接会自动在 Pi 上安装 vscode-server（约 100MB，装于 `~/.vscode-server`），只需等待。
3. 连接成功后 **File → Open Folder…** → 输入 `/home/fool/wheelbot`。

本机已经在 `~/.ssh/config` 中固化别名：

```
Host wheelbot-pi
    HostName 10.171.200.10
    User fool
```

之后 VS Code 中直接选择 `wheelbot-pi`。

## 日常工作流

| 操作 | 位置 |
|------|------|
| 编辑源码 | 本机 VS Code（文件实际保存在 Pi） |
| 构建 | VS Code 集成终端（跑在 Pi 上）：`bash tools/build_ros_pi.sh`（或 `~/wheelbot/tools/build_ros_pi.sh`） |
| 运行节点 | 集成终端中 `source /opt/ros/jazzy/setup.bash && source ~/wheelbot/ros2/wheelbot_ws/install/setup.bash && ros2 launch wheelbot_bringup bringup.launch.py` |
| 查看 topic | `ros2 topic list` / `ros2 topic echo /wheelbot/state` |

注意：

- 集成终端就是 Pi 的 shell，`colcon build`、`ros2 run` 都真实运行在树莓派上（ARM64）。
- 不要把本机的 `build/install/log` 拷到 Pi，也不要反向拷贝——两端各自 `colcon build`。
- 源码变更从本机提交并推送到 Git remote 后，用 `tools/pi_sync.sh` 在 Pi 上执行 `git pull --ff-only`，再到 Pi 上重新构建。脚本不会复制任何 `build/install/log` 或 ARM/x86 编译产物。
- ROS 2 环境不会自动加载，Pi 上每个终端需要 `source /opt/ros/jazzy/setup.bash`（已配置在交互式 bashrc 的场景除外）。

## 一次性仓库引导

在 Pi 上创建工作目录并配置 remote（将 `<REMOTE_URL>` 替换为实际 Git 服务地址）：

```bash
git clone <REMOTE_URL> /home/fool/wheelbot
cd /home/fool/wheelbot
bash deploy/raspberry_pi/setup.sh
```

之后日常只需在本机提交/推送，再运行 `tools/pi_sync.sh`；两台机器分别在各自架构上执行 `colcon build`。
