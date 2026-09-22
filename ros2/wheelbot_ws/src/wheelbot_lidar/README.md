# WheelBot X2 雷达链路

本包只负责接收 FishBot Laser Board 发来的 TCP 原始 UART 字节，并将其写入
PTY。X2 协议解析仍由官方 `YDLIDAR/ydlidar_ros2` 完成。

启动 TCP 转 PTY：

```bash
ros2 run wheelbot_lidar tcp_to_pty --ros-args -p port:=8889
```

程序启动时会输出一个 PTY 路径。生产环境可用 udev 或 systemd 将它固定为
`/dev/wheelbot-lidar`，再使用 `config/x2.yaml` 启动官方 YDLIDAR 节点。

验证顺序：先确认 TCP 收到 X2 原始帧，再启动官方驱动，最后检查：

```bash
ros2 topic echo /scan
ros2 topic hz /scan
```

没有看到真实 `sensor_msgs/msg/LaserScan` 前，不认为雷达链路验收通过。
