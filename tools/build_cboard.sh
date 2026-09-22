#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
build_dir="${repo_root}/build/c_board"
if [[ -f "${build_dir}/CMakeCache.txt" ]] && ! rg -q 'CMAKE_C_COMPILER:FILEPATH=.*/arm-none-eabi-gcc' "${build_dir}/CMakeCache.txt"; then
  cmake -E remove_directory "${build_dir}"
fi
cmake -S "${repo_root}/firmware/c_board" -B "${build_dir}" -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE="${repo_root}/firmware/c_board/cmake/toolchain-arm-none-eabi.cmake" "$@"
cmake --build "${build_dir}"
