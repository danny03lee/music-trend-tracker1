"""Tests for database module."""

import sqlite3
import tempfile
import os

import pytest

from src.database import get_connection, initialize_schema, get_listening_history, get_top_tracks


@pytest.fixture
def db_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.db")
        conn = get_connection(path)
        initialize_schema(conn)
        conn.close()
        yield path


class TestSchema:
    def test_creates_tables(self, db_path):
        conn = sqlite3.connect(db_path)
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = {t[0] for t in tables}
        assert "listening_history" in table_names
        assert "top_tracks" in table_names
        assert "top_artists" in table_names
        assert "audio_features" in table_names
        assert "saved_tracks" in table_names
        conn.close()


class TestGetListeningHistory:
    def test_empty_db(self, db_path):
        conn = get_connection(db_path)
        df = get_listening_history(conn)
        assert df.empty
        conn.close()

    def test_returns_data(self, db_path):
        conn = get_connection(db_path)
        conn.execute(
            "INSERT INTO listening_history VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("2025-06-01T12:00:00Z", "t1", "Song", "a1", "Artist",
             "alb1", "Album", "", 200000, 70, ""),
        )
        conn.commit()
        df = get_listening_history(conn)
        assert len(df) == 1
        assert df.iloc[0]["track_name"] == "Song"
        conn.close()
