from src.core.settings import Settings
from src.core.settings import Settings
from src.domain.contracts import AppHealth
from src.sync.service import SyncRunResult, SyncService


class AdminService:
    def __init__(self, settings: Settings, sync_service: SyncService | None = None) -> None:
        self._settings = settings
        self._sync_service = sync_service

    def get_health(self) -> AppHealth:
        return AppHealth(
            bot_enabled=True,
            pricing_city=self._settings.price_city,
            environment=self._settings.app_env,
        )

    async def run_manual_refresh(self) -> SyncRunResult:
        if self._sync_service is None:
            raise RuntimeError("Sync service is not configured.")

        return await self._sync_service.run_weekly_refresh()
