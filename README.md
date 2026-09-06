# Wheelbot

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

当前目录中的空文件仅用于保留规划结构；具体驱动和控制实现应在对应模块内逐步添加。
