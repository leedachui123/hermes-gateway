"""
Mock Hermes Agent — 模拟 Hermes 后端 dashboard
监听 9119 端口，供 Hermes Gateway 代理测试用
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import datetime

app = FastAPI(title="Mock Hermes Agent", version="0.1.0")

HTML_DASHBOARD = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>Hermes Agent Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
               background: #f0f2f5; color: #333; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                  color: white; padding: 20px 40px; }}
        .header h1 {{ font-size: 24px; }}
        .header p {{ opacity: 0.9; margin-top: 4px; }}
        .container {{ max-width: 1000px; margin: 30px auto; padding: 0 20px; }}
        .card {{ background: white; border-radius: 12px; padding: 24px; margin-bottom: 20px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
        .card h2 {{ font-size: 18px; margin-bottom: 16px; color: #555; }}
        .stat-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; }}
        .stat-item {{ text-align: center; padding: 16px; background: #f8f9ff; border-radius: 8px; }}
        .stat-value {{ font-size: 32px; font-weight: bold; color: #667eea; }}
        .stat-label {{ font-size: 13px; color: #888; margin-top: 4px; }}
        .status-badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px;
                        font-size: 13px; font-weight: 500; }}
        .status-ok {{ background: #e6f7e6; color: #2e7d32; }}
        .nav {{ margin-top: 16px; }}
        .nav a {{ color: white; text-decoration: none; margin-right: 20px; opacity: 0.85; }}
        .nav a:hover {{ opacity: 1; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
        th, td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid #eee; font-size: 14px; }}
        th {{ color: #888; font-weight: 500; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 Hermes Agent Dashboard</h1>
        <p>Mock backend — 用于 Gateway 代理测试</p>
        <div class="nav">
            <a href="/">首页</a>
            <a href="/api/sessions">会话列表</a>
            <a href="/api/stats">统计</a>
            <a href="/health">健康检查</a>
        </div>
    </div>
    <div class="container">
        <div class="card">
            <h2>📊 系统概览</h2>
            <div class="stat-grid">
                <div class="stat-item">
                    <div class="stat-value">{agents}</div>
                    <div class="stat-label">活跃 Agent</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{sessions}</div>
                    <div class="stat-label">今日会话</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{uptime}</div>
                    <div class="stat-label">运行时间</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">
                        <span class="status-badge status-ok">● 在线</span>
                    </div>
                    <div class="stat-label">状态</div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>📋 最近会话</h2>
            <table>
                <tr><th>ID</th><th>用户</th><th>模型</th><th>时间</th><th>状态</th></tr>
                {session_rows}
            </table>
        </div>

        <div class="card">
            <h2>🔗 网关测试信息</h2>
            <table>
                <tr><td style="color:#888;width:140px">代理路径</td><td><code>{proxy_path}</code></td></tr>
                <tr><td style="color:#888">请求头</td><td><code>X-Forwarded-For: {forwarded_for}</code></td></tr>
                <tr><td style="color:#888">请求时间</td><td><code>{request_time}</code></td></tr>
            </table>
        </div>
    </div>
</body>
</html>"""


@app.get("/")
async def root(request: Request):
    """Dashboard 主页 — 验证代理是否正常工作"""
    return HTMLResponse(
        HTML_DASHBOARD.format(
            agents="3",
            sessions="42",
            uptime="12h 34m",
            session_rows="".join(
                f"<tr><td>#{i}</td><td>user_{i}</td><td>gpt-4</td>"
                f"<td>{datetime.datetime.now():%H:%M}</td>"
                f'<td><span class="status-badge status-ok">✓ 完成</span></td></tr>'
                for i in range(1, 6)
            ),
            proxy_path=str(request.url.path) if request.url.path else "/",
            forwarded_for=request.headers.get("x-forwarded-for", "N/A"),
            request_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
    )


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "service": "hermes-agent", "version": "0.1.0-mock"}


@app.get("/api/sessions")
async def list_sessions():
    """返回模拟的会话列表"""
    return {
        "sessions": [
            {"id": i, "user": f"user_{i}", "model": "gpt-4",
             "started_at": datetime.datetime.now().isoformat(),
             "status": "completed"}
            for i in range(1, 11)
        ]
    }


@app.get("/api/stats")
async def stats():
    """返回模拟统计信息"""
    return {
        "total_sessions": 1024,
        "active_agents": 3,
        "uptime_hours": 12.5,
        "avg_response_time_ms": 320,
    }


@app.get("/api/info")
async def info(request: Request):
    """返回请求信息 — 用于验证代理是否正确传递了请求"""
    return {
        "method": request.method,
        "path": str(request.url.path),
        "headers": dict(request.headers),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=9119)
