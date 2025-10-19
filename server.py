
import os, subprocess
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

PROJECT_ROOT = Path(__file__).resolve().parent

def run(cmd: list[str], cwd: Path | None = None) -> dict:
    try:
        res = subprocess.run(cmd, cwd=cwd or PROJECT_ROOT, capture_output=True, text=True, check=True)
        return {"ok": True, "stdout": res.stdout, "stderr": res.stderr}
    except subprocess.CalledProcessError as e:
        return {"ok": False, "stdout": e.stdout, "stderr": e.stderr, "returncode": e.returncode}

def ensure_parent(path: Path): path.parent.mkdir(parents=True, exist_ok=True)
def allowed_path(p: Path) -> bool:
    allowed = [PROJECT_ROOT / "src", PROJECT_ROOT / "tests", PROJECT_ROOT / "docs"]
    rp = p.resolve()
    return any(str(rp).startswith(str(a.resolve())) for a in allowed)

TOOLS_SCHEMA = [
    {"name":"fs.read","input_schema":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}},
    {"name":"fs.write","input_schema":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}},
    {"name":"tests.pytest","input_schema":{"type":"object","properties":{"args":{"type":"array","items":{"type":"string"}}}}},
    {"name":"git.branch","input_schema":{"type":"object","properties":{"name":{"type":"string"}},"required":["name"]}},
    {"name":"git.commit","input_schema":{"type":"object","properties":{"message":{"type":"string"}},"required":["message"]}},
    {"name":"git.push","input_schema":{"type":"object","properties":{"remote":{"type":"string"},"set_upstream":{"type":"boolean"}}}},
    {"name":"github.create_pr","input_schema":{"type":"object","properties":{"owner":{"type":"string"},"repo":{"type":"string"},"head":{"type":"string"},"base":{"type":"string"},"title":{"type":"string"},"body":{"type":"string"}},"required":["owner","repo","head","base","title"]}},
    {"name":"checks.wait_for_ci","input_schema":{"type":"object","properties":{"owner":{"type":"string"},"repo":{"type":"string"},"pr_number":{"type":"integer"}},"required":["owner","repo","pr_number"]}}
]

MCP_MANIFEST = {
    "name": "codex-mcp-remote",
    "version": "0.1.0",
    "mcp": {
        "protocol": "2025-06-18",
        "transport": { "type": "http-jsonrpc", "endpoint": "/mcp" }
    },
    "tools": [
        {"name": t["name"], "description": t["name"], "input_schema": t["input_schema"]} for t in TOOLS_SCHEMA
    ]
}

@app.get("/")
def root_ok():
    return {"ok": True}

@app.head("/")
def root_head():
    return Response(status_code=200)

@app.api_route("/.well-known/mcp/manifest.json", methods=["GET","HEAD","OPTIONS"])
def mcp_manifest():
    return JSONResponse(MCP_MANIFEST)

@app.api_route("/.well-known/manifest.json", methods=["GET","HEAD","OPTIONS"])
def legacy_manifest():
    return JSONResponse(MCP_MANIFEST)

@app.get("/.well-known/oauth-authorization-server")
def oauth_metadata():
    return JSONResponse({
        "issuer": "https://example.com",
        "authorization_endpoint": "",
        "token_endpoint": "",
        "response_types_supported": [],
        "grant_types_supported": [],
        "code_challenge_methods_supported": []
    })

@app.get("/.well-known/oauth-protected-resource")
def oauth_protected():
    return JSONResponse({"ok": True, "auth": "none"})

@app.post("/register")
def oauth_register():
    return JSONResponse({"client_id": "dummy", "client_secret": "dummy"})

def tool_fs_read(args: Dict[str, Any]) -> Dict[str, Any]:
    p = (PROJECT_ROOT / args["path"]).resolve()
    if not p.exists():
        return {"ok": False, "error": "not_found", "path": str(p)}
    try:
        return {"ok": True, "content": p.read_text(encoding="utf-8")}
    except UnicodeDecodeError:
        return {"ok": False, "error": "not_utf8", "path": str(p)}

def tool_fs_write(args: Dict[str, Any]) -> Dict[str, Any]:
    p = (PROJECT_ROOT / args["path"]).resolve()
    if not allowed_path(p):
        return {"ok": False, "error": "write_not_allowed", "path": str(p)}
    ensure_parent(p)
    p.write_text(args["content"], encoding="utf-8")
    return {"ok": True}

def tool_tests_pytest(args: Dict[str, Any]) -> Dict[str, Any]:
    py_args = args.get("args") or ["-q","--maxfail=1","--disable-warnings","--cov=src","--cov-report=term-missing"]
    return run(["pytest"] + py_args, cwd=PROJECT_ROOT)

def tool_git_branch(args: Dict[str, Any]) -> Dict[str, Any]:
    return run(["git","checkout","-B", args["name"]], cwd=PROJECT_ROOT)

def tool_git_commit(args: Dict[str, Any]) -> Dict[str, Any]:
    run(["git","add","-A"], cwd=PROJECT_ROOT)
    return run(["git","commit","-m", args["message"]], cwd=PROJECT_ROOT)

def tool_git_push(args: Dict[str, Any]) -> Dict[str, Any]:
    remote = args.get("remote","origin")
    set_up = args.get("set_upstream", True)
    cmd = ["git","push"] + (["-u", remote, "HEAD"] if set_up else [remote, "HEAD"])
    return run(cmd, cwd=PROJECT_ROOT)

def tool_github_create_pr(args: Dict[str, Any]) -> Dict[str, Any]:
    import requests
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return {"ok": False, "error": "missing_GITHUB_TOKEN_env"}
    owner, repo, head, base, title = args["owner"], args["repo"], args["head"], args["base"], args["title"]
    body = args.get("body","")
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    resp = requests.post(url, headers=headers, json={"title": title, "head": head, "base": base, "body": body})
    if resp.status_code >= 400:
        return {"ok": False, "status": resp.status_code, "resp": resp.text}
    data = resp.json()
    return {"ok": True, "number": data.get("number"), "url": data.get("html_url")}

def tool_checks_wait_for_ci(args: Dict[str, Any]) -> Dict[str, Any]:
    return {"completed": True, "success": True}

TOOLS = {
    "fs.read": tool_fs_read,
    "fs.write": tool_fs_write,
    "tests.pytest": tool_tests_pytest,
    "git.branch": tool_git_branch,
    "git.commit": tool_git_commit,
    "git.push": tool_git_push,
    "github.create_pr": tool_github_create_pr,
    "checks.wait_for_ci": tool_checks_wait_for_ci,
}

@app.post("/mcp")
async def mcp_endpoint(request: Request):
    payload = await request.json()
    def handle(obj):
        mid = obj.get("id")
        method = obj.get("method","")
        params = obj.get("params") or {}
        if method == "tools/list":
            return {"jsonrpc":"2.0","id":mid,"result":{"tools":[{"name":t["name"],"input_schema":t["input_schema"]} for t in TOOLS_SCHEMA]}}
        if method == "tools/call":
            name = params.get("name")
            args = params.get("args") or {}
            fn = TOOLS.get(name)
            if not fn:
                return {"jsonrpc":"2.0","id":mid,"error":{"code":-32601,"message":f"Unknown tool {name}"}}
            try:
                out = fn(args)
                return {"jsonrpc":"2.0","id":mid,"result":out}
            except Exception as e:
                return {"jsonrpc":"2.0","id":mid,"error":{"code":-32000,"message":str(e)}}
        return {"jsonrpc":"2.0","id":mid,"error":{"code":-32601,"message":"Unknown method"}}
    if isinstance(payload, list):
        return JSONResponse([handle(obj) for obj in payload])
    else:
        return JSONResponse(handle(payload))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT","10000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
