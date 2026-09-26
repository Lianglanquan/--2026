#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if ! command -v idf.py >/dev/null 2>&1; then
    idf_root="${IDF_PATH:-/data/esp/esp-idf}"
    if [[ -f "$idf_root/export.sh" ]]; then
        if [[ -z "${IDF_TOOLS_PATH:-}" && -d /data/esp/.espressif ]]; then
            export IDF_TOOLS_PATH=/data/esp/.espressif
        fi
        export IDF_PATH="$idf_root"
        # shellcheck disable=SC1090
        source "$idf_root/export.sh" >/dev/null
    fi
fi
if ! command -v idf.py >/dev/null 2>&1; then
    echo "idf.py not found; install ESP-IDF or set IDF_PATH to its directory." >&2
    exit 127
fi

cd "$repo_root/firmware/esp32_s3"
python3 scripts/build.py wheelbot-s3-audio --name wheelbot-s3-audio \
    --language "${WHEELBOT_XIAOZHI_LANGUAGE:-zh-CN}" \
    --wake-word "${WHEELBOT_XIAOZHI_WAKE_WORD:-nihaoxiaozhi}"
