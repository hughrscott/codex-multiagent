import json, requests

from agents.pm import pm_step
from agents.ba import ba_step
from agents.swe import swe_step
from agents.qa import qa_step

MCP_URL = "http://127.0.0.1:3333"

def call_tool(tool_name: str, payload: dict):
    # Generic MCP client
    resp = requests.post(f"{MCP_URL}/tools/{tool_name}", json=payload, timeout=60)
    try:
        return resp.json()
    except Exception:
        return {"ok": False, "error": f"bad_response_{resp.status_code}", "text": resp.text}

def supervisor(state: dict) -> str:
    s = state.get("status","new")
    if s in ("new","planned"): return "pm"
    if s == "needs_prd": return "ba"
    if s == "needs_implementation": return "swe"
    if s == "testing": return "qa"
    if s == "needs_fix": return "swe"
    if s == "ready_for_pr": return "repoops"
    return "done"

def repoops_step(state: dict):
    # Create branch, commit, push, and open PR using MCP tools.
    ticket = state.get("ticket","MVP-001")
    branch = f"feat/{ticket.lower()}"
    call_tool("git.branch", {"name": branch})
    call_tool("git.commit", {"message": f"{ticket}: sample feature implementation"})
    call_tool("git.push", {"set_upstream": True})

    owner = state.get("github_owner") or "your-user"
    repo = state.get("github_repo") or "your-repo"
    pr_title = f"{ticket}: Sample feature"
    pr_body = "Auto-generated PR by codex-multiagent."
    pr = call_tool("github.create_pr", {"owner": owner, "repo": repo, "head": branch, "base": "main", "title": pr_title, "body": pr_body})
    state["pr_response"] = pr
    state["status"] = "done"
    state.setdefault("notes", []).append("RepoOps: PR opened." if pr.get("ok") else "RepoOps: PR failed; check creds.")
    return state

def run(state: dict) -> dict:
    # Simple state machine loop
    for _ in range(20):
        nxt = supervisor(state)
        if nxt == "pm":
            state = pm_step(state)
        elif nxt == "ba":
            state = ba_step(state)
        elif nxt == "swe":
            state = swe_step(state, call_tool)
        elif nxt == "qa":
            state = qa_step(state, call_tool)
        elif nxt == "repoops":
            state = repoops_step(state)
        else:
            break
    return state
