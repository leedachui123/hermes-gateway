import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from auth import (
    authenticate,
    count_admins,
    create_access_token,
    create_user,
    decode_access_token,
    delete_user,
    get_all_users,
    get_user_by_id,
    get_user_by_username,
    init_db,
    pwd_context,
    update_password,
    update_user,
)
from proxy import HERMES_BASE_URL, proxy_request

# ---------- config ----------
COOKIE_NAME = "hermes_token"
COOKIE_MAX_AGE = 86400  # 24h

PUBLIC_PATHS = {"/login", "/health", "/api/logout"}
PUBLIC_PREFIXES = {"/api/login"}

templates = Jinja2Templates(directory="templates")


# ---------- lifespan ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    app.state.httpx_client = httpx.AsyncClient(
        base_url=HERMES_BASE_URL, timeout=60.0, follow_redirects=False, trust_env=False
    )
    yield
    await app.state.httpx_client.aclose()


# ---------- app ----------
app = FastAPI(
    title="Hermes Gateway",
    version="0.1.0",
    description="Authentication gateway for Hermes agent dashboard",
    lifespan=lifespan,
)


# ---------- auth middleware ----------
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path.rstrip("/") or "/"

    # Allow public paths through
    if path in PUBLIC_PATHS or any(path.startswith(p) for p in PUBLIC_PREFIXES):
        return await call_next(request)

    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return RedirectResponse(url="/login", status_code=302)

    payload = decode_access_token(token)
    if not payload:
        resp = RedirectResponse(url="/login", status_code=302)
        resp.delete_cookie(COOKIE_NAME, path="/")
        return resp

    request.state.username = payload.get("sub")
    request.state.role = payload.get("role", "user")
    return await call_next(request)


# ---------- helpers ----------
def _require_admin(request: Request):
    """Raise 403 if the current user is not an admin."""
    if getattr(request.state, "role", None) != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


def _cookie_settings():
    return {
        "httponly": True,
        "samesite": "lax",
        "secure": os.environ.get("GATEWAY_COOKIE_SECURE", "").lower()
        in ("1", "true", "yes"),
        "max_age": COOKIE_MAX_AGE,
    }


# ---------- login / logout ----------
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = None):
    return templates.TemplateResponse(request, "login.html", {"error": error})


@app.post("/api/login")
async def login_action(request: Request):
    form = await request.form()
    username = (form.get("username") or "").strip()
    password = form.get("password") or ""

    if not username or not password:
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Username and password are required"},
            status_code=422,
        )

    user = authenticate(username, password)
    if user:
        token = create_access_token(user["username"], user["role"])
        resp = RedirectResponse(url="/", status_code=302)
        resp.set_cookie(
            key=COOKIE_NAME, value=token, **_cookie_settings()
        )
        return resp

    return templates.TemplateResponse(
        request,
        "login.html",
        {"error": "Invalid username or password"},
        status_code=401,
    )


@app.post("/api/logout")
async def logout():
    resp = RedirectResponse(url="/login", status_code=302)
    resp.delete_cookie(COOKIE_NAME, path="/")
    return resp


@app.get("/health")
async def health():
    return {"status": "ok", "service": "hermes-gateway"}


# ---------- admin page ----------
@app.get("/admin", response_class=HTMLResponse)
@app.get("/admin/", response_class=HTMLResponse)
async def admin_index(request: Request):
    """Redirect /admin to the user management page."""
    _require_admin(request)
    return RedirectResponse(url="/admin/users", status_code=302)


@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users_page(request: Request):
    role = getattr(request.state, "role", None)
    if role != "admin":
        return HTMLResponse(
            "<h1>403 Forbidden</h1><p>Admin access required.</p>",
            status_code=403,
        )
    return templates.TemplateResponse(
        request,
        "admin_users.html",
        {
            "username": request.state.username,
            "role": role,
        },
    )


# ---------- admin API — user management ----------
@app.get("/api/admin/users")
async def api_list_users(request: Request):
    _require_admin(request)
    return {"users": get_all_users()}


@app.post("/api/admin/users", status_code=201)
async def api_create_user(request: Request):
    _require_admin(request)
    body = await request.json()
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    role = body.get("role", "user")

    # Validation
    if not username or not password:
        raise HTTPException(status_code=422, detail="username and password are required")
    if len(password) < 6:
        raise HTTPException(status_code=422, detail="Password must be at least 6 characters")
    if role not in ("admin", "user"):
        raise HTTPException(status_code=422, detail="Role must be 'admin' or 'user'")
    if get_user_by_username(username):
        raise HTTPException(status_code=409, detail="Username already exists")

    user = create_user(username, password, role)
    return {"user": user}


@app.put("/api/admin/users/{user_id}")
async def api_update_user(request: Request, user_id: int):
    _require_admin(request)
    body = await request.json()

    # Check user exists
    existing = get_user_by_id(user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate fields
    username = body.get("username")
    if username is not None:
        username = username.strip()
        if not username:
            raise HTTPException(status_code=422, detail="Username cannot be empty")
        # Check for duplicates (excluding self)
        dup = get_user_by_username(username)
        if dup and dup["id"] != user_id:
            raise HTTPException(status_code=409, detail="Username already exists")

    role = body.get("role")
    if role is not None and role not in ("admin", "user"):
        raise HTTPException(status_code=422, detail="Role must be 'admin' or 'user'")

    is_active = body.get("is_active")
    if is_active is not None:
        is_active = bool(is_active)

    user = update_user(
        user_id,
        username=username,
        role=role,
        is_active=is_active,
    )
    return {"user": user}


@app.delete("/api/admin/users/{user_id}")
async def api_delete_user(request: Request, user_id: int):
    _require_admin(request)

    # Cannot delete yourself
    current = get_user_by_username(request.state.username)
    if current and current["id"] == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    # Cannot delete the last admin
    target = get_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target["role"] == "admin" and count_admins() <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the last admin")

    delete_user(user_id)
    return {"message": "User deleted"}


@app.post("/api/admin/users/{user_id}/reset-password")
async def api_reset_password(request: Request, user_id: int):
    _require_admin(request)

    target = get_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    body = await request.json()
    new_password = body.get("password") or ""
    if len(new_password) < 6:
        raise HTTPException(status_code=422, detail="Password must be at least 6 characters")

    update_password(user_id, new_password)
    return {"message": "Password updated"}


# ---------- self-service ----------
@app.get("/api/me")
async def api_me(request: Request):
    return {
        "username": request.state.username,
        "role": request.state.role,
    }


@app.put("/api/me/password")
async def api_change_own_password(request: Request):
    body = await request.json()
    old_password = body.get("old_password") or ""
    new_password = body.get("new_password") or ""

    if not old_password or not new_password:
        raise HTTPException(status_code=422, detail="old_password and new_password are required")
    if len(new_password) < 6:
        raise HTTPException(status_code=422, detail="New password must be at least 6 characters")

    # Verify current password
    user = get_user_by_username(request.state.username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not pwd_context.verify(old_password, user["password"]):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    update_password(user["id"], new_password)
    return {"message": "Password updated"}


# ---------- catch-all proxy ----------
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def catch_all(request: Request, path: str = ""):
    client: httpx.AsyncClient = request.app.state.httpx_client
    target = f"/{path}" if path else "/"
    return await proxy_request(client, request, target)
