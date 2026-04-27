# Implementation Plan: Spotify Global Trend Tracker

## Overview

Build a Python ETL pipeline that extracts weekly Spotify chart data, audio features, and artist metadata via Spotipy, transforms with Pandas, loads into SQLite, backs up to S3, and visualizes through a Streamlit dashboard. A GitHub Actions workflow automates the weekly schedule.

## Tasks

- [x] 1. Set up project structure and configuration
  - [x] 1.1 Create project directory structure and install dependencies
    - Create directories: `src/` for pipeline modules, `tests/` for test files
    - Create `requirements.txt` with dependencies: spotipy, pandas, boto3, streamlit, pytest
    - Create `__init__.py` files as needed
    - _Requirements: 15.1_

  - [x] 1.2 Implement `config.py` configuration module
    - Implement the `Config` dataclass with fields: `spotify_client_id`, `spotify_client_secret`, `s3_bucket`, `s3_key_prefix`, `regions` (dict mapping region name to playlist ID), `db_path`
    - Implement `load_config()` that reads defaults and overrides from environment variables (`SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `S3_BUCKET`, `S3_KEY_PREFIX`, `DB_PATH`)
    - Hardcode default region-to-playlist-ID mapping: Global (`37i9dQZEVXbMDoHDwVN2tF`), US (`37i9dQZEVXbLRQDuF5jeBp`), UK (`37i9dQZEVXbLnolsZ8PSNw`), Japan (`37i9dQZEVXbKXQ4mDTEBXq`), Brazil (`37i9dQZEVXbMXbN3EUUhlg`)
    - Raise `ValueError` with a descriptive message if any required config value is missing
    - _Requirements: 15.1, 15.2, 15.3_

  - [x] 1.3 Write unit tests for `config.py`
    - Test loading config with all values present
    - Test environment variable overrides
    - Test missing required values raise descriptive errors
    - _Requirements: 15.1, 15.2, 15.3_

- [x] 2. Implement database layer
  - [x] 2.1 Implement `database.py` with schema initialization and connection management
    - Implement `get_connection(db_path)` returning a `sqlite3.Connection`
    - Implement `initialize_schema(conn)` that creates `charts`, `audio_features`, and `artists` tables using `CREATE TABLE IF NOT EXISTS` with the schema defined in the design (charts PK: `week, region, track_id`; audio_features PK: `track_id`; artists PK: `artist_id`)
    - Implement `get_previous_weeks_data(conn, region, n_weeks=3)` that queries the `charts` table for the most recent n weeks of data for a given region, returning a Pandas DataFrame
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 6.1_

  - [x] 2.2 Write unit tests for `database.py`
    - Test schema creation creates all three tables with correct columns
    - Test `get_previous_weeks_data` returns correct data filtered by region and week count
    - Test idempotent schema initialization (calling twice doesn't error)
    - _Requirements: 7.1, 7.2, 7.3, 6.1_

- [x] 3. Implement extraction layer
  - [x] 3.1 Implement `extract.py` chart data extraction
    - Implement `extract_chart_data(sp, config)` that iterates over `config.regions`, calls `sp.playlist_tracks()` for each playlist ID, and returns a list of dicts with keys: `region`, `rank` (1-based position), `track_id`, `track_name`, `artist_id`
    - On Spotify API error for any region, log the region name and HTTP status code, then raise an `ExtractionError` to halt the pipeline
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 3.2 Implement `extract.py` audio features extraction
    - Implement `extract_audio_features(sp, track_ids)` that calls `sp.audio_features()` in batches (Spotify supports up to 100 IDs per call)
    - Capture `energy`, `tempo`, `danceability`, `valence`, `acousticness`, and `popularity` (popularity from track object) for each track
    - On per-track API error, log the track ID and error, skip that track, and continue
    - Return list of audio feature dicts (may be shorter than input)
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 3.3 Implement `extract.py` artist metadata extraction
    - Implement `extract_artist_metadata(sp, artist_ids)` that calls `sp.artists()` in batches
    - Capture `artist_id`, `name`, `genres`, `followers` (total count), and `popularity` for each artist
    - On per-artist API error, log the artist ID and error, skip that artist, and continue
    - Return list of artist metadata dicts (may be shorter than input)
    - _Requirements: 3.1, 3.2, 3.3_

  - [x] 3.4 Write unit tests for `extract.py`
    - Mock Spotipy client and test chart data extraction for multiple regions
    - Test audio features extraction with partial failures (some tracks fail)
    - Test artist metadata extraction with partial failures
    - Test that `ExtractionError` is raised on region-level API failure
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3_

- [x] 4. Checkpoint
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement transformation layer
  - [x] 5.1 Implement `transform.py` chart data normalization
    - Implement `normalize_chart_data(raw_charts, week)` that converts the list of raw chart dicts into a Pandas DataFrame with columns: `week`, `region`, `rank`, `track_id`, `track_name`, `artist_id`
    - Assign the provided `week` (ISO 8601 Monday date string) to all records
    - Ensure consistent column names and data types regardless of source region
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 5.2 Implement `transform.py` join operations
    - Implement `join_audio_features(charts_df, features)` that performs a left join on `track_id`, retaining chart entries with null audio feature columns when no match exists
    - Implement `join_artist_metadata(charts_df, artists)` that performs a left join on `artist_id`, retaining chart entries with null artist metadata columns when no match exists
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [x] 5.3 Implement `transform.py` track status classification
    - Implement `classify_track_status(current_df, previous_weeks)` that compares current week chart entries against previous weeks per region
    - Assign `track_status` values: `new_entry` (not in previous week), `rising` (higher rank than previous week), `returning` (absent 2+ consecutive weeks then reappears), `stable_or_falling` (same or lower rank)
    - Return the DataFrame with an added `track_status` column
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [x] 5.4 Write unit tests for `transform.py`
    - Test normalization produces correct schema and assigns week timestamp
    - Test left joins retain entries with missing audio features / artist metadata as nulls
    - Test track status classification for all four statuses: new_entry, rising, returning, stable_or_falling
    - _Requirements: 4.1, 4.2, 4.3, 5.1, 5.2, 5.3, 5.4, 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 6. Implement load layer
  - [x] 6.1 Implement `load.py` SQLite loading
    - Implement `load_to_sqlite(db_path, charts_df, features_df, artists_df)` that writes DataFrames to SQLite within a transaction
    - Charts table: append new rows (INSERT with conflict handling on PK `week, region, track_id`)
    - Audio features and artists tables: use `INSERT OR REPLACE` keyed on `track_id` / `artist_id` for upsert behavior
    - Roll back the transaction and log the error on any database write failure
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [x] 6.2 Implement `load.py` S3 backup
    - Implement `backup_to_s3(db_path, bucket, key_prefix, week)` that uploads the SQLite file to S3 using boto3
    - Include the `week` timestamp in the S3 object key (e.g., `{key_prefix}/{week}/spotify_trends.db`)
    - On S3 upload failure, log the error with bucket name and HTTP status code but do not halt the pipeline
    - _Requirements: 8.1, 8.2, 8.3_

  - [x] 6.3 Write unit tests for `load.py`
    - Test SQLite loading writes correct data to all three tables
    - Test transaction rollback on write error
    - Test S3 backup with mocked boto3 client
    - Test S3 failure is logged but does not raise
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 8.1, 8.2, 8.3_

- [x] 7. Checkpoint
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Wire pipeline end-to-end
  - [x] 8.1 Create `pipeline.py` main orchestrator
    - Implement a `run_pipeline()` function that executes Extract → Transform → Load in sequence
    - Initialize Spotipy client using Client Credentials flow with config values
    - Call extractors, pass results to transformers, then load to SQLite and backup to S3
    - Compute the current `week` as the ISO 8601 Monday date string
    - Retrieve previous weeks data from SQLite for track status classification
    - Handle stage failures: log and halt on extraction/transform errors; log and continue on S3 backup errors
    - Add a `__main__` entry point so the pipeline can be run via `python -m src.pipeline` or `python src/pipeline.py`
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 5.1, 5.2, 5.3, 5.4, 6.1, 6.2, 6.3, 6.4, 6.5, 7.1, 7.2, 7.3, 7.4, 7.5, 8.1, 8.2, 8.3, 14.2, 14.4, 15.1_

  - [x] 8.2 Write integration tests for the pipeline
    - Test full pipeline run with mocked Spotipy and boto3 clients
    - Verify data flows correctly from extraction through transformation to SQLite
    - Verify S3 backup is attempted after SQLite load
    - _Requirements: 14.2, 14.4_

- [x] 9. Implement Streamlit dashboard
  - [x] 9.1 Implement shared dashboard filters and layout in `dashboard.py`
    - Create Streamlit app with sidebar filters: Region multi-select, date range picker (start week / end week), genre multi-select populated from artist metadata
    - Connect to SQLite database and load data based on applied filters
    - Set up tabbed or page-based navigation for the four dashboard views
    - _Requirements: 13.1, 13.2, 13.3, 13.4_

  - [x] 9.2 Implement Global vs Regional Chart Comparison view
    - Query tracks appearing in 2+ regions within the same week
    - Display cross-market tracks with their rankings across all regions where they appear
    - Allow filtering by week selection, region, date range, and genre
    - _Requirements: 9.1, 9.2, 9.3_

  - [x] 9.3 Implement Audio Feature Breakdown view
    - Display aggregated audio features (energy, tempo, danceability, valence, acousticness) for top charting tracks in a selected week
    - Show average audio feature values for the top 50 tracks filtered by region and date range
    - Present data using radar charts or bar charts suitable for comparing multiple numeric dimensions
    - _Requirements: 10.1, 10.2, 10.3_

  - [x] 9.4 Implement Artist Popularity Trends view
    - Display time-series line chart of selected artists' popularity scores across all available weeks
    - Provide artist search/select by name
    - Display follower count alongside popularity score for each selected artist
    - _Requirements: 11.1, 11.2, 11.3_

  - [x] 9.5 Implement Rising vs Falling Tracks view
    - Display tracks with their `track_status` classification for a selected week and region
    - Sort by rank change magnitude in descending order
    - Allow filtering by region and date range
    - _Requirements: 12.1, 12.2, 12.3_

- [x] 10. Checkpoint
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Set up GitHub Actions workflow
  - [x] 11.1 Create `.github/workflows/weekly_run.yml`
    - Configure cron schedule: `0 8 * * 1` (every Monday at 08:00 UTC)
    - Set up Python environment and install dependencies from `requirements.txt`
    - Retrieve `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET` from GitHub Secrets and set as environment variables
    - Execute the pipeline via `python src/pipeline.py` (or `python -m src.pipeline`)
    - Ensure that if any pipeline stage fails, the workflow reports failure in the Actions run log and stops subsequent stages
    - _Requirements: 14.1, 14.2, 14.3, 14.4_

- [x] 12. Final checkpoint
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- The design uses Python with Spotipy, Pandas, SQLite, boto3, and Streamlit
- Audio features and artists tables use upsert (INSERT OR REPLACE); charts table appends new rows
