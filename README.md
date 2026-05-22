# sf-claude-mcp

Proxy local que conecta o **Claude Code** diretamente ao **Salesforce** via MCP (Model Context Protocol).

Você conversa com o Claude Code normalmente — ele é quem fala com o Salesforce por baixo dos panos, sem precisar de nenhum agente Python no meio.

---

## Como funciona

```
Você  ──→  Claude Code  ──→  .mcp.json  ──→  localhost:8766 (proxy.py)
                                                      │
                                          OAuth 2.0 + PKCE (uma vez)
                                                      │
                                         Salesforce MCP API
                                     ┌────────────────────────────┐
                                     │  /reads      → sobject-reads │
                                     │  /mutations  → sobject-mut.  │
                                     │  /metadata   → metadata-exp. │
                                     │  /api-context → api-ctx      │
                                     │  /all        → sobject-all   │
                                     └──────────────────────────────┘
```

O proxy faz o OAuth uma vez ao iniciar e injeta o Bearer token em todos os requests. O Claude Code enxerga apenas `localhost` — não precisa saber nada sobre autenticação.

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
cd sf-claude-mcp
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

**Terminal 2 — abre o Claude Code nesta pasta:**
```bash
claude
```
O Claude Code lê o `.mcp.json` e conecta nos 5 MCP servers automaticamente. Você já pode perguntar sobre o Salesforce diretamente.

### Exemplos do que perguntar ao Claude

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
sf-claude-mcp/
├── proxy.py        ← servidor HTTP local (roteador + injetor de token)
├── auth.py         ← OAuth 2.0 + PKCE (RFC 7636), auto-contido
├── .mcp.json       ← lido pelo Claude Code para descobrir os MCP servers
├── .env.example    ← template de credenciais
└── requirements.txt
```
