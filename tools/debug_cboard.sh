#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
elf_file="${1:-${repo_root}/build/c_board/wheelbot_cboard.elf}"
if ! command -v arm-none-eabi-gdb >/dev/null 2>&1; then echo "arm-none-eabi-gdb not found; install the ARM GDB package" >&2; exit 127; fi
exec arm-none-eabi-gdb "${elf_file}"
