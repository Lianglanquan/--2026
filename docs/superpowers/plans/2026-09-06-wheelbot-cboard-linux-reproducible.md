# WheelBot C Board Linux Reproducible Engineering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reproduce the DJI RoboMaster C Board `20.standard_robot` firmware with Linux-hosted GCC/CMake/Ninja/J-Link tooling while adding only thin QD4310, FashionStar, USB test, and ROS2 bridge adapters.

**Architecture:** Vendor code is kept under `firmware/c_board/vendor/` with source and hardware configuration preserved. CMake wraps the vendor build inputs; adapters in `drivers/`, `communication/`, and `port/` depend on existing HAL interfaces without replacing HAL, CMSIS, FreeRTOS, BMI088, INS, or USB implementations.

**Tech Stack:** arm-none-eabi-gcc, CMake, Ninja, J-Link Commander, GDB, STM32F4 HAL/CMSIS/FreeRTOS, ROS 2 Jazzy, Python, pyserial, colcon.

**Spec:** User-provided WheelBot C板 Linux 可复现工程 requirements in the conversation.

## Global Constraints

- Reuse official DJI and FashionStar implementations; do not rewrite vendor drivers or business logic.
- Preserve STM32 HAL, CMSIS, FreeRTOS, BMI088, INS, CAN/UART/USB BSP, interrupts, DMA, clocks, startup, and linker layout.
- CMake configure command: `cmake -S firmware/c_board -B build/c_board -G Ninja`.
- Build outputs: `wheelbot_cboard.elf`, `wheelbot_cboard.bin`, `wheelbot_cboard.hex`.
- QD4310 uses CAN1 at 1 Mbps and official protocol only.
- FashionStar uses C Board UART6 and official STM32F407 HAL SDK packet/control logic.
- First USB protocol is PING/PONG; no complex RobotState protocol in phase one.
- ROS2 scope is only `wheelbot_bridge`; no RL, Nav2, LiDAR, camera, ESP32, URDF, or balance controller.

### Task 1: Lock upstream sources and inventory vendor build inputs

**Files:**
- Create: `firmware/c_board/vendor/README.md`
- Create: `firmware/c_board/vendor/dji/`
- Create: `firmware/c_board/vendor/fashionstar/`
- Create: `docs/architecture/cboard-build-inputs.md`

- [ ] Clone the DJI and FashionStar repositories into the vendor paths at recorded commits.
- [ ] Copy or reference `20.standard_robot` and the listed DJI examples without modifying their implementation files.
- [ ] Record repository URLs, commit hashes, selected example paths, MCU, board, compiler assumptions, and license notes in `vendor/README.md`.
- [ ] Inventory Keil source lists, include paths, preprocessor defines, startup file, linker script, HAL/CMSIS/FreeRTOS roots, and document the mapping in `cboard-build-inputs.md`.
- [ ] Verify the inventory with `find`, `rg`, and the vendor project files before writing CMake.

### Task 2: Reproduce the official C Board build with CMake/Ninja

**Files:**
- Create: `firmware/c_board/CMakeLists.txt`
- Create: `firmware/c_board/cmake/toolchain-arm-none-eabi.cmake`
- Create: `firmware/c_board/port/build_config.h`
- Create: `tools/build_cboard.sh`
- Create: `firmware/c_board/README.md`

- [ ] Translate the inventoried Keil inputs into a CMake target named `wheelbot_cboard` without renaming vendor symbols or changing application logic.
- [ ] Configure `arm-none-eabi-gcc` flags for the exact STM32F4 CPU/FPU/ABI identified in the vendor project.
- [ ] Add the vendor startup and linker script unchanged; enable binary and Intel HEX post-build outputs.
- [ ] Make `tools/build_cboard.sh` run the exact configure and build commands with `set -euo pipefail`.
- [ ] Run `cmake -S firmware/c_board -B build/c_board -G Ninja` and `cmake --build build/c_board`.
- [ ] Confirm all three output files exist and use `arm-none-eabi-size` to record image size.

### Task 3: Add J-Link flash/debug tooling

**Files:**
- Create: `tools/flash_cboard.sh`
- Create: `tools/debug_cboard.sh`
- Create: `deploy/jlink/README.md`

- [ ] Make `flash_cboard.sh` validate J-Link tools and the generated HEX/BIN, then invoke J-Link Commander over SWD with the correct device and reset sequence.
- [ ] Make `debug_cboard.sh` launch `arm-none-eabi-gdb` with the ELF, remote target, reset/halt, and load/continue guidance without hardcoding a running server process.
- [ ] Document probe serial/device override environment variables and a dry-run command.
- [ ] Run shell syntax checks with `bash -n` and a dry-run path that does not touch hardware.

### Task 4: Add thin QD4310 CAN1 adapter

**Files:**
- Create: `firmware/c_board/drivers/qd4310/qd4310.h`
- Create: `firmware/c_board/drivers/qd4310/qd4310.c`
- Create: `firmware/c_board/drivers/qd4310/README.md`
- Create: `tests/unit/test_qd4310_codec.c`

- [ ] Extract the official QD4310 frame definitions and command semantics from the supplied manual/example, recording the source reference in the README.
- [ ] Implement only frame packing/unpacking and calls into the existing C Board HAL CAN1 send/receive path.
- [ ] Expose exactly `qd4310_enable`, `qd4310_disable`, `qd4310_set_current`, `qd4310_set_speed`, `qd4310_set_angle`, and `qd4310_get_state` with explicit node ID and state fields.
- [ ] Add codec tests for enable, current, speed, angle, state, and fault decoding using known official frames.
- [ ] Add the adapter target to CMake without introducing a replacement CAN abstraction.

### Task 5: Migrate FashionStar STM32F407 HAL SDK to UART6

**Files:**
- Create: `firmware/c_board/drivers/fashionstar/README.md`
- Create: `firmware/c_board/drivers/fashionstar/fashionstar_port.c`
- Create: `firmware/c_board/drivers/fashionstar/fashionstar_port.h`
- Modify: `firmware/c_board/CMakeLists.txt`

- [ ] Import the official `STM32F407/STM32F407_SDK(HAL)` sources unchanged under `vendor/fashionstar`.
- [ ] Implement only UART handle binding to the C Board UART6 handle and TX/RX callbacks using existing HAL APIs.
- [ ] Preserve official packet parser and control logic; expose ping, angle, and status calls through the port header.
- [ ] Add a compile-only integration target proving the SDK and port layer link together.
- [ ] Record any SDK assumptions and unsupported features in the README.

### Task 6: Verify USB PING/PONG and hardware acceptance hooks

**Files:**
- Create: `firmware/c_board/communication/usb_test_protocol.c`
- Create: `firmware/c_board/communication/usb_test_protocol.h`
- Create: `docs/verification/cboard-acceptance.md`
- Create: `tools/usb_ping.py`

- [ ] Reuse the official USB receive/transmit callbacks and add only a PING-to-PONG dispatch hook.
- [ ] Make `usb_ping.py` send a bounded test frame to a configurable Linux USB serial device and validate PONG.
- [ ] Document the ordered hardware checks: LED heartbeat, FreeRTOS scheduling, BMI088, gyro/accel, INS, CAN1, UART6, USB, QD4310, servo.
- [ ] Keep all checks runnable individually and record expected evidence without pretending hardware was tested in CI.

### Task 7: Create the minimal ROS2 `wheelbot_bridge`

**Files:**
- Create: `ros2/wheelbot_ws/src/wheelbot_bridge/package.xml`
- Create: `ros2/wheelbot_ws/src/wheelbot_bridge/setup.py`
- Create: `ros2/wheelbot_ws/src/wheelbot_bridge/wheelbot_bridge/bridge_node.py`
- Create: `ros2/wheelbot_ws/src/wheelbot_bridge/resource/wheelbot_bridge`
- Create: `ros2/wheelbot_ws/README.md`

- [ ] Implement a ROS2 node that opens a configurable USB serial device, sends PING at startup/on timer, validates PONG, and publishes a small diagnostic/status topic.
- [ ] Add clean shutdown, serial timeout, reconnect behavior, and parameterized device/baud/period values.
- [ ] Build with `colcon build --symlink-install` and run a parser-level test without requiring ROS hardware.
- [ ] Document Raspberry Pi Ubuntu 24.04 ARM64 setup commands for ROS2 Jazzy ros-base, colcon, rosdep, vcstool, pyserial, git, and cmake.

## Verification

Run host checks in order: `bash -n tools/*.sh`, CMake configure/build, ELF/BIN/HEX existence and size, QD4310 codec tests, FashionStar compile-only target, USB ping parser test, and ROS2 package build. Hardware-only claims must be marked pending until a connected C Board, J-Link, QD4310 ID1, and UC-01/servo produce evidence.
