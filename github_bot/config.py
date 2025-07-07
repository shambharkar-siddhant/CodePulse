# github_bot/config.py

import os
from dotenv import load_dotenv

load_dotenv()  # Load from .env if available


class Settings:
    APP_ID: str = os.getenv("APP_ID", "")
    PRIVATE_KEY_PATH: str = os.getenv("PRIVATE_KEY_PATH", "")
    WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "")
    MCP_URL: str = os.getenv("MCP_URL", "")
    MCP_SERVER_URL: str = os.getenv("MCP_SERVER_URL", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "")
    GITHUB_REDIRECT_URI: str = os.getenv("GITHUB_REDIRECT_URI", "")
    GITHUB_CLIENT_ID: str = os.getenv("GITHUB_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET: str = os.getenv("GITHUB_CLIENT_SECRET", "")
    # Add more configs as needed (e.g. DEBUG, LOG_LEVEL, etc.)


settings = Settings()
