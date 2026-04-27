"""Centralized configuration module for Music Trend Tracker.

Reads defaults and supports overrides via environment variables.
Raises ValueError if required configuration values are missing.
"""

import os
from dataclasses import dataclass, field


DEFAULT_REGIONS: dict[str, str] = {
    "Global": "global",
    "United States": "united states",
    "United Kingdom": "united kingdom",
    "Japan": "japan",
    "Brazil": "brazil",
}

DEFAULT_DB_PATH = "music_trends.db"
DEFAULT_S3_KEY_PREFIX = "music-trends"


@dataclass
class Config:
    """Pipeline configuration container."""

    lastfm_api_key: str
    s3_bucket: str
    s3_key_prefix: str = DEFAULT_S3_KEY_PREFIX
    regions: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_REGIONS))
    db_path: str = DEFAULT_DB_PATH


def load_config() -> Config:
    """Load configuration from defaults, overridable via environment variables.

    Environment variables:
        LASTFM_API_KEY  – (required) Last.fm API key
        S3_BUCKET       – (required) S3 bucket name for backups
        S3_KEY_PREFIX   – S3 key prefix (default: "music-trends")
        DB_PATH         – SQLite database path (default: "music_trends.db")

    Returns:
        A fully populated Config instance.

    Raises:
        ValueError: If any required configuration value is missing.
    """
    lastfm_api_key = os.environ.get("LASTFM_API_KEY", "")
    s3_bucket = os.environ.get("S3_BUCKET", "")
    s3_key_prefix = os.environ.get("S3_KEY_PREFIX", DEFAULT_S3_KEY_PREFIX)
    db_path = os.environ.get("DB_PATH", DEFAULT_DB_PATH)

    missing: list[str] = []
    if not lastfm_api_key:
        missing.append("LASTFM_API_KEY")
    if not s3_bucket:
        missing.append("S3_BUCKET")

    if missing:
        raise ValueError(
            f"Missing required configuration value(s): {', '.join(missing)}. "
            "Set them as environment variables."
        )

    return Config(
        lastfm_api_key=lastfm_api_key,
        s3_bucket=s3_bucket,
        s3_key_prefix=s3_key_prefix,
        regions=dict(DEFAULT_REGIONS),
        db_path=db_path,
    )
