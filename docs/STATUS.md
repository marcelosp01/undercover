# Status

The pilot, built in phases from `docs/PLAN.md`.

## Built

- `backend/`: FastAPI and SQLite. The database (`backend/undercover.db`, or `UNDERCOVER_DB`) is created and seeded from `data/` on first use. Read routes: claims (with derived state), policies, plans, customers, handlers, company, policy wording and the agent's instructions (`backend/instructions.md`). Write routes: start, steps, decision, sign-off and payment. The backend refuses a payment over $1,000 until a handler signs off.
- `agent/`: the UnderCover Agent. `run(claim_id, thread_id)` loads its instructions from the backend, works through seven tools (read claim, policy, plan, customer, wording; record decision; pay) and logs each tool call as a step. Run it with `uv run -m agent.main CLAIM_ID` while the backend is up. `agent/stub.py` is the scripted model used by tests; set `UNDERCOVER_STUB_AGENT=1` to use it in place of a live model.
- `dashboard/`: one page that shows whether the backend is up (replaced in phase 4).
- `e2e/`: one test of that page.

## Run

`uv sync`, `npm install`, then `npm run dev`. `npm run check` runs every check.
