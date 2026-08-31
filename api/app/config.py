"""Application settings, read from environment variables (see .env.example).

Deliberately does NOT load a local .env file: the project .env is Docker Compose's
interpolation source for docker-compose.yml (wants `mailpit`, `ollama` hostnames) and
is read directly by Compose, never by the app. Inside a container the app only ever
sees real process env vars injected by Compose. Loading .env here too would make a
local host run (venv, tests, eval scripts) silently pick up container-only hostnames."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    # Defaults describe a LOCAL run (venv, tests, eval scripts) and are deliberately
    # host names, not compose service names. docker-compose.yml overrides them with
    # `ollama` and `mailpit`, which only resolve inside the compose network.
    ollama_model: str = "llama3.2:3b"
    ollama_base_url: str = "http://localhost:11434"
    llm_timeout_seconds: float = 120.0

    # Mail. Reply-To is set per request from the sender's address, never from here.
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    mail_from: str = "router@example.com"

    log_level: str = "INFO"

    @property
    def ollama_openai_url(self) -> str:
        """Ollama's OpenAI-compatible endpoint, which is what pydantic-ai talks to."""
        return f"{self.ollama_base_url.rstrip('/')}/v1"


@lru_cache
def get_settings() -> Settings:
    """Cached so the whole app shares one instance."""
    return Settings()
