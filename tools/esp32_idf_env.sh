#!/usr/bin/env bash

set -euo pipefail

export IDF_PATH="${WHEELBOT_IDF_PATH:-/data/esp/esp-idf-6.1}"
export IDF_TOOLS_PATH="${IDF_TOOLS_PATH:-/data/esp/.espressif}"

if [[ ! -f "$IDF_PATH/export.sh" ]]; then
    echo "ESP-IDF 6.1 export script not found: $IDF_PATH/export.sh" >&2
    return 1 2>/dev/null || exit 1
fi

# shellcheck disable=SC1090
source "$IDF_PATH/export.sh"
