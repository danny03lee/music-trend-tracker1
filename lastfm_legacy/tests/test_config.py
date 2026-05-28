"""Tests for src.config module."""

import pytest
from src.config import Config, load_config, DEFAULT_REGIONS, DEFAULT_DB_PATH, DEFAULT_S3_KEY_PREFIX


@pytest.fixture
def required_env(monkeypatch):
    monkeypatch.setenv("LASTFM_API_KEY", "test-api-key")
    monkeypatch.setenv("S3_BUCKET", "my-bucket")


class TestLoadConfigSuccess:
    def test_loads_with_required_env_vars(self, required_env):
        cfg = load_config()
        assert cfg.lastfm_api_key == "test-api-key"
        assert cfg.s3_bucket == "my-bucket"

    def test_default_regions(self, required_env):
        cfg = load_config()
        assert cfg.regions == DEFAULT_REGIONS
        assert len(cfg.regions) == 5

    def test_default_db_path(self, required_env):
        cfg = load_config()
        assert cfg.db_path == DEFAULT_DB_PATH

    def test_default_s3_key_prefix(self, required_env):
        cfg = load_config()
        assert cfg.s3_key_prefix == DEFAULT_S3_KEY_PREFIX

    def test_env_overrides_db_path(self, required_env, monkeypatch):
        monkeypatch.setenv("DB_PATH", "/tmp/custom.db")
        cfg = load_config()
        assert cfg.db_path == "/tmp/custom.db"

    def test_env_overrides_s3_key_prefix(self, required_env, monkeypatch):
        monkeypatch.setenv("S3_KEY_PREFIX", "custom-prefix")
        cfg = load_config()
        assert cfg.s3_key_prefix == "custom-prefix"


class TestLoadConfigMissingValues:
    def test_missing_api_key_raises(self, monkeypatch):
        monkeypatch.setenv("S3_BUCKET", "bucket")
        monkeypatch.delenv("LASTFM_API_KEY", raising=False)
        with pytest.raises(ValueError, match="LASTFM_API_KEY"):
            load_config()

    def test_missing_s3_bucket_raises(self, monkeypatch):
        monkeypatch.setenv("LASTFM_API_KEY", "key")
        monkeypatch.delenv("S3_BUCKET", raising=False)
        with pytest.raises(ValueError, match="S3_BUCKET"):
            load_config()

    def test_missing_multiple_values_lists_all(self, monkeypatch):
        monkeypatch.delenv("LASTFM_API_KEY", raising=False)
        monkeypatch.delenv("S3_BUCKET", raising=False)
        with pytest.raises(ValueError) as exc_info:
            load_config()
        msg = str(exc_info.value)
        assert "LASTFM_API_KEY" in msg
        assert "S3_BUCKET" in msg


class TestConfigDataclass:
    def test_config_fields(self):
        cfg = Config(lastfm_api_key="key", s3_bucket="bucket")
        assert cfg.lastfm_api_key == "key"
        assert cfg.db_path == DEFAULT_DB_PATH
        assert cfg.regions == DEFAULT_REGIONS
