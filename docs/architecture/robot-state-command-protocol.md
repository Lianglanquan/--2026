# RobotState / RobotCommand USB 协议

Pi 与 C 板之间的执行器控制边界采用 WB v1 二进制帧。C 板内部仍保留 DJI、
QD4310 和 FashionStar 的官方实现，只有 USB 边界使用此协议。

帧头为 `WB`、版本、类型、payload 长度和序号，随后是 payload 与 CRC-16/CCITT-FALSE。
类型 `1` 为 `RobotCommand`，类型 `2` 为 `RobotState`；整数均为 little-endian，浮点数为
IEEE-754 float32。接收端必须同时校验 magic、版本、类型、长度和 CRC，失败帧不得触发执行器。

`RobotCommand` 固定包含 enable、mode、4 个关节目标和 2 个轮命令。
`RobotState` 固定包含时间戳、IMU（gyro/accel/quaternion/rpy）、4 个关节、2 个轮、电池和故障字段。
字段顺序与 `firmware/c_board/communication/robot_protocol.h` 及 ROS 消息完全一致。

`RobotState.faults` 的 bit 7 表示启用中的非 idle 命令超过 200 ms 未刷新；C Board 在置位
该故障时会把命令转换为 idle、取消关节目标并停止/禁用轮电机。新有效命令会清除此位。

ASCII `PING\n` / `PONG\n` 继续保留，仅用于链路诊断，不替代状态协议。
