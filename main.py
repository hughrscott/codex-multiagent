from graph.workflow import run

if __name__ == "__main__":
    # You can pass GitHub owner/repo in state for PR creation
    state = {
        "ticket": "MVP-001",
        "goal": "Create a minimal FastAPI app with tests and open a PR.",
        # Optional: override with your real repo to open a PR
        # "github_owner": "your-user-or-org",
        # "github_repo":  "your-repo-name",
    }
    final_state = run(state)
    print("Status:", final_state.get("status"))
    print("Notes:", *final_state.get("notes", []), sep="\n - ")
    if "pr_response" in final_state:
        print("PR response:", final_state["pr_response"])
