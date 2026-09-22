# WheelBot ESP32-S3

ESP32-S3 是 WheelBot 的“人机交互 + 无线入口”，不是主控制器。它只产生控制意图，经 UART 发给 DJI C Board；C Board 负责仲裁、超时和电机闭环。

## 已落地的核心

- 双轮差速混合：`vx_mps` + `yaw_rate_rps` → 左右轮 rpm，带最大转速限制。
- 与 C Board `robot_protocol` 兼容的 `WB`/CRC16 command frame（36 字节）。
- 输入路由：停止命令全局最高优先级；非停止优先级为 BLE > Wi-Fi > 语音；统一 200 ms 意图有效期由上层 watchdog 使用。
- 语音命令词解析：`前进`、`后退`、`左转`、`右转`、`停止`、`趴下`（英文等价词亦支持）。
- 手机控制文本解析：`vx=0.3;yaw_rate=-0.2;mode=2;stop=0`。
- ESP-IDF UART 入口：UART1，默认 GPIO17 TX / GPIO16 RX，115200 8N1；引脚和波特率应按实际 PCB 修改。
- `app_main` 以 50 Hz 选择并发送当前意图；没有有效输入时持续发送 stop。
- ESP-IDF SoftAP 控制入口：SSID `WheelBot-ESP32`，密码 `wheelbot42`，请求 `/control?cmd=vx=0.2;yaw_rate=0;mode=2;stop=0`。
- 语音入口带唤醒门控：ESP-SR WakeNet 成功后调用 `wheelbot_voice_on_wake()`，MultiNet 命令调用 `wheelbot_voice_on_command()`；每次命令后自动退出唤醒态。
- BLE 手柄适配器将 HID 摇杆和 stop 按钮转换为统一意图，带 10% 摇杆死区；NimBLE 回调只需调用 `wheelbot_provider_submit_ble_report()`。
- I2S 音频输出已接入 ESP-IDF，默认 GPIO4/5 时钟、GPIO7 数据、16 kHz，兼容 MAX98357A；可调用 `wheelbot_audio_beep()` 播放提示音。
- I2S 音频现为收发共用时钟：INMP441 数据输入 GPIO6，MAX98357A 数据输出 GPIO7；可调用 `wheelbot_audio_read()` 获取 16-bit PCM 麦克风采样。
- UART、轮径、轮距、最大转速和超时参数集中在 `include/wheelbot_config.h`，默认值也写入 `sdkconfig.defaults`。

## 输入源接入边界

ESP-SR 的 WakeNet/MultiNet 回调、Wi-Fi HTTP/TCP/UDP 服务、BLE 手柄回调都只需构造 `wheelbot_intent_t`，然后调用 `wheelbot_input_router_submit()`；禁止各输入源直接拼接 C Board 字节帧。语音播报通过独立 I2S/MAX98357A provider 接入，不影响 UART 协议。

## 构建与测试（无需 ESP-IDF）

```bash
bash tools/test_esp32_s3.sh
```

有 ESP-IDF 时，在仓库根目录执行 `bash tools/build_esp32_s3.sh`。脚本会检查 `idf.py`、设置 `esp32s3` 目标并构建。真实语音、Wi-Fi、BLE、I2S 和 UART 电气联调必须接入对应硬件后验证。
