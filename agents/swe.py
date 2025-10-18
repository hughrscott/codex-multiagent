from pathlib import Path

def swe_step(state: dict, tools):
    # Write minimal FastAPI app + tests using MCP fs.write
    app_py = r'''
from fastapi import FastAPI
app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/hello")
def hello(name: str = "World"):
    return {"message": f"Hello, {name}!"}
'''.lstrip()

    test_py = r'''
from fastapi.testclient import TestClient
from src.app import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True

def test_hello_default():
    r = client.get("/hello")
    assert r.status_code == 200
    assert r.json()["message"] == "Hello, World!"

def test_hello_name():
    r = client.get("/hello", params={"name":"Hugh"})
    assert r.status_code == 200
    assert r.json()["message"] == "Hello, Hugh!"
'''.lstrip()

    readme = "# Sample app\\n\\nRun: `uvicorn src.app:app --reload`\\n"

    # Use MCP tool to write files
    tools("fs.write", {"path":"src/app.py","content":app_py})
    tools("fs.write", {"path":"tests/test_app.py","content":test_py})
    tools("fs.write", {"path":"docs/PRD.md","content":state.get("prd","")})
    tools("fs.write", {"path":"README.md","content":readme})

    state["status"] = "testing"
    state.setdefault("notes", []).append("SWE: code and tests written.")
    return state
