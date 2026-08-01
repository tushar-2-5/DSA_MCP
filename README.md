# Recall

Recall is a persistent-memory MCP (Model Context Protocol) server designed for Data Structures and Algorithms (DSA) practice. Built for the CockroachDB × AWS Hackathon.

## Architecture & Stack
- **Database**: CockroachDB (v24.2) for relational data & vector embeddings (`VECTOR(1024)` with HNSW index)
- **Embeddings**: AWS Bedrock
- **Protocol**: Model Context Protocol (MCP) using Python SDK
- **Environment & Package Manager**: `uv` (Python 3.11+)

## Setup & Local Development
```bash
# Install dependencies
uv sync

# Run CockroachDB container
docker compose up -d

# Run connection test
uv run python -m scripts.test_connection
```
