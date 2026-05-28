"""Tests for Spotify config module."""

import pytest
from src.config import Config, load_config


@pytest.fixture
def spotify_env(monkeypatch):
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "test-id")
    monkeypatch.setenv("SPOTIFY_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")


class TestLoadConfig:
    def test_loads_with_env(self, spotify_env):
        cfg = load_config()
        assert cfg.client_id == "test-id"
        assert cfg.client_secret == "test-secret"

    def test_missing_client_id_raises(self, monkeypatch):
        monkeypatch.delenv("SPOTIFY_CLIENT_ID", raising=False)
        monkeypatch.delenv("SPOTIFY_CLIENT_SECRET", raising=False)
        with pytest.raises(ValueError, match="SPOTIFY_CLIENT_ID"):
            load_config()

    def test_default_db_path(self, spotify_env):
        cfg = load_config()
        assert cfg.db_path == "spotify_tracker.db"

    def test_custom_db_path(self, spotify_env, monkeypatch):
        monkeypatch.setenv("DB_PATH", "/tmp/custom.db")
        cfg = load_config()
        assert cfg.db_path == "/tmp/custom.db"
