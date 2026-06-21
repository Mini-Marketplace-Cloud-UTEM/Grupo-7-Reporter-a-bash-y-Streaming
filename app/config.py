"""Configuración centralizada del servicio leída desde variables de entorno o archivo .env."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Parámetros de configuración del servicio de Reportería."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Entorno de ejecución
    APP_ENV: str = "development"
    APP_PORT: int = 8070

    # Supabase (base de datos y storage)
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    DATABASE_URL: str = ""

    # Google Cloud Pub/Sub — suscripciones a los tópicos de eventos upstream
    GOOGLE_CLOUD_PROJECT: str = ""
    PUBSUB_SUBSCRIPTION_ORDER_CREATED: str = ""
    PUBSUB_SUBSCRIPTION_PAYMENT_APPROVED: str = ""
    PUBSUB_SUBSCRIPTION_INVENTORY_SHORTAGE: str = ""
    PUBSUB_SUBSCRIPTION_SHIPMENT_DELIVERED: str = ""


settings = Settings()
