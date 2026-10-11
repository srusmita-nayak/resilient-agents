import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    BACKEND_HOST: str = "127.0.0.1"
    BACKEND_PORT: int = 8000
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    
    # Database
    DATABASE_PATH: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent / "resilient_agents.db")
    SQLITE_TIMEOUT_SECONDS: float = 30.0
    
    # LLM Settings (Safe placeholders; never exposed or committed)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    LLM_CALL_BUDGET: int = 50
    LLM_TIMEOUT_SECONDS: float = 10.0
    
    # Simulation Defaults
    MAX_SIMULATED_TIME_DEFAULT: float = 1000.0
    MAX_EVENTS_DEFAULT: int = 10000
    MAX_WALL_SECONDS_DEFAULT: float = 60.0
    
    # System info
    VERSION: str = "1.0.0"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
