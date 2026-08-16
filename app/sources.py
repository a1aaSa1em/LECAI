from .models import AssetRecord


SOURCE_A_SNAPSHOT = [
    AssetRecord(
        asset_id="robot-17",
        location="Dock 1",
        status="idle",
        faults=[],
        updated_at="2026-08-16T10:00:00Z",
        source="source_a",
    ),
    AssetRecord(
        asset_id="sensor-22",
        location="Zone B",
        status="operational",
        faults=[],
        updated_at="2026-08-16T10:02:00Z",
        source="source_a",
    ),
]

SOURCE_B_SNAPSHOT = [
    AssetRecord(
        asset_id="robot-17",
        location="Dock 1",
        status="idle",
        faults=[],
        updated_at="2026-08-16T10:00:05Z",
        source="source_b",
    ),
    AssetRecord(
        asset_id="sensor-22",
        location="Zone B",
        status="operational",
        faults=[],
        updated_at="2026-08-16T10:02:03Z",
        source="source_b",
    ),
]


def get_source_a_assets() -> list[AssetRecord]:
    return SOURCE_A_SNAPSHOT


def get_source_b_assets() -> list[AssetRecord]:
    return SOURCE_B_SNAPSHOT
