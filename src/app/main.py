import asyncio

import structlog

from src.app.container import build_container
from src.core.logging import configure_logging


async def run() -> None:
    container, dispatcher, bot = build_container()
    configure_logging(container.settings.log_level)
    logger = structlog.get_logger(__name__)
    logger.info(
        "app_started",
        environment=container.settings.app_env,
        pricing_city=container.settings.price_city,
    )
    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()
        await container.database.dispose()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
