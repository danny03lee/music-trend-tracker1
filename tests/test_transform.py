"""Tests for src.transform module."""

import pandas as pd
import pytest
from src.transform import classify_track_status, join_artist_metadata, join_track_info, normalize_chart_data


def _raw(n=3, region="US"):
    return [{"region": region, "rank": i+1, "track_id": f"A{i}::S{i}", "track_name": f"S{i}", "artist_id": f"A{i}"} for i in range(n)]

def _info(track_ids):
    return [{"track_id": tid, "listeners": 1000, "playcount": 5000, "duration": 200000, "tags": ["pop"]} for tid in track_ids]

def _artists(aids):
    return [{"artist_id": a, "name": f"Artist {a}", "genres": ["pop"], "followers": 1000, "popularity": 75} for a in aids]

def _prev(rows):
    cols = ["week", "region", "rank", "track_id", "track_name", "artist_id", "track_status"]
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=cols)


class TestNormalize:
    def test_columns(self):
        df = normalize_chart_data(_raw(), "2025-01-06")
        assert list(df.columns) == ["week", "region", "rank", "track_id", "track_name", "artist_id"]

    def test_assigns_week(self):
        df = normalize_chart_data(_raw(2), "2025-01-06")
        assert (df["week"] == "2025-01-06").all()

    def test_empty(self):
        df = normalize_chart_data([], "2025-01-06")
        assert len(df) == 0


class TestJoinTrackInfo:
    def test_adds_columns(self):
        charts = normalize_chart_data(_raw(2), "2025-01-06")
        result = join_track_info(charts, _info(["A0::S0", "A1::S1"]))
        assert "listeners" in result.columns
        assert len(result) == 2

    def test_missing_produces_nulls(self):
        charts = normalize_chart_data(_raw(2), "2025-01-06")
        result = join_track_info(charts, _info(["A0::S0"]))
        assert pd.isna(result.loc[result["track_id"] == "A1::S1", "listeners"].iloc[0])

    def test_empty_info(self):
        charts = normalize_chart_data(_raw(2), "2025-01-06")
        result = join_track_info(charts, [])
        assert pd.isna(result["listeners"].iloc[0])


class TestJoinArtistMetadata:
    def test_adds_columns(self):
        charts = normalize_chart_data(_raw(1), "2025-01-06")
        result = join_artist_metadata(charts, _artists(["A0"]))
        assert "artist_name" in result.columns

    def test_empty(self):
        charts = normalize_chart_data(_raw(1), "2025-01-06")
        result = join_artist_metadata(charts, [])
        assert pd.isna(result["artist_name"].iloc[0])


class TestClassifyTrackStatus:
    def test_new_entry_no_prev(self):
        current = normalize_chart_data(_raw(1), "2025-01-13")
        result = classify_track_status(current, _prev([]))
        assert result.iloc[0]["track_status"] == "new_entry"

    def test_rising(self):
        current = normalize_chart_data([{"region": "US", "rank": 3, "track_id": "A::S", "track_name": "S", "artist_id": "A"}], "2025-01-13")
        prev = _prev([{"week": "2025-01-06", "region": "US", "rank": 10, "track_id": "A::S", "track_name": "S", "artist_id": "A", "track_status": "new_entry"}])
        result = classify_track_status(current, prev)
        assert result.iloc[0]["track_status"] == "rising"

    def test_stable_or_falling(self):
        current = normalize_chart_data([{"region": "US", "rank": 5, "track_id": "A::S", "track_name": "S", "artist_id": "A"}], "2025-01-13")
        prev = _prev([{"week": "2025-01-06", "region": "US", "rank": 5, "track_id": "A::S", "track_name": "S", "artist_id": "A", "track_status": "new_entry"}])
        result = classify_track_status(current, prev)
        assert result.iloc[0]["track_status"] == "stable_or_falling"

    def test_returning(self):
        current = normalize_chart_data([{"region": "US", "rank": 10, "track_id": "A::S", "track_name": "S", "artist_id": "A"}], "2025-01-27")
        prev = _prev([
            {"week": "2025-01-20", "region": "US", "rank": 1, "track_id": "X::Y", "track_name": "Y", "artist_id": "X", "track_status": "new_entry"},
            {"week": "2025-01-13", "region": "US", "rank": 1, "track_id": "X::Y", "track_name": "Y", "artist_id": "X", "track_status": "new_entry"},
            {"week": "2025-01-06", "region": "US", "rank": 5, "track_id": "A::S", "track_name": "S", "artist_id": "A", "track_status": "new_entry"},
        ])
        result = classify_track_status(current, prev)
        assert result.iloc[0]["track_status"] == "returning"
