"""Main pipeline orchestrator for Music Trend Tracker.

Executes the Extract → Transform → Load stages in sequence.
"""

import datetime
import logging

import pandas as pd

from src.config import load_config
from src.database import get_connection, get_previous_weeks_data, initialize_schema
from src.extract import (
    ExtractionError,
    extract_artist_metadata,
    extract_chart_data,
    extract_track_info,
)
from src.load import backup_to_s3, load_to_sqlite
from src.transform import (
    classify_track_status,
    join_artist_metadata,
    join_track_info,
    normalize_chart_data,
)

logger = logging.getLogger(__name__)


def _compute_week() -> str:
    """Return the ISO 8601 Monday date string for the current week."""
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())
    return monday.isoformat()


def run_pipeline() -> None:
    """Execute the full ETL pipeline: Extract → Transform → Load."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info("Loading configuration...")
    config = load_config()
    week = _compute_week()
    logger.info("Pipeline run for week: %s", week)

    # ── EXTRACT ──────────────────────────────────────────────────────
    try:
        logger.info("Extracting chart data...")
        raw_charts = extract_chart_data(config.lastfm_api_key, config.regions)

        logger.info("Extracting track info for %d entries...", len(raw_charts))
        raw_track_info = extract_track_info(config.lastfm_api_key, raw_charts)

        artist_names = list({e["artist_id"] for e in raw_charts if e["artist_id"]})
        logger.info("Extracting artist metadata for %d artists...", len(artist_names))
        raw_artists = extract_artist_metadata(config.lastfm_api_key, artist_names)
    except ExtractionError:
        logger.error("Extraction stage failed — halting pipeline.", exc_info=True)
        raise
    except Exception:
        logger.error("Unexpected extraction error — halting pipeline.", exc_info=True)
        raise

    # ── TRANSFORM ────────────────────────────────────────────────────
    try:
        logger.info("Normalizing chart data...")
        charts_df = normalize_chart_data(raw_charts, week)

        logger.info("Joining track info...")
        charts_df = join_track_info(charts_df, raw_track_info)

        logger.info("Joining artist metadata...")
        charts_df = join_artist_metadata(charts_df, raw_artists)

        logger.info("Classifying track status...")
        conn = get_connection(config.db_path)
        initialize_schema(conn)

        previous_frames: list[pd.DataFrame] = []
        for region in config.regions:
            prev = get_previous_weeks_data(conn, region, n_weeks=3)
            if not prev.empty:
                previous_frames.append(prev)
        conn.close()

        if previous_frames:
            previous_weeks = pd.concat(previous_frames, ignore_index=True)
        else:
            previous_weeks = pd.DataFrame(
                columns=["week", "region", "rank", "track_id", "track_name", "artist_id", "track_status"]
            )

        charts_df = classify_track_status(charts_df, previous_weeks)
    except Exception:
        logger.error("Transform stage failed — halting pipeline.", exc_info=True)
        raise

    # ── Prepare DataFrames for loading ───────────────────────────────
    track_info_df = pd.DataFrame(raw_track_info) if raw_track_info else pd.DataFrame(
        columns=["track_id", "listeners", "playcount", "duration", "tags"]
    )
    artists_df = pd.DataFrame(raw_artists) if raw_artists else pd.DataFrame(
        columns=["artist_id", "name", "genres", "followers", "popularity"]
    )

    # ── LOAD ─────────────────────────────────────────────────────────
    try:
        logger.info("Loading data to SQLite...")
        load_to_sqlite(config.db_path, charts_df, track_info_df, artists_df)
    except Exception:
        logger.error("SQLite load failed — halting pipeline.", exc_info=True)
        raise

    try:
        logger.info("Backing up database to S3...")
        backup_to_s3(config.db_path, config.s3_bucket, config.s3_key_prefix, week)
    except Exception:
        logger.error("S3 backup failed — continuing pipeline.", exc_info=True)

    logger.info("Pipeline completed successfully for week %s.", week)


if __name__ == "__main__":
    run_pipeline()
