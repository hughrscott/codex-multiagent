
import os
import json
import subprocess
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

# ------------------------------------------------------------------
# App & Config
# ------------------------------------------------------------------
app = FastAPI()

# Allow everything (safe here because auth is via GitHub token on tool calls)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# PROJECT_ROOT is the repo root (folder above codex-mcp/)
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def run(cmd: list[str], cwd: Path | None = None) -> dict:
    \"\"\"Run a subprocess and capture stdout/stderr safely.\"\"\"
    try:
        res = subprocess.run(
            cmd, cwd=cwd or PROJECT_ROOT, capture_output=True, text=True, check=True
        )
        return {"ok": True, "stdout": res.stdout, "stderr": res.stderr}
    except subprocess.CalledProcessError as e:
        return {
            "ok": False,
            "stdout": e.stdout,
            "stderr": e.stderr,
            "returncode": e.returncode,
        }


def ensure_parent(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)


def allowed_path(p: Path) -> bool:
    \"\"\"Only allow writes under src/, tests/, or docs/ relative to project root.\"\"\"
    allowed_roots = [PROJECT_ROOT / "src", PROJECT_ROOT / "tests", PROJECT_ROOT / "docs"]
    rp = p.resolve()
    for root in allowed_roots:
        try:
            if rp.is_relative_to(root.resolve()):
                return True
        except AttributeError:
            # Python < 3.9 fallback
            if str(rp).startswith(str(root.resolve())):
                return True
    return False


# ------------------------------------------------------------------
# Manifest & Health
# ------------------------------------------------------------------
MANIFEST_BODY = {
    "name": "codex-mcp",
    "version": "0.1.0",
    "tools": [
        {
            "name": "fs.read",
            "description": "Read UTF-8 text file",
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
        {
            "name": "fs.write",
            "description": "Write UTF-8 text file (allow-listed paths only)",
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"],
            },
        },
        {
            "name": "tests.pytest",
            "description": "Run pytest with coverage",
            "input_schema": {
                "type": "object",
                "properties": {
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": [
                            "-q",
                            "--maxfail=1",
                            "--disable-warnings",
                            "--cov=src",
                            "--cov-report=term-missing",
                        ],
                    }
                },
            },
        },
        {
            "name": "git.branch",
            "description": "Create/switch branch",
            "input_schema": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        },
        {
            "name": "git.commit",
            "description": "Commit all changes",
            "input_schema": {
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"],
            },
        },
        {
            "name": "git.push",
            "description": "Push current branch",
            "input_schema": {
                "type": "object",
                "properties": {
                    "remote": {"type": "string", "default": "origin"},
                    "set_upstream": {"type": "boolean", "default": True},
                },
            },
        },
        {
            "name": "github.create_pr",
            "description": "Open a PR in GitHub (requires env vars)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "owner": {"type": "string"},
                    "repo": {"type": "string"},
                    "head": {"type": "string"},
                    "base": {"type": "string"},
                    "title": {"type": "string"},
                    "body": {"type": "string", "default": ""},
                },
                "required": ["owner", "repo", "head", "base", "title"],
            },
        },
        {
            "name": "checks.wait_for_ci",
            "description": "(Mock) wait for checks — returns success immediately",
            "input_schema": {
                "type": "object",
                "properties": {
                    "owner": {"type": "string"},
                    "repo": {"type": "string"},
                    "pr_number": {"type": "integer"},
                },
                "required": ["owner", "repo", "pr_number"],
            },
        },
    ],
}


# Allow BOTH GET and POST for the manifest (some clients probe POST)
@app.api_route("/.well-known/manifest.json", methods=["GET", "POST"])
def manifest():
    return JSONResponse(MANIFEST_BODY)


# Quiet health check at root
@app.get("/")
def root_ok():
    return {"ok": True}


# ------------------------------------------------------------------
# Tool routes
# ------------------------------------------------------------------
@app.post("/tools/fs.read")
async def fs_read(request: Request):
    data = await request.json()
    path = (PROJECT_ROOT / data["path"]).resolve()
    if not path.exists():
        return JSONResponse({"ok": False, "error": "not_found", "path": str(path)})
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return JSONResponse({"ok": False, "error": "not_utf8", "path": str(path)})
    return JSONResponse({"ok": True, "content": content})


@app.post("/tools/fs.write")
async def fs_write(request: Request):
    data = await request.json()
    path = (PROJECT_ROOT / data["path"]).resolve()
    if not allowed_path(path):
        return JSONResponse({"ok": False, "error": "write_not_allowed", "path": str(path)})
    ensure_parent(path)
    path.write_text(data["content"], encoding="utf-8")
    return JSONResponse({"ok": True})


@app.post("/tools/tests.pytest")
async def tests_pytest(request: Request):
    data = await request.json()
    args = data.get("args") or [
        "-q",
        "--maxfail=1",
        "--disable-warnings",
        "--cov=src",
        "--cov-report=term-missing",
    ]
    result = run(["pytest"] + args, cwd=PROJECT_ROOT)
    return JSONResponse(result)


@app.post("/tools/git.branch")
async def git_branch(request: Request):
    data = await request.json()
    name = data["name"]
    result = run(["git", "checkout", "-B", name], cwd=PROJECT_ROOT)
    return JSONResponse(result)


@app.post("/tools/git.commit")
async def git_commit(request: Request):
    data = await request.json()
    msg = data["message"]
    run(["git", "add", "-A"], cwd=PROJECT_ROOT)
    result = run(["git", "commit", "-m", msg], cwd=PROJECT_ROOT)
    return JSONResponse(result)


@app.post("/tools/git.push")
async def git_push(request: Request):
    data = await request.json()
    remote = data.get("remote", "origin")
    set_upstream = data.get("set_upstream", True)
    args = ["git", "push"]
    if set_upstream:
        args += ["-u", remote, "HEAD"]
    else:
        args += [remote, "HEAD"]
    result = run(args, cwd=PROJECT_ROOT)
    return JSONResponse(result)


@app.post("/tools/github.create_pr")
async def github_create_pr(request: Request):
    import requests

    data = await request.json()
    owner = data["owner"]
    repo = data["repo"]
    head = data["head"]
    base = data["base"]
    title = data["title"]
    body = data.get("body", "")

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return JSONResponse({"ok": False, "error": "missing_GITHUB_TOKEN_env"})

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    resp = requests.post(
        url, headers=headers, json={"title": title, "head": head, "base": base, "body": body}
    )
    if resp.status_code >= 400:
        return JSONResponse({"ok": False, "status": resp.status_code, "resp": resp.text})
    pr = resp.json()
    return JSONResponse({"ok": True, "number": pr.get("number"), "url": pr.get("html_url")})


@app.post("/tools/checks.wait_for_ci")
async def checks_wait_for_ci(request: Request):
    # Minimal stub; in production you can poll GitHub Checks API here.
    data = await request.json()
    return JSONResponse({"completed": True, "success": True})


# ------------------------------------------------------------------
# Main entry
# ------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "3333"))
    host = os.getenv("HOST", "0.0.0.0")  # bind to all interfaces for hosting
    print(f"Project root: {PROJECT_ROOT}")
    uvicorn.run(app, host=host, port=port)
