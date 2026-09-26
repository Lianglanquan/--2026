# Wiring

电源、CAN、UART、USB 和执行器总线接线资料。

## RoboMaster C Board 连接确认

以下映射来自《ROBOMASTER 开发板 C 型用户手册》附表和 UART 接口章节：

| C 板外壳丝印 | STM32 实例 | MCU 引脚 | 接口线序 |
| --- | --- | --- | --- |
| 实际 UART1（4-pin，外壳通常标 UART2） | `USART1` | `PA9` TX, `PB7` RX | 1 RXD, 2 TXD, 3 GND, 4 5V |
| 实际 UART6（3-pin，外壳通常标 UART1） | `USART6` | `PG14` TX, `PG9` RX | 1 GND, 2 TXD, 3 RXD |

手册特别说明：外壳丝印与 MCU 实例并不对应，**丝印 UART1 实际对应 STM32 UART6，丝印 UART2 实际对应 STM32 UART1**。因此本项目总线舵机接在实际 UART6/3-pin 接口，ESP32-S3 接在实际 UART1/4-pin 接口；不能按外壳名称绑定 HAL 句柄。

QD4310 使用 C 板 `CAN1`：`PD1` = CAN1_TX，`PD0` = CAN1_RX；接口为 2-pin CAN，最高 1 Mbps。CAN 收发器和执行器必须共地，并按 CANH/CANL 接线。

板载无源蜂鸣器连接 `TIM4_CH3 / PD14`。官方 `20.standard_robot` 的 `test_task` 会扫描 DBUS、电机、IMU、OLED 等离线状态并鸣叫；未连接完整 DJI 外设时持续鸣叫属于故障提示。

## ESP32-S3 音频模块

当前 ESP32-S3 固件按以下接线配置 I2S：

| ESP32-S3 | INMP441 | MAX98357A |
| --- | --- | --- |
| 3V3 | VDD | — |
| 5V/VBUS | — | VIN/VCC |
| GND | GND | GND |
| GPIO4 | SCK/BCLK | BCLK |
| GPIO5 | WS/LRCLK | LRC/WS |
| GPIO6 | SD/DOUT | — |
| GPIO7 | — | DIN |

扬声器接 MAX98357A 的 `SPK+` 和 `SPK-`，不要将 `SPK-` 接地。INMP441 的 `L/R` 接 GND 选择左声道，接 3V3 选择右声道。功放电源电流较大时可单独供电，但必须与 ESP32 共地。
