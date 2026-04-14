from dataclasses import dataclass
from datetime import UTC, datetime

from src.admin.service import AdminService
from src.core.settings import Settings
from src.sync.service import SyncRunResult


@dataclass(slots=True)
class StubSyncService:
    result: SyncRunResult
    call_count: int = 0

    async def run_weekly_refresh(self) -> SyncRunResult:
        self.call_count += 1
        return self.result


def test_admin_service_uses_moscow_pricing() -> None:
    settings = Settings(
        _env_file=None,
        BOT_TOKEN="token",
        ADMIN_TELEGRAM_IDS="1,2",
        DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/test",
        PRICE_CITY="moscow",
    )
    service = AdminService(settings)

    health = service.get_health()

    assert health.pricing_city == "moscow"
    assert health.bot_enabled is True


async def test_admin_service_runs_manual_refresh() -> None:
    settings = Settings(
        _env_file=None,
        BOT_TOKEN="token",
        ADMIN_TELEGRAM_IDS="1,2",
        DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/test",
        PRICE_CITY="moscow",
    )
    sync_service = StubSyncService(
        SyncRunResult(
            snapshot_id="snapshot-42",
            version=42,
            status="active",
            category_count=5,
            imported_at=datetime(2026, 3, 31, tzinfo=UTC),
        )
    )
    service = AdminService(settings, sync_service)

    result = await service.run_manual_refresh()

    assert sync_service.call_count == 1
    assert result.snapshot_id == "snapshot-42"
    assert result.status == "active"
    assert result.category_count == 5
