# Asset Reconciliation Agent

A small Python/FastAPI agent that maintains a canonical inventory of physical assets by reconciling two independent operational feeds that can disagree.

The project focuses on the decision-making part of reconciliation: detecting conflicts, choosing which source to trust with explicit rules, logging the reasoning, and keeping one canonical record per asset for downstream consumers.

## What It Does

- Mocks two independent asset-state systems: `source_a` and `source_b`.
- Polls both sources continuously through a background reconciliation loop.
- Detects conflicts for the same `asset_id` across `location`, `status`, `faults`, and `updated_at`.
- Resolves disagreements with a documented conflict policy.
- Persists canonical assets and decision logs in SQLite.
- Exposes canonical state through a simple FastAPI interface.
- Includes a CLI demo that shows two conflict scenarios end to end.

## Stack

- Python
- FastAPI
- SQLite
- Pydantic
- pytest

This stack keeps the demo easy to run while still showing realistic service boundaries, persistence, and API access.

## Architecture

```text
source_a mock feed ┐
                   ├─ reconciliation_agent ── SQLite canonical store ── FastAPI API
source_b mock feed ┘
```

Main files:

- `app/sources.py`: mocked source snapshots.
- `app/models.py`: asset, decision, poll, and agent status models.
- `app/conflict_policy.py`: explicit trust policy and reasoning.
- `app/reconciliation_agent.py`: polling, conflict detection, decisions, and loop control.
- `app/store.py`: SQLite-backed canonical assets and decision log.
- `app/main.py`: FastAPI app and API routes.
- `demo.py`: terminal demo for the two required scenarios.

## Conflict Policy

Rules are applied in order:

1. **Recent fault safety override**: if exactly one source reports `status = faulted` or a non-empty `faults` list, trust that source as long as the fault report is no more than 15 minutes older than the other report. This prioritizes safety-critical information over a newer normal status.
2. **Newest timestamp**: if no safety override applies, trust the source with the most recent `updated_at`.
3. **Source reliability tiebreaker**: if timestamps are tied, trust the source with the higher configured reliability score. In this demo, `source_a = 0.92` and `source_b = 0.86`.

Each decision records the winning source, losing source, conflicting fields, rule, human-readable reason, and structured evidence.

## Demo Scenarios

The mocked feeds include two intentional conflicts:

| Asset | Conflict | Source A says | Source B says | Winner | Rule |
| --- | --- | --- | --- | --- | --- |
| `robot-17` | Location and timestamp | `Dock 1` at `10:00` | `Zone C` at `10:04` | `source_b` | Newest timestamp |
| `sensor-22` | Status, faults, and timestamp | `operational` at `10:10` | `faulted` with `temperature_spike` at `10:05` | `source_b` | Recent fault safety override |

The important difference is that `sensor-22` chooses the older record because it contains a recent safety fault.

## Quickstart

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Run the terminal demo:

```bash
.venv/bin/python demo.py
```

Run the API:

```bash
.venv/bin/python -m uvicorn app.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000/docs
```

## API

Mock source feeds:

- `GET /source-a/assets`
- `GET /source-b/assets`

Agent controls:

- `POST /agent/poll-once`
- `POST /agent/start`
- `POST /agent/stop`
- `GET /agent/status`

Canonical downstream interface:

- `GET /assets`
- `GET /assets/{asset_id}`
- `GET /decisions`

The FastAPI app starts the background reconciliation loop automatically. It polls every 5 seconds by default.

## Persistence

The canonical store writes to:

```text
data/canonical.sqlite3
```

It contains:

- `canonical_assets`: one current row per asset, keyed by `asset_id`.
- `decision_log`: append-only audit history of conflict decisions.

Repeated polls are idempotent. If the same conflict appears again and the canonical state already matches the winning record, the conflict is still detected but a duplicate decision log is not written.

To reset local demo state for the API, delete:

```text
data/canonical.sqlite3
```

The CLI demo uses a temporary SQLite database, so it is repeatable and does not alter `data/canonical.sqlite3`.

## Tests

Run the test suite:

```bash
.venv/bin/python -m pytest -q
```

The tests cover:

- API routes for source snapshots, manual polling, agent status, decisions, and canonical assets
- safety override conflict resolution
- newest timestamp conflict resolution
- reliability tiebreaking
- SQLite canonical-store upsert behavior and decision-log round trips
- canonical state updates for both demo conflicts
- avoiding duplicate decision logs on repeated polls
- background loop start/stop behavior
- SQLite persistence after closing and reopening the store
- CLI demo output

## Design Notes

The policy is intentionally explicit instead of trying to infer truth with a black-box score. That makes each decision defensible in a review: a teammate can read the decision log and see exactly which rule fired and what evidence was used.

SQLite is enough for this submission because the canonical-state contract matters more than distributed infrastructure. The store still uses a real primary key on `asset_id`, so downstream teams get one canonical state per asset.

## What I Would Do Next

- Add real source connectors with authentication, retries, and source-specific adapters.
- Track historical source accuracy from confirmed outcomes instead of static reliability scores.
- Add a human review queue for low-confidence or high-impact conflicts.
- Emit metrics for conflict rate, stale sources, fault overrides, and reconciliation latency.
- Add migrations for schema changes.
- Add API authentication before exposing canonical state to downstream teams.
- Add a small web dashboard for inspecting assets and decision history.
