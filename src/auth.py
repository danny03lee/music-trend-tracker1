"""Spotify OAuth authentication via spotipy."""

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from src.config import SCOPES, load_config


def get_spotify_client() -> spotipy.Spotify:
    """Get an authenticated Spotify client for the current user."""
    config = load_config()
    auth_manager = SpotifyOAuth(
        client_id=config.client_id,
        client_secret=config.client_secret,
        redirect_uri=config.redirect_uri,
        scope=" ".join(SCOPES),
        cache_path=".spotify_cache",
        open_browser=True,
    )
    return spotipy.Spotify(auth_manager=auth_manager)


def get_public_client() -> spotipy.Spotify:
    """Get a client-credentials Spotify client (no user login, public data only)."""
    from spotipy.oauth2 import SpotifyClientCredentials

    config = load_config()
    auth_manager = SpotifyClientCredentials(
        client_id=config.client_id,
        client_secret=config.client_secret,
    )
    return spotipy.Spotify(auth_manager=auth_manager)
