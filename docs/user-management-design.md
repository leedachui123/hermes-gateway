# 用户管理功能设计文档

> 为 Hermes Gateway 增加运行时用户管理能力，支持管理员通过 Web 界面添加/编辑/删除用户。

---

## 1. 背景与目标

### 现状

当前所有用户通过环境变量 `GATEWAY_USERS`（JSON 数组）或 `GATEWAY_USERNAME`/`GATEWAY_PASSWORD` 在启动时配置，用户信息缓存在全局变量 `_users` 中，**运行时无法修改**。添加新用户需要重启服务。

### 目标

1. 管理员可以通过 Web 界面管理用户（增删改查）
2. 用户信息持久化存储，重启不丢失
3. 兼容现有的环境变量配置方式，首次启动自动迁移
4. 区分管理员和普通用户角色
5. 支持普通用户自行修改密码
6. 零额外依赖（使用 Python 内置组件）

---

## 2. 存储设计

### 方案选择：SQLite

| 方案 | 优点 | 缺点 |
|------|------|------|
| **SQLite**（选用） | 内置 `sqlite3`，零依赖；并发安全；查询灵活 | 需处理首次建表 |
| JSON 文件 | 实现简单 | 并发写入有竞争风险；不适合频繁修改 |
| YAML | 人工编辑友好 | 需额外依赖 |

### 表结构

```sql
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT    NOT NULL UNIQUE,
    password    TEXT    NOT NULL,
    role        TEXT    NOT NULL DEFAULT 'user' CHECK(role IN ('admin', 'user')),
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
```

字段说明：
- `password` — bcrypt 哈希值
- `role` — `admin` 或 `user`
- `is_active` — 是否启用（禁用的用户无法登录）
- `created_at` / `updated_at` — ISO-8601 时间戳

### 数据库路径

默认路径：`data/users.db`（相对于项目根目录）
- 可通过环境变量 `GATEWAY_DB_PATH` 自定义
- 首次运行自动创建目录和表

---

## 3. 角色与权限模型

### 角色定义

| 角色 | 权限 |
|------|------|
| `admin` | 所有操作：用户管理、查看所有用户、删除用户 |
| `user` | 仅登录代理、修改自己的密码 |

### 权限矩阵

| 操作 | admin | user |
|------|-------|------|
| 登录代理 | ✅ | ✅ |
| 查看用户列表 | ✅ | ❌ |
| 创建用户 | ✅ | ❌ |
| 编辑用户 | ✅ | ❌ |
| 删除用户（不能删自己） | ✅ | ❌ |
| 重置他人密码 | ✅ | ❌ |
| 修改自己的密码 | ✅ | ✅ |

### 策略说明

- **首个用户自动为 admin**：首次启动时，从环境变量导入的用户中，第一个用户自动获得 `admin` 角色，其余为 `user`。
- **至少保留一个 admin**：删除用户时，如果目标用户是最后一个 admin，操作被拒绝。
- **admin 不能删除自己**：防止误操作导致无管理员可用。

---

## 4. API 设计

### 路由概览

```
前缀：/api/admin/users  —— 仅 admin 角色可访问
前缀：/api/me            —— 任意登录用户可访问
```

### 详细接口

#### 4.1 获取用户列表

```
GET /api/admin/users
Query: ?q=<搜索关键词（可选，匹配用户名）>
Response 200:
{
  "users": [
    {
      "id": 1,
      "username": "admin",
      "role": "admin",
      "is_active": true,
      "created_at": "2026-07-16T10:00:00",
      "updated_at": "2026-07-16T10:00:00"
    }
  ]
}
```

#### 4.2 创建用户

```
POST /api/admin/users
Request Body:
{
  "username": "alice",
  "password": "plaintext-password",
  "role": "user"          // 可选，默认 "user"
}
Response 201:
{ "id": 2, "username": "alice", "role": "user", "is_active": true, ... }

Error 409: { "error": "Username already exists" }
Error 422: { "error": "Validation error details" }
```

密码在服务端用 bcrypt 哈希后存储，不返回明文。

#### 4.3 更新用户

```
PUT /api/admin/users/{user_id}
Request Body (全部可选):
{
  "username": "alice_new",
  "role": "admin",
  "is_active": true
}
Response 200: { "id": 2, "username": "alice_new", "role": "admin", ... }

Error 404: { "error": "User not found" }
Error 409: { "error": "Username already exists" }
```

> 注意：此接口不修改密码。修改密码有独立接口。

#### 4.4 删除用户

```
DELETE /api/admin/users/{user_id}
Response 200: { "message": "User deleted" }

Error 400: { "error": "Cannot delete yourself" }
Error 400: { "error": "Cannot delete the last admin" }
Error 404: { "error": "User not found" }
```

#### 4.5 重置用户密码

```
POST /api/admin/users/{user_id}/reset-password
Request Body:
{ "password": "new-plaintext-password" }
Response 200: { "message": "Password updated" }
```

#### 4.6 获取当前用户信息

```
GET /api/me
Response 200:
{ "id": 1, "username": "admin", "role": "admin" }
```

#### 4.7 修改自己的密码

```
PUT /api/me/password
Request Body:
{
  "old_password": "current-password",
  "new_password": "new-password"
}
Response 200: { "message": "Password updated" }

Error 401: { "error": "Current password is incorrect" }
Error 422: { "error": "New password is too short" }
```

---

## 5. 页面设计

### 5.1 布局变化

引入一个简单的导航栏，放在所有页面的顶部：

```
┌─────────────────────────────────────────────────┐
│  🔐 Hermes Gateway   仪表盘  用户管理  [admin] │  ← 新导航栏
├─────────────────────────────────────────────────┤
│                                                   │
│  (页面内容)                                        │
│                                                   │
└─────────────────────────────────────────────────┘
```

- **仪表盘** — 当前登录后的页面（目前是直接代理到 Hermes 后端，保持不变）
- **用户管理** — 仅 admin 角色可见
- **右上角** — 显示当前用户名 + 登出按钮

### 5.2 用户管理页面 (`/admin/users`)

```
┌──────────────────────────────────────────────────────────────┐
│  用户管理                                     [+ 添加用户]   │
│                                                              │
│  ┌──────┬──────────┬──────────┬──────────┬──────────┐        │
│  │  #   │ 用户名   │ 角色     │ 状态     │ 操作     │        │
│  ├──────┼──────────┼──────────┼──────────┼──────────┤        │
│  │  1   │ admin    │ 管理员   │ 活跃    │ 编辑     │        │
│  │  2   │ alice    │ 用户     │ 活跃    │ 编辑 删除│        │
│  │  3   │ bob      │ 用户     │ 禁用    │ 编辑 删除│        │
│  └──────┴──────────┴──────────┴──────────┴──────────┘        │
└──────────────────────────────────────────────────────────────┘
```

### 5.3 添加/编辑用户弹窗

```
┌──────────────────────────────┐
│  添加用户                     │
│                              │
│  用户名:  [_______________]  │
│  密码:    [_______________]  │
│  角色:    [用户 ▼]           │
│                              │
│  [取消]          [确认添加]   │
└──────────────────────────────┘
```

### 5.4 实现方式

- 服务端渲染 HTML（Jinja2 模板）
- 页面交互使用简单的原生 JavaScript（无前端框架依赖）
- CSS 风格与现有登录页面保持一致

#### 模板文件

| 文件 | 说明 |
|------|------|
| `templates/base.html` | 基础布局模板（导航栏 + 内容区） |
| `templates/admin_users.html` | 用户管理页面 |
| `templates/login.html` | 登录页（保持不变，或继承 base.html） |

---

## 6. 迁移策略

### 首次启动流程

```
服务启动
    │
    ▼
检查 SQLite 是否有用户记录
    │
    ├── 有用户 ──► 正常加载
    │
    └── 无用户 ──► 从环境变量导入
                   │
                   ├── 有 GATEWAY_USERS ──► 导入所有用户，第一个为 admin
                   │
                   └── 有 GATEWAY_USERNAME/PASSWORD ──► 导入为 admin
                       │
                       └── 都没有 ──► 创建默认 admin/admin 用户（admin 角色）
```

### 迁移后的行为

- 启动后用户来源为 SQLite，环境变量不再生效
- 环境变量仅在**首次启动且数据库为空**时作为初始数据源
- 如需重新导入，删除 `data/users.db` 后重启即可
- 管理员可以在 UI 中自主添加/修改用户

### 关于 GATEWAY_USERS 兼容性

环境变量 `GATEWAY_USERS` **仅用于首次建库**。建库后更改环境变量不会影响已有用户。这是有意为之——运行时用户管理不再依赖环境变量。

---

## 7. 文件变更清单

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `auth.py` | 修改 | 重构为 SQLite 存储，添加角色支持 |
| `main.py` | 修改 | 增加导航栏上下文，添加 admin 路由 |
| `templates/base.html` | 新增 | 基础布局 + 导航栏 |
| `templates/admin_users.html` | 新增 | 用户管理页面 |
| `templates/login.html` | 修改 | 继承 base.html 或增加导航 |
| `data/` | 新增 | 数据库目录（自动创建） |
| `.env.example` | 修改 | 增加 `GATEWAY_DB_PATH` 说明 |

### 无需修改的文件

- `proxy.py` — 代理逻辑不变
- `pyproject.toml` — 零额外依赖
- `Dockerfile` — SQLite 文件在内，挂载 volume 即可持久化

---

## 8. 安全注意事项

1. **密码传输**：密码通过表单/JSON 明文传输，在生产环境必须配合 HTTPS（已有 Nginx + HTTPS 方案）
2. **SQL 注入防护**：使用参数化查询（`?` 占位符），禁止字符串拼接 SQL
3. **密码强度**：服务端校验密码长度 ≥ 6 位
4. **管理员保护**：无法删除最后一个 admin；admin 不能删除自己
5. **Token 角色注入**：登录时 `create_access_token` 写入用户名**和角色**，中间件可从 token 中读取角色，无需查库
6. **并发安全**：SQLite 写操作使用 `exclusive` 事务模式

---

## 9. 环境变量变更

| 变量 | 说明 | 默认值 | 是否新增 |
|------|------|--------|----------|
| `GATEWAY_DB_PATH` | SQLite 数据库路径 | `data/users.db` | ✅ 新增 |

其余环境变量不变。

---

## 10. 后续可能的扩展

- 用户分组（Group）
- API Token 管理（替代 Cookie 认证）
- 登录日志审计
- LDAP/OAuth 集成
- 密码过期策略

---

> **文档版本**: v1.0
> **更新日期**: 2026-07-16
