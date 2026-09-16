#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
firmware_dir="$repo_root/firmware/esp32_s3"
build_dir="${WHEELBOT_ESP32_BUILD_DIR:-/tmp/wheelbot-xiaozhi-build}"

if [[ "$build_dir" != /tmp/* ]] || [[ "$build_dir" == *..* ]] ||
    ! LC_ALL=C grep -q '^[ -~]*$' <<<"$build_dir"; then
    echo "WHEELBOT_ESP32_BUILD_DIR must be an ASCII path below /tmp: $build_dir" >&2
    exit 2
fi

# shellcheck disable=SC1091
source "$repo_root/tools/esp32_idf_env.sh" >/dev/null

idf_version="$(idf.py --version)"
if [[ "$idf_version" != "ESP-IDF v6.1"* ]]; then
    echo "ESP-IDF 6.1 is required; active version: $idf_version" >&2
    exit 2
fi

project_build="$firmware_dir/build"
if [[ -L "$project_build" ]]; then
    if [[ "$(readlink -- "$project_build")" != "$build_dir" ]]; then
        echo "Refusing to replace unexpected build symlink: $project_build" >&2
        exit 2
    fi
    rm -- "$project_build"
elif [[ -e "$project_build" ]]; then
    rm -rf -- "$project_build"
fi
rm -rf -- "$build_dir"
mkdir -p -- "$build_dir"
ln -s -- "$build_dir" "$project_build"

cleanup_project_build() {
    if [[ -L "$project_build" ]] && [[ "$(readlink -- "$project_build")" == "$build_dir" ]]; then
        rm -- "$project_build"
    fi
}
trap cleanup_project_build EXIT

cd "$firmware_dir"
python3 scripts/build.py wheelbot-s3-audio \
    --config config.production.json \
    --name wheelbot-s3-audio \
    --language zh-CN
