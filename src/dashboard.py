"""Spotify Music Tracker: Streamlit Dashboard."""

import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.auth import get_public_client, get_spotify_client
from src.config import load_config
from src.database import (
    get_audio_features,
    get_connection,
    get_listening_history,
    get_top_artists,
    get_top_tracks,
    initialize_schema,
)
from src.extract import (
    GLOBAL_CHART_PLAYLISTS,
    extract_currently_playing,
    extract_global_charts,
    extract_playlist_tracks,
    extract_user_playlists,
)

SPOTIFY_GREEN = "#1DB954"
SPOTIFY_BLACK = "#191414"
SPOTIFY_DARK = "#121212"
SPOTIFY_GRAY = "#282828"
SPOTIFY_LIGHT = "#B3B3B3"
SPOTIFY_WHITE = "#FFFFFF"


def apply_spotify_theme():
    st.markdown(f"""
    <style>
        .stApp {{
            background-color: {SPOTIFY_BLACK};
            color: {SPOTIFY_WHITE};
        }}
        .stSidebar > div:first-child {{
            background-color: {SPOTIFY_DARK};
        }}
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
        }}
        .stTabs [data-baseweb="tab"] {{
            background-color: {SPOTIFY_GRAY};
            color: {SPOTIFY_LIGHT};
            border-radius: 20px;
            padding: 8px 16px;
        }}
        .stTabs [aria-selected="true"] {{
            background-color: {SPOTIFY_GREEN} !important;
            color: {SPOTIFY_BLACK} !important;
        }}
        .stMetric {{
            background-color: {SPOTIFY_GRAY};
            padding: 16px;
            border-radius: 12px;
        }}
        .stMetric label {{
            color: {SPOTIFY_LIGHT} !important;
        }}
        .stMetric [data-testid="stMetricValue"] {{
            color: {SPOTIFY_GREEN} !important;
        }}
        h1, h2, h3, h4 {{
            color: {SPOTIFY_WHITE} !important;
        }}
        .track-card {{
            background: {SPOTIFY_GRAY};
            border-radius: 8px;
            padding: 12px;
            margin: 6px 0;
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .track-card img {{
            border-radius: 4px;
            width: 48px;
            height: 48px;
        }}
        .track-rank {{
            color: {SPOTIFY_LIGHT};
            font-size: 1.2em;
            font-weight: bold;
            min-width: 28px;
        }}
        .track-info {{
            flex: 1;
        }}
        .track-name {{
            color: {SPOTIFY_WHITE};
            font-weight: 600;
            font-size: 0.95em;
        }}
        .track-artist {{
            color: {SPOTIFY_LIGHT};
            font-size: 0.85em;
        }}
        .now-playing {{
            background: linear-gradient(135deg, {SPOTIFY_GRAY}, #1a3a2a);
            border: 1px solid {SPOTIFY_GREEN};
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        .now-playing-label {{
            color: {SPOTIFY_GREEN};
            font-size: 0.75em;
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-bottom: 8px;
        }}
        .genre-pill {{
            display: inline-block;
            background: {SPOTIFY_GRAY};
            color: {SPOTIFY_GREEN};
            padding: 4px 12px;
            border-radius: 16px;
            margin: 3px;
            font-size: 0.8em;
        }}
        .user-header {{
            text-align: center;
            padding: 20px;
        }}
        div[data-testid="stDataFrame"] {{
            background-color: {SPOTIFY_GRAY};
            border-radius: 8px;
        }}
    </style>
    """, unsafe_allow_html=True)


def render_track_card(rank: int, name: str, artist: str, album_art: str = "", popularity: int = 0):
    art_html = f'<img src="{album_art}" />' if album_art else ""
    pop_bar = f'<div style="width:{popularity}%;height:3px;background:{SPOTIFY_GREEN};border-radius:2px;margin-top:4px;"></div>' if popularity else ""
    st.markdown(f"""
    <div class="track-card">
        <span class="track-rank">{rank}</span>
        {art_html}
        <div class="track-info">
            <div class="track-name">{name}</div>
            <div class="track-artist">{artist}</div>
            {pop_bar}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_now_playing(sp):
    now = extract_currently_playing(sp)
    if now and now["is_playing"]:
        progress_pct = (now["progress_ms"] / now["duration_ms"] * 100) if now["duration_ms"] else 0
        art = f'<img src="{now["album_art_url"]}" style="width:64px;height:64px;border-radius:8px;margin-right:16px;" />' if now["album_art_url"] else ""
        st.markdown(f"""
        <div class="now-playing">
            <div class="now-playing-label">Now Playing</div>
            <div style="display:flex;align-items:center;">
                {art}
                <div>
                    <div style="color:{SPOTIFY_WHITE};font-size:1.1em;font-weight:600;">{now["track_name"]}</div>
                    <div style="color:{SPOTIFY_LIGHT};">{now["artist_name"]} | {now["album_name"]}</div>
                </div>
            </div>
            <div style="margin-top:12px;background:{SPOTIFY_DARK};border-radius:4px;height:4px;">
                <div style="width:{progress_pct:.0f}%;height:4px;background:{SPOTIFY_GREEN};border-radius:4px;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_my_stats(conn, sp):
    """Tab: Your personal listening stats."""
    render_now_playing(sp)

    time_labels = {"short_term": "Last 4 Weeks", "medium_term": "Last 6 Months", "long_term": "All Time"}
    selected_range = st.radio("Time range", list(time_labels.keys()), format_func=lambda x: time_labels[x], horizontal=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Your Top Tracks")
        top_t = get_top_tracks(conn, time_range=selected_range)
        if top_t.empty:
            st.info("No data yet. Run a sync first!")
        else:
            for _, row in top_t.head(20).iterrows():
                render_track_card(
                    rank=int(row["rank"]),
                    name=row["track_name"],
                    artist=row["artist_name"],
                    album_art=row.get("album_art_url", ""),
                    popularity=int(row.get("popularity", 0)),
                )

    with col2:
        st.markdown("### Your Top Artists")
        top_a = get_top_artists(conn, time_range=selected_range)
        if top_a.empty:
            st.info("No data yet. Run a sync first!")
        else:
            for _, row in top_a.head(20).iterrows():
                genres = []
                try:
                    genres = json.loads(row["genres"]) if isinstance(row["genres"], str) else row.get("genres", [])
                except (json.JSONDecodeError, TypeError):
                    pass
                genre_html = "".join(f'<span class="genre-pill">{g}</span>' for g in (genres or [])[:3])
                img = f'<img src="{row["image_url"]}" style="width:48px;height:48px;border-radius:50%;" />' if row.get("image_url") else ""
                st.markdown(f"""
                <div class="track-card">
                    <span class="track-rank">{int(row["rank"])}</span>
                    {img}
                    <div class="track-info">
                        <div class="track-name">{row["artist_name"]}</div>
                        <div>{genre_html}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)


def render_listening_history(conn):
    """Tab: Recent listening timeline."""
    st.markdown("### Recent Listens")
    history = get_listening_history(conn, limit=200)
    if history.empty:
        st.info("No listening history yet. Run a sync to pull your recent plays!")
        return

    history["played_at"] = pd.to_datetime(history["played_at"])
    history["hour"] = history["played_at"].dt.hour
    history["day"] = history["played_at"].dt.day_name()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Plays", len(history))
    col2.metric("Unique Tracks", history["track_id"].nunique())
    col3.metric("Unique Artists", history["artist_name"].nunique())

    st.markdown("---")

    st.markdown("#### Listening Heatmap")
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    heatmap_data = history.groupby(["day", "hour"]).size().reset_index(name="plays")
    heatmap_pivot = heatmap_data.pivot(index="day", columns="hour", values="plays").fillna(0)
    heatmap_pivot = heatmap_pivot.reindex(day_order)

    fig = px.imshow(
        heatmap_pivot,
        color_continuous_scale=[[0, SPOTIFY_DARK], [0.5, "#1a5c35"], [1, SPOTIFY_GREEN]],
        labels={"x": "Hour", "y": "Day", "color": "Plays"},
        aspect="auto",
    )
    fig.update_layout(
        plot_bgcolor=SPOTIFY_BLACK,
        paper_bgcolor=SPOTIFY_BLACK,
        font_color=SPOTIFY_LIGHT,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Recent Tracks")
    for _, row in history.head(30).iterrows():
        time_str = row["played_at"].strftime("%b %d, %I:%M %p")
        art = f'<img src="{row["album_art_url"]}" style="width:36px;height:36px;border-radius:4px;margin-right:10px;" />' if row.get("album_art_url") else ""
        st.markdown(f"""
        <div style="display:flex;align-items:center;padding:6px 0;border-bottom:1px solid {SPOTIFY_GRAY};">
            {art}
            <div style="flex:1;">
                <span style="color:{SPOTIFY_WHITE};">{row["track_name"]}</span>
                <span style="color:{SPOTIFY_LIGHT};"> | {row["artist_name"]}</span>
            </div>
            <span style="color:{SPOTIFY_LIGHT};font-size:0.8em;">{time_str}</span>
        </div>
        """, unsafe_allow_html=True)


def render_audio_vibe(conn):
    """Tab: Audio features / vibe analysis."""
    st.markdown("### Your Sonic DNA")
    st.caption("Audio characteristics of your top tracks")

    top_t = get_top_tracks(conn, time_range="medium_term")
    if top_t.empty:
        st.info("No top tracks data. Run a sync first!")
        return

    track_ids = top_t["track_id"].tolist()
    features = get_audio_features(conn, track_ids)

    if features.empty:
        st.info("No audio features cached yet. Run a sync to populate this data.")
        return

    dims = ["danceability", "energy", "valence", "acousticness", "instrumentalness", "speechiness"]
    avgs = features[dims].mean()

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=avgs.values,
        theta=dims,
        fill="toself",
        fillcolor=f"rgba(29, 185, 84, 0.3)",
        line=dict(color=SPOTIFY_GREEN, width=2),
        name="Your Vibe",
    ))
    fig.update_layout(
        polar=dict(
            bgcolor=SPOTIFY_GRAY,
            radialaxis=dict(visible=True, range=[0, 1], gridcolor=SPOTIFY_LIGHT),
            angularaxis=dict(gridcolor=SPOTIFY_GRAY),
        ),
        paper_bgcolor=SPOTIFY_BLACK,
        font_color=SPOTIFY_WHITE,
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Avg Tempo", f"{features['tempo'].mean():.0f} BPM")
    col2.metric("Avg Energy", f"{features['energy'].mean():.0%}")
    col3.metric("Avg Danceability", f"{features['danceability'].mean():.0%}")
    col4.metric("Happiness (Valence)", f"{features['valence'].mean():.0%}")

    st.markdown("---")
    st.markdown("#### Energy vs. Danceability")
    merged = top_t.merge(features[["track_id", "energy", "danceability", "valence"]], on="track_id", how="inner")
    if not merged.empty:
        fig2 = px.scatter(
            merged, x="danceability", y="energy", size="valence",
            hover_name="track_name", color="valence",
            color_continuous_scale=[[0, "#4a1942"], [0.5, SPOTIFY_GREEN], [1, "#1DB954"]],
            labels={"danceability": "Danceability", "energy": "Energy", "valence": "Happiness"},
        )
        fig2.update_layout(
            plot_bgcolor=SPOTIFY_DARK,
            paper_bgcolor=SPOTIFY_BLACK,
            font_color=SPOTIFY_LIGHT,
        )
        st.plotly_chart(fig2, use_container_width=True)


def render_explore_users(sp):
    """Tab: Look up other Spotify users' public playlists."""
    st.markdown("### Explore a User")
    st.caption("Enter a Spotify username or user ID to see their public playlists")

    user_id = st.text_input("Spotify Username / User ID", placeholder="e.g. spotify, or a friend's username")

    if not user_id:
        st.markdown(f"""
        <div style="text-align:center;padding:60px;color:{SPOTIFY_LIGHT};">
            <p style="font-size:1.2em;">Enter a username above to explore their playlists</p>
            <p style="font-size:0.9em;">Try "spotify" to see Spotify's official playlists</p>
        </div>
        """, unsafe_allow_html=True)
        return

    try:
        playlists = extract_user_playlists(sp, user_id)
    except Exception as e:
        st.error(f"Could not find user: {user_id}")
        return

    if not playlists:
        st.info("This user has no public playlists.")
        return

    st.markdown(f"#### {user_id}'s Playlists ({len(playlists)})")

    selected_pl = st.selectbox(
        "Pick a playlist to explore",
        options=playlists,
        format_func=lambda x: f"{x['name']} ({x['track_count']} tracks)",
    )

    if selected_pl:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if selected_pl["image_url"]:
                st.image(selected_pl["image_url"], width=200)
        with col2:
            st.markdown(f"### {selected_pl['name']}")
            st.markdown(f"*{selected_pl['description']}*" if selected_pl["description"] else "")
            st.markdown(f"**{selected_pl['track_count']} tracks** | by {selected_pl['owner']}")

        st.markdown("---")

        tracks = extract_playlist_tracks(sp, selected_pl["id"])
        if tracks:
            for i, t in enumerate(tracks[:30], start=1):
                render_track_card(
                    rank=i,
                    name=t["track_name"],
                    artist=t["artist_name"],
                    album_art=t.get("album_art_url", ""),
                    popularity=t.get("popularity", 0),
                )


def render_global_charts(sp):
    """Tab: What the world is listening to right now."""
    st.markdown("### Global Charts")
    st.caption("Live Top 50 from Spotify's official playlists around the world")

    all_regions = list(GLOBAL_CHART_PLAYLISTS.keys())

    view_mode = st.radio("View", ["Single Region", "Compare Regions", "World Overview"], horizontal=True, label_visibility="collapsed")

    if view_mode == "Single Region":
        selected_region = st.selectbox("Pick a country", all_regions, index=0)
        with st.spinner(f"Loading {selected_region} Top 50..."):
            charts = extract_global_charts(sp, [selected_region])

        tracks = charts.get(selected_region, [])
        if not tracks:
            st.warning(f"Could not load chart for {selected_region}")
            return

        st.markdown(f"#### Top 50 | {selected_region}")

        col1, col2, col3 = st.columns(3)
        artists = {t["artist_name"] for t in tracks}
        avg_pop = sum(t["popularity"] for t in tracks) / len(tracks) if tracks else 0
        col1.metric("Tracks", len(tracks))
        col2.metric("Unique Artists", len(artists))
        col3.metric("Avg Popularity", f"{avg_pop:.0f}")

        st.markdown("---")
        for t in tracks:
            render_track_card(
                rank=t["rank"],
                name=t["track_name"],
                artist=t["artist_name"],
                album_art=t.get("album_art_url", ""),
                popularity=t.get("popularity", 0),
            )

    elif view_mode == "Compare Regions":
        selected_regions = st.multiselect(
            "Select regions to compare",
            all_regions,
            default=["Global", "United States", "United Kingdom"],
            max_selections=5,
        )
        if not selected_regions:
            st.info("Pick at least one region above.")
            return

        with st.spinner("Loading charts..."):
            charts = extract_global_charts(sp, selected_regions)

        all_tracks: set[str] = set()
        for region, tracks in charts.items():
            for t in tracks:
                all_tracks.add(t["track_id"])

        track_regions: dict[str, list[str]] = {}
        track_names: dict[str, str] = {}
        track_artists: dict[str, str] = {}
        track_ranks: dict[str, dict[str, int]] = {}

        for region, tracks in charts.items():
            for t in tracks:
                tid = t["track_id"]
                track_names[tid] = t["track_name"]
                track_artists[tid] = t["artist_name"]
                track_regions.setdefault(tid, []).append(region)
                track_ranks.setdefault(tid, {})[region] = t["rank"]

        crossover = {tid: regions for tid, regions in track_regions.items() if len(regions) >= 2}

        st.markdown(f"#### Cross-Market Hits ({len(crossover)} tracks in 2+ regions)")
        if crossover:
            rows = []
            for tid, regions in sorted(crossover.items(), key=lambda x: -len(x[1])):
                row = {"Track": track_names[tid], "Artist": track_artists[tid], "Regions": len(regions)}
                for r in selected_regions:
                    row[r] = track_ranks.get(tid, {}).get(r, "-")
                rows.append(row)
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, height=400)
        else:
            st.info("No tracks appear in multiple selected regions.")

        st.markdown("---")
        st.markdown("#### Side-by-Side Top 10")
        cols = st.columns(len(selected_regions))
        for i, region in enumerate(selected_regions):
            with cols[i]:
                st.markdown(f"**{region}**")
                for t in charts.get(region, [])[:10]:
                    st.markdown(f"""
                    <div style="background:{SPOTIFY_GRAY};border-radius:6px;padding:8px;margin:4px 0;">
                        <span style="color:{SPOTIFY_GREEN};font-weight:bold;">{t['rank']}.</span>
                        <span style="color:{SPOTIFY_WHITE};">{t['track_name']}</span><br/>
                        <span style="color:{SPOTIFY_LIGHT};font-size:0.8em;">{t['artist_name']}</span>
                    </div>
                    """, unsafe_allow_html=True)

    elif view_mode == "World Overview":
        st.markdown("#### Scanning the globe...")
        st.caption("Loading Top 50 from all 20 regions. This takes a moment.")

        with st.spinner("Fetching all charts..."):
            charts = extract_global_charts(sp)

        artist_counts: dict[str, int] = {}
        track_counts: dict[str, int] = {}
        track_names_map: dict[str, str] = {}
        artist_names_map: dict[str, str] = {}

        for region, tracks in charts.items():
            for t in tracks:
                artist_counts[t["artist_id"]] = artist_counts.get(t["artist_id"], 0) + 1
                artist_names_map[t["artist_id"]] = t["artist_name"]
                track_counts[t["track_id"]] = track_counts.get(t["track_id"], 0) + 1
                track_names_map[t["track_id"]] = t["track_name"]

        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Most Global Artists")
            st.caption("Artists appearing in the most country charts")
            top_artists = sorted(artist_counts.items(), key=lambda x: -x[1])[:15]
            for i, (aid, count) in enumerate(top_artists, 1):
                pct = count / len(charts) * 100
                st.markdown(f"""
                <div style="display:flex;align-items:center;margin:6px 0;">
                    <span style="color:{SPOTIFY_LIGHT};min-width:24px;">{i}.</span>
                    <span style="color:{SPOTIFY_WHITE};flex:1;">{artist_names_map[aid]}</span>
                    <span style="color:{SPOTIFY_GREEN};font-weight:bold;">{count} charts</span>
                    <div style="width:60px;height:6px;background:{SPOTIFY_DARK};border-radius:3px;margin-left:8px;">
                        <div style="width:{pct:.0f}%;height:6px;background:{SPOTIFY_GREEN};border-radius:3px;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        with col2:
            st.markdown("#### Most Global Tracks")
            st.caption("Songs charting in the most countries simultaneously")
            top_tracks = sorted(track_counts.items(), key=lambda x: -x[1])[:15]
            for i, (tid, count) in enumerate(top_tracks, 1):
                pct = count / len(charts) * 100
                st.markdown(f"""
                <div style="display:flex;align-items:center;margin:6px 0;">
                    <span style="color:{SPOTIFY_LIGHT};min-width:24px;">{i}.</span>
                    <span style="color:{SPOTIFY_WHITE};flex:1;">{track_names_map[tid]}</span>
                    <span style="color:{SPOTIFY_GREEN};font-weight:bold;">{count} charts</span>
                    <div style="width:60px;height:6px;background:{SPOTIFY_DARK};border-radius:3px;margin-left:8px;">
                        <div style="width:{pct:.0f}%;height:6px;background:{SPOTIFY_GREEN};border-radius:3px;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### Regional Diversity Score")
        st.caption("How unique is each country's chart vs. the Global Top 50?")
        global_ids = {t["track_id"] for t in charts.get("Global", [])}
        diversity_data = []
        for region, tracks in charts.items():
            if region == "Global":
                continue
            region_ids = {t["track_id"] for t in tracks}
            overlap = len(region_ids & global_ids)
            unique_pct = (1 - overlap / len(region_ids)) * 100 if region_ids else 0
            diversity_data.append({"Region": region, "Uniqueness": unique_pct, "Overlap with Global": overlap})

        if diversity_data:
            div_df = pd.DataFrame(diversity_data).sort_values("Uniqueness", ascending=False)
            fig = px.bar(
                div_df, x="Region", y="Uniqueness",
                color="Uniqueness",
                color_continuous_scale=[[0, SPOTIFY_GRAY], [0.5, "#1a5c35"], [1, SPOTIFY_GREEN]],
                labels={"Uniqueness": "% Unique (not in Global Top 50)"},
            )
            fig.update_layout(
                plot_bgcolor=SPOTIFY_BLACK,
                paper_bgcolor=SPOTIFY_BLACK,
                font_color=SPOTIFY_LIGHT,
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)


def render_sync_panel(sp):
    """Tab: Manual sync controls."""
    st.markdown("### Sync Your Data")
    st.caption("Pull fresh data from Spotify into your local database")

    if st.button("Sync Now", type="primary"):
        with st.spinner("Syncing with Spotify..."):
            from src.sync import sync_all
            stats = sync_all()
        st.success("Sync complete!")
        for key, val in stats.items():
            st.markdown(f"- **{key.replace('_', ' ').title()}**: {val} items")
        st.rerun()

    st.markdown("---")
    st.markdown("#### What gets synced:")
    st.markdown(f"""
    - Recently played tracks (last 50)
    - Top tracks & artists (short/medium/long term)
    - Audio features for your recent plays
    - Your liked/saved tracks (latest 50)
    """)


def main():
    st.set_page_config(
        page_title="Spotify Tracker",
        page_icon="https://storage.googleapis.com/pr-newsroom-wp/1/2018/11/Spotify_Logo_RGB_Green.png",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    apply_spotify_theme()

    config = load_config()
    conn = get_connection(config.db_path)
    initialize_schema(conn)

    try:
        sp = get_spotify_client()
    except Exception:
        sp = None

    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:24px;">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="{SPOTIFY_GREEN}">
            <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
        </svg>
        <h1 style="margin:0;color:{SPOTIFY_WHITE};">Music Tracker</h1>
    </div>
    """, unsafe_allow_html=True)

    tabs = st.tabs(["My Stats", "Global Charts", "History", "Sonic DNA", "Explore Users", "Sync"])

    with tabs[0]:
        if sp:
            render_my_stats(conn, sp)
        else:
            st.warning("Spotify not connected. Go to Sync tab to authenticate.")

    with tabs[1]:
        if sp:
            render_global_charts(sp)
        else:
            st.warning("Connect Spotify to see global charts.")

    with tabs[2]:
        render_listening_history(conn)

    with tabs[3]:
        render_audio_vibe(conn)

    with tabs[4]:
        if sp:
            render_explore_users(sp)
        else:
            st.warning("Connect Spotify first via the Sync tab.")

    with tabs[5]:
        if sp:
            render_sync_panel(sp)
        else:
            st.warning("Run `python -m src.sync` from your terminal to authenticate for the first time.")
            st.code("cd 'Side Projects' && python -m src.sync", language="bash")

    conn.close()


if __name__ == "__main__":
    main()
