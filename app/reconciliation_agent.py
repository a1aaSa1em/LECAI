import asyncio
from collections.abc import Callable
from contextlib import suppress
from datetime import datetime, timezone
from uuid import uuid4

from .conflict_policy import resolve_conflict
from .models import AgentStatus, AssetRecord, DecisionRecord, PollSummary
from .store import CanonicalStore


class ReconciliationAgent:
    def __init__(
        self,
        store: CanonicalStore,
        source_a_loader: Callable[[], list[AssetRecord]],
        source_b_loader: Callable[[], list[AssetRecord]],
        poll_interval_seconds: float = 5.0,
    ) -> None:
        self.store = store
        self.source_a_loader = source_a_loader
        self.source_b_loader = source_b_loader
        self.poll_interval_seconds = poll_interval_seconds
        self._task: asyncio.Task[None] | None = None
        self._polls_completed = 0
        self._last_summary: PollSummary | None = None
        self._last_error: str | None = None
        self._started_at: datetime | None = None
        self._stopped_at: datetime | None = None

    def poll_once(self) -> PollSummary:
        source_a_records = self.source_a_loader()
        source_b_records = self.source_b_loader()
        source_a_by_id = {record.asset_id: record for record in source_a_records}
        source_b_by_id = {record.asset_id: record for record in source_b_records}
        asset_ids = sorted(source_a_by_id.keys() | source_b_by_id.keys())

        conflicts_detected = 0
        canonical_updates = 0
        decisions_logged = 0

        for asset_id in asset_ids:
            source_a_record = source_a_by_id.get(asset_id)
            source_b_record = source_b_by_id.get(asset_id)

            if source_a_record is None or source_b_record is None:
                if self._upsert_if_changed(source_a_record or source_b_record):
                    canonical_updates += 1
                continue

            decision = resolve_conflict(source_a_record, source_b_record)
            if decision is None:
                if self._upsert_if_changed(source_a_record):
                    canonical_updates += 1
                continue

            conflicts_detected += 1
            canonical_changed = self._upsert_if_changed(decision.winner)
            if canonical_changed:
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
                decisions_logged += 1

        return PollSummary(
            source_a_records=len(source_a_records),
            source_b_records=len(source_b_records),
            conflicts_detected=conflicts_detected,
            canonical_updates=canonical_updates,
            decisions_logged=decisions_logged,
        )

    async def start(self) -> AgentStatus:
        if self.is_running:
            return self.status()

        self._started_at = datetime.now(timezone.utc)
        self._stopped_at = None
        self._task = asyncio.create_task(self._run_loop())
        return self.status()

    async def stop(self) -> AgentStatus:
        if self._task is None:
            return self.status()

        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None
        self._stopped_at = datetime.now(timezone.utc)
        return self.status()

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    def status(self) -> AgentStatus:
        return AgentStatus(
            running=self.is_running,
            poll_interval_seconds=self.poll_interval_seconds,
            polls_completed=self._polls_completed,
            last_summary=self._last_summary,
            last_error=self._last_error,
            started_at=self._started_at,
            stopped_at=self._stopped_at,
        )

    async def _run_loop(self) -> None:
        while True:
            try:
                self._last_summary = self.poll_once()
                self._last_error = None
            except Exception as exc:
                self._last_error = f"{type(exc).__name__}: {exc}"
            finally:
                self._polls_completed += 1

            await asyncio.sleep(self.poll_interval_seconds)

    def _upsert_if_changed(self, asset: AssetRecord) -> bool:
        if self.store.canonical_matches(asset):
            return False
        self.store.upsert_asset(asset)
        return True
