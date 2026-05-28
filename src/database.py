"""SQLite schema and helpers for Spotify Tracker."""

import sqlite3
from datetime import datetime

import pandas as pd

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS listening_history (
    played_at TEXT PRIMARY KEY,
    track_id TEXT NOT NULL,
    track_name TEXT NOT NULL,
    artist_id TEXT NOT NULL,
    artist_name TEXT NOT NULL,
    album_id TEXT,
    album_name TEXT,
    album_art_url TEXT,
    duration_ms INTEGER,
    popularity INTEGER,
    preview_url TEXT
);

CREATE TABLE IF NOT EXISTS top_tracks (
    snapshot_date TEXT NOT NULL,
    time_range TEXT NOT NULL,
    rank INTEGER NOT NULL,
    track_id TEXT NOT NULL,
    track_name TEXT NOT NULL,
    artist_id TEXT NOT NULL,
    artist_name TEXT NOT NULL,
    album_name TEXT,
    album_art_url TEXT,
    popularity INTEGER,
    PRIMARY KEY (snapshot_date, time_range, rank)
);

CREATE TABLE IF NOT EXISTS top_artists (
    snapshot_date TEXT NOT NULL,
    time_range TEXT NOT NULL,
    rank INTEGER NOT NULL,
    artist_id TEXT NOT NULL,
    artist_name TEXT NOT NULL,
    genres TEXT,
    popularity INTEGER,
    followers INTEGER,
    image_url TEXT,
    PRIMARY KEY (snapshot_date, time_range, rank)
);

CREATE TABLE IF NOT EXISTS audio_features (
    track_id TEXT PRIMARY KEY,
    danceability REAL,
    energy REAL,
    valence REAL,
    tempo REAL,
    acousticness REAL,
    instrumentalness REAL,
    speechiness REAL,
    liveness REAL,
    loudness REAL,
    key_sig INTEGER,
    mode INTEGER,
    time_signature INTEGER
);

CREATE TABLE IF NOT EXISTS saved_tracks (
    track_id TEXT PRIMARY KEY,
    added_at TEXT,
    track_name TEXT,
    artist_name TEXT,
    album_name TEXT,
    album_art_url TEXT
);
"""


def get_connection(db_path: str) -> sqlite3.Connection:
    return sqlite3.connect(db_path)


def initialize_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA_SQL)


def get_latest_played_at(conn: sqlite3.Connection) -> str | None:
    """Return the most recent played_at timestamp, or None."""
    cur = conn.execute("SELECT MAX(played_at) FROM listening_history")
    row = cur.fetchone()
    return row[0] if row and row[0] else None


def get_listening_history(conn: sqlite3.Connection, limit: int = 500) -> pd.DataFrame:
    return pd.read_sql_query(
        "SELECT * FROM listening_history ORDER BY played_at DESC LIMIT ?",
        conn, params=(limit,),
    )


def get_top_tracks(conn: sqlite3.Connection, time_range: str = "medium_term", snapshot_date: str | None = None) -> pd.DataFrame:
    if snapshot_date:
        return pd.read_sql_query(
            "SELECT * FROM top_tracks WHERE time_range = ? AND snapshot_date = ? ORDER BY rank",
            conn, params=(time_range, snapshot_date),
        )
    return pd.read_sql_query(
        "SELECT * FROM top_tracks WHERE time_range = ? AND snapshot_date = (SELECT MAX(snapshot_date) FROM top_tracks WHERE time_range = ?) ORDER BY rank",
        conn, params=(time_range, time_range),
    )


def get_top_artists(conn: sqlite3.Connection, time_range: str = "medium_term", snapshot_date: str | None = None) -> pd.DataFrame:
    if snapshot_date:
        return pd.read_sql_query(
            "SELECT * FROM top_artists WHERE time_range = ? AND snapshot_date = ? ORDER BY rank",
            conn, params=(time_range, snapshot_date),
        )
    return pd.read_sql_query(
        "SELECT * FROM top_artists WHERE time_range = ? AND snapshot_date = (SELECT MAX(snapshot_date) FROM top_artists WHERE time_range = ?) ORDER BY rank",
        conn, params=(time_range, time_range),
    )


def get_audio_features(conn: sqlite3.Connection, track_ids: list[str]) -> pd.DataFrame:
    if not track_ids:
        return pd.DataFrame()
    placeholders = ",".join("?" for _ in track_ids)
    return pd.read_sql_query(
        f"SELECT * FROM audio_features WHERE track_id IN ({placeholders})",
        conn, params=track_ids,
    )
