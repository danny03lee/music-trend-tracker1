"""Configuration for Spotify Music Tracker."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DEFAULT_DB_PATH = "spotify_tracker.db"

SCOPES = [
    "user-read-recently-played",
    "user-top-read",
    "user-read-currently-playing",
    "user-library-read",
    "playlist-read-private",
    "playlist-read-collaborative",
]


@dataclass
class Config:
    client_id: str
    client_secret: str
    redirect_uri: str
    db_path: str = DEFAULT_DB_PATH


def load_config() -> Config:
    client_id = os.environ.get("SPOTIFY_CLIENT_ID", "")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET", "")
    redirect_uri = os.environ.get("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")
    db_path = os.environ.get("DB_PATH", DEFAULT_DB_PATH)

    missing = []
    if not client_id:
        missing.append("SPOTIFY_CLIENT_ID")
    if not client_secret:
        missing.append("SPOTIFY_CLIENT_SECRET")
    if missing:
        raise ValueError(f"Missing: {', '.join(missing)}. Set them in .env or environment.")

    return Config(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        db_path=db_path,
    )
