import json
import sqlite3
from pathlib import Path
from threading import RLock

from .models import AssetRecord, DecisionRecord


DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "canonical.sqlite3"


class CanonicalStore:
    """SQLite-backed canonical assets and decision log."""

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        if self.db_path != Path(":memory:"):
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._connection = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
        )
        self._connection.row_factory = sqlite3.Row
        self._initialize()

    def list_assets(self) -> list[AssetRecord]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT asset_id, location, status, faults_json, updated_at, source
                FROM canonical_assets
                ORDER BY asset_id
                """
            ).fetchall()
        return [self._asset_from_row(row) for row in rows]

    def get_asset(self, asset_id: str) -> AssetRecord | None:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT asset_id, location, status, faults_json, updated_at, source
                FROM canonical_assets
                WHERE asset_id = ?
                """,
                (asset_id,),
            ).fetchone()
        if row is None:
            return None
        return self._asset_from_row(row)

    def upsert_asset(self, asset: AssetRecord) -> None:
        canonical_asset = asset.model_copy(update={"source": "canonical"})
        with self._lock:
            self._connection.execute(
                """
                INSERT INTO canonical_assets (
                    asset_id,
                    location,
                    status,
                    faults_json,
                    updated_at,
                    source
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(asset_id) DO UPDATE SET
                    location = excluded.location,
                    status = excluded.status,
                    faults_json = excluded.faults_json,
                    updated_at = excluded.updated_at,
                    source = excluded.source
                """,
                (
                    canonical_asset.asset_id,
                    canonical_asset.location,
                    canonical_asset.status,
                    json.dumps(canonical_asset.faults),
                    canonical_asset.updated_at.isoformat(),
                    canonical_asset.source,
                ),
            )
            self._connection.commit()

    def canonical_matches(self, asset: AssetRecord) -> bool:
        existing = self.get_asset(asset.asset_id)
        if existing is None:
            return False
        return existing.comparison_payload() == asset.comparison_payload()

    def list_decisions(self) -> list[DecisionRecord]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT
                    decision_id,
                    asset_id,
                    winner,
                    loser,
                    conflict_fields_json,
                    rule,
                    reason,
                    evidence_json,
                    created_at
                FROM decision_log
                ORDER BY created_at, decision_id
                """
            ).fetchall()
        return [self._decision_from_row(row) for row in rows]

    def record_decision(self, decision: DecisionRecord) -> None:
        with self._lock:
            self._connection.execute(
                """
                INSERT INTO decision_log (
                    decision_id,
                    asset_id,
                    winner,
                    loser,
                    conflict_fields_json,
                    rule,
                    reason,
                    evidence_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision.decision_id,
                    decision.asset_id,
                    decision.winner,
                    decision.loser,
                    json.dumps(decision.conflict_fields),
                    decision.rule,
                    decision.reason,
                    json.dumps(decision.evidence),
                    decision.created_at.isoformat(),
                ),
            )
            self._connection.commit()

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def _initialize(self) -> None:
        with self._lock:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS canonical_assets (
                    asset_id TEXT PRIMARY KEY,
                    location TEXT NOT NULL,
                    status TEXT NOT NULL,
                    faults_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    source TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS decision_log (
                    decision_id TEXT PRIMARY KEY,
                    asset_id TEXT NOT NULL,
                    winner TEXT NOT NULL,
                    loser TEXT NOT NULL,
                    conflict_fields_json TEXT NOT NULL,
                    rule TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_decision_log_asset_id
                ON decision_log(asset_id);
                """
            )
            self._connection.commit()

    def _asset_from_row(self, row: sqlite3.Row) -> AssetRecord:
        return AssetRecord(
            asset_id=row["asset_id"],
            location=row["location"],
            status=row["status"],
            faults=json.loads(row["faults_json"]),
            updated_at=row["updated_at"],
            source=row["source"],
        )

    def _decision_from_row(self, row: sqlite3.Row) -> DecisionRecord:
        return DecisionRecord(
            decision_id=row["decision_id"],
            asset_id=row["asset_id"],
            winner=row["winner"],
            loser=row["loser"],
            conflict_fields=json.loads(row["conflict_fields_json"]),
            rule=row["rule"],
            reason=row["reason"],
            evidence=json.loads(row["evidence_json"]),
            created_at=row["created_at"],
        )


canonical_store = CanonicalStore()
