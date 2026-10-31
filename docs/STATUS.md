# Status

The pilot is built, in the six phases of `docs/PLAN.md`.

## What is built

- `backend/`: FastAPI and SQLite. The database (`backend/undercover.db`, or the file in `UNDERCOVER_DB`) is created and seeded from `data/` on first use. It never reads `data/evals/`.
  - Read: `list_claims`, `get_claim`, `get_policy`, `get_plan`, `get_customer`, `list_handlers`, `get_company`, `get_policy_wording`, `get_instructions`.
  - Write: `start_claim`, `add_step`, `record_decision`, `sign_off_claim`, `pay_claim`, `run_agent`.
  - A claim is `waiting`, `in_progress`, `awaiting_sign_off` or `decided`, worked out from what is stored.
  - `pay_claim` refuses a payout over $1,000 until a handler signs off, whoever calls it.
  - The agent's instructions are `backend/instructions.md`, served read only.
- `agent/`: the UnderCover Agent. `run(claim_id, thread_id)` loads its instructions from the backend, works through seven tools (read the claim, policy, plan, customer and wording; record the decision; pay) and logs each tool call as a step. `agent/stub.py` is a scripted model for tests: it approves every claim as claimed and then tries to pay.
- `dashboard/`: React, Vite and TypeScript, styled to `docs/BRAND.md` in light and dark.
  - The queue, with a count per state.
  - A claim page: story, items, documents, policy, customer history, the decision, and the agent's steps, which refresh every two seconds while it works.
  - Run agent on a waiting claim; sign off and pay on a claim waiting for sign-off.
  - The agent's instructions, read only.
- `e2e/`: Playwright tests against a fresh database and the stub model.

## Run

`uv sync` and `npm install`, then:

- `npm run dev` starts the backend on port 8000 and the dashboard on port 5173. Put your `OPENROUTER_API_KEY` in `.env` for the live model, or set `UNDERCOVER_STUB_AGENT=1` to use the stub.
- `uv run -m agent.main CLM-1001` runs the agent on one claim while the backend is up.
- Delete `backend/undercover.db` to start over from the seed data.
- `npm run check` runs every check. Stop `npm run dev` first, because the end-to-end tests start their own backend on port 8000.

## Not built yet

The claims manual, sign-in, real payments, messages to customers, and scoring the agent against `data/evals/`.
