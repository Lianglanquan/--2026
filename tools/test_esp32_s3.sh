#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
build_dir="${WHEELBOT_ESP32_BUILD_DIR:-/tmp/wheelbot-esp32-host-tests}"
component_dir="$repo_root/firmware/esp32_s3/local_components/wheelbot_control"
board_dir="$repo_root/firmware/esp32_s3/main/boards/wheelbot-s3-audio"

if ! grep -Eq 'REQUIRES[^\n]*esp_driver_gpio|esp_driver_gpio' \
    "$component_dir/CMakeLists.txt"; then
    echo "wheelbot_control must declare esp_driver_gpio because its public config includes driver/gpio.h" >&2
    exit 1
fi

python3 - "$board_dir" <<'PY'
import json
import pathlib
import re
import sys

board_dir = pathlib.Path(sys.argv[1])
config = json.loads((board_dir / "config.json").read_text(encoding="utf-8"))
assert config["type"] == "wheelbot-s3-audio"
assert config["target"] == "esp32s3"
assert config["builds"][0]["name"] == "wheelbot-s3-audio"

header = (board_dir / "config.h").read_text(encoding="utf-8")
expected = {
    "AUDIO_I2S_GPIO_BCLK": 4,
    "AUDIO_I2S_GPIO_WS": 5,
    "AUDIO_I2S_GPIO_DIN": 6,
    "AUDIO_I2S_GPIO_DOUT": 7,
}
for name, gpio in expected.items():
    assert re.search(rf"^#define\s+{name}\s+GPIO_NUM_{gpio}\s*$", header, re.MULTILINE), name
assert "AUDIO_I2S_METHOD_SIMPLEX" not in header
PY

cmake -S "$repo_root/tests/esp32_s3" -B "$build_dir" \
    -DWHEELBOT_COMPONENT_DIR="$component_dir"
cmake --build "$build_dir"
ctest --test-dir "$build_dir" --output-on-failure

cc -std=c11 -Wall -Wextra -Werror \
    -I"$repo_root/firmware/c_board/communication" \
    "$repo_root/tests/esp32_s3/test_cboard_uart_receiver.c" \
    "$repo_root/firmware/c_board/communication/uart_robot_protocol.c" \
    "$repo_root/firmware/c_board/communication/robot_protocol.c" \
    -o "$build_dir/test_cboard_uart_receiver"
"$build_dir/test_cboard_uart_receiver"
