from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from src.domain.snapshot_schema import SnapshotSchema
from src.parser.contracts import SnapshotImporter
from src.storage.models.snapshot import Snapshot
from src.storage.repositories.snapshot_repository import SnapshotRepository


@dataclass(slots=True, frozen=True)
class SyncRunResult:
    snapshot_id: str
    version: int
    category_count: int
    imported_at: datetime


class SyncService:
    def __init__(self, importer: SnapshotImporter, snapshot_repository: SnapshotRepository) -> None:
        self._importer = importer
        self._snapshot_repository = snapshot_repository

    async def run_weekly_refresh(self) -> SyncRunResult:
        snapshot_schema = await self._importer.import_snapshot()
        persisted_snapshot = await self._snapshot_repository.create_draft_snapshot(snapshot_schema)
        return self._build_result(snapshot_schema, persisted_snapshot)

    def _build_result(self, snapshot_schema: SnapshotSchema, persisted_snapshot: Snapshot) -> SyncRunResult:
        imported_at = persisted_snapshot.imported_at or snapshot_schema.imported_at or datetime.now(tz=UTC)
        return SyncRunResult(
            snapshot_id=persisted_snapshot.id,
            version=persisted_snapshot.version,
            category_count=len(snapshot_schema.categories),
            imported_at=imported_at,
        )
