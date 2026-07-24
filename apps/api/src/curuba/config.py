"""Configuración: todo sale del entorno, nada hardcodeado."""

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openrouter_api_key: str
    curuba_model: str = "openrouter:anthropic/claude-sonnet-5"

    # Railway la inyecta sola vía ${{Postgres.DATABASE_URL}}. En local se usa
    # la URL PÚBLICA del servicio de Postgres.
    database_url: str = ""

    # Vacías por defecto a propósito: así puedes correr el agente en local
    # con solo la llave de OpenRouter. Solo hacen falta para ENVIAR por
    # WhatsApp y para validar la firma del webhook.
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = ""

    # Se apaga solo para pruebas locales, donde Twilio no está firmando nada.
    validate_twilio_signature: bool = True


settings = Settings()

# Pydantic AI busca OPENROUTER_API_KEY en os.environ, no en este objeto.
# En Railway la variable ya está en el entorno real, pero en local sale del
# archivo .env — y pydantic-settings lo lee sin exportarlo. Sin esta línea
# el agente falla en local con "no API key" aunque el .env esté bien.
os.environ.setdefault("OPENROUTER_API_KEY", settings.openrouter_api_key)
