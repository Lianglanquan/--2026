#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
hex_file="${1:-${repo_root}/build/c_board/wheelbot_cboard.hex}"
device="${JLINK_DEVICE:-STM32F407VG}"
if ! command -v JLinkExe >/dev/null 2>&1; then echo "JLinkExe not found" >&2; exit 127; fi
if [[ ! -f "${hex_file}" ]]; then echo "Firmware not found: ${hex_file}" >&2; exit 2; fi
tmp="$(mktemp)"
trap 'rm -f "${tmp}"' EXIT
printf 'r\nh\nloadfile %s\nr\ng\nq\n' "${hex_file}" >"${tmp}"
JLinkExe -device "${device}" -if SWD -speed "${JLINK_SPEED:-4000}" -autoconnect 1 -CommandFile "${tmp}"
