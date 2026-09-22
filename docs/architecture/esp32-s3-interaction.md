# ESP32-S3 人机交互与串口入口

## 定位

ESP32-S3 是 WheelBot 的人机交互与无线入口，不是主控制器。它不直接驱动电机，只把语音、手机和 BLE 手柄输入转换为控制意图，经 UART 发送给 DJI C Board。

## 串口链路

默认参数为 115200 baud、8 data bits、无校验、1 stop bit（8N1）。建议连接如下：

| ESP32-S3 | C Board | 说明 |
|---|---|---|
| UART TX | USART1 RX（PB7） | 控制意图帧 |
| UART RX | USART1 TX（PA9） | 预留状态回传 |
| GND | GND | 必须共地 |

C Board 的 USART6（开发板丝印 UART1）继续保留给 FashionStar 舵机，不与 ESP32 复用。两端均为 3.3 V 逻辑；实际接线前核对所用 ESP32-S3 模组引脚复用和电平。

同一条 C Board USART1 与 ESP32-S3 UART1 也是全双工链路：ESP32 发送控制帧，C Board 反向发送 `W B` 电压遥测帧（类型 3，18 字节，115200/8N1）。遥测负载包含 `float voltage` 和 `uint16 percentage`，C Board 每 100 ms 发送一次；ESP32 固件已接收、校验 CRC 并记录最新值。

当前 C Board 工程已包含通用 UART 字节流解析器和主机测试；实际 STM32 中断回调需要与 FashionStar 现有 `HAL_UART_RxCpltCallback` 合并时再接入，避免两个 HAL 回调实现互相覆盖。

## 控制意图

```c
typedef struct {
    float vx_mps;
    float yaw_rate_rps;
    uint8_t mode;
    uint8_t stop;
} wheelbot_intent_t;
```

ESP32-S3 使用车轮半径、轮距和最大转速配置，将 `vx_mps`/`yaw_rate_rps` 换算成左右轮 rpm，再填入与 C Board 共用的 `wheelbot_command_t`。

帧格式为现有 `WB` + version/type/length/sequence + payload + CRC16-CCITT，命令帧固定 36 字节。C Board 侧使用 `communication/uart_robot_protocol.c` 按字节接收，允许中断分包并丢弃坏 CRC 帧。

## 输入优先级和安全

- `stop=1` 在所有输入源中优先级最高。
- 非停止输入优先级：BLE > Wi-Fi > 语音。
- 输入意图默认 200 ms 有效；超时后必须由上层发送 stop，C Board 仍需执行自己的 200 ms 安全超时。
- ESP-SR WakeNet/MultiNet、Wi-Fi HTTP/TCP/UDP、BLE 手柄和 I2S/MAX98357A 播放均通过 provider 接口接入，不得绕过统一路由器和 UART 传输层。

## 当前实现与待硬件验证

`firmware/esp32_s3` 已提供协议核心、差速混合、输入路由、语音/手机文本解析和 ESP-IDF UART 初始化入口。真实 ESP-SR 模型、Wi-Fi 服务、BLE profile、I2S 音频播放以及 UART 电气链路需要在具体 ESP32-S3 模组和接线确认后进行板级联调。

ESP-IDF `app_main` 以 50 Hz 发送当前路由结果；没有有效输入时发送 stop 帧，避免上电后产生运动命令。

Wi-Fi provider 已提供 SoftAP 和 HTTP 控制入口：连接 `WheelBot-ESP32`（密码 `wheelbot42`）后访问 `/control?cmd=vx=0.2;yaw_rate=0;mode=2;stop=0`。请求只进入 Wi-Fi provider 和统一输入路由，不直接写 UART。

主机回归测试统一运行 `bash tools/test_esp32_s3.sh`，覆盖 ESP32 核心库、输入 provider、UART 帧编码，以及 C Board UART 接收器的分包/CRC 行为。
