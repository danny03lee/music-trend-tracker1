"""Tests for Spotify extraction module."""

from unittest.mock import MagicMock, patch

from src.extract import (
    extract_audio_features,
    extract_currently_playing,
    extract_global_charts,
    extract_recently_played,
    extract_top_items,
    extract_user_playlists,
)


def _make_track(track_id="abc123", name="Test Song", artist="Test Artist"):
    return {
        "id": track_id,
        "name": name,
        "artists": [{"id": "art1", "name": artist}],
        "album": {
            "id": "alb1",
            "name": "Test Album",
            "images": [{"url": "https://img.example.com/art.jpg"}],
        },
        "duration_ms": 210000,
        "popularity": 72,
        "preview_url": "https://preview.example.com/test.mp3",
    }


class TestExtractRecentlyPlayed:
    def test_parses_items(self):
        sp = MagicMock()
        sp.current_user_recently_played.return_value = {
            "items": [{"played_at": "2025-06-01T12:00:00Z", "track": _make_track()}]
        }
        result = extract_recently_played(sp)
        assert len(result) == 1
        assert result[0]["track_name"] == "Test Song"
        assert result[0]["artist_name"] == "Test Artist"
        assert result[0]["album_art_url"] == "https://img.example.com/art.jpg"

    def test_empty_response(self):
        sp = MagicMock()
        sp.current_user_recently_played.return_value = {"items": []}
        assert extract_recently_played(sp) == []


class TestExtractTopItems:
    def test_top_tracks(self):
        sp = MagicMock()
        sp.current_user_top_tracks.return_value = {"items": [_make_track()]}
        result = extract_top_items(sp, item_type="tracks", time_range="short_term")
        assert len(result) == 1
        assert result[0]["rank"] == 1
        assert result[0]["time_range"] == "short_term"

    def test_top_artists(self):
        sp = MagicMock()
        sp.current_user_top_artists.return_value = {
            "items": [{
                "id": "art1", "name": "Cool Artist",
                "genres": ["indie", "rock"],
                "popularity": 85,
                "followers": {"total": 500000},
                "images": [{"url": "https://img.example.com/artist.jpg"}],
            }]
        }
        result = extract_top_items(sp, item_type="artists", time_range="long_term")
        assert len(result) == 1
        assert result[0]["artist_name"] == "Cool Artist"
        assert result[0]["genres"] == ["indie", "rock"]


class TestExtractAudioFeatures:
    def test_parses_features(self):
        sp = MagicMock()
        sp.audio_features.return_value = [{
            "id": "abc123",
            "danceability": 0.8,
            "energy": 0.7,
            "valence": 0.6,
            "tempo": 120.0,
            "acousticness": 0.1,
            "instrumentalness": 0.0,
            "speechiness": 0.05,
            "liveness": 0.15,
            "loudness": -5.0,
            "key": 7,
            "mode": 1,
            "time_signature": 4,
        }]
        result = extract_audio_features(sp, ["abc123"])
        assert len(result) == 1
        assert result[0]["danceability"] == 0.8
        assert result[0]["tempo"] == 120.0

    def test_skips_none(self):
        sp = MagicMock()
        sp.audio_features.return_value = [None, None]
        assert extract_audio_features(sp, ["a", "b"]) == []


class TestExtractGlobalCharts:
    def test_fetches_multiple_regions(self):
        sp = MagicMock()
        sp.playlist_tracks.return_value = {
            "items": [{"track": _make_track("t1", "Hit Song", "Pop Star")}]
        }
        result = extract_global_charts(sp, ["Global", "United States"])
        assert "Global" in result
        assert "United States" in result
        assert result["Global"][0]["rank"] == 1
        assert result["Global"][0]["track_name"] == "Hit Song"

    def test_skips_unknown_region(self):
        sp = MagicMock()
        result = extract_global_charts(sp, ["Narnia"])
        assert result == {}

    def test_handles_api_error(self):
        sp = MagicMock()
        sp.playlist_tracks.side_effect = Exception("rate limited")
        result = extract_global_charts(sp, ["Global"])
        assert result == {}


class TestExtractUserPlaylists:
    def test_parses_playlists(self):
        sp = MagicMock()
        sp.user_playlists.return_value = {
            "items": [{
                "id": "pl1", "name": "Chill Vibes",
                "description": "Relaxing tunes",
                "tracks": {"total": 42},
                "images": [{"url": "https://img.example.com/pl.jpg"}],
                "owner": {"display_name": "someone"},
                "public": True,
            }]
        }
        result = extract_user_playlists(sp, "someone")
        assert len(result) == 1
        assert result[0]["name"] == "Chill Vibes"
        assert result[0]["track_count"] == 42
