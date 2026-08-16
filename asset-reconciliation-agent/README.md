# Asset Reconciliation Agent

This project will demonstrate an agent that keeps a canonical inventory of physical assets by reconciling two independent operational feeds that can disagree.

## Step 1: Stack Choice

The project uses a small Python stack that is easy to run, explain, and review:

- **Python** for the agent, source mocks, and demo logic.
- **FastAPI** for two mocked operational source APIs and one canonical asset API.
- **SQLite** for the canonical asset state and decision history.
- **Background polling loop** for the continuously running reconciliation agent.
- **JSON decision logs** so every conflict resolution can be inspected by a teammate.

## Why This Stack

FastAPI makes it straightforward to expose realistic REST endpoints without a large framework. SQLite gives the project durable canonical state with no database server setup. A background polling loop is enough to show the agent behavior clearly: it can fetch snapshots, compare records, detect conflicts, choose a winner, write the result, and expose the canonical state.

The goal is not to build production infrastructure. The goal is to make the reconciliation logic transparent, runnable, and defensible.

## Planned Components

- `source_a`: mocked operational feed A.
- `source_b`: mocked operational feed B.
- `reconciler`: multi-step agent that polls both feeds and applies conflict rules.
- `canonical_store`: SQLite-backed canonical asset state.
- `decision_log`: structured history of conflicts, winners, and justifications.
- `api`: simple downstream interface for querying canonical state and decisions.

## Step 2: System Shape

The first runnable shape is split into three pieces:

- **`source_a` mock feed**: exposed at `GET /source-a/assets`.
- **`source_b` mock feed**: exposed at `GET /source-b/assets`.
- **`reconciliation_agent`**: exposed for now through `POST /agent/poll-once`, which polls both feeds and reports what it saw.

The downstream-facing canonical interface is:

- `GET /assets`
- `GET /assets/{asset_id}`
- `GET /decisions`

For this step, the canonical store is temporarily in memory. The next steps will define the asset model in more detail, add SQLite persistence, and implement the conflict-resolution policy.

## Next Step

Define the asset data model and the conflict-resolution policy.
