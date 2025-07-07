# mcp_server/config.py

import os
from dotenv import load_dotenv

load_dotenv()  # Loads variables from a .env file in dev


class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    DEFAULT_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4")
    RULES_PATH: str = os.getenv("RULES_PATH", "mcp_server/rules.yaml")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "")
    


settings = Settings()
