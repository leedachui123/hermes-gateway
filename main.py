import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from auth import authenticate, create_access_token, decode_access_token
from proxy import HERMES_BASE_URL, proxy_request

# ---------- config ----------
COOKIE_SECURE = os.environ.get("GATEWAY_COOKIE_SECURE", "").lower() in ("1", "true", "yes")
COOKIE_NAME = "hermes_token"
COOKIE_MAX_AGE = 86400  # 24h

PUBLIC_PATHS = {"/login", "/health", "/api/logout"}
PUBLIC_PREFIXES = {"/api/login"}

templates = Jinja2Templates(directory="templates")


# ---------- lifespan ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
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
    return await call_next(request)


# ---------- routes ----------
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
            request, "login.html", {"error": "Username and password are required"},
            status_code=422,
        )

    if authenticate(username, password):
        # 验证 Hermes 后端连通性
        client: httpx.AsyncClient = request.app.state.httpx_client
        try:
            await client.get("/", timeout=5.0)
        except httpx.ConnectError:
            return templates.TemplateResponse(
                request, "login.html",
                {"error": "Hermes 后端无法连接，请确认服务已启动后重试"},
                status_code=503,
            )
        except httpx.TimeoutException:
            return templates.TemplateResponse(
                request, "login.html",
                {"error": "Hermes 后端响应超时，请稍后重试"},
                status_code=504,
            )

        token = create_access_token(username)
        resp = RedirectResponse(url="/", status_code=302)
        resp.set_cookie(
            key=COOKIE_NAME,
            value=token,
            httponly=True,
            samesite="lax",
            secure=COOKIE_SECURE,
            max_age=COOKIE_MAX_AGE,
        )
        return resp

    return templates.TemplateResponse(
        request, "login.html", {"error": "Invalid username or password"},
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


# ---------- catch-all proxy ----------
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def catch_all(request: Request, path: str = ""):
    client: httpx.AsyncClient = request.app.state.httpx_client
    target = f"/{path}" if path else "/"
    return await proxy_request(client, request, target)
