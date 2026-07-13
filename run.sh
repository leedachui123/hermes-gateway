#!/usr/bin/env bash
set -euo pipefail

# Hermes Gateway 启动脚本（非 Docker 方式）
# 需要 Python 3.10+ 和 pip

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 加载 .env 文件
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

# 安装依赖
pip install -q -r requirements.txt

# 启动
exec uvicorn main:app --host "${GATEWAY_HOST:-0.0.0.0}" --port "${GATEWAY_PORT:-8000}"
