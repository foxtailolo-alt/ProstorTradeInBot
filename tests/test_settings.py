from src.core.settings import Settings


def test_settings_keep_moscow_default() -> None:
    settings = Settings(
        BOT_TOKEN="token",
        DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/test",
    )

    assert settings.price_city == "moscow"
