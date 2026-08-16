# Recall.ai — Persistent Memory MCP Server for DSA Practice

> Your AI coding practice has amnesia. Recall fixes that.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-dsa--mcp.onrender.com-purple)](https://dsa-mcp.onrender.com)
[![Tests](https://img.shields.io/badge/Tests-49%20passing-green)]()
[![Python](https://img.shields.io/badge/Python-3.11+-blue)]()
[![License](https://img.shields.io/badge/License-MIT-yellow)]()

Recall is an open-source MCP server that gives AI coding assistants 
long-term structured memory of your DSA practice history. 
Connect Cursor, Claude Desktop, or VS Code to a persistent memory 
backend built on CockroachDB + Google Gemini embeddings.

## 🌐 Live Demo
- **Web Dashboard**: https://dsa-mcp.onrender.com
- **MCP Endpoint**: https://dsa-mcp.onrender.com/mcp  
- **Demo Login**: alex@recall.dev / recall@demo123

## ⚡ Quick Connect (30 seconds)

### Claude Desktop / Cursor
Add to your MCP config:
```json
{
  "mcpServers": {
    "recall": {
      "url": "https://dsa-mcp.onrender.com/mcp"
    }
  }
}
```

Then ask your AI:
- *"I'm yourname@email.com. What should I practice today?"*
- *"Give me an Amazon interview study plan"*
- *"Flag my recurring mistakes in this code"*

## 🎯 Why Recall Exists

AI coding assistants forget everything between sessions.
LeetCode tracks pass/fail but not WHY you failed.
No tool remembers your specific mistake patterns across problems.

Recall fixes this with 3-tier memory:
1. **Episodic Memory** — every attempt logged with outcome + code
2. **Semantic Memory** — mastery scores that decay like human memory (14-day half-life)
3. **Vector Memory** — 768-dim embeddings of your mistakes for pattern detection

## 🔧 8 MCP Tools

| Tool | What it does |
|------|-------------|
| `get_or_create_user` | Register/fetch user by email |
| `get_mastery_report` | Topic mastery with 14-day decay |
| `log_attempt` | Record attempt + generate mistake embeddings |
| `suggest_next_problem` | Epsilon-greedy weak topic + vector ranking |
| `flag_recurring_mistake` | Cosine similarity against past mistake embeddings |
| `get_problem_context` | Problem details + similar past attempts |
| `study_plan` | 7-day company-specific study plan |
| `say_hello` | Test MCP connection |

## 🧠 How Memory Works

### Mastery Decay Formula

mastery(t) = base_score × 0.5^(days_elapsed / 14)

If you score 0.80 in Binary Search but don't practice for 14 days → score drops to 0.40.
GitHub Actions runs this decay automatically every night at midnight UTC.

### Vector Mistake Detection
1. You fail a problem → mistake text embedded with Gemini (768-dim)
2. Next time you write similar code → cosine similarity check
3. If similarity > 0.35 → "⚠️ You made this exact mistake before!"

## 🏗️ Architecture

```text
┌─────────────────────────────────────────┐
│              Client Layer               │
│    Cursor/Claude (stdio) │ VS Code │ Web│
└──────────────┬──────────────────────────┘
               │ MCP Protocol
               ▼
┌─────────────────────────────────────────┐
│              Render Server              │
│  FastMCP (8 tools) + FastAPI Dashboard  │
│    Rate Limiting + Structured Logging   │
└──────┬──────────────┬───────────────────┘
       │              │
       ▼              ▼
┌──────────────┐ ┌───────────────────────┐
│ CockroachDB  │ │   Google Gemini API   │
│ 3,359 probs  │ │  text-embedding-004   │
│ HNSW vectors │ │    768-dim vectors    │
└──────────────┘ └───────────────────────┘
       │
       ▼
┌──────────────┐
│GitHub Actions│
│ Nightly Decay│
│ 0 0 * * *    │
└──────────────┘
```

## 📸 Screenshots

### Web Dashboard
![Dashboard](docs/screenshots/dashboard.png)

### AI Study Assistant  
![AI Assistant](docs/screenshots/ai-assistant.png)

### Problems Browser (3,359 problems)
![Problems](docs/screenshots/problems.png)

### Progress & Analytics
![Progress](docs/screenshots/progress.png)

## 🚀 Tech Stack

| Component | Technology |
|-----------|-----------|
| MCP Server | FastMCP (Python 3.11+) |
| Database | CockroachDB Serverless |
| Vector Search | HNSW Index (cosine similarity) |
| Embeddings | Google Gemini text-embedding-004 |
| Web Dashboard | FastAPI + Jinja2 + Alpine.js |
| Auth | bcrypt password hashing |
| Rate Limiting | slowapi |
| Deployment | Render (primary) |
| CI/CD | GitHub Actions |
| Tests | pytest (49 passing) |

## 🛠️ Local Setup

### Prerequisites
- Python 3.11+
- uv package manager
- CockroachDB Serverless account (free)
- Google AI Studio API key (free)

### Steps
```bash
git clone https://github.com/tushar-2-5/DSA_MCP.git
cd DSA_MCP
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your DATABASE_URL and GEMINI_API_KEY

# Apply migrations
uv run python scripts/apply_migration.py

# Seed 3,359 problems
uv run python scripts/seed_problems.py
uv run python scripts/seed_company_problems.py

# Run tests
uv run pytest -v

# Start server
uv run python -m server.main
```

### MCP Config (Local)
```json
{
  "mcpServers": {
    "recall": {
      "command": "uv",
      "args": ["--directory", "/path/to/DSA_MCP", 
               "run", "python", "-m", "server.main"]
    }
  }
}
```

## 🧪 Testing

```bash
uv run pytest -v
# 49 passed (4 integration + 45 unit tests)
```

## ✅ Project Status

| Feature | Status |
|---------|--------|
| 8 MCP Tools | ✅ Complete |
| Web Dashboard | ✅ Complete |
| Password Authentication | ✅ Complete |
| 3,359 Company-tagged Problems | ✅ Complete |
| AI Study Assistant | ✅ Complete |
| VS Code Extension | ✅ Complete |
| Mastery Decay Engine | ✅ Complete |
| Vector Mistake Detection | ✅ Complete |
| GitHub Actions Nightly Decay | ✅ Complete |
| Rate Limiting | ✅ Complete |
| Integration Tests (49/49) | ✅ Complete |

## 📄 License
MIT License — see [LICENSE](LICENSE)

---

> Built for hackathon by Tushar, KIIT
