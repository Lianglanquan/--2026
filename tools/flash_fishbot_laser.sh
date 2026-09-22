#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
image="${1:-${repo_root}/artifacts/fishbot_laser_build/fishbot_laser_control_4mb.bin}"
port="${ESPPORT:-/dev/ttyUSB0}"

[[ -f "${image}" ]] || { echo "Firmware not found: ${image}" >&2; exit 2; }
[[ -e "${port}" ]] || { echo "Serial port not found: ${port}" >&2; exit 3; }

echo "Refusing to flash unless the FishBot board has been identified as ESP8266 with 4MB flash."
esptool --chip ESP8266 --port "${port}" flash-id
esptool --chip ESP8266 --port "${port}" write-flash --flash-mode dio --flash-size 4MB 0x0000 "${image}"
