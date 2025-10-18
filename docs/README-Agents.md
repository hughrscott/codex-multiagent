# Agents

- **PM**: turns your ask into a ticket/goal and kicks off BA.
- **BA**: drafts/updates PRD and acceptance criteria.
- **SWE**: writes code and tests via MCP tools.
- **QA**: runs pytest with coverage and gates the PR step.

Add new agents by creating a file in `agents/` and updating the router in `graph/workflow.py`.
