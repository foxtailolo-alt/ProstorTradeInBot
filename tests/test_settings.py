from pathlib import Path

from src.core.settings import Settings


def test_settings_keep_moscow_default() -> None:
    settings = Settings(
        BOT_TOKEN="token",
        DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/test",
    )

    assert settings.price_city == "moscow"


def test_settings_accept_empty_admin_ids_from_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "BOT_TOKEN=token",
                "ADMIN_TELEGRAM_IDS=",
                "DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/test",
            ]
        ),
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.admin_telegram_ids == ()
