#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# shellcheck disable=SC1091
source "$repo_root/tools/esp32_idf_env.sh" >/dev/null

idf_version="$(idf.py --version)"
if [[ "$idf_version" != "ESP-IDF v6.1"* ]]; then
    echo "ESP-IDF 6.1 is required; active version: $idf_version" >&2
    exit 2
fi

cd "$repo_root/firmware/esp32_s3"
python scripts/build.py wheelbot-s3-audio
