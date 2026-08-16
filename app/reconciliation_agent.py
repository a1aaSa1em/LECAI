from collections.abc import Callable

from .models import AssetRecord, PollSummary
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

        return PollSummary(
            source_a_records=len(source_a_records),
            source_b_records=len(source_b_records),
            conflicts_detected=0,
            canonical_updates=0,
        )
