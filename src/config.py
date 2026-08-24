"""Application configuration for MeetingMind."""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import os

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    """Environment-backed settings used by the application."""

    gemini_api_key: str | None
    gemini_model: str
    data_directory: Path

    @property
    def has_gemini_key(self) -> bool:
        """Return whether a Gemini API key has been configured."""
        return bool(self.gemini_api_key)


@lru_cache
def get_settings() -> Settings:
    """Load settings once per application process."""
    data_directory = PROJECT_ROOT / "data"
    data_directory.mkdir(exist_ok=True)

    return Settings(
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.6-flash"),
        data_directory=data_directory,
    )