"""Load extracted Spotify data into SQLite."""

import json
import logging
import sqlite3

from src.database import get_connection, initialize_schema

logger = logging.getLogger(__name__)


def load_recently_played(db_path: str, tracks: list[dict]) -> int:
    """Insert recently played tracks. Returns count of new rows."""
    if not tracks:
        return 0
    conn = get_connection(db_path)
    initialize_schema(conn)
    inserted = 0
    for t in tracks:
        try:
            conn.execute(
                """INSERT OR IGNORE INTO listening_history
                   (played_at, track_id, track_name, artist_id, artist_name,
                    album_id, album_name, album_art_url, duration_ms, popularity, preview_url)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (t["played_at"], t["track_id"], t["track_name"], t["artist_id"],
                 t["artist_name"], t["album_id"], t["album_name"], t["album_art_url"],
                 t["duration_ms"], t["popularity"], t["preview_url"]),
            )
            inserted += conn.total_changes
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    conn.close()
    return inserted


def load_top_tracks(db_path: str, tracks: list[dict]) -> None:
    if not tracks:
        return
    conn = get_connection(db_path)
    initialize_schema(conn)
    for t in tracks:
        conn.execute(
            """INSERT OR REPLACE INTO top_tracks
               (snapshot_date, time_range, rank, track_id, track_name,
                artist_id, artist_name, album_name, album_art_url, popularity)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (t["snapshot_date"], t["time_range"], t["rank"], t["track_id"],
             t["track_name"], t["artist_id"], t["artist_name"],
             t["album_name"], t["album_art_url"], t["popularity"]),
        )
    conn.commit()
    conn.close()


def load_top_artists(db_path: str, artists: list[dict]) -> None:
    if not artists:
        return
    conn = get_connection(db_path)
    initialize_schema(conn)
    for a in artists:
        conn.execute(
            """INSERT OR REPLACE INTO top_artists
               (snapshot_date, time_range, rank, artist_id, artist_name,
                genres, popularity, followers, image_url)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (a["snapshot_date"], a["time_range"], a["rank"], a["artist_id"],
             a["artist_name"], json.dumps(a.get("genres", [])),
             a["popularity"], a["followers"], a.get("image_url", "")),
        )
    conn.commit()
    conn.close()


def load_audio_features(db_path: str, features: list[dict]) -> None:
    if not features:
        return
    conn = get_connection(db_path)
    initialize_schema(conn)
    for f in features:
        conn.execute(
            """INSERT OR REPLACE INTO audio_features
               (track_id, danceability, energy, valence, tempo, acousticness,
                instrumentalness, speechiness, liveness, loudness, key_sig, mode, time_signature)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (f["track_id"], f["danceability"], f["energy"], f["valence"],
             f["tempo"], f["acousticness"], f["instrumentalness"],
             f["speechiness"], f["liveness"], f["loudness"],
             f["key_sig"], f["mode"], f["time_signature"]),
        )
    conn.commit()
    conn.close()


def load_saved_tracks(db_path: str, tracks: list[dict]) -> None:
    if not tracks:
        return
    conn = get_connection(db_path)
    initialize_schema(conn)
    for t in tracks:
        conn.execute(
            """INSERT OR REPLACE INTO saved_tracks
               (track_id, added_at, track_name, artist_name, album_name, album_art_url)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (t["track_id"], t["added_at"], t["track_name"],
             t["artist_name"], t["album_name"], t["album_art_url"]),
        )
    conn.commit()
    conn.close()
