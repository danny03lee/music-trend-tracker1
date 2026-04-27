"""Streamlit dashboard for Music Trend Tracker."""

import json
import os
import sqlite3

import pandas as pd
import streamlit as st

DB_PATH = os.environ.get("DB_PATH", "music_trends.db")


# ---------------------------------------------------------------------------
# Database helpers (kept for test compatibility)
# ---------------------------------------------------------------------------

def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def load_weeks(conn: sqlite3.Connection) -> list[str]:
    df = pd.read_sql_query("SELECT DISTINCT week FROM charts ORDER BY week", conn)
    return df["week"].tolist()


def load_regions(conn: sqlite3.Connection) -> list[str]:
    df = pd.read_sql_query("SELECT DISTINCT region FROM charts ORDER BY region", conn)
    return df["region"].tolist()


def load_genres(conn: sqlite3.Connection) -> list[str]:
    df = pd.read_sql_query("SELECT genres FROM artists WHERE genres IS NOT NULL", conn)
    all_genres: set[str] = set()
    for raw in df["genres"]:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                all_genres.update(g for g in parsed if isinstance(g, str))
        except (json.JSONDecodeError, TypeError):
            pass
    return sorted(all_genres)


def load_filtered_charts(
    conn: sqlite3.Connection,
    regions: list[str],
    start_week: str,
    end_week: str,
    genres: list[str] | None = None,
) -> pd.DataFrame:
    placeholders_r = ",".join("?" for _ in regions)
    params: list[str] = list(regions) + [start_week, end_week]
    if genres:
        query = f"""
            SELECT c.week, c.region, c.rank, c.track_id, c.track_name,
                   c.artist_id, c.track_status
            FROM charts c JOIN artists a ON c.artist_id = a.artist_id
            WHERE c.region IN ({placeholders_r})
              AND c.week >= ? AND c.week <= ?
              AND ({' OR '.join('a.genres LIKE ?' for _ in genres)})
        """
        params += [f"%{g}%" for g in genres]
    else:
        query = f"""
            SELECT c.week, c.region, c.rank, c.track_id, c.track_name,
                   c.artist_id, c.track_status
            FROM charts c
            WHERE c.region IN ({placeholders_r})
              AND c.week >= ? AND c.week <= ?
        """
    return pd.read_sql_query(query, conn, params=params)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def render_sidebar(conn):
    with st.sidebar:
        st.image("https://www.last.fm/static/images/lastfm_avatar_twitter.52a5d69a85ac.png", width=60)
        st.markdown("## 🎵 Filters")
        st.markdown("---")

        all_regions = load_regions(conn)
        selected_regions = st.multiselect("🌍 Regions", options=all_regions, default=all_regions)

        all_weeks = load_weeks(conn)
        if all_weeks:
            start_week = st.selectbox("📅 Start week", options=all_weeks, index=0)
            end_week = st.selectbox("📅 End week", options=all_weeks, index=len(all_weeks) - 1)
        else:
            start_week, end_week = "", ""

        all_genres = load_genres(conn)
        selected_genres = st.multiselect("🎸 Genres", options=all_genres, default=[])

        st.markdown("---")
        st.caption("Data powered by Last.fm API")

    return selected_regions, start_week, end_week, selected_genres


# ---------------------------------------------------------------------------
# Tab 1: Overview / Top Charts
# ---------------------------------------------------------------------------

def render_overview(conn, regions, start_week, end_week, genres):
    charts = load_filtered_charts(conn, regions, start_week, end_week, genres or None)
    if charts.empty:
        st.info("No chart data available for the selected filters.")
        return

    latest_week = sorted(charts["week"].unique())[-1]
    week_data = charts[charts["week"] == latest_week]

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📅 Latest Week", latest_week)
    col2.metric("🌍 Regions", len(week_data["region"].unique()))
    col3.metric("🎵 Unique Tracks", len(week_data["track_id"].unique()))
    col4.metric("🎤 Unique Artists", len(week_data["artist_id"].unique()))

    st.markdown("---")

    # Top 10 per region in columns
    region_list = sorted(week_data["region"].unique())
    if len(region_list) <= 3:
        cols = st.columns(len(region_list))
    else:
        cols = st.columns(3)

    for i, region in enumerate(region_list):
        col = cols[i % len(cols)]
        with col:
            st.markdown(f"### 🏆 {region}")
            region_data = week_data[week_data["region"] == region].nsmallest(10, "rank")
            for _, row in region_data.iterrows():
                rank = int(row["rank"])
                medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"**{rank}.**")
                st.markdown(f"{medal} {row['track_name']}  \n*{row['artist_id']}*")
            st.markdown("---")


# ---------------------------------------------------------------------------
# Tab 2: Global vs Regional
# ---------------------------------------------------------------------------

def render_global_vs_regional(conn, regions, start_week, end_week, genres):
    charts = load_filtered_charts(conn, regions, start_week, end_week, genres or None)
    if charts.empty:
        st.info("No chart data available.")
        return

    available_weeks = sorted(charts["week"].unique())
    selected_week = st.selectbox("Select week", options=available_weeks, key="gvr_week")
    week_data = charts[charts["week"] == selected_week]

    region_counts = week_data.groupby("track_id")["region"].nunique().reset_index().rename(columns={"region": "region_count"})
    cross_ids = region_counts[region_counts["region_count"] >= 2]["track_id"]
    cross = week_data[week_data["track_id"].isin(cross_ids)]

    if cross.empty:
        st.info("No tracks appear in 2+ regions this week.")
        return

    # Metric
    st.metric("🌐 Cross-market tracks", len(cross["track_id"].unique()))

    # Heatmap-style pivot
    pivot = cross.pivot_table(index="track_name", columns="region", values="rank", aggfunc="first")

    # Order columns: Global first, then alphabetical
    ordered_cols = []
    if "Global" in pivot.columns:
        ordered_cols.append("Global")
    ordered_cols += sorted([c for c in pivot.columns if c != "Global"])
    pivot = pivot[ordered_cols]
    pivot = pivot.sort_values(by=pivot.columns.tolist(), ascending=True)

    st.caption("Numbers show chart rank in each region (lower = higher on the chart). '—' means not in the top 50.")
    st.dataframe(pivot.fillna("—"), use_container_width=True, height=400)

    # Bar chart: how many regions each track appears in
    track_region_count = cross.groupby("track_name")["region"].nunique().sort_values(ascending=False).head(15)
    st.markdown("### Tracks by number of regions")
    st.bar_chart(track_region_count)


# ---------------------------------------------------------------------------
# Tab 3: Track Stats
# ---------------------------------------------------------------------------

def render_track_stats(conn, regions, start_week, end_week, genres):
    charts = load_filtered_charts(conn, regions, start_week, end_week, genres or None)
    if charts.empty:
        st.info("No chart data available.")
        return

    available_weeks = sorted(charts["week"].unique())
    selected_week = st.selectbox("Select week", options=available_weeks, key="ts_week")
    week_data = charts[charts["week"] == selected_week]
    top = week_data.nsmallest(50, "rank")
    track_ids = top["track_id"].unique().tolist()

    if not track_ids:
        st.info("No tracks found.")
        return

    placeholders = ",".join("?" for _ in track_ids)
    info = pd.read_sql_query(f"SELECT * FROM track_info WHERE track_id IN ({placeholders})", conn, params=track_ids)

    if info.empty:
        st.info("No track info available.")
        return

    # Summary metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("👂 Avg Listeners", f"{info['listeners'].mean():,.0f}")
    col2.metric("▶️ Avg Playcount", f"{info['playcount'].mean():,.0f}")
    avg_dur = info["duration"].mean() / 1000
    col3.metric("⏱️ Avg Duration", f"{int(avg_dur // 60)}:{int(avg_dur % 60):02d}")

    st.markdown("---")

    # Top tracks table with stats
    merged = top.merge(info[["track_id", "listeners", "playcount"]], on="track_id", how="left")
    display = merged[["rank", "track_name", "artist_id", "region", "listeners", "playcount"]].copy()
    display.columns = ["Rank", "Track", "Artist", "Region", "Listeners", "Plays"]
    st.dataframe(display, use_container_width=True, height=500)

    # Top tags
    st.markdown("### 🏷️ Most Common Tags")
    all_tags: list[str] = []
    for raw in info["tags"]:
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(parsed, list):
                all_tags.extend(parsed)
        except (json.JSONDecodeError, TypeError):
            pass
    if all_tags:
        tag_counts = pd.Series(all_tags).value_counts().head(20)
        st.bar_chart(tag_counts)
    else:
        st.info("No tag data available.")


# ---------------------------------------------------------------------------
# Tab 4: Artist Deep Dive
# ---------------------------------------------------------------------------

def render_artist_trends(conn):
    artists_df = pd.read_sql_query(
        "SELECT artist_id, name, followers, popularity, genres FROM artists ORDER BY popularity DESC", conn
    )
    if artists_df.empty:
        st.info("No artist data available.")
        return

    # Top artists by playcount
    st.markdown("### 🔥 Top Artists by Playcount")
    top_artists = artists_df.nlargest(15, "popularity")
    chart_data = top_artists.set_index("name")["popularity"]
    st.bar_chart(chart_data)

    st.markdown("---")

    # Artist search
    selected_names = st.multiselect(
        "🔍 Search / select artists to compare",
        options=artists_df["name"].tolist(),
        key="artist_select",
    )

    if not selected_names:
        st.info("Select artists above to see detailed info.")
        return

    selected = artists_df[artists_df["name"].isin(selected_names)]

    # Artist cards
    cols = st.columns(min(len(selected_names), 4))
    for i, (_, row) in enumerate(selected.iterrows()):
        with cols[i % len(cols)]:
            st.markdown(f"#### 🎤 {row['name']}")
            st.metric("Listeners", f"{row['followers']:,}")
            st.metric("Playcount", f"{row['popularity']:,}")
            try:
                genres = json.loads(row["genres"]) if isinstance(row["genres"], str) else row["genres"]
                if genres:
                    st.markdown("**Tags:** " + ", ".join(f"`{g}`" for g in genres[:5]))
            except (json.JSONDecodeError, TypeError):
                pass

    # Weekly chart presence
    st.markdown("---")
    st.markdown("### 📈 Chart Presence Over Time")
    artist_ids = selected["artist_id"].tolist()
    placeholders = ",".join("?" for _ in artist_ids)
    chart_weeks = pd.read_sql_query(
        f"""SELECT c.week, c.artist_id, a.name,
                   COUNT(*) as chart_entries, MIN(c.rank) as best_rank
            FROM charts c JOIN artists a ON c.artist_id = a.artist_id
            WHERE c.artist_id IN ({placeholders})
            GROUP BY c.week, c.artist_id, a.name
            ORDER BY c.week""",
        conn, params=artist_ids,
    )
    if chart_weeks.empty:
        st.info("No weekly chart data found.")
        return

    pivot = chart_weeks.pivot_table(index="week", columns="name", values="chart_entries", aggfunc="first", fill_value=0)
    st.line_chart(pivot)


# ---------------------------------------------------------------------------
# Tab 5: Rising & Falling
# ---------------------------------------------------------------------------

def render_rising_falling(conn, regions, start_week, end_week):
    if not regions:
        st.info("Select at least one region.")
        return

    placeholders_r = ",".join("?" for _ in regions)
    charts = pd.read_sql_query(
        f"""SELECT week, region, rank, track_id, track_name, track_status
            FROM charts WHERE region IN ({placeholders_r})
            AND week >= ? AND week <= ?
            ORDER BY week, region, rank""",
        conn, params=list(regions) + [start_week, end_week],
    )
    if charts.empty:
        st.info("No chart data available.")
        return

    available_weeks = sorted(charts["week"].unique())
    col1, col2 = st.columns(2)
    with col1:
        selected_week = st.selectbox("Select week", options=available_weeks, key="rf_week")
    with col2:
        selected_region = st.selectbox("Select region", options=regions, key="rf_region")

    current = charts[(charts["week"] == selected_week) & (charts["region"] == selected_region)].copy()
    if current.empty:
        st.info("No data for the selected week and region.")
        return

    # Compute rank change
    weeks_sorted = sorted(charts["week"].unique())
    week_idx = weeks_sorted.index(selected_week) if selected_week in weeks_sorted else -1
    if week_idx > 0:
        prev_week = weeks_sorted[week_idx - 1]
        prev = charts[(charts["week"] == prev_week) & (charts["region"] == selected_region)][["track_id", "rank"]].rename(columns={"rank": "prev_rank"})
        current = current.merge(prev, on="track_id", how="left")
        current["rank_change"] = current["prev_rank"] - current["rank"]
        current["rank_change"] = current["rank_change"].fillna(0).astype(int)
    else:
        current["rank_change"] = 0

    # Status breakdown
    status_counts = current["track_status"].value_counts()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🆕 New", status_counts.get("new_entry", 0))
    col2.metric("📈 Rising", status_counts.get("rising", 0))
    col3.metric("📉 Falling", status_counts.get("stable_or_falling", 0))
    col4.metric("🔄 Returning", status_counts.get("returning", 0))

    st.markdown("---")

    # Styled table
    current["abs_change"] = current["rank_change"].abs()
    current = current.sort_values("abs_change", ascending=False)

    display = current[["rank", "track_name", "track_status", "rank_change"]].copy()
    display.columns = ["Rank", "Track", "Status", "Change"]

    st.dataframe(display, use_container_width=True, height=500)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title="Music Trend Tracker", page_icon="🎵", layout="wide")

    st.markdown("""
    <style>
    .stMetric { background-color: #f8f9fa; padding: 10px; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

    st.title("🎵 Music Trend Tracker")
    st.caption("Weekly chart data from Last.fm across multiple regions")

    conn = get_connection()
    selected_regions, start_week, end_week, selected_genres = render_sidebar(conn)

    if not selected_regions or not start_week or not end_week:
        st.warning("Please select at least one region and a valid date range.")
        conn.close()
        return

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Overview",
        "🌍 Global vs Regional",
        "🎵 Track Stats",
        "🎤 Artists",
        "📈 Rising & Falling",
    ])

    with tab1:
        render_overview(conn, selected_regions, start_week, end_week, selected_genres)
    with tab2:
        render_global_vs_regional(conn, selected_regions, start_week, end_week, selected_genres)
    with tab3:
        render_track_stats(conn, selected_regions, start_week, end_week, selected_genres)
    with tab4:
        render_artist_trends(conn)
    with tab5:
        render_rising_falling(conn, selected_regions, start_week, end_week)

    conn.close()


if __name__ == "__main__":
    main()
