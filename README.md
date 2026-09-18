# Recall.ai — Persistent Memory MCP Server for DSA Practice

> **Your AI coding practice has amnesia. Recall fixes that.**

[![Live Demo](https://img.shields.io/badge/🌐_Live_Demo-dsa--mcp.onrender.com-7C3AED?style=for-the-badge)](https://dsa-mcp.onrender.com)
[![Tests](https://img.shields.io/badge/Tests-49_passing-22C55E?style=for-the-badge)]()
[![Python](https://img.shields.io/badge/Python-3.11+-3B82F6?style=for-the-badge&logo=python)]()
[![MCP](https://img.shields.io/badge/MCP-Compatible-F59E0B?style=for-the-badge)]()
[![License](https://img.shields.io/badge/License-MIT-6B7280?style=for-the-badge)]()

Recall is an open-source **Model Context Protocol (MCP) server** that gives AI coding assistants long-term, structured memory of your DSA practice. Connect Cursor, Claude Desktop, Claude.ai, or VS Code and let your AI tutor remember your weaknesses, track your mistakes, and plan your interview prep — automatically.

---

## ⚡ Quick Connect (No Installation Required)

Add to your `claude_desktop_config.json` and restart Claude Desktop:

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`  
**Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "recall": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://dsa-mcp.onrender.com/sse"]
    }
  }
}
```

> ⚠️ Free tier — first request may take ~30 seconds to wake up.

---

## 🤖 Claude.ai Integration

Claude.ai uses a deferred tool loading mechanism where tools are dynamically discovered via search.

### MCP Configuration
Use `mcp-remote` to connect directly to the live SSE stream:
```bash
npx -y mcp-remote https://dsa-mcp.onrender.com/sse
```

### Tool Discovery & Initialization
- Search query: Claude must search **`register user email`** to load the `get_or_create_user` tool at session start.
- Once discovered, Claude calls `get_or_create_user` to retrieve the user's `user_id` and authentication `token`.
- Pass both `user_id` and `token` to all subsequent tool invocations (`get_mastery_report`, `log_attempt`, etc.).

### Claude Desktop / Claude.ai User Preferences & Custom Instructions
Add this exact block to your Claude.ai Project instructions or Custom Instructions:

```text
When working with Recall DSA tools:
1. First, search for "register user email" to load get_or_create_user.
2. Call get_or_create_user(email="alex@recall.dev", password="recall@demo123") to obtain the user_id and session token.
3. Pass the returned user_id and token to every subsequent Recall tool call (get_mastery_report, log_attempt, get_problem_context, flag_recurring_mistake, suggest_next_problem, study_plan).
```

### Default Demo Account
- **Email:** `alex@recall.dev`
- **Password:** `recall@demo123`
- **User ID:** `77ae399e-31ea-4a84-9fdb-23dab394f2d7`

---

## 🌐 Live Demo & REST Endpoints

| Resource | URL | Details |
|---|---|---|
| **Web Dashboard** | https://dsa-mcp.onrender.com | Live dashboard & practice interface |
| **MCP SSE Endpoint** | https://dsa-mcp.onrender.com/sse | Claude Desktop & Cursor remote SSE |
| **Health Check** | https://dsa-mcp.onrender.com/health | Uptime monitoring (`status: ok`) |
| **REST User API** | https://dsa-mcp.onrender.com/api/users | HTTP registration / user lookup |
| **Demo Login** | `alex@recall.dev` / `recall@demo123` | Pre-seeded with 40 attempts & masteries |

---

## 🎯 Why Recall Exists

| Problem | Recall's Solution |
|---------|-----------------|
| AI assistants forget everything between sessions | Persistent memory via MCP protocol |
| LeetCode only tracks pass/fail, not WHY you failed | Vector embeddings of mistake patterns |
| No personalized problem recommendations | Epsilon-greedy weak topic selection |
| No company-specific interview prep | 3,359 problems tagged with 129+ companies |
| Mastery fades without practice | 14-day exponential decay formula |

---

## 🔧 MCP Tools

| Tool | Trigger / Search Term | What it does |
|------|-----------------------|-------------|
| `get_or_create_user` | `register user email`, `recall login` | Register or fetch a user by email |
| `register_user` | `register user`, `create user` | Alias for `get_or_create_user` |
| `get_mastery_report` | `mastery report`, `topic scores` | Get DSA topic mastery scores |
| `log_attempt` | `log attempt`, `record solution` | Log a problem attempt |
| `get_problem_context` | `problem context`, `similar attempts` | Get similar past attempts |
| `flag_recurring_mistake` | `check bugs`, `recurring mistakes` | Check code for recurring bugs |
| `suggest_next_problem` | `suggest problem`, `next question` | Suggest next DSA problem |
| `study_plan` | `study plan`, `interview prep` | Generate a personalized study plan |

---

## 🧠 How Memory Works

### 1. Episodic Memory — Attempt History
Every attempt logged: problem, outcome, code, time, mistakes.

### 2. Semantic Memory — Decaying Mastery Scores

$$\text{mastery}(t) = \text{base\_score} \times 0.5^{(\text{days\_elapsed} / 14)}$$

Score 0.80 in Binary Search → don't practice for 14 days → score drops to 0.40. **GitHub Actions** runs nightly decay at midnight UTC automatically.

### 3. Vector Memory — Mistake Pattern Detection
Your mistake → Gemini text-embedding-004 → 768-dim vector → stored in Neon PostgreSQL (`pgvector` with HNSW index)  
Next similar code → cosine distance check (`<->`) → distance < 0.35 → recurring mistake warning!

---

## 🏗️ Architecture

```text
┌────────────────────────────────────────────────────┐
│                    CLIENT LAYER                    │
│ Cursor / Claude Desktop │ Claude.ai │ Web Browser │
│        (MCP SSE/stdio)  │  (Remote) │   (HTTPS)   │
└──────────────┬─────────────────────────────────────┘
               │ MCP Protocol / REST API
               ▼
┌────────────────────────────────────────────────────┐
│              RENDER PRODUCTION SERVER              │
│     FastMCP Tools + FastAPI Web Dashboard          │
│    Rate Limiting (slowapi) + Structured Logging    │
└────────────┬──────────────────┬────────────────────┘
             │                  │
             ▼                  ▼
┌──────────────────┐  ┌────────────────────────────┐
│ Neon PostgreSQL  │  │     Google Gemini API      │
│  with pgvector   │  │     text-embedding-004     │
│  3,359 problems  │  │  768-dimensional vectors   │
│ HNSW vector idx  │  └────────────────────────────┘
└──────────────────┘
             │
             ▼
┌──────────────────┐
│  GitHub Actions  │
│   Nightly Decay  │
│    0 0 * * *     │
└──────────────────┘
```

---

## 🚀 Local Setup

### Prerequisites
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- Neon PostgreSQL database instance
- Google AI Studio API key (free)

### Installation

```bash
# Clone repository
git clone https://github.com/tushar-2-5/DSA_MCP.git
cd DSA_MCP

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env — add DATABASE_URL and GEMINI_API_KEY

# Apply database migrations
uv run python scripts/apply_migration.py

# Seed problem database (3,359 problems)
uv run python scripts/seed_problems.py
uv run python scripts/seed_company_problems.py

# Generate embeddings
uv run python scripts/embed_seed_problems.py

# Run tests (49 should pass)
uv run pytest -v

# Start local server
uv run python -m server.main
```

### Local MCP Config
```json
{
  "mcpServers": {
    "recall": {
      "command": "uv",
      "args": ["--directory", "/path/to/DSA_MCP", "run", "python", "-m", "server.main"]
    }
  }
}
```

---

## 🧪 Test Suite

```text
49 passed in 15.44s
├── integration/
│   ├── test_user_lifecycle
│   ├── test_study_plan_integration
│   ├── test_company_filtering
│   └── test_error_recovery
└── unit/
    ├── test_dashboard (8 tests)
    ├── test_gemini_client (4 tests)
    ├── test_mastery (5 tests)
    ├── test_mcp_server (2 tests)
    ├── test_recommendation (6 tests)
    ├── test_user_api (1 test)
    └── test_validation (20 tests)
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE)

---

*Built with ❤️ for AI-assisted DSA Mastery. BY TUSHAR 24051523, 7710809*
