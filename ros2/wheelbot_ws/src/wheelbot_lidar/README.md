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

## 生产环境自恢复

树莓派上的 `ydlidar-x2.service` 负责驱动，`wheelbot-lidar-watchdog.service`
负责监测 `/scan`。watchdog 启动后有 10 秒宽限期；连续 1.5 秒没有收到扫描才会
重启 YDLIDAR，单次丢帧不会触发重启。重启后 15 秒内不会重复触发。

查看状态：

```bash
systemctl status wheelbot-lidar-watchdog.service
journalctl -u wheelbot-lidar-watchdog.service -f
```

阶段一主服务和雷达 watchdog 相互独立，重启雷达驱动不会停止 C Board、EKF 或
`slam_toolbox`。四个相关服务均已设置为开机自动启动：

```text
wheelbot-lidar-tcp.service
ydlidar-x2.service
wheelbot-lidar-watchdog.service
wheelbot-phase1.service
```
