# WheelBot S3 Audio

WheelBot's XiaoZhi voice endpoint is a dedicated ESP32-S3 N16R8 build. It keeps
the official XiaoZhi Wi-Fi, activation, ASR/LLM/TTS, MCP and OTA behavior, and
adds only high-level WheelBot mission tools.

## Wiring

| ESP32-S3 | Peripheral |
|---|---|
| GPIO4 | INMP441 SCK and MAX98357A BCLK |
| GPIO5 | INMP441 WS and MAX98357A LRC |
| GPIO6 | INMP441 SD |
| GPIO7 | MAX98357A DIN |
| 3.3 V | INMP441 power |
| 5 V/VBUS | MAX98357A power |
| GND | Shared ground |

INMP441 L/R is tied to GND. The speaker connects only to SPK+ and SPK-.

## Mission boundary

The model sees `navigate`, `fetch_item`, `return_home`, `get_mission_status`
and `cancel_mission`. The ESP32 sends authenticated JSON requests to the
Raspberry Pi Mission Manager. It never emits wheel speed, motor, joint, or
navigation-controller commands.

Identical submissions within 30 seconds reuse the same `request_id`, so an MCP
or network retry cannot create a second physical mission.

Configure `WheelBot mission base URL` and `WheelBot mission API token` in
menuconfig. The token must match the `wheelbot_mission` launch argument. Change
the development token before running on a shared network.

## Build

```bash
source /path/to/esp-idf-6.1/export.sh
python3 scripts/build.py wheelbot-s3-audio --name wheelbot-s3-audio \
  --language zh-CN --wake-word nihaoxiaozhi
idf.py flash monitor
```

Before motion tests, verify microphone level, speaker playback, wake-up, cloud
conversation, MCP discovery, and Mission Manager reachability separately.
