import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Kubernetes Troubleshooting Agent"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "anthropic/claude-3-sonnet"
    KUBECONFIG_PATH: str = ""
    INSFORGE_URL: str = "https://y8swi44k.us-east.insforge.app"
    INSFORGE_API_KEY: str = "ik_4327bb1f4e937e2b5d86e8a0e6a0e074"

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
