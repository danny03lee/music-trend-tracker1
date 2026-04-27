"""Tests for src/database.py."""

import sqlite3
import pandas as pd
import pytest
from src.database import get_connection, get_previous_weeks_data, initialize_schema


class TestGetConnection:
    def test_returns_sqlite_connection(self, tmp_path):
        conn = get_connection(str(tmp_path / "test.db"))
        assert isinstance(conn, sqlite3.Connection)
        conn.close()


class TestInitializeSchema:
    def test_creates_all_three_tables(self, tmp_path):
        conn = get_connection(str(tmp_path / "test.db"))
        initialize_schema(conn)
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert "charts" in tables
        assert "track_info" in tables
        assert "artists" in tables
        conn.close()

    def test_track_info_columns(self, tmp_path):
        conn = get_connection(str(tmp_path / "test.db"))
        initialize_schema(conn)
        cols = [r[1] for r in conn.execute("PRAGMA table_info(track_info)").fetchall()]
        assert cols == ["track_id", "listeners", "playcount", "duration", "tags"]
        conn.close()

    def test_idempotent(self, tmp_path):
        conn = get_connection(str(tmp_path / "test.db"))
        initialize_schema(conn)
        initialize_schema(conn)
        conn.close()


class TestGetPreviousWeeksData:
    @pytest.fixture()
    def conn(self, tmp_path):
        c = get_connection(str(tmp_path / "test.db"))
        initialize_schema(c)
        yield c
        c.close()

    def _insert(self, conn, week, region, rank, track_id):
        conn.execute("INSERT INTO charts (week,region,rank,track_id,track_name,artist_id) VALUES (?,?,?,?,?,?)",
                      (week, region, rank, track_id, "t", "a"))
        conn.commit()

    def test_empty(self, conn):
        assert get_previous_weeks_data(conn, "US").empty

    def test_filters_by_region(self, conn):
        self._insert(conn, "2025-01-06", "US", 1, "t1")
        self._insert(conn, "2025-01-06", "UK", 1, "t2")
        df = get_previous_weeks_data(conn, "US")
        assert len(df) == 1

    def test_limits_weeks(self, conn):
        for i, w in enumerate(["2025-01-06", "2025-01-13", "2025-01-20", "2025-01-27"]):
            self._insert(conn, w, "US", 1, f"t{i}")
        df = get_previous_weeks_data(conn, "US", n_weeks=2)
        assert len(df["week"].unique()) == 2
