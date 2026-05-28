"""Sync script: pulls latest data from Spotify and loads into the database."""

import logging

from src.auth import get_spotify_client
from src.config import load_config
from src.extract import (
    extract_audio_features,
    extract_recently_played,
    extract_saved_tracks,
    extract_top_items,
)
from src.load import (
    load_audio_features,
    load_recently_played,
    load_saved_tracks,
    load_top_artists,
    load_top_tracks,
)

logger = logging.getLogger(__name__)


def sync_all() -> dict[str, int]:
    """Run a full sync: recently played, top items, audio features, saved tracks."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    config = load_config()
    sp = get_spotify_client()
    stats = {}

    logger.info("Syncing recently played...")
    recent = extract_recently_played(sp)
    count = load_recently_played(config.db_path, recent)
    stats["recently_played"] = len(recent)
    logger.info("  Got %d plays (%d new)", len(recent), count)

    for time_range in ("short_term", "medium_term", "long_term"):
        logger.info("Syncing top tracks (%s)...", time_range)
        top_t = extract_top_items(sp, item_type="tracks", time_range=time_range)
        load_top_tracks(config.db_path, top_t)
        stats[f"top_tracks_{time_range}"] = len(top_t)

        logger.info("Syncing top artists (%s)...", time_range)
        top_a = extract_top_items(sp, item_type="artists", time_range=time_range)
        load_top_artists(config.db_path, top_a)
        stats[f"top_artists_{time_range}"] = len(top_a)

    all_track_ids = list({t["track_id"] for t in recent})
    if all_track_ids:
        logger.info("Fetching audio features for %d tracks...", len(all_track_ids))
        features = extract_audio_features(sp, all_track_ids)
        load_audio_features(config.db_path, features)
        stats["audio_features"] = len(features)

    logger.info("Syncing saved tracks...")
    saved = extract_saved_tracks(sp, limit=50)
    load_saved_tracks(config.db_path, saved)
    stats["saved_tracks"] = len(saved)

    logger.info("Sync complete!")
    return stats


if __name__ == "__main__":
    sync_all()
