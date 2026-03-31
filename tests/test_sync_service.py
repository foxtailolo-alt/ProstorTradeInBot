from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from src.domain.enums import SupportedCategory
from src.domain.snapshot_schema import CategorySchema, SnapshotSchema
from src.sync.service import SyncService


@dataclass(slots=True)
class StubImporter:
    snapshot: SnapshotSchema

    async def import_snapshot(self) -> SnapshotSchema:
        return self.snapshot


@dataclass(slots=True)
class StubPersistedSnapshot:
    id: str
    version: int
    imported_at: datetime


@dataclass(slots=True)
class StubSnapshotRepository:
    persisted_snapshot: StubPersistedSnapshot
    saved_snapshot: SnapshotSchema | None = None

    async def create_draft_snapshot(self, snapshot_schema: SnapshotSchema) -> StubPersistedSnapshot:
        self.saved_snapshot = snapshot_schema
        return self.persisted_snapshot


async def test_sync_service_persists_imported_snapshot() -> None:
    snapshot = SnapshotSchema(
        version=1,
        source_name="damprodam_api",
        pricing_city="moscow",
        imported_at=datetime(2026, 3, 31, tzinfo=UTC),
        categories=(
            CategorySchema(
                category_code=SupportedCategory.IPHONE,
                title="iPhone",
                models=(),
                questions=(),
            ),
        ),
    )
    persisted_snapshot = StubPersistedSnapshot(
        id="snapshot-1",
        version=4,
        imported_at=datetime(2026, 4, 1, tzinfo=UTC),
    )
    repository = StubSnapshotRepository(persisted_snapshot)
    service = SyncService(StubImporter(snapshot), repository)

    result = await service.run_weekly_refresh()

    assert repository.saved_snapshot == snapshot
    assert result.snapshot_id == "snapshot-1"
    assert result.version == 4
    assert result.category_count == 1
    assert result.imported_at == persisted_snapshot.imported_at