"""Transformation layer for Music Trend Tracker."""

import pandas as pd


def normalize_chart_data(raw_charts: list[dict], week: str) -> pd.DataFrame:
    """Normalize raw chart entries into a DataFrame with a consistent schema."""
    columns = ["week", "region", "rank", "track_id", "track_name", "artist_id"]
    if not raw_charts:
        return pd.DataFrame(columns=columns)
    df = pd.DataFrame(raw_charts)
    df["week"] = week
    df["rank"] = df["rank"].astype(int)
    for col in ("week", "region", "track_id", "track_name", "artist_id"):
        df[col] = df[col].astype(str)
    return df[columns]


def join_track_info(charts_df: pd.DataFrame, track_info: list[dict]) -> pd.DataFrame:
    """Left-join chart data with track info on track_id."""
    if not track_info:
        for col in ("listeners", "playcount", "duration", "tags"):
            charts_df[col] = pd.NA
        return charts_df
    info_df = pd.DataFrame(track_info)
    return charts_df.merge(info_df, on="track_id", how="left")


def join_artist_metadata(charts_df: pd.DataFrame, artists: list[dict]) -> pd.DataFrame:
    """Left-join chart data with artist metadata on artist_id."""
    if not artists:
        for col in ("artist_name", "genres", "followers", "artist_popularity"):
            charts_df[col] = pd.NA
        return charts_df
    artists_df = pd.DataFrame(artists)
    artists_df = artists_df.rename(columns={
        "name": "artist_name",
        "popularity": "artist_popularity",
    })
    return charts_df.merge(artists_df, on="artist_id", how="left")


def classify_track_status(
    current_df: pd.DataFrame,
    previous_weeks: pd.DataFrame,
) -> pd.DataFrame:
    """Compare current week chart entries against previous weeks per region."""
    result = current_df.copy()
    result["track_status"] = "new_entry"

    if previous_weeks.empty:
        return result

    sorted_weeks = sorted(previous_weeks["week"].unique(), reverse=True)
    prev_week_str = sorted_weeks[0]
    prev_week_df = previous_weeks[previous_weeks["week"] == prev_week_str]

    prev_rank_lookup: dict[tuple[str, str], int] = {}
    for _, row in prev_week_df.iterrows():
        prev_rank_lookup[(row["region"], row["track_id"])] = int(row["rank"])

    prev_week_tracks = set(prev_rank_lookup.keys())

    older_weeks_tracks: set[tuple[str, str]] = set()
    for wk in sorted_weeks[1:]:
        wk_df = previous_weeks[previous_weeks["week"] == wk]
        for _, row in wk_df.iterrows():
            older_weeks_tracks.add((row["region"], row["track_id"]))

    second_prev_tracks: set[tuple[str, str]] = set()
    if len(sorted_weeks) >= 2:
        second_prev_str = sorted_weeks[1]
        second_prev_df = previous_weeks[previous_weeks["week"] == second_prev_str]
        for _, row in second_prev_df.iterrows():
            second_prev_tracks.add((row["region"], row["track_id"]))

    statuses: list[str] = []
    for _, row in result.iterrows():
        key = (row["region"], row["track_id"])
        current_rank = int(row["rank"])

        if key in prev_week_tracks:
            prev_rank = prev_rank_lookup[key]
            if current_rank < prev_rank:
                statuses.append("rising")
            else:
                statuses.append("stable_or_falling")
        else:
            if key not in second_prev_tracks and key in older_weeks_tracks:
                statuses.append("returning")
            else:
                statuses.append("new_entry")

    result["track_status"] = statuses
    return result
