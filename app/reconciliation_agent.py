from collections.abc import Callable
from datetime import datetime, timezone
from uuid import uuid4

from .conflict_policy import resolve_conflict
from .models import AssetRecord, DecisionRecord, PollSummary
from .store import CanonicalStore


class ReconciliationAgent:
    def __init__(
        self,
        store: CanonicalStore,
        source_a_loader: Callable[[], list[AssetRecord]],
        source_b_loader: Callable[[], list[AssetRecord]],
    ) -> None:
        self.store = store
        self.source_a_loader = source_a_loader
        self.source_b_loader = source_b_loader

    def poll_once(self) -> PollSummary:
        source_a_records = self.source_a_loader()
        source_b_records = self.source_b_loader()
        source_a_by_id = {record.asset_id: record for record in source_a_records}
        source_b_by_id = {record.asset_id: record for record in source_b_records}
        asset_ids = sorted(source_a_by_id.keys() | source_b_by_id.keys())

        conflicts_detected = 0
        canonical_updates = 0

        for asset_id in asset_ids:
            source_a_record = source_a_by_id.get(asset_id)
            source_b_record = source_b_by_id.get(asset_id)

            if source_a_record is None or source_b_record is None:
                self.store.upsert_asset(source_a_record or source_b_record)
                canonical_updates += 1
                continue

            decision = resolve_conflict(source_a_record, source_b_record)
            if decision is None:
                self.store.upsert_asset(source_a_record)
                canonical_updates += 1
                continue

            conflicts_detected += 1
            self.store.upsert_asset(decision.winner)
            self.store.record_decision(
                DecisionRecord(
                    decision_id=str(uuid4()),
                    asset_id=asset_id,
                    winner=decision.winner.source,
                    loser=decision.loser.source,
                    conflict_fields=decision.conflict_fields,
                    rule=decision.rule,
                    reason=decision.reason,
                    evidence=decision.evidence,
                    created_at=datetime.now(timezone.utc),
                )
            )
            canonical_updates += 1

        return PollSummary(
            source_a_records=len(source_a_records),
            source_b_records=len(source_b_records),
            conflicts_detected=conflicts_detected,
            canonical_updates=canonical_updates,
        )
