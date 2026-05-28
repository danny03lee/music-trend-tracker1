"""SQLite connection management and schema initialization for Music Trend Tracker."""

import sqlite3

import pandas as pd

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS charts (
    week TEXT NOT NULL,
    region TEXT NOT NULL,
    rank INTEGER NOT NULL,
    track_id TEXT NOT NULL,
    track_name TEXT NOT NULL,
    artist_id TEXT NOT NULL,
    track_status TEXT,
    PRIMARY KEY (week, region, track_id)
);

CREATE TABLE IF NOT EXISTS track_info (
    track_id TEXT PRIMARY KEY,
    listeners INTEGER,
    playcount INTEGER,
    duration INTEGER,
    tags TEXT
);

CREATE TABLE IF NOT EXISTS artists (
    artist_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    genres TEXT,
    followers INTEGER,
    popularity INTEGER
);
"""


def get_connection(db_path: str) -> sqlite3.Connection:
    """Return a connection to the SQLite database at *db_path*."""
    return sqlite3.connect(db_path)


def initialize_schema(conn: sqlite3.Connection) -> None:
    """Create the charts, track_info, and artists tables if they don't exist."""
    conn.executescript(_SCHEMA_SQL)


def get_previous_weeks_data(
    conn: sqlite3.Connection,
    region: str,
    n_weeks: int = 3,
) -> pd.DataFrame:
    """Retrieve chart data for the most recent *n_weeks* weeks for *region*."""
    query = """
        SELECT week, region, rank, track_id, track_name, artist_id, track_status
        FROM charts
        WHERE region = ?
          AND week IN (
              SELECT DISTINCT week
              FROM charts
              WHERE region = ?
              ORDER BY week DESC
              LIMIT ?
          )
        ORDER BY week DESC, rank ASC
    """
    return pd.read_sql_query(query, conn, params=(region, region, n_weeks))
