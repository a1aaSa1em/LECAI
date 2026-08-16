from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


AssetStatus = Literal["operational", "idle", "faulted", "maintenance", "offline"]
SourceName = Literal["source_a", "source_b", "canonical"]


class AssetRecord(BaseModel):
    asset_id: str
    location: str
    status: AssetStatus
    faults: list[str] = Field(default_factory=list)
    updated_at: datetime
    source: SourceName


class DecisionRecord(BaseModel):
    decision_id: str
    asset_id: str
    winner: SourceName
    conflict_fields: list[str]
    reason: str
    created_at: datetime


class PollSummary(BaseModel):
    source_a_records: int
    source_b_records: int
    conflicts_detected: int
    canonical_updates: int
