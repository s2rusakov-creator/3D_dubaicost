from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://dubaicost:changeme@localhost:5432/dubaicost"
    api_cors_origins: str = "http://localhost:5173"
    log_level: str = "INFO"

    # Dubai Pulse / DLD open data (бесплатно, но нужна регистрация приложения)
    dubai_pulse_client_id: str = ""
    dubai_pulse_client_secret: str = ""
    dubai_pulse_token_url: str = ""
    dubai_pulse_base_url: str = ""
    # Прямые ссылки на bulk CSV DLD (открытые данные, OAuth не нужен)
    dld_sales_csv_url: str = ""
    dld_rent_csv_url: str = ""
    # Транзакции старше этого года не грузим (полный датасет — с 2003)
    sales_since_year: int = 2010

    # Токен для admin-эндпоинтов (review-очередь matching'а). Пусто = эндпоинты закрыты.
    admin_token: str = ""

    # Алерты (опционально)
    alert_telegram_bot_token: str = ""
    alert_telegram_chat_id: str = ""

    # Пути внутри контейнера
    data_dir: str = "/data"   # ручные конфиги (cooling_tariffs.yaml и т.п.)
    raw_dir: str = "/raw"     # скачанные сырые файлы


settings = Settings()
