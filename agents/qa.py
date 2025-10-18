def qa_step(state: dict, tools):
    # Run pytest via MCP tool
    result = tools("tests.pytest", {"args":["-q","--maxfail=1","--disable-warnings","--cov=src","--cov-report=term-missing","--cov-fail-under=85"]})
    if not result.get("ok"):
        state["status"] = "needs_fix"
        state.setdefault("notes", []).append("QA: tests failing.")
    else:
        state["status"] = "ready_for_pr"
        state.setdefault("notes", []).append("QA: tests passed and coverage OK.")
    state["test_result"] = result
    return state
