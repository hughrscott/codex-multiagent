def ba_step(state: dict) -> dict:
    # Minimal PRD text; in real use, call your LLM client here.
    prd = f"""# PRD for {state['ticket']}

## Problem
Provide a simple HTTP API endpoint to demonstrate the multi-agent workflow.

## Scope
- FastAPI app with GET /health and GET /hello?name=World
- Unit tests with pytest
- Coverage >= 85% on src/

## Acceptance Criteria
- `uvicorn src.app:app` runs locally
- `/hello?name=Hugh` returns 200 and greeting

## Non-goals
- DB, auth, or deployment

"""
    state["prd"] = prd
    state["status"] = "needs_implementation"
    state.setdefault("notes", []).append("BA: PRD drafted.")
    return state
