# sf-llm-mcp

Proxy local que conecta **LLMs com suporte a MCP** diretamente ao **Salesforce** via Model Context Protocol.

Você conversa normalmente com sua ferramenta de IA — ela fala com o Salesforce por baixo dos panos, sem precisar de nenhum agente Python no meio.

| Ferramenta | Config | Status |
|---|---|---|
| Claude Code | `.mcp.json` | ✅ Suportado |
| GitHub Copilot (VS Code) | `.vscode/mcp.json` | ✅ Suportado |
| Cursor | `.cursor/mcp.json` | Em breve |
| Codex CLI | — | Em breve |

---

## Como funciona

```
Você  ──→  LLM (Claude / Copilot / Codex)
                    │
            config MCP local
                    │
           localhost:8766 (proxy.py)
                    │
        OAuth 2.0 + PKCE (uma vez)
                    │
       Salesforce MCP API
   ┌────────────────────────────────┐
   │  /reads       → sobject-reads  │
   │  /mutations   → sobject-mut.   │
   │  /metadata    → metadata-exp.  │
   │  /api-context → api-ctx        │
   │  /all         → sobject-all    │
   └────────────────────────────────┘
```

O proxy faz o OAuth uma vez ao iniciar e injeta o Bearer token em todos os requests. A LLM enxerga apenas `localhost` — não precisa saber nada sobre autenticação.

---

## Pré-requisitos

- Python 3.11+
- Salesforce org com **External Client App** configurada:
  - Flow: **Authorization Code and Credentials**
  - Escopos: `mcp_api` + `refresh_token`
  - Callback URL: `http://localhost:8765/callback`

---

## Instalação

```bash
cd sf-llm-mcp
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

pip install -r requirements.txt
cp .env.example .env
# editar .env com suas credenciais
```

---

## Uso

**Terminal 1 — inicia o proxy:**
```bash
python proxy.py
```
O browser abre para login OAuth. Após autenticar, o proxy fica escutando em `localhost:8766`.

**Terminal 2 — abre sua ferramenta de IA:**

```bash
# Claude Code
claude

# GitHub Copilot — basta abrir o VS Code nesta pasta
# O .vscode/mcp.json é lido automaticamente
code .
```

### Exemplos do que perguntar

```
Quais são as 5 Opportunities com maior valor?
Crie um contato João Silva na conta Acme Corp
Quantos Cases estão abertos esta semana?
Descreva os campos do objeto Opportunity
```

---

## Variáveis de ambiente (`.env`)

| Variável | Exemplo | Descrição |
|---|---|---|
| `SF_INSTANCE_URL` | `https://minha-org.my.salesforce.com` | URL da sua org Salesforce |
| `SF_CLIENT_ID` | `3MVG9...` | Consumer Key da External Client App |
| `SF_MCP_BASE_URL` | `https://api.salesforce.com/platform/mcp/v1/platform` | Base URL dos MCP servers |

---

## Estrutura

```
sf-llm-mcp/
├── proxy.py           ← servidor HTTP local (roteador + injetor de token)
├── auth.py            ← OAuth 2.0 + PKCE (RFC 7636), auto-contido
├── .mcp.json          ← Claude Code
├── .vscode/mcp.json   ← GitHub Copilot (VS Code)
├── .env.example       ← template de credenciais
└── requirements.txt
```
