# ESP32-S3 小智语音与任务入口

## 定位

ESP32-S3 采用官方 `78/xiaozhi-esp32`，负责唤醒、音频、联网、官方云端对话、MCP 和 OTA。
它不是机器人主控制器，不直接驱动 C Board、电机或机械臂。

本仓库以固定提交导入上游，并新增唯一板型 `wheelbot-s3-audio`。上游来源与升级规则见
`firmware/esp32_s3/UPSTREAM.md`。

## 硬件

目标为 ESP32-S3 N16R8：

| GPIO | 连接 |
|---|---|
| 4 | INMP441 SCK / MAX98357A BCLK |
| 5 | INMP441 WS / MAX98357A LRC |
| 6 | INMP441 SD |
| 7 | MAX98357A DIN |

输入输出共用 BCLK/WS，使用官方 `NoAudioCodecDuplex`。麦克风供电 3.3 V，功放供电
5 V/VBUS，三者共地；扬声器只能接 SPK+ 与 SPK-。

## MCP 能力

- `self.wheelbot.navigate(location)`
- `self.wheelbot.fetch_item(item, pickup_location, return_location)`
- `self.wheelbot.return_home(location)`
- `self.wheelbot.get_mission_status(mission_id)`
- `self.wheelbot.cancel_mission(mission_id)`

这些工具通过带 Bearer token 的 REST 请求调用树莓派 Mission Manager。没有前进、后退、
轮速、RPM 或关节级 MCP 工具。

## 安全与配置

- `CONFIG_WHEELBOT_MISSION_BASE_URL` 指向树莓派任务服务。
- `CONFIG_WHEELBOT_MISSION_TOKEN` 必须与 ROS 启动参数一致；部署前必须替换开发默认值。
- API 断开、非 2xx 响应或任务校验失败都会作为 MCP 错误返回，不会降级为底层运动。
- 语义位置是否可执行由 Mission Manager 的 `commissioned` 标志决定，ESP32 无权绕过。

## 构建

使用 ESP-IDF 6.1：

```bash
bash tools/build_esp32_s3.sh
```

必须在实物上分别验收扬声器、麦克风、唤醒、官方云对话、MCP 列表、Mission API 和重复
请求/断网行为；编译成功不等于音频或机器人联调成功。
