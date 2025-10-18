def pm_step(state: dict) -> dict:
    # Simple PM: assert a ticket and goal exist; set status for BA.
    ticket = state.get("ticket", "MVP-001")
    goal = state.get("goal", "Build sample FastAPI endpoint with tests.")
    state["ticket"] = ticket
    state["pm_brief"] = f"Ticket {ticket}: {goal}"
    state["status"] = "needs_prd"
    state.setdefault("notes", []).append("PM: brief created.")
    return state
