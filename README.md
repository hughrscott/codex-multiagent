# codex-multiagent (Python)

A starter project for a **multi-agent Codex** workflow driven from ChatGPT (GPT-5), using a **local MCP server** that exposes repo tools (fs, git, tests, GitHub). Multi‑LLM wiring is included, but all agents default to **GPT‑5**.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# in one terminal
python codex-mcp/mcp_server.py

# connect the manifest URL in ChatGPT:
# http://127.0.0.1:3333/.well-known/manifest.json

# in another terminal
python main.py
```

## Environment

Copy `.env.example` to `.env` and fill values if you want GitHub integration (PR creation).  
For local-only mode, you can skip the GitHub fields.

## What this does

- Runs a **LangGraph** with agents (PM, BA, SWE, QA) — each is easy to extend.
- Uses the **MCP server** for file edits, tests, git, and GitHub PRs.
- Includes a **sample task**: create a tiny FastAPI app and tests, then open a PR.

> Tip: keep `main` protected and require CI checks before merge.
