from persona_sim.core.config import Settings, get_settings


def get_app_settings() -> Settings:
    """Dependency wrapper for application settings."""

    return get_settings()
