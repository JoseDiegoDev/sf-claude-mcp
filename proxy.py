"""
Proxy HTTP local para os Salesforce Hosted MCP Servers.

Faz OAuth 2.0 + PKCE uma vez na inicialização e injeta o Bearer token
em todos os requests. O Claude Code enxerga apenas localhost — nunca
precisa lidar com autenticação.

Rotas expostas:
  http://localhost:8766/reads       → sobject-reads
  http://localhost:8766/mutations   → sobject-mutations
  http://localhost:8766/metadata    → metadata-experts
  http://localhost:8766/api-context → salesforce-api-context
  http://localhost:8766/all         → sobject-all

Uso:
    python proxy.py
    # Mantém rodando — Ctrl+C para encerrar
"""

import os

import httpx
import uvicorn
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from starlette.routing import Route

from auth import get_access_token

load_dotenv()

PROXY_PORT = 8766
_EXCLUDED = frozenset({"host", "content-length", "transfer-encoding", "connection"})

_SERVER_MAP = {
    "/reads": "sobject-reads",
    "/mutations": "sobject-mutations",
    "/metadata": "metadata-experts",
    "/api-context": "salesforce-api-context",
    "/all": "sobject-all",
}

_access_token: str = ""
_base_url: str = ""


def _upstream(path: str) -> str | None:
    for prefix, server in _SERVER_MAP.items():
        if path == prefix or path.startswith(prefix + "/"):
            return f"{_base_url}/{server}{path[len(prefix):]}"
    return None


async def _proxy(request: Request) -> Response:
    url = _upstream(request.url.path)
    if url is None:
        rotas = ", ".join(_SERVER_MAP)
        return Response(
            content=f"Rota desconhecida: {request.url.path}\nRotas válidas: {rotas}".encode(),
            status_code=404,
        )

    req_headers = {k: v for k, v in request.headers.items() if k.lower() not in _EXCLUDED}
    req_headers["Authorization"] = f"Bearer {_access_token}"
    req_headers["Accept"] = "application/json, text/event-stream"
    body = await request.body()

    client = httpx.AsyncClient(timeout=None)
    r = await client.send(
        client.build_request(request.method, url, headers=req_headers, content=body),
        stream=True,
    )

    resp_headers = {k: v for k, v in r.headers.items() if k.lower() not in _EXCLUDED}
    content_type = r.headers.get("content-type", "text/event-stream")

    async def _stream():
        try:
            async for chunk in r.aiter_bytes():
                yield chunk
        finally:
            await r.aclose()
            await client.aclose()

    return StreamingResponse(
        _stream(),
        status_code=r.status_code,
        headers=resp_headers,
        media_type=content_type,
    )


app = Starlette(routes=[
    Route("/", _proxy, methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]),
    Route("/{path:path}", _proxy, methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]),
])


def main() -> None:
    global _access_token, _base_url
    _base_url = os.environ["SF_MCP_BASE_URL"].rstrip("/")

    print("[proxy] Autenticando no Salesforce (OAuth 2.0 + PKCE)...")
    _access_token = get_access_token()

    print(f"\n[proxy] Pronto! Claude Code pode se conectar agora.")
    print(f"[proxy] Porta: http://localhost:{PROXY_PORT}")
    for prefix, server in _SERVER_MAP.items():
        print(f"[proxy]   {prefix:15} → {_base_url}/{server}")
    print("\n[proxy] Ctrl+C para encerrar.\n")

    uvicorn.run(app, host="127.0.0.1", port=PROXY_PORT, log_level="warning")


if __name__ == "__main__":
    main()
