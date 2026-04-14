from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.bot.routers.common import router as common_router
from src.bot.routers.wizard import build_router as build_wizard_router
from src.catalog.service import CatalogService
from src.core.settings import Settings
from src.lead.service import LeadService
from src.pricing.service import PricingService


def build_dispatcher(
    catalog_service: CatalogService,
    pricing_service: PricingService,
    lead_service: LeadService,
) -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.include_router(build_wizard_router(catalog_service, pricing_service, lead_service))
    dispatcher.include_router(common_router)
    return dispatcher


def build_bot(settings: Settings) -> Bot:
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
