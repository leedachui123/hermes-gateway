import os

import httpx
from starlette.requests import Request
from starlette.responses import HTMLResponse, StreamingResponse

HERMES_BASE_URL = os.environ.get("HERMES_BASE_URL", "http://127.0.0.1:9119")

HOP_BY_HOP_HEADERS = frozenset({
    "host", "content-length", "transfer-encoding", "connection",
    "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailer", "upgrade",
})


async def proxy_request(client: httpx.AsyncClient, request: Request, path: str):
    url = httpx.URL(path=path, query=request.url.query.encode())
    body = await request.body()

    headers = {}
    for key, value in request.headers.items():
        if key.lower() not in HOP_BY_HOP_HEADERS:
            headers[key] = value

    # Standard forwarding headers
    headers["x-forwarded-for"] = request.client.host
    headers["x-forwarded-proto"] = request.url.scheme
    headers["x-forwarded-host"] = request.url.hostname

    try:
        req = client.build_request(
            method=request.method,
            url=url,
            headers=headers,
            content=body,
        )
        resp = await client.send(req, stream=True)

        resp_headers = dict(resp.headers)
        resp_headers.pop("transfer-encoding", None)
        resp_headers.pop("content-encoding", None)

        return StreamingResponse(
            content=resp.aiter_bytes(),
            status_code=resp.status_code,
            headers=resp_headers,
        )
    except httpx.ConnectError:
        return HTMLResponse(
            "<h1>503 Service Unavailable</h1><p>Hermes backend is not reachable.</p>",
            status_code=503,
        )
    except httpx.TimeoutException:
        return HTMLResponse(
            "<h1>504 Gateway Timeout</h1><p>Hermes backend did not respond in time.</p>",
            status_code=504,
        )
