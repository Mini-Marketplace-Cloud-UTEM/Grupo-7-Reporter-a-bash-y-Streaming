from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    APP_ENV: str = "development"
    APP_PORT: int = 8070

    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    DATABASE_URL: str = ""

    GOOGLE_CLOUD_PROJECT: str = ""
    PUBSUB_SUBSCRIPTION_ORDER_CREATED: str = ""
    PUBSUB_SUBSCRIPTION_PAYMENT_APPROVED: str = ""
    PUBSUB_SUBSCRIPTION_INVENTORY_SHORTAGE: str = ""
    PUBSUB_SUBSCRIPTION_SHIPMENT_DELIVERED: str = ""


settings = Settings()
