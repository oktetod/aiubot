# app/core/config_extra.py
# Supplemental settings to avoid overwriting existing config.py
# Import or merge these settings in your main Settings if desired.

from pydantic import BaseSettings
from typing import Optional

class ExtraSettings(BaseSettings):
    # Project identifier - required in pipeline
    PROJECT_ID: Optional[str] = None

    # Controls how many characters of a file are considered before chunking
    MAX_CONTENT_LENGTH: int = 200_000

    # Minimum completeness score for auto-promotion / commit (0..1)
    COMPLETENESS_THRESHOLD: float = 0.95

    class Config:
        env_file = ".env"
