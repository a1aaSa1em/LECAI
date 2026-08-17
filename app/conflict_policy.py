from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from .models import CONFLICT_FIELDS, AssetRecord


RECENT_FAULT_WINDOW = timedelta(minutes=15)
SOURCE_RELIABILITY = {
    "source_a": 0.92,
    "source_b": 0.86,
}


@dataclass(frozen=True)
class PolicyDecision:
    winner: AssetRecord
    loser: AssetRecord
    conflict_fields: list[str]
    rule: str
    reason: str
    evidence: dict[str, Any]


def detect_conflict_fields(source_a: AssetRecord, source_b: AssetRecord) -> list[str]:
    if source_a.asset_id != source_b.asset_id:
        raise ValueError("Cannot compare records for different asset IDs")

    return [
        field
        for field in CONFLICT_FIELDS
        if getattr(source_a, field) != getattr(source_b, field)
    ]


def resolve_conflict(
    source_a: AssetRecord, source_b: AssetRecord
) -> PolicyDecision | None:
    conflict_fields = detect_conflict_fields(source_a, source_b)
    if not conflict_fields:
        return None

    safety_decision = _resolve_by_safety(source_a, source_b, conflict_fields)
    if safety_decision is not None:
        return safety_decision

    if source_a.updated_at != source_b.updated_at:
        winner, loser = _ordered_by_timestamp(source_a, source_b)
        return PolicyDecision(
            winner=winner,
            loser=loser,
            conflict_fields=conflict_fields,
            rule="newest_timestamp",
            reason=(
                f"{winner.source} won because its record is newer "
                f"({winner.updated_at.isoformat()} vs {loser.updated_at.isoformat()})."
            ),
            evidence={
                "winner_updated_at": winner.updated_at.isoformat(),
                "loser_updated_at": loser.updated_at.isoformat(),
            },
        )

    winner, loser = _ordered_by_reliability(source_a, source_b)
    return PolicyDecision(
        winner=winner,
        loser=loser,
        conflict_fields=conflict_fields,
        rule="source_reliability_tiebreaker",
        reason=(
            f"{winner.source} won because timestamps were tied and its configured "
            f"historical reliability score is higher "
            f"({SOURCE_RELIABILITY[winner.source]} vs {SOURCE_RELIABILITY[loser.source]})."
        ),
        evidence={
            "source_reliability": SOURCE_RELIABILITY,
            "updated_at": winner.updated_at.isoformat(),
        },
    )


def _resolve_by_safety(
    source_a: AssetRecord, source_b: AssetRecord, conflict_fields: list[str]
) -> PolicyDecision | None:
    source_a_faulted = _has_active_fault(source_a)
    source_b_faulted = _has_active_fault(source_b)

    if source_a_faulted == source_b_faulted:
        return None

    fault_record = source_a if source_a_faulted else source_b
    other_record = source_b if source_a_faulted else source_a
    fault_age = other_record.updated_at - fault_record.updated_at

    if fault_age > RECENT_FAULT_WINDOW:
        return None

    return PolicyDecision(
        winner=fault_record,
        loser=other_record,
        conflict_fields=conflict_fields,
        rule="recent_fault_safety_override",
        reason=(
            f"{fault_record.source} won because it reported an active fault within "
            f"the {int(RECENT_FAULT_WINDOW.total_seconds() / 60)} minute safety window. "
            "Recent safety-critical fault reports override normal status reports."
        ),
        evidence={
            "winner_status": fault_record.status,
            "winner_faults": fault_record.faults,
            "winner_updated_at": fault_record.updated_at.isoformat(),
            "loser_status": other_record.status,
            "loser_faults": other_record.faults,
            "loser_updated_at": other_record.updated_at.isoformat(),
            "safety_window_minutes": int(
                RECENT_FAULT_WINDOW.total_seconds() / 60
            ),
        },
    )


def _has_active_fault(record: AssetRecord) -> bool:
    return record.status == "faulted" or bool(record.faults)


def _ordered_by_timestamp(
    source_a: AssetRecord, source_b: AssetRecord
) -> tuple[AssetRecord, AssetRecord]:
    if source_a.updated_at > source_b.updated_at:
        return source_a, source_b
    return source_b, source_a


def _ordered_by_reliability(
    source_a: AssetRecord, source_b: AssetRecord
) -> tuple[AssetRecord, AssetRecord]:
    source_a_score = SOURCE_RELIABILITY[source_a.source]
    source_b_score = SOURCE_RELIABILITY[source_b.source]

    if source_a_score >= source_b_score:
        return source_a, source_b
    return source_b, source_a
