"""Tests for src/load.py."""

import sqlite3
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest
from botocore.exceptions import ClientError
from src.load import backup_to_s3, load_to_sqlite


def _charts():
    return pd.DataFrame([{"week": "2025-01-06", "region": "US", "rank": 1, "track_id": "A::S", "track_name": "Song", "artist_id": "A", "track_status": "new_entry"}])

def _info():
    return pd.DataFrame([{"track_id": "A::S", "listeners": 1000, "playcount": 5000, "duration": 200000, "tags": ["pop"]}])

def _artists():
    return pd.DataFrame([{"artist_id": "A", "name": "Artist", "genres": ["pop"], "followers": 1000, "popularity": 75}])


class TestLoadToSqlite:
    def test_writes_charts(self, tmp_path):
        db = str(tmp_path / "t.db")
        load_to_sqlite(db, _charts(), _info(), _artists())
        conn = sqlite3.connect(db)
        assert len(conn.execute("SELECT * FROM charts").fetchall()) == 1
        conn.close()

    def test_writes_track_info(self, tmp_path):
        db = str(tmp_path / "t.db")
        load_to_sqlite(db, _charts(), _info(), _artists())
        conn = sqlite3.connect(db)
        rows = conn.execute("SELECT * FROM track_info").fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "A::S"
        conn.close()

    def test_writes_artists(self, tmp_path):
        db = str(tmp_path / "t.db")
        load_to_sqlite(db, _charts(), _info(), _artists())
        conn = sqlite3.connect(db)
        assert len(conn.execute("SELECT * FROM artists").fetchall()) == 1
        conn.close()

    def test_upsert_track_info(self, tmp_path):
        db = str(tmp_path / "t.db")
        load_to_sqlite(db, _charts(), _info(), _artists())
        updated = _info()
        updated["listeners"] = 9999
        load_to_sqlite(db, _charts(), updated, _artists())
        conn = sqlite3.connect(db)
        val = conn.execute("SELECT listeners FROM track_info WHERE track_id='A::S'").fetchone()[0]
        assert val == 9999
        conn.close()

    def test_empty_dfs(self, tmp_path):
        db = str(tmp_path / "t.db")
        empty_c = pd.DataFrame(columns=["week", "region", "rank", "track_id", "track_name", "artist_id", "track_status"])
        empty_i = pd.DataFrame(columns=["track_id", "listeners", "playcount", "duration", "tags"])
        empty_a = pd.DataFrame(columns=["artist_id", "name", "genres", "followers", "popularity"])
        load_to_sqlite(db, empty_c, empty_i, empty_a)


class TestBackupToS3:
    @patch("src.load.boto3")
    def test_uploads(self, mock_boto3, tmp_path):
        db = tmp_path / "t.db"
        db.write_text("data")
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        backup_to_s3(str(db), "bucket", "prefix", "2025-01-06")
        mock_client.upload_file.assert_called_once()

    @patch("src.load.boto3")
    def test_failure_no_raise(self, mock_boto3, tmp_path):
        db = tmp_path / "t.db"
        db.write_text("data")
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_client.upload_file.side_effect = ClientError(
            {"Error": {"Code": "403", "Message": "Forbidden"}, "ResponseMetadata": {"HTTPStatusCode": 403}}, "PutObject")
        backup_to_s3(str(db), "bucket", "prefix", "2025-01-06")
