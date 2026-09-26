# WheelBot ESP32-S3 Audio

This board profile combines the official XiaoZhi application with the WheelBot
UART safety component on an ESP32-S3 N16R8 module.

## Wiring

| Signal | ESP32-S3 GPIO |
| --- | ---: |
| INMP441 BCLK/WS/SD | 4 / 5 / 6 |
| MAX98357A DIN/LRC/BCLK | 7 / 15 / 16 |
| MAX98357A SD (open-drain enable) | 8 |
| SSD1315 I2C SDA/SCL | 41 / 42 |
| SSD1315 address | module label 0x78 (ESP-IDF 7-bit 0x3C) |
| KEY1/KEY2/KEY3 | 9 / 10 / 11 |
| WheelBot UART TX | 17 |
| WheelBot UART RX | 18 |
| BOOT button | 0 |

Connect the INMP441 L/R pin to GND. All modules must share ground. The
INMP441 is powered from 3.3 V; power the MAX98357A according to the amplifier
module and speaker requirements while keeping its logic ground common. The OLED
driver uses SSD1315's SSD1306-compatible page transfer with a board-specific
initialization sequence.

The BOOT button toggles chat after startup. Clicking it while the device is
still starting enters Wi-Fi configuration mode.

Voice, cloud responses, and wake callbacks are intentionally not connected to
WheelBot movement. Until another explicitly authorized provider submits an
intent, the UART control task emits only stop commands.
