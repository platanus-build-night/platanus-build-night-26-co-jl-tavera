"""Configuración: todo sale del entorno, nada hardcodeado."""

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openrouter_api_key: str
    curuba_model: str = "openrouter:anthropic/claude-sonnet-5"

    # El modelo de búsqueda web: traduce marcas comerciales a principio activo y
    # busca precios de droguería. Sale por la MISMA OPENROUTER_API_KEY — es otro
    # slug del mismo gateway, no otro proveedor ni otra llave.
    #
    # OJO: perplexity/sonar NO soporta tool calling ni response_format (sus
    # supported_parameters en OpenRouter son solo max_tokens, temperature, top_p,
    # top_k, frequency_penalty, presence_penalty y web_search_options). Y el
    # default de Pydantic AI para ese slug es structured output en modo `tool`,
    # así que un output_type pelado manda `tools` a un endpoint que no los tiene.
    # Por eso el sub-agente de agent.py usa PromptedOutput y no es opcional.
    curuba_web_model: str = "openrouter:perplexity/sonar"

    # Sonar tarda ~5 s típico y a veces 20+. El agente corre en BackgroundTasks,
    # así que el límite no es Twilio: es la paciencia de quien está esperando.
    curuba_web_timeout: float = 25.0

    # La llave PÚBLICA de solo-búsqueda que Farmatodo embebe en su propio frontend
    # para consultar su índice de Algolia. No es un secreto y no es nuestra: va acá
    # como variable, y no como constante del módulo, solo para poder arreglar una
    # rotación desde Railway sin desplegar. Si algún día deja de servir, se vuelve a
    # sacar de https://www.farmatodo.com.co/main-es2020.*.js, en `envs.prod`.
    curuba_farmatodo_key: str = "eb9544fe7bfe7ec4c1aa5e5bf7740feb"

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

    # Con esto se arman los enlaces de los PDF que Twilio descarga para
    # adjuntarlos. En Railway va la URL pública del servicio; en local, la de
    # ngrok. Sin barra al final: los enlaces se arman como f"{base}/f/{id}".
    public_base_url: str = ""


settings = Settings()

# Pydantic AI busca OPENROUTER_API_KEY en os.environ, no en este objeto.
# En Railway la variable ya está en el entorno real, pero en local sale del
# archivo .env — y pydantic-settings lo lee sin exportarlo. Sin esta línea
# el agente falla en local con "no API key" aunque el .env esté bien.
os.environ.setdefault("OPENROUTER_API_KEY", settings.openrouter_api_key)
