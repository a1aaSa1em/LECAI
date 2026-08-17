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

## Step 3: Asset Model

Every source reports assets using the same `AssetRecord` shape:

```json
{
  "asset_id": "robot-17",
  "location": "Zone A",
  "status": "operational",
  "faults": [],
  "updated_at": "2026-08-16T10:01:00Z",
  "source": "source_a"
}
```

The model is defined in `app/models.py` and validates:

- `asset_id`: required string identifying the same physical asset across feeds.
- `location`: required string.
- `status`: one of `operational`, `idle`, `faulted`, `maintenance`, or `offline`.
- `faults`: list of fault codes, normalized by trimming blanks and removing duplicates.
- `updated_at`: timestamp used as evidence during reconciliation.
- `source`: one of `source_a`, `source_b`, or `canonical`.

The agent will match records by `asset_id`, then compare `location`, `status`, `faults`, and `updated_at` to detect disagreements. The `source` field is metadata, not a conflict field, because the same asset is expected to arrive from different feeds.

## Step 4: Conflict Policy

The conflict policy is implemented in `app/conflict_policy.py`. The rules are deliberately explicit so a teammate can understand why the agent trusted one source over the other.

Rules are applied in this order:

1. **Recent fault safety override**: if exactly one source reports `status = faulted` or a non-empty `faults` list, trust that source as long as the fault report is no more than 15 minutes older than the other report. This favors safety-critical information over a newer normal status.
2. **Newest timestamp**: if no safety override applies, trust the source with the most recent `updated_at` timestamp.
3. **Source reliability tiebreaker**: if timestamps are tied, trust the source with the higher configured reliability score. For this demo, `source_a` is set to `0.92` and `source_b` is set to `0.86`.

Each policy decision returns:

- the winning record
- the losing record
- the fields that conflicted
- the rule that fired
- a human-readable reason
- structured evidence that can be written to the decision log

This approach is intentionally conservative: recent safety faults are prioritized, routine disagreements are settled by freshness, and source reliability is only used when the evidence is otherwise tied.

## Next Step

Mock two conflict scenarios that demonstrate the policy.
