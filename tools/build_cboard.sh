#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
build_dir="${repo_root}/build/c_board"
cmake -S "${repo_root}/firmware/c_board" -B "${build_dir}" -G Ninja "$@"
cmake --build "${build_dir}"
