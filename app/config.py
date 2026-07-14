"""Configuración centralizada del servicio leída desde variables de entorno o archivo .env."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Parámetros de configuración del servicio de Reportería."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # Ignora variables de entorno del SO / Docker que no estén declaradas aquí
        # (p. ej. PUBSUB_EMULATOR_HOST que consume el cliente de Pub/Sub directamente).
        extra="ignore",
    )

    # Entorno de ejecución
    APP_ENV: str = "development"
    APP_PORT: int = 8070

    # Mocks — cuando es True el middleware mock_status intercepta X-MOCK-HTTP-STATUS
    USE_MOCKS: bool = False

    # Supabase (base de datos y storage)
    # SUPABASE_PUBLISHABLE_KEY: clave pública (antes anon_key), segura para uso en cliente/frontend.
    # SUPABASE_SECRET_KEY: clave secreta (antes service_role_key), con privilegios elevados para uso en backend.
    SUPABASE_URL: str = ""
    SUPABASE_PUBLISHABLE_KEY: str = ""
    SUPABASE_SECRET_KEY: str = ""
    DATABASE_URL: str = ""

    # Google Cloud — credenciales y proyecto
    GOOGLE_CLOUD_PROJECT: str = ""
    # Contenido del JSON de la service account codificado en base64
    GOOGLE_CLOUD_SERVICE_ACCOUNT_KEY_CONTENT: str = ""

    # Google Cloud Pub/Sub — suscripciones a los tópicos de eventos upstream
    PUBSUB_SUBSCRIPTION_ORDER_CREATED: str = ""
    PUBSUB_SUBSCRIPTION_PAYMENT_APPROVED: str = ""
    PUBSUB_SUBSCRIPTION_INVENTORY_SHORTAGE: str = ""
    PUBSUB_SUBSCRIPTION_SHIPMENT_DELIVERED: str = ""


settings = Settings()
