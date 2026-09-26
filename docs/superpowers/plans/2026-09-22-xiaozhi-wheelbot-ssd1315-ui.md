# XiaoZhi WheelBot SSD1315 UI Implementation Plan

**Goal:** Make `xiaozhi-wheelbot` the single ESP32-S3 implementation with SSD1315 OLED, conversation-driven expressions, GPIO9/10/11 buttons, and the requested UART pin map.

**Architecture:** Keep XiaoZhi's LVGL/display abstraction, add a board-local SSD1315 `esp_lcd` panel driver using the SSD1315 page protocol, and render a small monochrome face canvas as the 128×64 UI. Map application state and LLM emotion callbacks to named face states; keep the legacy standalone firmware outside the source tree after archiving it.

**Tech Stack:** ESP-IDF 6.1, ESP-LCD I²C, LVGL 9, C/C++, existing wheelbot_control component, host C tests.

## Global Constraints

- SSD1315 is 128×64 I²C; GPIO41=SDA and GPIO42=SCL.
- The user's `0x78` is the 8-bit write address; ESP-IDF receives the 7-bit address `0x3C`.
- Audio pins remain GPIO4/5/6/7; UART is GPIO17 TX and GPIO18 RX; buttons are GPIO9/10/11.
- Do not delete C Board, ROS, simulation, or mechanical materials.
- Preserve a recoverable archive of the legacy standalone firmware before cleanup.

### Tasks

1. Add failing host checks for the pin contract and face-state mapping, then implement the board constants and pure face mapping.
2. Add and wire the board-local SSD1315 panel driver, I²C display setup, and button inputs.
3. Replace the 128×64 OLED layout with a compact black-background face UI and map XiaoZhi state/emotion events to the ten requested expressions.
4. Build the XiaoZhi ESP-IDF target and run the existing host tests plus static pin/driver checks.
5. Archive and remove only the legacy root `firmware/esp32_s3` directory, then document the single ESP32 mainline and verify no unrelated paths changed.
