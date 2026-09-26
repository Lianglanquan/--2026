#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fishbot_root="${FISHBOT_ROOT:-/tmp/fishbot-laser-control-main}"
sdk_root="${IDF_PATH:-/data/工具/esp8266/ESP8266_RTOS_SDK}"
tool_root="/data/工具/esp8266/xtensa-lx106-elf/bin"
out_dir="${repo_root}/artifacts/fishbot_laser_build"
mkdir -p "${out_dir}"

export IDF_PATH="${sdk_root}"
export PATH="${repo_root}/tools:${tool_root}:${PATH}"
make -C "${fishbot_root}" -j2

esptool --chip ESP8266 merge-bin \
  -o "${out_dir}/fishbot_laser_control_4mb.bin" \
  --flash-mode dio --flash-size 4MB \
  0x0000 "${fishbot_root}/build/bootloader/bootloader.bin" \
  0x8000 "${fishbot_root}/build/partitions_singleapp.bin" \
  0x10000 "${fishbot_root}/build/uart2udp.bin"

sha256sum "${out_dir}/fishbot_laser_control_4mb.bin"
