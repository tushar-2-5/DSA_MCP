# System Architecture

```mermaid
graph TB
    subgraph Clients["🖥️ Client Layer"]
        A[Cursor / Claude Desktop<br/>MCP stdio transport]
        B[VS Code Extension<br/>Sidebar + Notifications]
        C[Web Browser<br/>Dashboard UI]
    end

    subgraph Render["🚀 Render Production Server"]
        D[FastMCP Server<br/>8 MCP Tools]
        E[FastAPI Dashboard<br/>REST API + Templates]
        F[Rate Limiter<br/>slowapi middleware]
        G[Request Logging<br/>Structured JSON logs]
    end

    subgraph Tools["🔧 MCP Tools"]
        H[get_or_create_user]
        I[get_mastery_report]
        J[log_attempt]
        K[suggest_next_problem]
        L[flag_recurring_mistake]
        M[get_problem_context]
        N[study_plan]
    end

    subgraph Data["🗄️ Data Layer - CockroachDB"]
        O[(users table)]
        P[(problems table<br/>3,359 problems)]
        Q[(mastery table<br/>14-day decay)]
        R[(attempts table)]
        S[(mistakes table)]
        T[(embeddings table<br/>768-dim vectors)]
    end

    subgraph AI["🤖 AI Layer"]
        U[Google Gemini API<br/>text-embedding-004<br/>768-dim vectors]
        V[HNSW Vector Index<br/>cosine similarity search]
    end

    subgraph Automation["⚙️ Automation"]
        W[GitHub Actions<br/>Nightly decay cron<br/>0 0 * * *]
    end

    A -->|stdio JSON-RPC| D
    B -->|REST API HTTP| E
    C -->|HTTPS| E
    E --> F
    E --> G
    D --> H & I & J & K & L & M & N
    H & I & J & K & L & M & N --> O & P & Q & R & S & T
    J -->|on fail/partial| U
    U -->|768-dim vector| T
    T --> V
    V -->|similarity search| K & L & M
    W -->|UPDATE mastery decay| Q
```

## System Overview

The Recall architecture is structured into 5 core layers:

1. **Client Layer**:
   - Cursor & Claude Desktop integration via standard I/O (stdio) MCP JSON-RPC.
   - VS Code Extension sidebar providing quick access & background notifications.
   - Modern Web Dashboard built with FastAPI, Jinja2 templates, and Alpine.js.

2. **Server & Security Layer**:
   - FastMCP server registering 8 dedicated MCP tools.
   - SlowAPI rate limiting middleware enforcing 5 to 60 req/min limits.
   - Structlog structured JSON logging with ISO timestamps.

3. **Data Layer (CockroachDB)**:
   - Serverless distributed SQL database.
   - Stores 3,359 company-tagged LeetCode problems, topic masteries, attempts, and mistake history.

4. **AI & Vector Layer**:
   - Google Gemini API (`text-embedding-004`) generating 768-dimensional dense vector embeddings.
   - Cosine similarity vector search for recurring mistake pattern detection and weak topic problem recommendations.

5. **Automation Layer**:
   - GitHub Actions automated cron job executing nightly exponential mastery decay calculations (`0 0 * * *`).
