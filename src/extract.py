"""Spotify data extraction: pulls your listening data and any user's public info."""

import logging
from datetime import datetime

import spotipy

logger = logging.getLogger(__name__)


def extract_recently_played(sp: spotipy.Spotify, after_ms: int | None = None) -> list[dict]:
    """Fetch recently played tracks (up to 50 per call)."""
    kwargs = {"limit": 50}
    if after_ms:
        kwargs["after"] = after_ms

    results = sp.current_user_recently_played(**kwargs)
    items = results.get("items", [])

    tracks = []
    for item in items:
        track = item["track"]
        album = track.get("album", {})
        artists = track.get("artists", [])
        tracks.append({
            "played_at": item["played_at"],
            "track_id": track["id"],
            "track_name": track["name"],
            "artist_id": artists[0]["id"] if artists else "",
            "artist_name": artists[0]["name"] if artists else "",
            "album_id": album.get("id", ""),
            "album_name": album.get("name", ""),
            "album_art_url": album.get("images", [{}])[0].get("url", "") if album.get("images") else "",
            "duration_ms": track.get("duration_ms", 0),
            "popularity": track.get("popularity", 0),
            "preview_url": track.get("preview_url", ""),
        })

    return tracks


def extract_top_items(sp: spotipy.Spotify, item_type: str = "tracks", time_range: str = "medium_term", limit: int = 50) -> list[dict]:
    """Fetch user's top tracks or artists.

    time_range: short_term (~4 weeks), medium_term (~6 months), long_term (all time)
    """
    today = datetime.now().strftime("%Y-%m-%d")

    if item_type == "tracks":
        results = sp.current_user_top_tracks(limit=limit, time_range=time_range)
        items = []
        for rank, track in enumerate(results.get("items", []), start=1):
            album = track.get("album", {})
            artists = track.get("artists", [])
            items.append({
                "snapshot_date": today,
                "time_range": time_range,
                "rank": rank,
                "track_id": track["id"],
                "track_name": track["name"],
                "artist_id": artists[0]["id"] if artists else "",
                "artist_name": artists[0]["name"] if artists else "",
                "album_name": album.get("name", ""),
                "album_art_url": album.get("images", [{}])[0].get("url", "") if album.get("images") else "",
                "popularity": track.get("popularity", 0),
            })
        return items

    elif item_type == "artists":
        results = sp.current_user_top_artists(limit=limit, time_range=time_range)
        items = []
        for rank, artist in enumerate(results.get("items", []), start=1):
            items.append({
                "snapshot_date": today,
                "time_range": time_range,
                "rank": rank,
                "artist_id": artist["id"],
                "artist_name": artist["name"],
                "genres": artist.get("genres", []),
                "popularity": artist.get("popularity", 0),
                "followers": artist.get("followers", {}).get("total", 0),
                "image_url": artist.get("images", [{}])[0].get("url", "") if artist.get("images") else "",
            })
        return items

    return []


def extract_audio_features(sp: spotipy.Spotify, track_ids: list[str]) -> list[dict]:
    """Fetch audio features for a batch of tracks (max 100 at a time)."""
    all_features = []
    for i in range(0, len(track_ids), 100):
        batch = track_ids[i:i + 100]
        results = sp.audio_features(batch)
        for feat in results:
            if feat is None:
                continue
            all_features.append({
                "track_id": feat["id"],
                "danceability": feat["danceability"],
                "energy": feat["energy"],
                "valence": feat["valence"],
                "tempo": feat["tempo"],
                "acousticness": feat["acousticness"],
                "instrumentalness": feat["instrumentalness"],
                "speechiness": feat["speechiness"],
                "liveness": feat["liveness"],
                "loudness": feat["loudness"],
                "key_sig": feat["key"],
                "mode": feat["mode"],
                "time_signature": feat["time_signature"],
            })
    return all_features


def extract_saved_tracks(sp: spotipy.Spotify, limit: int = 50) -> list[dict]:
    """Fetch user's saved/liked tracks."""
    results = sp.current_user_saved_tracks(limit=limit)
    items = []
    for item in results.get("items", []):
        track = item["track"]
        album = track.get("album", {})
        artists = track.get("artists", [])
        items.append({
            "track_id": track["id"],
            "added_at": item["added_at"],
            "track_name": track["name"],
            "artist_name": artists[0]["name"] if artists else "",
            "album_name": album.get("name", ""),
            "album_art_url": album.get("images", [{}])[0].get("url", "") if album.get("images") else "",
        })
    return items


def extract_user_playlists(sp: spotipy.Spotify, user_id: str) -> list[dict]:
    """Fetch a user's public playlists."""
    results = sp.user_playlists(user_id, limit=50)
    playlists = []
    for pl in results.get("items", []):
        playlists.append({
            "id": pl["id"],
            "name": pl["name"],
            "description": pl.get("description", ""),
            "track_count": pl.get("tracks", {}).get("total", 0),
            "image_url": pl.get("images", [{}])[0].get("url", "") if pl.get("images") else "",
            "owner": pl.get("owner", {}).get("display_name", ""),
            "public": pl.get("public", False),
        })
    return playlists


def extract_playlist_tracks(sp: spotipy.Spotify, playlist_id: str, limit: int = 100) -> list[dict]:
    """Fetch tracks from a specific playlist."""
    results = sp.playlist_tracks(playlist_id, limit=limit)
    tracks = []
    for item in results.get("items", []):
        track = item.get("track")
        if not track or not track.get("id"):
            continue
        album = track.get("album", {})
        artists = track.get("artists", [])
        tracks.append({
            "track_id": track["id"],
            "track_name": track["name"],
            "artist_id": artists[0]["id"] if artists else "",
            "artist_name": artists[0]["name"] if artists else "",
            "album_name": album.get("name", ""),
            "album_art_url": album.get("images", [{}])[0].get("url", "") if album.get("images") else "",
            "popularity": track.get("popularity", 0),
            "duration_ms": track.get("duration_ms", 0),
            "added_at": item.get("added_at", ""),
        })
    return tracks


GLOBAL_CHART_PLAYLISTS = {
    "Global": "37i9dQZEVXbMDoHDwVN2tF",
    "United States": "37i9dQZEVXbLRQDuF5jeBp",
    "United Kingdom": "37i9dQZEVXbLnolsZ8PSNw",
    "Japan": "37i9dQZEVXbKXQ4mDTEBXq",
    "Brazil": "37i9dQZEVXbMXbN3EUUhlg",
    "Germany": "37i9dQZEVXbJiZcmkrIHGU",
    "France": "37i9dQZEVXbIPWwFssbupI",
    "Canada": "37i9dQZEVXbKj23U1GF4IR",
    "Australia": "37i9dQZEVXbJPcfkRz0wJ0",
    "Mexico": "37i9dQZEVXbO3qyFxbkOE1",
    "India": "37i9dQZEVXbLZ52XmnySJg",
    "South Korea": "37i9dQZEVXbNxXF4SkHj9F",
    "Spain": "37i9dQZEVXbNFJfN1Vw8d9",
    "Italy": "37i9dQZEVXbIQnj7RRhdSX",
    "Argentina": "37i9dQZEVXbMMy2roB9myp",
    "Philippines": "37i9dQZEVXbNBz9cRCSFkY",
    "Colombia": "37i9dQZEVXbOa2lmxNORXQ",
    "Sweden": "37i9dQZEVXbLoATJ81JYXz",
    "Nigeria": "37i9dQZEVXbKY7jLzlJ11V",
    "Saudi Arabia": "37i9dQZEVXbLrQBcXYS7QY",
}


def extract_global_charts(sp: spotipy.Spotify, regions: list[str] | None = None) -> dict[str, list[dict]]:
    """Fetch current Top 50 charts for selected regions.

    Returns a dict mapping region name -> list of track dicts with rank.
    """
    targets = regions if regions else list(GLOBAL_CHART_PLAYLISTS.keys())
    charts = {}

    for region in targets:
        playlist_id = GLOBAL_CHART_PLAYLISTS.get(region)
        if not playlist_id:
            continue
        try:
            results = sp.playlist_tracks(playlist_id, limit=50)
            tracks = []
            for rank, item in enumerate(results.get("items", []), start=1):
                track = item.get("track")
                if not track or not track.get("id"):
                    continue
                album = track.get("album", {})
                artists = track.get("artists", [])
                tracks.append({
                    "rank": rank,
                    "track_id": track["id"],
                    "track_name": track["name"],
                    "artist_id": artists[0]["id"] if artists else "",
                    "artist_name": artists[0]["name"] if artists else "",
                    "album_name": album.get("name", ""),
                    "album_art_url": album.get("images", [{}])[0].get("url", "") if album.get("images") else "",
                    "popularity": track.get("popularity", 0),
                    "duration_ms": track.get("duration_ms", 0),
                })
            charts[region] = tracks
        except Exception as exc:
            logger.error("Failed to fetch chart for %s: %s", region, exc)
            continue

    return charts


def extract_currently_playing(sp: spotipy.Spotify) -> dict | None:
    """Get the currently playing track, or None."""
    result = sp.current_user_playing_track()
    if not result or not result.get("item"):
        return None
    track = result["item"]
    album = track.get("album", {})
    artists = track.get("artists", [])
    return {
        "is_playing": result.get("is_playing", False),
        "track_id": track["id"],
        "track_name": track["name"],
        "artist_name": artists[0]["name"] if artists else "",
        "album_name": album.get("name", ""),
        "album_art_url": album.get("images", [{}])[0].get("url", "") if album.get("images") else "",
        "progress_ms": result.get("progress_ms", 0),
        "duration_ms": track.get("duration_ms", 0),
    }
