"""Integration tests for the pipeline."""

import os
import sqlite3
import tempfile
from unittest.mock import MagicMock, patch
import pytest
from src.config import Config
from src.pipeline import run_pipeline


class TestPipelineIntegration:
    def _config(self, db_path):
        return Config(lastfm_api_key="test_key", s3_bucket="test-bucket", s3_key_prefix="test-prefix",
                      regions={"TestRegion": "united states"}, db_path=db_path)

    @patch("src.pipeline.backup_to_s3")
    @patch("src.pipeline.extract_artist_metadata")
    @patch("src.pipeline.extract_track_info")
    @patch("src.pipeline.extract_chart_data")
    @patch("src.pipeline.load_config")
    @patch("src.pipeline._compute_week", return_value="2025-01-06")
    def test_full_pipeline(self, mock_week, mock_cfg, mock_charts, mock_info, mock_artists, mock_backup):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            mock_cfg.return_value = self._config(db_path)
            mock_charts.return_value = [
                {"region": "TestRegion", "rank": 1, "track_id": "A::S", "track_name": "Song", "artist_id": "A"},
            ]
            mock_info.return_value = [
                {"track_id": "A::S", "listeners": 1000, "playcount": 5000, "duration": 200000, "tags": ["pop"]},
            ]
            mock_artists.return_value = [
                {"artist_id": "A", "name": "Artist", "genres": ["pop"], "followers": 1000, "popularity": 75},
            ]

            run_pipeline()

            conn = sqlite3.connect(db_path)
            charts = conn.execute("SELECT * FROM charts").fetchall()
            assert len(charts) == 1
            assert charts[0][3] == "A::S"
            info = conn.execute("SELECT * FROM track_info").fetchall()
            assert len(info) == 1
            artists = conn.execute("SELECT * FROM artists").fetchall()
            assert len(artists) == 1
            conn.close()
            mock_backup.assert_called_once()
