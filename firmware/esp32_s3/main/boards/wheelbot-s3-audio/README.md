# WheelBot ESP32-S3 Audio

This board profile combines the official XiaoZhi application with the WheelBot
UART safety component on an ESP32-S3 N16R8 module.

## Wiring

| Signal | ESP32-S3 GPIO |
| --- | ---: |
| Shared I2S BCLK | 4 |
| Shared I2S WS/LRC | 5 |
| INMP441 SD | 6 |
| MAX98357A DIN | 7 |
| WheelBot UART TX | 17 |
| WheelBot UART RX | 16 |
| BOOT button | 0 |

Connect the INMP441 L/R pin to GND. All modules must share ground. The
INMP441 is powered from 3.3 V; power the MAX98357A according to the amplifier
module and speaker requirements while keeping its logic ground common.

The BOOT button toggles chat after startup. Clicking it while the device is
still starting enters Wi-Fi configuration mode.

Voice, cloud responses, and wake callbacks are intentionally not connected to
WheelBot movement. Until another explicitly authorized provider submits an
intent, the UART control task emits only stop commands.
