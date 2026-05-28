"""Load layer for Music Trend Tracker."""

import json
import logging
import sqlite3

import boto3
import pandas as pd
from botocore.exceptions import ClientError

from src.database import get_connection, initialize_schema

logger = logging.getLogger(__name__)


def backup_to_s3(db_path: str, bucket: str, key_prefix: str, week: str) -> None:
    """Upload the SQLite database file to S3."""
    s3_key = f"{key_prefix}/{week}/music_trends.db"
    try:
        s3_client = boto3.client("s3")
        s3_client.upload_file(db_path, bucket, s3_key)
        logger.info("Backed up %s to s3://%s/%s", db_path, bucket, s3_key)
    except ClientError as exc:
        http_status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", "unknown")
        logger.error("S3 upload failed for bucket=%s key=%s (HTTP %s): %s", bucket, s3_key, http_status, exc)
    except Exception:
        logger.error("S3 upload failed for bucket=%s key=%s", bucket, s3_key, exc_info=True)


def load_to_sqlite(
    db_path: str,
    charts_df: pd.DataFrame,
    track_info_df: pd.DataFrame,
    artists_df: pd.DataFrame,
) -> None:
    """Write DataFrames to SQLite tables within a transaction."""
    conn = get_connection(db_path)
    initialize_schema(conn)
    try:
        conn.execute("BEGIN")

        charts_cols = ["week", "region", "rank", "track_id", "track_name", "artist_id", "track_status"]
        for _, row in charts_df.iterrows():
            values = tuple(row[c] if c in charts_df.columns else None for c in charts_cols)
            conn.execute(
                "INSERT OR IGNORE INTO charts (week, region, rank, track_id, track_name, artist_id, track_status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)", values,
            )

        info_cols = ["track_id", "listeners", "playcount", "duration", "tags"]
        for _, row in track_info_df.iterrows():
            raw = [row[c] if c in track_info_df.columns else None for c in info_cols]
            values = tuple(json.dumps(v) if isinstance(v, list) else v for v in raw)
            conn.execute(
                "INSERT OR REPLACE INTO track_info (track_id, listeners, playcount, duration, tags) "
                "VALUES (?, ?, ?, ?, ?)", values,
            )

        artists_cols = ["artist_id", "name", "genres", "followers", "popularity"]
        for _, row in artists_df.iterrows():
            raw = [row[c] if c in artists_df.columns else None for c in artists_cols]
            values = tuple(json.dumps(v) if isinstance(v, list) else v for v in raw)
            conn.execute(
                "INSERT OR REPLACE INTO artists (artist_id, name, genres, followers, popularity) "
                "VALUES (?, ?, ?, ?, ?)", values,
            )

        conn.commit()
    except Exception:
        conn.rollback()
        logger.error("Database write failed, transaction rolled back", exc_info=True)
        raise
    finally:
        conn.close()
