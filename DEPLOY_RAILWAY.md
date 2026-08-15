# Deploying Recall MCP Server to Railway

This document details how to deploy the Recall MCP server as a public remote MCP server over HTTP/HTTPS to [Railway](https://railway.app/).

---

## Architecture Overview

```mermaid
graph TD
    Client["Cursor / Claude / MCP Client"] -->|"HTTPS /mcp"| Railway["Railway Cloud App"]
    Railway -->|"Python FastMCP Streamable-HTTP"| Server["server/main.py"]
    Server -->|"DB Queries"| CockroachDB[("CockroachDB / PostgreSQL")]
    Server -->|"Embeddings & Analysis"| Gemini["Google Gemini API"]
```

---

## 1. Railway Setup & GitHub Deployment

1. **Log in to Railway**: Go to [railway.app](https://railway.app) and sign in.
2. **Create New Project**: Click **+ New Project** -> **Deploy from GitHub repo**.
3. **Select Repository**: Choose `tushar-2-5/DSA_MCP`.
4. **Deploy**: Railway will automatically detect the Python project and build environment via `uv` / `pyproject.toml`.

---

## 2. Environment Variables Configuration

In your Railway project dashboard, navigate to **Variables** and add the following required environment variables:

| Variable Name | Description | Example Value |
|---|---|---|
| `DATABASE_URL` | Connection URI for CockroachDB / PostgreSQL | `postgresql://user:pass@host.cockroachlabs.cloud:26257/recall?sslmode=verify-full` |
| `GEMINI_API_KEY` | Google Gemini API Key | `AIzaSy...` |
| `MCP_TRANSPORT` | Transport mode for FastMCP | `streamable-http` (default) |
| `PORT` | Dynamically provided by Railway | *(Set automatically by Railway)* |

> [!CAUTION]
> **Never commit your `.env` file** or hardcode secrets in source control. Railway securely injects these environment variables into the running container.

---

## 3. One-Time Database Initialization & Migration

Do **NOT** run migrations or seed scripts as the service start command. Execute them as one-time setup commands (either locally pointed at your remote DB URL or via Railway CLI / one-off task):

```bash
# 1. Apply database migrations (creates users, problems, attempts tables)
uv run python scripts/apply_migration.py

# 2. Seed initial DSA problems into the database
uv run python scripts/seed_problems.py

# 3. Generate Gemini vector embeddings for seed problems
uv run python scripts/embed_seed_problems.py
```

---

## 4. Build & Start Commands

Railway will build and start the container using the provided `Procfile`:

- **Build Command**: `uv sync` (handled automatically by Railway Python builder)
- **Start Command**: 
  ```bash
  uv run python -m server.main --transport streamable-http
  ```

---

## 5. Domain Generation & Public MCP Endpoint

1. Go to **Settings** in your Railway service dashboard.
2. Under **Networking** -> **Public Networking**, click **Generate Domain**.
3. Your service will receive a public domain, such as `dsa-mcp-production.up.railway.app`.

### Endpoints Format

- **Public MCP Server Endpoint**: `https://<YOUR_RAILWAY_DOMAIN>/mcp`
- **Health Check Endpoint**: `https://<YOUR_RAILWAY_DOMAIN>/health`

---

## 6. Testing the Deployment

### A. Health Check Test
```bash
curl -i https://<YOUR_RAILWAY_DOMAIN>/health
```
Expected output:
```json
HTTP/1.1 200 OK
{"status":"ok","service":"recall-mcp-server","transport":"/mcp"}
```

### B. MCP Endpoint Handshake Test
```bash
curl -i -H "Accept: application/json, text/event-stream" https://<YOUR_RAILWAY_DOMAIN>/mcp
```
Expected output (indicates active Streamable-HTTP transport expecting session headers):
```json
HTTP/1.1 400 Bad Request
{"jsonrpc":"2.0","id":"server-error","error":{"code":-32600,"message":"Bad Request: Missing session ID"}}
```

---

## 7. Connecting to Clients

### Connecting to Cursor IDE

Add the remote MCP server to your Cursor settings (`.cursor/mcp.json` or Cursor Settings -> MCP):

```json
{
  "mcpServers": {
    "recall-remote": {
      "url": "https://<YOUR_RAILWAY_DOMAIN>/mcp"
    }
  }
}
```

### Connecting to Claude Desktop / Claude CLI

If using an SSE / HTTP-compatible bridge or Claude client supporting remote HTTP MCP servers:

```json
{
  "mcpServers": {
    "recall": {
      "url": "https://<YOUR_RAILWAY_DOMAIN>/mcp"
    }
  }
}
```

*(Note: For local stdio usage, you can still run `python -m server.main --transport stdio`)*

---

## 8. Registered MCP Tools Reference

The deployed server exposes the following 8 MCP tools:
1. `say_hello` - Test connection and greeting
2. `get_or_create_user` - Manage user profile and track active user
3. `get_mastery_report` - Retrieve user topic mastery percentages and stats
4. `log_attempt` - Record problem submission results and update mastery
5. `get_problem_context` - Fetch problem statement and similarity matches
6. `flag_recurring_mistake` - Record recurring coding errors
7. `suggest_next_problem` - Get AI-driven DSA problem recommendation
8. `study_plan` - Generate personalized 7-day DSA study plan with company targeting

---

## 9. Troubleshooting Common Railway Issues

| Issue | Cause | Solution |
|---|---|---|
| **Port Binding Error (`127.0.0.1`)** | Server listening on localhost instead of `0.0.0.0` | Ensure `server/main.py` initializes `FastMCP("recall", host="0.0.0.0", port=port)` |
| **Health Check Failed / Timeout** | Container listening on wrong port | Verify Railway injected `$PORT` is passed to `int(os.environ.get("PORT", 8000))` |
| **Database Connection Error** | Missing `DATABASE_URL` or SSL config | Verify `DATABASE_URL` in Railway Variables and add `?sslmode=verify-full` if connecting to CockroachDB |
| **Gemini API Error** | Missing `GEMINI_API_KEY` | Ensure `GEMINI_API_KEY` is set in Railway Variables |
