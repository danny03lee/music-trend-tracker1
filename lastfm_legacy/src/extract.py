"""Extraction layer for Music Trend Tracker.

Fetches chart data, track info, and artist metadata from the Last.fm
Web API. Raises ExtractionError on region-level failures;
logs and skips per-track / per-artist errors.
"""

import logging
import re

import requests

logger = logging.getLogger(__name__)

LASTFM_BASE_URL = "http://ws.audioscrobbler.com/2.0/"


class ExtractionError(Exception):
    """Raised when a critical extraction failure should halt the pipeline."""


def _lastfm_get(params: dict) -> dict:
    """Make a GET request to the Last.fm API and return parsed JSON."""
    resp = requests.get(LASTFM_BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise requests.HTTPError(
            f"Last.fm API error {data['error']}: {data.get('message', '')}"
        )
    return data


def extract_chart_data(api_key: str, regions: dict[str, str]) -> list[dict]:
    """Fetch top 50 tracks for each configured region.

    For "global", uses chart.getTopTracks. For countries, uses geo.getTopTracks.

    Returns:
        List of dicts with keys: region, rank, track_id, track_name, artist_id.

    Raises:
        ExtractionError: On any API error for a region.
    """
    chart_entries: list[dict] = []

    for region_name, country_code in regions.items():
        try:
            if country_code == "global":
                params = {
                    "method": "chart.getTopTracks",
                    "api_key": api_key,
                    "limit": 50,
                    "format": "json",
                }
                data = _lastfm_get(params)
                tracks = data.get("tracks", {}).get("track", [])
            else:
                params = {
                    "method": "geo.getTopTracks",
                    "country": country_code,
                    "api_key": api_key,
                    "limit": 50,
                    "format": "json",
                }
                data = _lastfm_get(params)
                tracks = data.get("tracks", {}).get("track", [])

            for rank, track in enumerate(tracks, start=1):
                artist_name = track.get("artist", {}).get("name", "")
                track_name = track.get("name", "")
                track_id = f"{artist_name}::{track_name}"
                chart_entries.append({
                    "region": region_name,
                    "rank": rank,
                    "track_id": track_id,
                    "track_name": track_name,
                    "artist_id": artist_name,
                })

        except Exception as exc:
            logger.error("API error for region %s: %s", region_name, exc)
            raise ExtractionError(
                f"Failed to extract chart data for region {region_name}: {exc}"
            ) from exc

    return chart_entries


def extract_track_info(api_key: str, tracks: list[dict]) -> list[dict]:
    """Fetch track info for unique (artist, track) pairs.

    Returns:
        List of dicts with keys: track_id, listeners, playcount, duration, tags.
    """
    seen: set[str] = set()
    results: list[dict] = []

    for entry in tracks:
        track_id = entry["track_id"]
        if track_id in seen:
            continue
        seen.add(track_id)

        artist_name = entry["artist_id"]
        track_name = entry["track_name"]

        # Build a list of track name variants to try
        name_variants = [track_name]
        # Strip featured artists: "Song + Artist2", "Song (feat. Artist2)", "Song (ft. Artist2)"
        for pattern in [r"\s*\+\s*.+$", r"\s*\(feat\.?\s*.+\)$", r"\s*\(ft\.?\s*.+\)$", r"\s*feat\.?\s*.+$", r"\s*ft\.?\s*.+$"]:
            stripped = re.sub(pattern, "", track_name, flags=re.IGNORECASE).strip()
            if stripped and stripped != track_name:
                name_variants.append(stripped)

        track_data = None
        for variant in name_variants:
            try:
                params = {
                    "method": "track.getInfo",
                    "artist": artist_name,
                    "track": variant,
                    "api_key": api_key,
                    "format": "json",
                }
                data = _lastfm_get(params)
                track_data = data.get("track", {})
                break  # found it
            except Exception:
                continue

        if track_data is None:
            logger.debug("Track not found after retries: %s", track_id)
            continue

        try:
            tag_list = track_data.get("toptags", {}).get("tag", [])
            tags = [t["name"] for t in tag_list if isinstance(t, dict) and "name" in t]

            results.append({
                "track_id": track_id,
                "listeners": int(track_data.get("listeners", 0)),
                "playcount": int(track_data.get("playcount", 0)),
                "duration": int(track_data.get("duration", 0)),
                "tags": tags,
            })
        except Exception as exc:
            logger.debug("Error processing track info for %s: %s", track_id, exc)
            continue

    return results


def extract_artist_metadata(api_key: str, artist_names: list[str]) -> list[dict]:
    """Fetch artist metadata for unique artist names.

    Returns:
        List of dicts with keys: artist_id, name, genres, followers, popularity.
    """
    results: list[dict] = []

    for artist_name in artist_names:
        try:
            params = {
                "method": "artist.getInfo",
                "artist": artist_name,
                "api_key": api_key,
                "format": "json",
            }
            data = _lastfm_get(params)
            artist_data = data.get("artist", {})

            tag_list = artist_data.get("tags", {}).get("tag", [])
            genres = [t["name"] for t in tag_list if isinstance(t, dict) and "name" in t]

            stats = artist_data.get("stats", {})
            results.append({
                "artist_id": artist_name,
                "name": artist_data.get("name", artist_name),
                "genres": genres,
                "followers": int(stats.get("listeners", 0)),
                "popularity": int(stats.get("playcount", 0)),
            })
        except Exception as exc:
            logger.error("Error fetching artist metadata for %s: %s", artist_name, exc)
            continue

    return results
