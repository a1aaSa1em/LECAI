from pathlib import Path
from tempfile import TemporaryDirectory

from app.reconciliation_agent import ReconciliationAgent
from app.sources import get_source_a_assets, get_source_b_assets
from app.store import CanonicalStore


def run_demo() -> int:
    source_a_records = get_source_a_assets()
    source_b_records = get_source_b_assets()

    with TemporaryDirectory() as temp_dir:
        store = CanonicalStore(Path(temp_dir) / "demo.sqlite3")
        agent = ReconciliationAgent(
            store=store,
            source_a_loader=get_source_a_assets,
            source_b_loader=get_source_b_assets,
        )

        print("Asset Reconciliation Agent Demo")
        print("=" * 33)
        print()
        _print_sources(source_a_records, source_b_records)

        summary = agent.poll_once()
        print("Poll Summary")
        print("-" * 12)
        print(f"source_a records: {summary.source_a_records}")
        print(f"source_b records: {summary.source_b_records}")
        print(f"conflicts detected: {summary.conflicts_detected}")
        print(f"canonical updates: {summary.canonical_updates}")
        print(f"decisions logged: {summary.decisions_logged}")
        print()

        _print_decisions(
            source_a_records,
            source_b_records,
            store.list_decisions(),
        )
        _print_canonical_state(store.list_assets())

        repeat_summary = agent.poll_once()
        print("Repeat Poll Check")
        print("-" * 17)
        print(f"conflicts still detected: {repeat_summary.conflicts_detected}")
        print(f"new canonical updates: {repeat_summary.canonical_updates}")
        print(f"new decisions logged: {repeat_summary.decisions_logged}")
        print()
        print("Result: canonical state is stable and duplicate decisions are avoided.")

        store.close()

    return 0


def _print_sources(source_a_records, source_b_records) -> None:
    print("Mock Source Snapshots")
    print("-" * 21)
    for record in source_a_records:
        print(f"source_a {record.asset_id}: {_format_asset(record)}")
    for record in source_b_records:
        print(f"source_b {record.asset_id}: {_format_asset(record)}")
    print()


def _print_decisions(source_a_records, source_b_records, decisions) -> None:
    source_a_by_id = {record.asset_id: record for record in source_a_records}
    source_b_by_id = {record.asset_id: record for record in source_b_records}

    print("Conflict Decisions")
    print("-" * 18)
    for decision in decisions:
        source_a = source_a_by_id[decision.asset_id]
        source_b = source_b_by_id[decision.asset_id]
        print(f"{decision.asset_id}")
        print(f"  fields: {', '.join(decision.conflict_fields)}")
        print(f"  source_a: {_format_fields(source_a, decision.conflict_fields)}")
        print(f"  source_b: {_format_fields(source_b, decision.conflict_fields)}")
        print(f"  winner: {decision.winner}")
        print(f"  rule: {decision.rule}")
        print(f"  reason: {decision.reason}")
    print()


def _print_canonical_state(assets) -> None:
    print("Canonical State")
    print("-" * 15)
    for asset in assets:
        print(f"{asset.asset_id}: {_format_asset(asset)}")
    print()


def _format_asset(asset) -> str:
    faults = ", ".join(asset.faults) if asset.faults else "none"
    return (
        f"location={asset.location}, status={asset.status}, faults={faults}, "
        f"updated_at={asset.updated_at.isoformat()}, source={asset.source}"
    )


def _format_fields(asset, fields) -> str:
    values = []
    for field in fields:
        value = getattr(asset, field)
        if field == "faults":
            value = ", ".join(value) if value else "none"
        elif hasattr(value, "isoformat"):
            value = value.isoformat()
        values.append(f"{field}={value}")
    return "; ".join(values)


if __name__ == "__main__":
    raise SystemExit(run_demo())
