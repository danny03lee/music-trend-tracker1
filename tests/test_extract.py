"""Tests for src.extract module."""

import pytest
from unittest.mock import patch, MagicMock

from src.extract import ExtractionError, extract_chart_data, extract_track_info, extract_artist_metadata


def _geo_response(tracks):
    return {"tracks": {"track": tracks}}


def _track(name, artist):
    return {"name": name, "artist": {"name": artist}}


class TestExtractChartData:
    @patch("src.extract.requests.get")
    def test_extracts_multiple_regions(self, mock_get):
        resp1 = MagicMock()
        resp1.json.return_value = _geo_response([_track("Song1", "A1"), _track("Song2", "A2")])
        resp1.raise_for_status = MagicMock()
        resp2 = MagicMock()
        resp2.json.return_value = _geo_response([_track("Song3", "A3")])
        resp2.raise_for_status = MagicMock()
        mock_get.side_effect = [resp1, resp2]

        result = extract_chart_data("key", {"US": "united states", "UK": "united kingdom"})
        assert len(result) == 3
        assert result[0]["region"] == "US"
        assert result[0]["rank"] == 1
        assert result[0]["track_id"] == "A1::Song1"

    @patch("src.extract.requests.get")
    def test_global_uses_chart_endpoint(self, mock_get):
        resp = MagicMock()
        resp.json.return_value = _geo_response([_track("Hit", "Star")])
        resp.raise_for_status = MagicMock()
        mock_get.return_value = resp

        extract_chart_data("key", {"Global": "global"})
        call_params = mock_get.call_args[1]["params"]
        assert call_params["method"] == "chart.getTopTracks"

    @patch("src.extract.requests.get")
    def test_raises_extraction_error_on_failure(self, mock_get):
        mock_get.side_effect = Exception("network error")
        with pytest.raises(ExtractionError, match="US"):
            extract_chart_data("key", {"US": "united states"})

    @patch("src.extract.requests.get")
    def test_empty_response(self, mock_get):
        resp = MagicMock()
        resp.json.return_value = {"tracks": {"track": []}}
        resp.raise_for_status = MagicMock()
        mock_get.return_value = resp
        result = extract_chart_data("key", {"US": "united states"})
        assert result == []


class TestExtractTrackInfo:
    @patch("src.extract._lastfm_get")
    def test_returns_track_info(self, mock_get):
        mock_get.return_value = {
            "track": {
                "listeners": "1000", "playcount": "5000", "duration": "240000",
                "toptags": {"tag": [{"name": "pop"}, {"name": "rock"}]},
            }
        }
        tracks = [{"track_id": "A::S", "track_name": "S", "artist_id": "A"}]
        result = extract_track_info("key", tracks)
        assert len(result) == 1
        assert result[0]["listeners"] == 1000
        assert result[0]["tags"] == ["pop", "rock"]

    @patch("src.extract._lastfm_get")
    def test_skips_on_error(self, mock_get):
        mock_get.side_effect = Exception("fail")
        tracks = [{"track_id": "A::S", "track_name": "S", "artist_id": "A"}]
        result = extract_track_info("key", tracks)
        assert result == []

    @patch("src.extract._lastfm_get")
    def test_deduplicates(self, mock_get):
        mock_get.return_value = {
            "track": {"listeners": "100", "playcount": "500", "duration": "200000", "toptags": {"tag": []}}
        }
        tracks = [
            {"track_id": "A::S", "track_name": "S", "artist_id": "A"},
            {"track_id": "A::S", "track_name": "S", "artist_id": "A"},
        ]
        result = extract_track_info("key", tracks)
        assert len(result) == 1
        assert mock_get.call_count == 1


class TestExtractArtistMetadata:
    @patch("src.extract._lastfm_get")
    def test_returns_metadata(self, mock_get):
        mock_get.return_value = {
            "artist": {
                "name": "Artist One",
                "tags": {"tag": [{"name": "pop"}]},
                "stats": {"listeners": "50000", "playcount": "1000000"},
            }
        }
        result = extract_artist_metadata("key", ["Artist One"])
        assert len(result) == 1
        assert result[0]["artist_id"] == "Artist One"
        assert result[0]["genres"] == ["pop"]
        assert result[0]["followers"] == 50000

    @patch("src.extract._lastfm_get")
    def test_skips_on_error(self, mock_get):
        mock_get.side_effect = Exception("fail")
        result = extract_artist_metadata("key", ["Bad Artist"])
        assert result == []
