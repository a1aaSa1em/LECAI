from .models import AssetRecord, DecisionRecord


class CanonicalStore:
    """Temporary in-memory store; step three will replace this with SQLite."""

    def __init__(self) -> None:
        self._assets: dict[str, AssetRecord] = {}
        self._decisions: list[DecisionRecord] = []

    def list_assets(self) -> list[AssetRecord]:
        return list(self._assets.values())

    def get_asset(self, asset_id: str) -> AssetRecord | None:
        return self._assets.get(asset_id)

    def upsert_asset(self, asset: AssetRecord) -> None:
        canonical_asset = asset.model_copy(update={"source": "canonical"})
        self._assets[asset.asset_id] = canonical_asset

    def list_decisions(self) -> list[DecisionRecord]:
        return self._decisions

    def record_decision(self, decision: DecisionRecord) -> None:
        self._decisions.append(decision)


canonical_store = CanonicalStore()
