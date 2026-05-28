"""Tests for dashboard helpers."""

import json
import sqlite3
import pytest
from src.dashboard import load_filtered_charts, load_genres, load_regions, load_weeks
from src.database import initialize_schema


@pytest.fixture()
def db_conn():
    conn = sqlite3.connect(":memory:")
    initialize_schema(conn)
    conn.executemany("INSERT INTO charts VALUES (?,?,?,?,?,?,?)", [
        ("2024-01-01", "US", 1, "A::S1", "S1", "A", "rising"),
        ("2024-01-01", "UK", 1, "B::S2", "S2", "B", "new_entry"),
        ("2024-01-08", "US", 1, "A::S1", "S1", "A", "stable_or_falling"),
    ])
    conn.executemany("INSERT INTO track_info VALUES (?,?,?,?,?)", [
        ("A::S1", 1000, 5000, 200000, json.dumps(["pop"])),
        ("B::S2", 500, 2000, 180000, json.dumps(["rock"])),
    ])
    conn.executemany("INSERT INTO artists VALUES (?,?,?,?,?)", [
        ("A", "Artist A", json.dumps(["pop", "rock"]), 100000, 90),
        ("B", "Artist B", json.dumps(["hip-hop"]), 50000, 75),
    ])
    conn.commit()
    yield conn
    conn.close()


def test_load_weeks(db_conn):
    assert load_weeks(db_conn) == ["2024-01-01", "2024-01-08"]

def test_load_regions(db_conn):
    assert load_regions(db_conn) == ["UK", "US"]

def test_load_genres(db_conn):
    assert load_genres(db_conn) == ["hip-hop", "pop", "rock"]

def test_filtered_by_region(db_conn):
    df = load_filtered_charts(db_conn, ["US"], "2024-01-01", "2024-01-08")
    assert set(df["region"].unique()) == {"US"}

def test_filtered_by_genre(db_conn):
    df = load_filtered_charts(db_conn, ["US", "UK"], "2024-01-01", "2024-01-08", genres=["hip-hop"])
    assert all(df["artist_id"] == "B")

def test_empty_result(db_conn):
    df = load_filtered_charts(db_conn, ["Japan"], "2024-01-01", "2024-01-08")
    assert df.empty
