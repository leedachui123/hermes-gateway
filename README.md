# 🚀 Hermes Gateway

> Authentication gateway for [Hermes](https://github.com/SylarLi/hermes) agent dashboard — a lightweight reverse proxy with JWT-based authentication.

Hermes Gateway 位于用户和 Hermes 后端之间，提供统一的登录认证层。用户只需登录一次，后续所有请求都会自动携带认证令牌，由网关透明地代理到后端的 Hermes 服务。

---

## 📦 特性

- **JWT 认证** — 登录后签发 24 小时有效 Token，HTTP-only Cookie 存储
- **透明代理** — 认证通过后所有请求代理到 Hermes 后端（支持 GET/POST/PUT/DELETE 等）
- **多用户支持** — 通过 JSON 环境变量配置多用户，密码使用 bcrypt 哈希
- **优雅的错误处理** — 后端不可达返回 503，超时返回 504
- **Nginx 一键部署** — 提供 HTTPS 反代配置模板
- **uv 管理** — 使用 [uv](https://docs.astral.sh/uv/) 进行超快速依赖管理

---

## 🧱 架构

```
用户浏览器 ──► Hermes Gateway (8000) ──► Hermes Backend (9090)
                    │
                    ├── /login       → 登录页面
                    ├── /api/login   → 登录认证 → JWT Cookie
                    ├── /api/logout  → 登出
                    ├── /health      → 健康检查
                    └── /*           → 代理到 Hermes 后端（需认证）
```

网关默认监听 `0.0.0.0:8000`，后端地址默认为 `http://127.0.0.1:9090`。

---

## ⚡ 快速开始

### 前置条件

- Python >= 3.11
- [uv](https://docs.astral.sh/uv/#installation)（推荐）或 pip

### 1. 克隆并配置

```bash
git clone <repo-url>
cd hermes-gateway

# 创建配置文件
cp .env.example .env
# 编辑 .env，设置 GATEWAY_SECRET_KEY 和用户凭据
```

### 2. 安装依赖并启动

**使用 uv（推荐）：**

```bash
uv sync          # 自动创建 .venv 并安装依赖
uv run uvicorn main:app --reload
```

**或使用 pip：**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

**或使用启动脚本：**

```bash
./run.sh
```

### 3. 访问

打开浏览器访问 [http://localhost:8000](http://localhost:8000)，使用配置的用户名密码登录。

---

## 🔧 配置

所有配置通过环境变量进行（参见 [`.env.example`](.env.example)）：

| 变量 | 说明 | 默认值 |
|---|---|---|
| `GATEWAY_SECRET_KEY` | JWT 签名密钥（**必须修改**） | `change-me-in-production` |
| `GATEWAY_USERS` | 用户 JSON 数组（密码为 bcrypt 哈希） | — |
| `GATEWAY_USERNAME` | 单用户模式用户名 | `admin` |
| `GATEWAY_PASSWORD` | 单用户模式密码（明文） | — |
| `HERMES_BASE_URL` | Hermes 后端地址 | `http://127.0.0.1:9090` |
| `GATEWAY_HOST` | 监听地址 | `0.0.0.0` |
| `GATEWAY_PORT` | 监听端口 | `8000` |
| `GATEWAY_COOKIE_SECURE` | Cookie Secure 标志（HTTPS 时设为 `true`） | `false` |

### 多用户配置示例

```bash
GATEWAY_USERS=[{"username":"alice","password":"$2b$12$LJ3m4ys3Lk..."},{"username":"bob","password":"$2b$12$OtherHashHere..."}]
```

使用 [`hash_password.py`](hash_password.py) 生成 bcrypt 哈希：

```bash
uv run python hash_password.py mypassword
# $2b$12$ABCdefGHIJklMNOpqrsT...
```

---

## 🐳 Docker 部署

```bash
# 设置必要的环境变量
export GATEWAY_SECRET_KEY="your-strong-secret"
export GATEWAY_PASSWORD="your-admin-password"

# 启动（使用 docker compose）
docker compose up -d

# 查看日志
docker compose logs -f
```

> Docker 镜像使用 `ghcr.io/astral-sh/uv` 安装依赖，构建速度比 pip 快 10-100 倍。

### 单独构建

```bash
docker build -t hermes-gateway .
docker run -d \
  -p 8000:8000 \
  -e GATEWAY_SECRET_KEY=your-secret \
  -e GATEWAY_PASSWORD=your-password \
  -e HERMES_BASE_URL=http://host.docker.internal:9090 \
  hermes-gateway
```

---

## 🔒 HTTPS + Nginx

项目提供 [nginx 配置模板](nginx/hermes.conf) 用于生产部署：

```bash
# 1. 生成自签证书（或使用正式证书）
openssl req -x509 -newkey rsa:4096 -keyout hermes.key \
  -out hermes.crt -days 365 -nodes -subj "/CN=<服务器IP>"

# 2. 放置证书和配置
sudo cp hermes.crt hermes.key /etc/nginx/ssl/
sudo cp nginx/hermes.conf /etc/nginx/conf.d/

# 3. 重启 nginx
sudo nginx -t && sudo systemctl restart nginx
```

---

## 📂 项目结构

```
hermes-gateway/
├── main.py              # FastAPI 应用入口、路由、中间件
├── auth.py              # JWT 签发/验证、用户认证
├── proxy.py             # 反向代理逻辑
├── hash_password.py     # bcrypt 密码哈希工具
├── templates/
│   └── login.html       # 登录页面模板
├── nginx/
│   └── hermes.conf      # Nginx HTTPS 反代配置
├── pyproject.toml       # 项目元数据与依赖（uv）
├── uv.lock              # 依赖锁定文件
├── requirements.txt     # pip 兼容依赖列表
├── .env.example         # 环境变量模板
├── Dockerfile           # Docker 构建文件
├── docker-compose.yml   # Docker Compose 一键部署
└── run.sh               # 本地启动脚本
```

---

## 🛠 开发说明

```bash
# 启动开发服务器（热重载）
uv run uvicorn main:app --reload --port 8000

# 添加新依赖
uv add <package>

# 更新依赖
uv sync --upgrade

# 检查依赖一致性
uv lock --check
```

### 测试认证流程

```bash
# 启动服务
uv run uvicorn main:app --port 8000 &

# 健康检查
curl http://localhost:8000/health

# 登录（获取 JWT Cookie）
curl -c cookies.txt -X POST http://localhost:8000/api/login \
  -d "username=admin&password=admin"

# 访问受保护的代理路径（自动携带 Cookie）
curl -b cookies.txt http://localhost:8000/api/some-endpoint
```

---

## 📄 License

MIT
