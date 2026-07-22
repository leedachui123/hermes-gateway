#!/usr/bin/env bash
# ============================================================================
# Hermes Gateway — Docker 镜像构建与推送脚本
# 用法:
#   ./cicd/build-and-push.sh                    # 从 git tag 自动获取版本
#   ./cicd/build-and-push.sh v1.1.5             # 手动指定版本
#   ./cicd/build-and-push.sh --registry ghcr.io # 指定镜像仓库
# ============================================================================
set -euo pipefail

# ---- 配置（可覆盖的环境变量）----
REGISTRY="${REGISTRY:-ghcr.io}"
IMAGE_NAME="${IMAGE_NAME:-hermes-gateway}"
PLATFORMS="${PLATFORMS:-linux/amd64,linux/arm64}"
PUSH="${PUSH:-true}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

# ---- 获取版本号 ----
if [ $# -ge 1 ] && [ -n "$1" ] && ! echo "$1" | grep -q '^--'; then
    VERSION="$1"
    shift
else
    # 从最近的 git tag 提取（去掉前导 v）
    VERSION="$(git describe --tags --abbrev=0 2>/dev/null | sed 's/^v//' || echo 'latest')"
fi

# ---- 解析其它参数 ----
while [ $# -gt 0 ]; do
    case "$1" in
        --registry) REGISTRY="$2"; shift 2 ;;
        --no-push)  PUSH="false"; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ---- 推断完整镜像标签 ----
if [ -n "$REGISTRY" ]; then
    FULL_IMAGE_TAG="${REGISTRY}/${IMAGE_NAME}:${VERSION}"
    LATEST_TAG="${REGISTRY}/${IMAGE_NAME}:latest"
else
    FULL_IMAGE_TAG="${IMAGE_NAME}:${VERSION}"
    LATEST_TAG="${IMAGE_NAME}:latest"
fi

echo "=========================================="
echo "  Hermes Gateway 镜像构建"
echo "  版本:     ${VERSION}"
echo "  镜像:     ${FULL_IMAGE_TAG}"
echo "  平台:     ${PLATFORMS}"
echo "  推送:     ${PUSH}"
echo "=========================================="

# ---- 检查必要工具 ----
if ! command -v docker &>/dev/null; then
    echo "❌ docker 未安装"
    exit 1
fi

# ---- 登录检查（支持私有仓库）----
if [ "$PUSH" = "true" ] && [ -n "$REGISTRY" ]; then
    echo ""
    echo "🔑 检查仓库登录状态..."
    # 优先使用环境变量中的凭证
    if [ -n "${DOCKER_REGISTRY_USERNAME:-}" ] && [ -n "${DOCKER_REGISTRY_PASSWORD:-}" ]; then
        echo "$DOCKER_REGISTRY_PASSWORD" | docker login "$REGISTRY" \
            -u "$DOCKER_REGISTRY_USERNAME" --password-stdin 2>/dev/null && \
            echo "   ✅ 已登录 $REGISTRY" || \
            echo "   ⚠  DOCKER_REGISTRY_USERNAME/PASSWORD 登录失败"
    elif [ -n "${GITHUB_TOKEN:-}" ]; then
        echo "$GITHUB_TOKEN" | docker login "$REGISTRY" -u "${GITHUB_USER:-$IMAGE_NAME}" --password-stdin 2>/dev/null && \
            echo "   ✅ 已通过 GITHUB_TOKEN 登录" || \
            echo "   ⚠  GITHUB_TOKEN 登录失败，尝试已存在的 docker config..."
    else
        if docker system info 2>/dev/null | grep -q "Username"; then
            echo "   ✅ 使用已有的 docker config"
        else
            echo "   ⚠  未检测到 registry 登录凭证"
            echo "   请先执行: docker login $REGISTRY"
            echo "   或设置 DOCKER_REGISTRY_USERNAME / DOCKER_REGISTRY_PASSWORD"
            echo ""
            echo "   继续构建但不推送..."
            PUSH="false"
        fi
    fi
fi

# ---- 构建 ----
echo ""
echo "🏗️  构建镜像..."
BUILD_ARGS=(
    --file "$PROJECT_DIR/Dockerfile"
    --tag "$FULL_IMAGE_TAG"
    --tag "$LATEST_TAG"
)

# 只有 docker buildx 可用时才加 --platform
if docker buildx version &>/dev/null; then
    BUILD_ARGS+=(--platform "$PLATFORMS")
fi

if [ "$PUSH" = "true" ] && docker buildx version &>/dev/null; then
    BUILD_ARGS+=(--push)
else
    BUILD_ARGS+=(--load)
fi

docker buildx build "${BUILD_ARGS[@]}" "$PROJECT_DIR"

echo ""
echo "✅ 构建完成！"
echo "   镜像: ${FULL_IMAGE_TAG}"

if [ "$PUSH" = "true" ]; then
    # 单平台构建且没用 --push 时，手动推送
    if ! docker buildx version &>/dev/null || [ "${BUILD_ARGS[*]}" = "${BUILD_ARGS[*]%--push}" ]; then
        echo ""
        echo "📤 推送镜像..."
        docker push "$FULL_IMAGE_TAG"
        docker push "$LATEST_TAG"
        echo "   ✅ 推送完成"
    fi
    echo ""
    echo "📦 镜像地址:"
    echo "   ${FULL_IMAGE_TAG}"
    echo "   ${LATEST_TAG}"
else
    echo "   (未推送，使用 --no-push 或设置 PUSH=false)"
fi

echo ""
echo "🎉 完成!"
