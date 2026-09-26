#!/usr/bin/env bash
# WheelBot 代码同步：本机 -> 树莓派
# 源码以 Git 为唯一来源。本机提交后执行本脚本更新树莓派。
# 日常同步只允许 Git：本机提交后，Pi 从同一个 Git remote 拉取。
# 首次引导请按 docs/remote_development.md 配置 Pi 仓库和 remote。
set -euo pipefail

PI_HOST="${PI_HOST:-wheelbot-pi}"
PI_PATH="${PI_PATH:-/home/fool/wheelbot}"
LOCAL_REPO="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> 检查树莓派 Git 仓库和 remote"
REMOTE_URL=$(ssh "$PI_HOST" "cd '$PI_PATH' 2>/dev/null && git remote get-url origin 2>/dev/null || true")
if [ -z "$REMOTE_URL" ]; then
    echo "错误：${PI_HOST}:${PI_PATH} 尚未配置 Git remote。" >&2
    echo "请先按 docs/remote_development.md 完成一次性 Git 仓库引导；本脚本不再用 rsync 作为日常同步。" >&2
    exit 1
fi

echo "==> Pi remote: $REMOTE_URL"
ssh "$PI_HOST" "cd '$PI_PATH' && git pull --ff-only"

echo "==> 同步完成"
ssh "$PI_HOST" "cd '$PI_PATH' && git log --oneline -1"
