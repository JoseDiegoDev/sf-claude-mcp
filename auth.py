"""
OAuth 2.0 Authorization Code + PKCE flow para o Salesforce Hosted MCP Server.

Por que Authorization Code + PKCE e não Client Credentials?
O MCP Server do Salesforce requer contexto de usuário (sessão delegada).
PKCE (RFC 7636) substitui o client_secret em clientes públicos, impedindo
ataques de interceptação do authorization code.
"""

import base64
import hashlib
import os
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests

CALLBACK_PORT = 8765
CALLBACK_URL = f"http://localhost:{CALLBACK_PORT}/callback"


def _generate_pkce_pair() -> tuple[str, str]:
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return code_verifier, code_challenge


def get_access_token() -> str:
    """
    Executa o fluxo OAuth 2.0 + PKCE completo.
    Lê SF_INSTANCE_URL e SF_CLIENT_ID das variáveis de ambiente.

    Returns:
        access_token — tratar como segredo, nunca logar nem persistir

    Raises:
        RuntimeError: se qualquer etapa falhar
    """
    instance_url = os.environ["SF_INSTANCE_URL"].rstrip("/")
    client_id = os.environ["SF_CLIENT_ID"]

    code_verifier, code_challenge = _generate_pkce_pair()
    captured: dict[str, str] = {}
    code_received = threading.Event()

    class _CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path != "/callback":
                self._respond(404, "Not found")
                return
            params = parse_qs(parsed.query)
            if "error" in params:
                captured["error"] = f"{params['error'][0]}: {params.get('error_description', [''])[0]}"
                self._respond(400, "Erro de autorização")
            elif "code" not in params:
                captured["error"] = "Callback sem authorization code"
                self._respond(400, "authorization code ausente")
            else:
                captured["code"] = params["code"][0]
                self._respond(200, "Autorização concluída! Pode fechar esta aba.")
            code_received.set()

        def _respond(self, status: int, message: str) -> None:
            body = f"<html><body><h2>{message}</h2></body></html>".encode()
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_) -> None:
            pass

    server = HTTPServer(("localhost", CALLBACK_PORT), _CallbackHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    auth_url = f"{instance_url}/services/oauth2/authorize?" + urlencode({
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": CALLBACK_URL,
        "scope": "mcp_api refresh_token",
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    })

    print(f"[auth] Abrindo browser para login Salesforce...")
    print(f"[auth] Se não abrir, acesse manualmente:\n       {auth_url}\n")
    webbrowser.open(auth_url)

    if not code_received.wait(timeout=120):
        server.shutdown()
        raise RuntimeError("Timeout de 120s esperando o login. Tente novamente.")

    server.shutdown()

    if "error" in captured:
        raise RuntimeError(f"Falha na autorização: {captured['error']}")

    resp = requests.post(
        f"{instance_url}/services/oauth2/token",
        data={
            "grant_type": "authorization_code",
            "code": captured["code"],
            "redirect_uri": CALLBACK_URL,
            "client_id": client_id,
            "code_verifier": code_verifier,
        },
        timeout=30,
    )

    if not resp.ok:
        raise RuntimeError(f"Token endpoint HTTP {resp.status_code}: {resp.text}")

    data = resp.json()
    if "access_token" not in data:
        raise RuntimeError(f"Resposta sem access_token: {data}")

    return data["access_token"]
