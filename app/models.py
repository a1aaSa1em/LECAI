from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


AssetStatus = Literal["operational", "idle", "faulted", "maintenance", "offline"]
SourceName = Literal["source_a", "source_b", "canonical"]
ASSET_COMPARE_FIELDS = ("asset_id", "location", "status", "faults", "updated_at")
CONFLICT_FIELDS = ("location", "status", "faults", "updated_at")


class AssetRecord(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "asset_id": "robot-17",
                    "location": "Zone A",
                    "status": "operational",
                    "faults": [],
                    "updated_at": "2026-08-16T10:01:00Z",
                    "source": "source_a",
                }
            ]
        }
    )

    asset_id: str = Field(min_length=1)
    location: str = Field(min_length=1)
    status: AssetStatus
    faults: list[str] = Field(default_factory=list)
    updated_at: datetime
    source: SourceName

    @field_validator("asset_id", "location")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value cannot be blank")
        return stripped

    @field_validator("faults")
    @classmethod
    def normalize_faults(cls, faults: list[str]) -> list[str]:
        return sorted({fault.strip() for fault in faults if fault.strip()})

    def comparison_payload(self) -> dict[str, Any]:
        return {field: getattr(self, field) for field in ASSET_COMPARE_FIELDS}


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
