from dataclasses import dataclass

from src.admin.service import AdminService
from src.bot.factory import build_bot, build_dispatcher
from src.core.settings import Settings, get_settings
from src.parser.damprodam import DamProdamApiClient, DamProdamSnapshotImporter
from src.storage.db import Database
from src.storage.repositories.snapshot_repository import SnapshotRepository
from src.sync.service import SyncService


@dataclass(slots=True)
class AppContainer:
    settings: Settings
    database: Database
    admin_service: AdminService
    sync_service: SyncService


def build_container() -> tuple[AppContainer, object, object]:
    settings = get_settings()
    database = Database(settings)
    snapshot_repository = SnapshotRepository(database.session_factory)
    api_client = DamProdamApiClient()
    importer = DamProdamSnapshotImporter(api_client, pricing_city=settings.price_city)
    sync_service = SyncService(importer, snapshot_repository)
    admin_service = AdminService(settings, sync_service)
    dispatcher = build_dispatcher()
    bot = build_bot(settings)
    return AppContainer(settings, database, admin_service, sync_service), dispatcher, bot
