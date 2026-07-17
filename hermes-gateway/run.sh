#!/usr/bin/env bash
set -euo pipefail

# Hermes Gateway 启动脚本（非 Docker 方式）
# 需要 Python 3.11+ 和 uv (https://docs.astral.sh/uv/)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 加载 .env 文件
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

# 同步依赖（自动创建 .venv 并生成 uv.lock）
uv sync

# 启动（通过 uv run 在虚拟环境中执行）
exec uv run uvicorn main:app --host "${GATEWAY_HOST:-0.0.0.0}" --port "${GATEWAY_PORT:-8200}"
