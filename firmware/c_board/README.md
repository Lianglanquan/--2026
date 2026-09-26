# C Board Firmware

The CMake target reproduces the DJI `20.standard_robot` project with
`arm-none-eabi-gcc`, Ninja, the official STM32 HAL/CMSIS sources, and the
official FreeRTOS Cortex-M4 port. Build from the repository root with:

```sh
cmake -S firmware/c_board -B build/c_board -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE=firmware/c_board/cmake/toolchain-arm-none-eabi.cmake
cmake --build build/c_board
```

The generated artifacts are `wheelbot_cboard.elf`, `.bin`, and `.hex`.
Use `tools/build_cboard.sh` and `tools/flash_cboard.sh` for the reproducible
build and J-Link SWD programming flow.
