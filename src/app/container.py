from dataclasses import dataclass

from src.admin.service import AdminService
from src.bot.factory import build_bot, build_dispatcher
from src.catalog.service import CatalogService
from src.core.settings import Settings, get_settings
from src.lead.service import LeadService
from src.parser.damprodam import DamProdamApiClient, DamProdamSnapshotImporter
from src.pricing.service import PricingService
from src.storage.db import Database
from src.storage.repositories.lead_repository import LeadRepository
from src.storage.repositories.snapshot_repository import SnapshotRepository
from src.sync.service import SyncService


@dataclass(slots=True)
class AppContainer:
    settings: Settings
    database: Database
    admin_service: AdminService
    sync_service: SyncService
    catalog_service: CatalogService
    pricing_service: PricingService
    lead_service: LeadService


def build_container() -> tuple[AppContainer, object, object]:
    settings = get_settings()
    database = Database(settings)
    snapshot_repository = SnapshotRepository(database.session_factory)
    lead_repository = LeadRepository(database.session_factory)
    api_client = DamProdamApiClient()
    importer = DamProdamSnapshotImporter(api_client, pricing_city=settings.price_city)
    sync_service = SyncService(importer, snapshot_repository)
    admin_service = AdminService(settings, sync_service)
    catalog_service = CatalogService(snapshot_repository, api_client)
    pricing_service = PricingService(catalog_service, api_client)
    lead_service = LeadService(lead_repository, snapshot_repository)
    dispatcher = build_dispatcher(catalog_service, pricing_service, lead_service)
    bot = build_bot(settings)
    return (
        AppContainer(
            settings=settings,
            database=database,
            admin_service=admin_service,
            sync_service=sync_service,
            catalog_service=catalog_service,
            pricing_service=pricing_service,
            lead_service=lead_service,
        ),
        dispatcher,
        bot,
    )
