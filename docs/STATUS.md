# Status

The pilot, built in phases from `docs/PLAN.md`.

## Built

- `backend/`: FastAPI and SQLite. The database (`backend/undercover.db`, or `UNDERCOVER_DB`) is created and seeded from `data/` on first use. Read routes: claims (with derived state), policies, plans, customers, handlers, company, policy wording and the agent's instructions (`backend/instructions.md`). Write routes: start, steps, decision, sign-off and payment. The backend refuses a payment over $1,000 until a handler signs off.
- `agent/`: the hello-world entry point `run(claim_id, thread_id)` (replaced in phase 3).
- `dashboard/`: one page that shows whether the backend is up (replaced in phase 4).
- `e2e/`: one test of that page.

## Run

`uv sync`, `npm install`, then `npm run dev`. `npm run check` runs every check.
