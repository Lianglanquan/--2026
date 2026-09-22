#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
build_dir="${WHEELBOT_ESP32_BUILD_DIR:-/tmp/wheelbot-esp32-build}"

cmake -S "$repo_root/firmware/esp32_s3" -B "$build_dir" -DWHEELBOT_BUILD_TESTS=ON
cmake --build "$build_dir"
ctest --test-dir "$build_dir" --output-on-failure

cc -std=c11 -Wall -Wextra -Werror \
    -I"$repo_root/firmware/c_board/communication" \
    "$repo_root/tests/esp32_s3/test_cboard_uart_receiver.c" \
    "$repo_root/firmware/c_board/communication/uart_robot_protocol.c" \
    "$repo_root/firmware/c_board/communication/robot_protocol.c" \
    -o "$build_dir/test_cboard_uart_receiver"
"$build_dir/test_cboard_uart_receiver"

cc -std=c11 -Wall -Wextra -Werror \
    -I"$repo_root/firmware/c_board/communication" \
    "$repo_root/tests/unit/test_battery_protocol.c" \
    "$repo_root/firmware/c_board/communication/robot_protocol.c" \
    -lm -o "$build_dir/test_battery_protocol"
"$build_dir/test_battery_protocol"
