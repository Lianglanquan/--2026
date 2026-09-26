# Wheelbot

[![Software integration](https://github.com/Lianglanquan/--2026/actions/workflows/software-integration.yml/badge.svg)](https://github.com/Lianglanquan/--2026/actions/workflows/software-integration.yml)

轮足机器人 Monorepo，按实时控制、高层智能、人机交互、仿真与硬件资料分层组织。

## 目录

- `docs/`：系统架构、通信、电源、安全、接线和标定文档
- `hardware/`：机械结构、电气资料、CAD、BOM 和制造输出
- `firmware/`：DJI RoboMaster C Board 与 ESP32-S3 固件
- `ros2/`：Raspberry Pi 4 上的 ROS 2 Jazzy 工作空间
- `simulation/`：MuJoCo 仿真、强化学习训练和 sim-to-real 资料
- `shared/`：跨设备协议、配置和模型
- `tools/`：标定、日志、绘图和烧录工具
- `deploy/`：树莓派部署、systemd 服务和 udev 规则
- `tests/`：单元、集成、仿真和硬件在环测试

## 控制边界

DJI C Board 是唯一拥有电机控制权的实时核心。树莓派、ESP32-S3、手机、手柄和策略网络只提交控制意图，所有意图必须经过 C Board 的状态估计、仲裁和安全层。

ESP32-S3 的具体串口、人机交互和输入优先级约束见 [`docs/architecture/esp32-s3-interaction.md`](docs/architecture/esp32-s3-interaction.md)。

当前目录中的空文件仅用于保留规划结构；具体驱动和控制实现应在对应模块内逐步添加。

## 任务级语音闭环

- `firmware/esp32_s3/`：固定版本的官方小智固件与 `wheelbot-s3-audio` 专用板型。
- `ros2/wheelbot_ws/src/wheelbot_mission/`：Mission Manager、Nav2 适配、任务状态、REST/事件
  API、Web 控制台和小智反馈 webhook。
- `ros2/wheelbot_ws/src/wheelbot_navigation/`：要求显式实测参数的 Nav2 启动边界。
- `docs/current-system-capability-gap-analysis.md`：按任务书完成的现状与缺口审计。
- `docs/architecture/mission-manager.md`：小智、任务管理、导航、机械臂服务边界和接口说明。
- `docs/software-validation-2026-09-26.md`：本阶段实际测试、未完成项与下一步。

真实语义点默认未启用；完成地图、轮参数、雷达外参、footprint 与 Nav2 标定后，逐点设置
`commissioned: true`。不得用占位坐标进行真机自主运动。

## MuJoCo 运行规则

凡是运行 MuJoCo 运动演示、姿态测试或控制效果观察，默认同时启动可视化窗口，
让操作者能够直接观察机器人姿态、轮子接触、运动方向和倒下过程。可视化窗口与
后台数值记录同时运行，不替代日志、指标和自动化检查。

自动化回归测试、拓扑审计、参数扫描和批量强化学习训练可以使用无窗口模式，
以保证运行速度和可重复性；这类运行必须继续输出结构化结果或测试报告。

当前 MuJoCo 可视化只验证名义模型和控制程序，不代表已经完成 HA8/QD4310
真机标定。真实执行器到位后，仍需通过实测反馈校准延迟、响应、摩擦、质量、
质心和负载等参数。
