# Calibration

关节零位、IMU、HA8 总线舵机和 QD4310 标定流程与参数记录。

## HA8 实物标定记录

当前已通过 `/dev/ttyUSB0` 和 115200 baud 对左前 HA8 完成总线 ID 标记：

- 型号：FashionStar / 华馨京 `HA8-U25H-M`
- 机械位置：左前（LF）
- 项目逻辑编号：`1`
- 实际总线 ID：`1`
- 原始默认 ID：`0`，已确认旧 ID 不再响应
- 标定动作：仅写入用户参数地址 `34`（`servo_id`）并复核 Ping、角度读取
- 未执行：角度运动、速度控制、阻尼控制、设置原点

机器可读映射见 [`ha8_servo_mapping.json`](ha8_servo_mapping.json)。左后、右前、右后必须分别单独接线、确认在线后再分配不同的总线 ID；在完成实物标定前保持 `commissioned: false`。

注意：该记录只包含总线 ID 标记与通信复核，不包含五连杆机械零位、正方向、关节角限位，也不等同于运动学标定。固件默认禁止 HA8 角度下发；实测这些参数并验证机构无干涉后才能开启 `WHEELBOT_HA8_MOTION_ENABLED`。
