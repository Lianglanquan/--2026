#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
firmware_dir="$repo_root/firmware/esp32_s3"
build_dir="${WHEELBOT_ESP32_BUILD_DIR:-/tmp/wheelbot-xiaozhi-build}"
port="${WHEELBOT_ESP32_PORT:-/dev/ttyACM0}"

if [[ "$build_dir" != /tmp/* ]] || [[ "$build_dir" == *..* ]] ||
    ! LC_ALL=C grep -q '^[ -~]*$' <<<"$build_dir"; then
    echo "WHEELBOT_ESP32_BUILD_DIR must be an ASCII path below /tmp: $build_dir" >&2
    exit 2
fi
if [[ ! -f "$build_dir/xiaozhi.bin" ]]; then
    echo "Firmware image not found; run tools/build_esp32_s3.sh first: $build_dir/xiaozhi.bin" >&2
    exit 2
fi

# shellcheck disable=SC1091
source "$repo_root/tools/esp32_idf_env.sh" >/dev/null

cd "$build_dir"
python -m esptool --chip esp32s3 --port "$port" --baud 460800 \
    --before default-reset --after hard-reset write-flash "@flash_args"

if [[ "${WHEELBOT_ESP32_MONITOR:-1}" == "1" ]]; then
    exec idf.py -B "$build_dir" -p "$port" monitor
fi
