from app.core.config import Settings


def test_settings_normalize_postgresql_url_for_asyncpg() -> None:
    settings = Settings(database_url="postgresql://user:password@localhost/database")

    assert settings.database_url == "postgresql+asyncpg://user:password@localhost/database"


def test_settings_preserve_asyncpg_url() -> None:
    database_url = "postgresql+asyncpg://user:password@localhost/database"

    settings = Settings(database_url=database_url)

    assert settings.database_url == database_url


def test_settings_strip_channel_binding_and_map_sslmode() -> None:
    settings = Settings(
        database_url=(
            "postgresql://user:password@ep-x.neon.tech/db"
            "?sslmode=require&channel_binding=require"
        )
    )

    assert settings.database_url == (
        "postgresql+asyncpg://user:password@ep-x.neon.tech/db?ssl=require"
    )


def test_settings_preserve_ssl_require_query() -> None:
    database_url = "postgresql+asyncpg://user:password@ep-x.neon.tech/db?ssl=require"

    settings = Settings(database_url=database_url)

    assert settings.database_url == database_url


def test_settings_normalize_test_database_url() -> None:
    settings = Settings(
        test_database_url=(
            "postgresql://user:password@ep-x.neon.tech/test?channel_binding=require"
        )
    )

    assert settings.test_database_url == (
        "postgresql+asyncpg://user:password@ep-x.neon.tech/test"
    )

